-- SEOJEV Stage 10a: Historical Trends Schema

CREATE TABLE IF NOT EXISTS site_trends (
    id VARCHAR(128) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    site_id VARCHAR(64) NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    run_id VARCHAR(64) REFERENCES runs(id) ON DELETE CASCADE,
    metric VARCHAR(64) NOT NULL,
    date DATE NOT NULL,
    value NUMERIC NOT NULL,
    metadata_json JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_site_metric_run UNIQUE (org_id, site_id, metric, run_id)
);

CREATE INDEX IF NOT EXISTS idx_site_trends_lookup ON site_trends(org_id, site_id, metric, date ASC);
CREATE INDEX IF NOT EXISTS idx_site_trends_date ON site_trends(org_id, date ASC);
