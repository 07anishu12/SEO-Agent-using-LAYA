"""
SEOJEV S3 / MinIO Object Storage Service.
Manages artifact uploads, metadata ledger synchronization, direct presigned URL generation,
and bundle export zip archiving.
"""
import hashlib
import io
import mimetypes
import os
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from api.config import (
    S3_ENDPOINT_URL,
    S3_ACCESS_KEY,
    S3_SECRET_KEY,
    S3_BUCKET,
    S3_REGION
)
from database.connection import get_connection

# Initialize known MIME types
mimetypes.add_type("application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx")
mimetypes.add_type("text/csv", ".csv")
mimetypes.add_type("application/json", ".json")
mimetypes.add_type("text/html", ".html")
mimetypes.add_type("application/zip", ".zip")


def compute_sha256(file_path: str) -> str:
    """Computes SHA-256 hash of a file on disk."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_sha256_bytes(data: bytes) -> str:
    """Computes SHA-256 hash of in-memory bytes."""
    return hashlib.sha256(data).hexdigest()


class ObjectStorageService:
    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket: Optional[str] = None,
        region: Optional[str] = None
    ):
        self.endpoint_url = endpoint_url or S3_ENDPOINT_URL
        self.access_key = access_key or S3_ACCESS_KEY
        self.secret_key = secret_key or S3_SECRET_KEY
        self.bucket = bucket or S3_BUCKET
        self.region = region or S3_REGION
        self._client = None

        env = (os.environ.get("ENV") or os.environ.get("ENVIRONMENT") or "development").lower()
        if env in ("production", "prod"):
            if self.access_key == "minioadmin" or self.secret_key == "minioadmin":
                raise RuntimeError("CRITICAL SECURITY ERROR: Cannot use default minioadmin credentials in production object storage.")

    def check_health(self) -> dict:
        """Verifies S3 bucket accessibility."""
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return {"status": "ok", "healthy": True, "bucket": self.bucket, "endpoint": self.endpoint_url}
        except Exception as e:
            return {"status": "error", "healthy": False, "error": str(e), "bucket": self.bucket}

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
                config=Config(
                    signature_version="s3v4",
                    s3={"addressing_style": "path"}
                )
            )
        return self._client

    def ensure_bucket_exists(self):
        """Ensures target S3 bucket exists, creating it if needed."""
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code in ("404", "NoSuchBucket"):
                kwargs = {"Bucket": self.bucket}
                if self.region != "us-east-1":
                    kwargs["CreateBucketConfiguration"] = {"LocationConstraint": self.region}
                self.client.create_bucket(**kwargs)
            else:
                # Attempt creation anyway if head_bucket failed due to credentials/permissions
                try:
                    self.client.create_bucket(Bucket=self.bucket)
                except Exception:
                    pass

    def upload_file(
        self,
        local_path: str,
        s3_key: str,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Uploads a local file to S3 with metadata and SHA-256 checksum."""
        self.ensure_bucket_exists()
        size_bytes = os.path.getsize(local_path)
        sha256 = compute_sha256(local_path)

        if not content_type:
            content_type, _ = mimetypes.guess_type(local_path)
            content_type = content_type or "application/octet-stream"

        with open(local_path, "rb") as f:
            self.client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=f,
                ContentType=content_type,
                Metadata={"sha256": sha256}
            )

        return {
            "s3_key": s3_key,
            "size_bytes": size_bytes,
            "checksum_sha256": sha256,
            "content_type": content_type
        }

    def upload_bytes(
        self,
        data: bytes,
        s3_key: str,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Uploads raw bytes to S3 with metadata and SHA-256 checksum."""
        self.ensure_bucket_exists()
        size_bytes = len(data)
        sha256 = compute_sha256_bytes(data)

        if not content_type:
            content_type = "application/octet-stream"

        self.client.put_object(
            Bucket=self.bucket,
            Key=s3_key,
            Body=data,
            ContentType=content_type,
            Metadata={"sha256": sha256}
        )

        return {
            "s3_key": s3_key,
            "size_bytes": size_bytes,
            "checksum_sha256": sha256,
            "content_type": content_type
        }

    def generate_presigned_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """
        Generates a direct, signed, time-limited GET URL for the object.
        The API server returns this URL so clients fetch bytes directly from storage.
        """
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": s3_key},
            ExpiresIn=expires_in
        )

    def get_object_bytes(self, s3_key: str) -> bytes:
        """Fetches raw object bytes directly from S3."""
        res = self.client.get_object(Bucket=self.bucket, Key=s3_key)
        return res["Body"].read()

    def upload_run_artifacts(
        self,
        org_id: str,
        site_id: str,
        run_id: str,
        output_dir: str
    ) -> List[Dict[str, Any]]:
        """
        Recursively scans the engine output directory and uploads all artifacts
        (DOCX, CSVs, HTML explorer, ticket JSON/CSVs, summaries) to S3 under
        org_id/site_id/run_id/ and records them in the Postgres artifacts ledger.
        """
        if not os.path.exists(output_dir):
            return []

        self.ensure_bucket_exists()
        uploaded_records = []

        for root, _, files in os.walk(output_dir):
            for file_name in files:
                if file_name.startswith(".") or file_name.endswith(".tmp"):
                    continue

                full_path = os.path.join(root, file_name)
                rel_path = os.path.relpath(full_path, output_dir)
                clean_rel_path = os.path.normpath(rel_path).replace("\\", "/")
                if ".." in clean_rel_path or clean_rel_path.startswith("/"):
                    continue

                ext = os.path.splitext(file_name)[1].lower()

                # Determine artifact type
                if ext == ".docx":
                    artifact_type = "docx"
                elif ext == ".csv":
                    artifact_type = "csv"
                elif ext in (".html", ".htm"):
                    artifact_type = "html"
                elif ext == ".json":
                    artifact_type = "json"
                elif ext == ".zip":
                    artifact_type = "zip"
                else:
                    artifact_type = ext.lstrip(".") or "file"

                # Path keyed strictly by org_id/site_id/run_id/{clean_rel_path}
                s3_key = f"{org_id}/{site_id}/{run_id}/{clean_rel_path}"

                meta = self.upload_file(full_path, s3_key)
                artifact_id = f"art_{hashlib.sha256(f'{run_id}:{clean_rel_path}'.encode()).hexdigest()[:16]}"

                # Synchronize with PostgreSQL artifacts ledger
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO artifacts (
                                id, org_id, site_id, run_id, filename, artifact_type,
                                s3_key, size_bytes, checksum_sha256, content_type
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (run_id, filename) DO UPDATE SET
                                s3_key = EXCLUDED.s3_key,
                                size_bytes = EXCLUDED.size_bytes,
                                checksum_sha256 = EXCLUDED.checksum_sha256,
                                content_type = EXCLUDED.content_type
                            RETURNING id, org_id, site_id, run_id, filename, artifact_type,
                                      s3_key, size_bytes, checksum_sha256, content_type, created_at;
                            """,
                            (
                                artifact_id,
                                org_id,
                                site_id,
                                run_id,
                                rel_path,
                                artifact_type,
                                s3_key,
                                meta["size_bytes"],
                                meta["checksum_sha256"],
                                meta["content_type"]
                            )
                        )
                        row = cur.fetchone()
                    conn.commit()

                uploaded_records.append(dict(row))

        return uploaded_records

    def create_and_upload_export_zip(
        self,
        org_id: str,
        site_id: str,
        run_id: str,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Bundles every artifact for that run into a single zip, uploads it to S3,
        synchronizes with the artifacts table, and returns a signed download URL.
        """
        self.ensure_bucket_exists()
        zip_buffer = io.BytesIO()

        # If output_dir exists locally, pack files directly from disk
        if output_dir and os.path.exists(output_dir):
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, _, files in os.walk(output_dir):
                    for file_name in files:
                        if file_name.startswith(".") or file_name.endswith(".tmp") or file_name == "export.zip":
                            continue
                        full_path = os.path.join(root, file_name)
                        rel_path = os.path.relpath(full_path, output_dir)
                        clean_arcname = os.path.normpath(rel_path).replace("\\", "/")
                        if ".." in clean_arcname or clean_arcname.startswith("/"):
                            continue
                        zf.write(full_path, arcname=clean_arcname)
        else:
            # Fall back to packing objects directly from S3 using artifacts ledger
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT filename, s3_key FROM artifacts WHERE run_id = %s AND org_id = %s AND filename != 'export.zip'",
                        (run_id, org_id)
                    )
                    items = cur.fetchall()

            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for item in items:
                    clean_arcname = os.path.normpath(item["filename"]).replace("\\", "/")
                    if ".." in clean_arcname or clean_arcname.startswith("/"):
                        continue
                    raw_bytes = self.get_object_bytes(item["s3_key"])
                    zf.writestr(clean_arcname, raw_bytes)

        zip_data = zip_buffer.getvalue()
        zip_key = f"{org_id}/{site_id}/{run_id}/export.zip"
        meta = self.upload_bytes(zip_data, zip_key, content_type="application/zip")

        artifact_id = f"art_{hashlib.sha256(f'{run_id}:export.zip'.encode()).hexdigest()[:16]}"

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO artifacts (
                        id, org_id, site_id, run_id, filename, artifact_type,
                        s3_key, size_bytes, checksum_sha256, content_type
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (run_id, filename) DO UPDATE SET
                        s3_key = EXCLUDED.s3_key,
                        size_bytes = EXCLUDED.size_bytes,
                        checksum_sha256 = EXCLUDED.checksum_sha256,
                        content_type = EXCLUDED.content_type
                    RETURNING id, org_id, site_id, run_id, filename, artifact_type,
                              s3_key, size_bytes, checksum_sha256, content_type, created_at;
                    """,
                    (
                        artifact_id,
                        org_id,
                        site_id,
                        run_id,
                        "export.zip",
                        "zip",
                        zip_key,
                        meta["size_bytes"],
                        meta["checksum_sha256"],
                        "application/zip"
                    )
                )
                row = cur.fetchone()
            conn.commit()

        presigned_url = self.generate_presigned_url(zip_key, expires_in=3600)
        return {
            "artifact_id": artifact_id,
            "filename": "export.zip",
            "download_url": presigned_url,
            "expires_in": 3600,
            "size_bytes": meta["size_bytes"],
            "checksum_sha256": meta["checksum_sha256"]
        }


_global_storage_service: Optional[ObjectStorageService] = None


def get_storage_service() -> ObjectStorageService:
    global _global_storage_service
    if _global_storage_service is None:
        _global_storage_service = ObjectStorageService()
    return _global_storage_service


def check_storage_health() -> dict:
    """Verifies object storage connectivity."""
    try:
        svc = get_storage_service()
        return svc.check_health()
    except Exception as e:
        return {"status": "error", "healthy": False, "error": str(e)}

