"""
Artifacts Router: Direct S3 Presigned Download Links.
Guarantees the API server never proxies file bytes directly.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status

from database.scoped_query import ScopedQuery
from services.object_store import get_storage_service
from ..auth import get_current_user
from ..schemas import SignedDownloadResponse

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.get("/{id}/download", response_model=SignedDownloadResponse)
def get_artifact_signed_url(
    id: str,
    expires_in: int = Query(3600, ge=1, le=604800, description="Expiration time in seconds"),
    current_user: dict = Depends(get_current_user)
):
    """
    Returns a signed, time-limited direct URL to the artifact in object storage.
    The API server never proxies the file bytes itself.
    """
    org_id = current_user["org_id"]

    with ScopedQuery(org_id=org_id) as sq:
        artifact = sq.fetch_one("artifacts", where="id = %(id)s", params={"id": id})

    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found"
        )

    storage_service = get_storage_service()
    presigned_url = storage_service.generate_presigned_url(
        s3_key=artifact["s3_key"],
        expires_in=expires_in
    )

    return SignedDownloadResponse(
        artifact_id=artifact["id"],
        filename=artifact["filename"],
        download_url=presigned_url,
        expires_in=expires_in,
        size_bytes=artifact["size_bytes"],
        checksum_sha256=artifact["checksum_sha256"]
    )
