-- SEOJEV Phase 2: PostgreSQL Multi-Tenant Metadata Schema
-- Migration: 001_phase2_postgres.sql
-- Enforces row-level isolation via org_id on every table.

-- 1. Organizations
CREATE TABLE IF NOT EXISTS orgs (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Users
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(64) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'member',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_users_org_id ON users(org_id);

-- 3. API Keys
CREATE TABLE IF NOT EXISTS api_keys (
    id VARCHAR(64) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    user_id VARCHAR(64) REFERENCES users(id) ON DELETE SET NULL,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_api_keys_org_id ON api_keys(org_id);

-- 4. Sites
CREATE TABLE IF NOT EXISTS sites (
    id VARCHAR(64) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    domain VARCHAR(255) NOT NULL,
    url VARCHAR(500) NOT NULL,
    vertical VARCHAR(50) DEFAULT 'generic',
    config_json JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_sites_org_domain UNIQUE (org_id, domain)
);
CREATE INDEX IF NOT EXISTS idx_sites_org_id ON sites(org_id);

-- 5. Crawl Configurations
CREATE TABLE IF NOT EXISTS crawl_configs (
    id VARCHAR(64) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    site_id VARCHAR(64) NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    max_pages INTEGER DEFAULT 5000,
    concurrency INTEGER DEFAULT 10,
    render_enabled BOOLEAN DEFAULT FALSE,
    performance_sample INTEGER DEFAULT 100,
    delay NUMERIC(6,3) DEFAULT 0.05,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_crawl_configs_org_id ON crawl_configs(org_id);

-- 6. Runs (Audit Executions)
CREATE TABLE IF NOT EXISTS runs (
    id VARCHAR(64) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    site_id VARCHAR(64) NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'queued',
    started_at TIMESTAMP WITH TIME ZONE,
    finished_at TIMESTAMP WITH TIME ZONE,
    progress_pct NUMERIC(5,2) DEFAULT 0.0,
    current_pass VARCHAR(50),
    config_snapshot_json JSONB DEFAULT '{}',
    urls_discovered INTEGER DEFAULT 0,
    urls_crawled INTEGER DEFAULT 0,
    urls_failed INTEGER DEFAULT 0,
    total_issues INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_runs_org_id ON runs(org_id);
CREATE INDEX IF NOT EXISTS idx_runs_site_id ON runs(site_id);

-- 7. Findings
CREATE TABLE IF NOT EXISTS findings (
    id VARCHAR(128) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    run_id VARCHAR(64) NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    site_id VARCHAR(64) NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    display_id VARCHAR(64),
    rule_id VARCHAR(100),
    scope_key VARCHAR(50),
    subject TEXT,
    claim_type VARCHAR(50) DEFAULT 'OBSERVED',
    severity VARCHAR(50),
    priority VARCHAR(50),
    template_id VARCHAR(100),
    url TEXT,
    message TEXT,
    evidence_refs JSONB DEFAULT '[]',
    recommended_action TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_findings_org_id ON findings(org_id);
CREATE INDEX IF NOT EXISTS idx_findings_run_id ON findings(run_id);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(org_id, severity);

-- 8. Opportunities (Multi-Factor ICE Prioritized)
CREATE TABLE IF NOT EXISTS opportunities (
    id VARCHAR(128) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    run_id VARCHAR(64) NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    site_id VARCHAR(64) NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    fingerprint VARCHAR(128) NOT NULL,
    display_id VARCHAR(64) NOT NULL,
    type VARCHAR(50),
    tier VARCHAR(50),
    confidence VARCHAR(50),
    effort VARCHAR(50),
    priority_score NUMERIC(6,2),
    factors_json JSONB DEFAULT '{}',
    evidence_refs JSONB DEFAULT '[]',
    observation TEXT,
    diagnosis TEXT,
    hypothesis TEXT,
    action TEXT,
    implementation_location TEXT,
    affected_templates JSONB DEFAULT '[]',
    affected_urls_count INTEGER DEFAULT 0,
    sample_urls JSONB DEFAULT '[]',
    verification_spec TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_opps_org_id ON opportunities(org_id);
CREATE INDEX IF NOT EXISTS idx_opps_run_id ON opportunities(run_id);
CREATE INDEX IF NOT EXISTS idx_opps_tier ON opportunities(org_id, tier);

-- 9. Work Orders (Actionable Developer Tasks)
CREATE TABLE IF NOT EXISTS work_orders (
    id VARCHAR(128) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    run_id VARCHAR(64) NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    site_id VARCHAR(64) NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    opportunity_id VARCHAR(128),
    display_id VARCHAR(64) NOT NULL,
    title TEXT NOT NULL,
    order_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'open',
    priority VARCHAR(50),
    scope VARCHAR(50),
    problem TEXT,
    required_change TEXT,
    verify_spec TEXT,
    ticket_ref VARCHAR(100),
    verify_last_result VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_work_orders_org_id ON work_orders(org_id);
CREATE INDEX IF NOT EXISTS idx_work_orders_run_id ON work_orders(run_id);

-- 10. Blueprints (Path References)
CREATE TABLE IF NOT EXISTS blueprints (
    id VARCHAR(128) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    run_id VARCHAR(64) NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    site_id VARCHAR(64) NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    page_ref TEXT NOT NULL,
    artifact_path TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_blueprints_org_id ON blueprints(org_id);

-- 11. Templates
CREATE TABLE IF NOT EXISTS templates (
    id VARCHAR(128) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    run_id VARCHAR(64) NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    site_id VARCHAR(64) NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    template_id VARCHAR(100) NOT NULL,
    page_type VARCHAR(50),
    page_count INTEGER DEFAULT 0,
    avg_word_count NUMERIC(8,2),
    avg_inlinks NUMERIC(8,2),
    structural_signature TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_templates_org_id ON templates(org_id);

-- 12. GSC Summary
CREATE TABLE IF NOT EXISTS gsc_summary (
    id VARCHAR(128) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    run_id VARCHAR(64) NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    site_id VARCHAR(64) NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    total_queries INTEGER DEFAULT 0,
    total_clicks INTEGER DEFAULT 0,
    total_impressions INTEGER DEFAULT 0,
    avg_position NUMERIC(6,2),
    striking_distance_count INTEGER DEFAULT 0,
    data_json JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_gsc_summary_org_id ON gsc_summary(org_id);

-- 13. Snapshots
CREATE TABLE IF NOT EXISTS snapshots (
    id VARCHAR(128) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    run_id VARCHAR(64) NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    site_id VARCHAR(64) NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    snapshot_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_snapshots_org_id ON snapshots(org_id);

-- 14. Snapshot Diffs
CREATE TABLE IF NOT EXISTS snapshot_diffs (
    id VARCHAR(128) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    site_id VARCHAR(64) NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    before_run_id VARCHAR(64) NOT NULL,
    after_run_id VARCHAR(64) NOT NULL,
    diff_summary_json JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_snapshot_diffs_org_id ON snapshot_diffs(org_id);

-- 15. Watch Configurations
CREATE TABLE IF NOT EXISTS watch_configs (
    id VARCHAR(128) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    site_id VARCHAR(64) NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    cron_expression VARCHAR(50) DEFAULT '0 0 * * *',
    is_active BOOLEAN DEFAULT TRUE,
    checks_json JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_watch_configs_org_id ON watch_configs(org_id);

-- 16. Alerts
CREATE TABLE IF NOT EXISTS alerts (
    id VARCHAR(128) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    site_id VARCHAR(64) NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    run_id VARCHAR(64),
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    payload_json JSONB DEFAULT '{}',
    is_resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_alerts_org_id ON alerts(org_id);

-- 17. Feedback
CREATE TABLE IF NOT EXISTS feedback (
    id VARCHAR(128) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    finding_fingerprint VARCHAR(128) NOT NULL,
    verdict VARCHAR(50) NOT NULL,
    user_id VARCHAR(64),
    note TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_feedback_org_id ON feedback(org_id);

-- 18. Audit Log
CREATE TABLE IF NOT EXISTS audit_log (
    id VARCHAR(128) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    user_id VARCHAR(64),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(128),
    details_json JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_audit_log_org_id ON audit_log(org_id);
