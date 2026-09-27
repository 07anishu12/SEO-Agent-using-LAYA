-- SEOJEV Stage 8: Work Orders Columns & Verifications Ledger

ALTER TABLE work_orders ADD COLUMN IF NOT EXISTS acceptance_criteria TEXT;
ALTER TABLE work_orders ADD COLUMN IF NOT EXISTS evidence_json JSONB DEFAULT '{}';
ALTER TABLE work_orders ADD COLUMN IF NOT EXISTS file_locations_json JSONB DEFAULT '[]';

CREATE TABLE IF NOT EXISTS verifications (
    id VARCHAR(128) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    run_id VARCHAR(64) NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    work_order_id VARCHAR(128) NOT NULL,
    status VARCHAR(50) NOT NULL,
    spec TEXT,
    target_url TEXT,
    details TEXT,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_verifications_org_id ON verifications(org_id);
CREATE INDEX IF NOT EXISTS idx_verifications_run_id ON verifications(run_id);
CREATE INDEX IF NOT EXISTS idx_verifications_wo_id ON verifications(work_order_id);
