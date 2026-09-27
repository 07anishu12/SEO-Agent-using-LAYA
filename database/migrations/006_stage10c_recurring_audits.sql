-- SEOJEV Stage 10c: Scheduled Recurring Audits Extensions

ALTER TABLE watch_configs ADD COLUMN IF NOT EXISTS audit_config_json JSONB DEFAULT '{"max_pages": 15, "fresh": true}';
CREATE INDEX IF NOT EXISTS idx_runs_site_status ON runs(org_id, site_id, status);
