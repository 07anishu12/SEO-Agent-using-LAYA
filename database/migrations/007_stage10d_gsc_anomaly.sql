-- Migration 007: GSC Daily Metrics for Anomaly Detection (Stage 10d)

CREATE TABLE IF NOT EXISTS gsc_daily_metrics (
    id VARCHAR(128) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    site_id VARCHAR(64) NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    page TEXT NOT NULL,
    template_id VARCHAR(64) DEFAULT 'default',
    date DATE NOT NULL,
    clicks INTEGER DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    ctr NUMERIC(6,4) DEFAULT 0.0,
    position NUMERIC(6,2) DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_gsc_daily_site_page_date UNIQUE (site_id, page, date)
);

CREATE INDEX IF NOT EXISTS idx_gsc_daily_org_site ON gsc_daily_metrics(org_id, site_id, date);
CREATE INDEX IF NOT EXISTS idx_gsc_daily_site_template ON gsc_daily_metrics(site_id, template_id, date);
