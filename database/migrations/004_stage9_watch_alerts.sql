-- SEOJEV Stage 9: Watch / Alerts & Notifications Schema Extensions

-- 1. Extend watch_configs table
ALTER TABLE watch_configs ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'UTC';
ALTER TABLE watch_configs ADD COLUMN IF NOT EXISTS top_pages_json JSONB DEFAULT '[]';
ALTER TABLE watch_configs ADD COLUMN IF NOT EXISTS notification_channels_json JSONB DEFAULT '[]';
ALTER TABLE watch_configs ADD COLUMN IF NOT EXISTS last_run_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE watch_configs ADD COLUMN IF NOT EXISTS next_run_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE watch_configs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Unique constraint so each site has at most one watch_config per org
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_watch_configs_org_site'
    ) THEN
        ALTER TABLE watch_configs ADD CONSTRAINT uq_watch_configs_org_site UNIQUE (org_id, site_id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_watch_configs_active_next ON watch_configs(is_active, next_run_at);

-- 2. Extend alerts table
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS title VARCHAR(255);
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT 'watch';
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS fingerprint VARCHAR(64);
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS affected_urls_json JSONB DEFAULT '[]';
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS previous_value TEXT;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS current_value TEXT;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'open';
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS dispatched BOOLEAN DEFAULT FALSE;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS dispatch_status VARCHAR(50) DEFAULT 'pending';
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS dispatch_error TEXT;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_alerts_site_status ON alerts(org_id, site_id, status);
CREATE INDEX IF NOT EXISTS idx_alerts_fingerprint ON alerts(fingerprint);
CREATE INDEX IF NOT EXISTS idx_alerts_detected_at ON alerts(org_id, detected_at DESC);
