-- Migration 009: PostgreSQL Full-Text Search (Stage 10g)
-- Implements Section 6.10: Unified search across findings/opportunities, blueprints, and queries.

-- 1. Create queries table for search query records and performance metrics
CREATE TABLE IF NOT EXISTS queries (
    id VARCHAR(128) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    run_id VARCHAR(64) NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    site_id VARCHAR(64) NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    page_url TEXT,
    clicks INTEGER DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    ctr NUMERIC(6,4) DEFAULT 0.0,
    position NUMERIC(6,2) DEFAULT 0.0,
    intent VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_queries_run_query_page UNIQUE (run_id, query, page_url)
);

CREATE INDEX IF NOT EXISTS idx_queries_org_id ON queries(org_id);
CREATE INDEX IF NOT EXISTS idx_queries_site_id ON queries(site_id);
CREATE INDEX IF NOT EXISTS idx_queries_run_id ON queries(run_id);

-- 2. Add title column to blueprints if not present
ALTER TABLE blueprints ADD COLUMN IF NOT EXISTS title TEXT;

-- 3. Add generated tsvector columns and GIN indexes

-- Queries FTS
ALTER TABLE queries ADD COLUMN IF NOT EXISTS search_vector tsvector
GENERATED ALWAYS AS (
    to_tsvector('english', coalesce(query, '') || ' ' || coalesce(page_url, '') || ' ' || coalesce(intent, ''))
) STORED;
CREATE INDEX IF NOT EXISTS idx_queries_search_vector ON queries USING GIN(search_vector);

-- Findings FTS
ALTER TABLE findings ADD COLUMN IF NOT EXISTS search_vector tsvector
GENERATED ALWAYS AS (
    to_tsvector('english', coalesce(subject, '') || ' ' || coalesce(message, '') || ' ' || coalesce(recommended_action, '') || ' ' || coalesce(rule_id, '') || ' ' || coalesce(url, ''))
) STORED;
CREATE INDEX IF NOT EXISTS idx_findings_search_vector ON findings USING GIN(search_vector);

-- Opportunities FTS
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS search_vector tsvector
GENERATED ALWAYS AS (
    to_tsvector('english', coalesce(display_id, '') || ' ' || coalesce(type, '') || ' ' || coalesce(tier, '') || ' ' || coalesce(observation, '') || ' ' || coalesce(diagnosis, '') || ' ' || coalesce(hypothesis, '') || ' ' || coalesce(action, '') || ' ' || coalesce(implementation_location, ''))
) STORED;
CREATE INDEX IF NOT EXISTS idx_opportunities_search_vector ON opportunities USING GIN(search_vector);

-- Blueprints FTS
ALTER TABLE blueprints ADD COLUMN IF NOT EXISTS search_vector tsvector
GENERATED ALWAYS AS (
    to_tsvector('english', coalesce(url, '') || ' ' || coalesce(page_ref, '') || ' ' || coalesce(title, '') || ' ' || coalesce(artifact_path, ''))
) STORED;
CREATE INDEX IF NOT EXISTS idx_blueprints_search_vector ON blueprints USING GIN(search_vector);
