"""
SEOJEV API Configuration Settings.
"""
import os

JWT_SECRET = os.environ.get("JWT_SECRET", "seojev_jwt_secret_development_change_in_prod_2026")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", 60 * 24))

DEFAULT_DB_URL = os.environ.get("DATABASE_URL", "postgresql:///seojev_test")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# S3 / MinIO Object Storage Configuration
S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL", "http://127.0.0.1:9000")
S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY", "minioadmin")
S3_BUCKET = os.environ.get("S3_BUCKET", "seojev-artifacts")
S3_REGION = os.environ.get("S3_REGION", "us-east-1")
