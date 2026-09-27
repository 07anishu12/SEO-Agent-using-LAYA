"""
SEOJEV API Configuration Settings.
"""
import os

JWT_SECRET = os.environ.get("JWT_SECRET", "seojev_jwt_secret_development_change_in_prod_2026")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", 60 * 24))

DEFAULT_DB_URL = os.environ.get("DATABASE_URL", "postgresql:///seojev_test")
