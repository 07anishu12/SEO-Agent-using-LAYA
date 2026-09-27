-- Migration 002: Artifacts & S3 Object Storage Ledger
CREATE TABLE IF NOT EXISTS artifacts (
    id VARCHAR(128) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    site_id VARCHAR(64) NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    run_id VARCHAR(64) NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    artifact_type VARCHAR(50) NOT NULL,
    s3_key TEXT NOT NULL,
    size_bytes BIGINT NOT NULL DEFAULT 0,
    checksum_sha256 VARCHAR(64),
    content_type VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_artifacts_run_filename UNIQUE (run_id, filename)
);

CREATE INDEX IF NOT EXISTS idx_artifacts_org_id ON artifacts(org_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_run_id ON artifacts(run_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(artifact_type);
