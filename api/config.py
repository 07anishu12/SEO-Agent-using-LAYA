"""
SEOJEV API Configuration Settings.
"""
import os
from dotenv import load_dotenv

load_dotenv()

ENVIRONMENT = (os.environ.get("ENV") or os.environ.get("ENVIRONMENT") or "development").lower()

JWT_SECRET = os.environ.get("JWT_SECRET", "seojev_jwt_secret_development_change_in_prod_2026")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", 60 * 24))

DEFAULT_DB_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/seojev_test")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# S3 / MinIO Object Storage Configuration
S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL", "http://127.0.0.1:9000")
S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY", "minioadmin")
S3_BUCKET = os.environ.get("S3_BUCKET", "seojev-artifacts")
S3_REGION = os.environ.get("S3_REGION", "us-east-1")

# CORS Origin Configuration
CORS_ORIGINS_RAW = os.environ.get("CORS_ORIGINS", "")
if CORS_ORIGINS_RAW:
    CORS_ORIGINS = [o.strip() for o in CORS_ORIGINS_RAW.split(",") if o.strip()]
elif ENVIRONMENT in ("production", "prod"):
    # In production, require explicit CORS_ORIGINS or default to empty
    CORS_ORIGINS = []
else:
    CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]


def validate_production_secrets():
    """
    Validates that production environment variables are properly configured.
    Rejects startup immediately if any mandatory production secret is missing, default, or weak.
    """
    env = (os.environ.get("ENV") or os.environ.get("ENVIRONMENT") or ENVIRONMENT or "development").lower()
    if env not in ("production", "prod"):
        return

    errors = []
    # 1. JWT Secret Validation
    jwt_secret = os.environ.get("JWT_SECRET", JWT_SECRET)
    if not jwt_secret or jwt_secret == "seojev_jwt_secret_development_change_in_prod_2026":
        errors.append("JWT_SECRET must be explicitly set and cannot use the development default.")
    elif len(jwt_secret) < 32:
        errors.append("JWT_SECRET must be at least 32 characters long for production security.")

    # 2. Database URL Validation
    if not os.environ.get("DATABASE_URL"):
        errors.append("DATABASE_URL environment variable is required in production.")
    else:
        db_url = os.environ["DATABASE_URL"]
        if "postgres:postgres@localhost" in db_url or "postgres:postgres@127.0.0.1" in db_url:
            errors.append("DATABASE_URL cannot use default development credentials (postgres:postgres) in production.")

    # 3. Object Storage Validation
    s3_key = os.environ.get("S3_ACCESS_KEY", S3_ACCESS_KEY)
    s3_secret = os.environ.get("S3_SECRET_KEY", S3_SECRET_KEY)
    if s3_key == "minioadmin" or s3_secret == "minioadmin":
        errors.append("S3_ACCESS_KEY and S3_SECRET_KEY cannot use default development credentials (minioadmin) in production.")

    # 4. Redis URL Validation
    if not os.environ.get("REDIS_URL"):
        errors.append("REDIS_URL environment variable is required in production.")

    if errors:
        raise RuntimeError("CRITICAL PRODUCTION SECURITY ERROR:\n" + "\n".join(f" - {e}" for e in errors))


# Run validation on import
validate_production_secrets()

