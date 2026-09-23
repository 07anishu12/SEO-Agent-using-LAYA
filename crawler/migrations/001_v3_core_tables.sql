-- SEOJEV V3 Core Schema Migration
-- Forward-compatible and idempotent for existing V2 databases

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    target_url TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT,
    status TEXT NOT NULL,
    config_json TEXT,
    rss_peak_mb REAL DEFAULT 0.0,
    urls_crawled INTEGER DEFAULT 0,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS fetches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    url TEXT NOT NULL,
    status_code INTEGER,
    headers_json TEXT,
    response_time REAL,
    content_hash TEXT,
    raw_store_ref TEXT,
    rendered_store_ref TEXT,
    is_rendered INTEGER DEFAULT 0,
    fetched_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_fetches_run_url ON fetches (run_id, url);

CREATE TABLE IF NOT EXISTS template_members (
    run_id TEXT NOT NULL,
    url TEXT NOT NULL,
    template_id TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    PRIMARY KEY (run_id, url)
);
CREATE INDEX IF NOT EXISTS idx_tpl_members_run ON template_members (run_id, template_id);

CREATE TABLE IF NOT EXISTS entities (
    entity_id TEXT PRIMARY KEY,
    vertical TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    canonical_name TEXT NOT NULL,
    metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS entity_aliases (
    alias TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_aliases_entity ON entity_aliases (entity_id);

CREATE TABLE IF NOT EXISTS entity_page_roles (
    run_id TEXT NOT NULL,
    url TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    role TEXT NOT NULL, -- primary, mentioned, related
    PRIMARY KEY (run_id, url, entity_id)
);

CREATE TABLE IF NOT EXISTS schema_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    url TEXT NOT NULL,
    schema_type TEXT NOT NULL,
    item_json TEXT,
    is_valid INTEGER DEFAULT 1,
    errors_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_schema_items ON schema_items (run_id, url);

CREATE TABLE IF NOT EXISTS sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    url TEXT NOT NULL,
    section_name TEXT NOT NULL,
    heading_text TEXT,
    text_snippet TEXT,
    is_structured INTEGER DEFAULT 0,
    facts_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_sections_run_url ON sections (run_id, url);

CREATE TABLE IF NOT EXISTS attributes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    url TEXT NOT NULL,
    entity_id TEXT,
    attribute_name TEXT NOT NULL,
    attribute_value TEXT,
    unit TEXT,
    source_type TEXT, -- visible, json_ld, embedded_json
    selector TEXT,
    text_span TEXT,
    confidence REAL DEFAULT 1.0
);
CREATE INDEX IF NOT EXISTS idx_attrs_run ON attributes (run_id, url, attribute_name);

CREATE TABLE IF NOT EXISTS gsc_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    query TEXT NOT NULL,
    page TEXT NOT NULL,
    clicks INTEGER DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    ctr REAL DEFAULT 0.0,
    position REAL DEFAULT 0.0,
    date TEXT,
    country TEXT,
    device TEXT,
    search_appearance TEXT
);
CREATE INDEX IF NOT EXISTS idx_gsc_page ON gsc_rows (page);
CREATE INDEX IF NOT EXISTS idx_gsc_query ON gsc_rows (query);

CREATE TABLE IF NOT EXISTS queries (
    query_id TEXT PRIMARY KEY,
    query_text TEXT NOT NULL,
    brand TEXT,
    model TEXT,
    intent TEXT,
    secondary_intents_json TEXT,
    language TEXT,
    query_template TEXT
);

CREATE TABLE IF NOT EXISTS query_clusters (
    cluster_id TEXT PRIMARY KEY,
    cluster_name TEXT NOT NULL,
    primary_entity TEXT,
    primary_intent TEXT,
    query_count INTEGER DEFAULT 0,
    total_impressions INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS query_page_map (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    query TEXT NOT NULL,
    url TEXT NOT NULL,
    verdict TEXT NOT NULL, -- CORRECT_LANDING, WRONG_LANDING, WEAK_LANDING, COMPETING_URLS, MISSING_DEDICATED_PAGE
    position REAL,
    impressions INTEGER,
    clicks INTEGER,
    ctr REAL,
    click_gap REAL,
    evidence_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_qpm_run ON query_page_map (run_id, url);

CREATE TABLE IF NOT EXISTS serp_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    features_json TEXT,
    top_urls_json TEXT
);

CREATE TABLE IF NOT EXISTS serp_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL,
    rank INTEGER NOT NULL,
    url TEXT NOT NULL,
    domain TEXT NOT NULL,
    title TEXT,
    snippet TEXT,
    format TEXT
);

CREATE TABLE IF NOT EXISTS competitor_pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    domain TEXT NOT NULL,
    target_query TEXT,
    page_type TEXT,
    attributes_covered_json TEXT,
    sections_json TEXT
);

CREATE TABLE IF NOT EXISTS ai_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    engine TEXT NOT NULL,
    date TEXT NOT NULL,
    response_snippet TEXT,
    mentioned_domains_json TEXT,
    citations_json TEXT,
    mentioned_entities_json TEXT
);

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    url TEXT,
    evidence_type TEXT NOT NULL, -- dom_selector, byte_range, gsc_row, graph_edge, sql_query
    selector TEXT,
    line_number INTEGER,
    byte_range TEXT,
    gsc_row_id INTEGER,
    edge_id INTEGER,
    query_id TEXT,
    details_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_evidence_run ON evidence (run_id, url);

CREATE TABLE IF NOT EXISTS findings (
    fingerprint TEXT PRIMARY KEY,
    display_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    scope_key TEXT NOT NULL,
    subject TEXT NOT NULL,
    claim_type TEXT NOT NULL, -- OBSERVED, DERIVED, INFERRED, HYPOTHESIS
    severity TEXT NOT NULL,
    priority TEXT NOT NULL,
    template_id TEXT,
    url TEXT,
    message TEXT NOT NULL,
    evidence_refs_json TEXT,
    recommended_action TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_findings_run ON findings (run_id, priority);
CREATE INDEX IF NOT EXISTS idx_findings_display ON findings (display_id);

CREATE TABLE IF NOT EXISTS opportunities (
    opportunity_id TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL,
    display_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    type TEXT NOT NULL, -- SITE-TECH, TPL, PAGE, QUERY, ENG, CONTENT, LINK, AEO, GEO
    observation TEXT NOT NULL,
    diagnosis TEXT NOT NULL,
    hypothesis TEXT NOT NULL,
    action TEXT NOT NULL,
    implementation_location TEXT,
    affected_templates_json TEXT,
    affected_urls_count INTEGER DEFAULT 1,
    sample_urls_json TEXT,
    opportunity_tier TEXT NOT NULL, -- High, Medium, Low
    confidence_tier TEXT NOT NULL,   -- High, Medium, Low
    effort TEXT NOT NULL,            -- S, M, L
    priority_score REAL DEFAULT 0.0,
    priority_factors_json TEXT,
    verification_spec TEXT
);
CREATE INDEX IF NOT EXISTS idx_opps_v3 ON opportunities (run_id, priority_score);

CREATE TABLE IF NOT EXISTS actions (
    action_id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    action_type TEXT NOT NULL, -- engineering, content, metadata
    file_location TEXT,
    code_snippet TEXT,
    instructions TEXT
);

CREATE TABLE IF NOT EXISTS work_orders (
    work_order_id TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL,
    display_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    order_type TEXT NOT NULL, -- engineering (SEOJEV-ENG-###), content (SEOJEV-CONTENT-###)
    priority TEXT NOT NULL,
    scope TEXT NOT NULL,
    title TEXT NOT NULL,
    problem TEXT NOT NULL,
    evidence_json TEXT,
    required_change TEXT NOT NULL,
    acceptance_criteria TEXT NOT NULL,
    verify_spec TEXT NOT NULL,
    file_locations_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_wo_run ON work_orders (run_id, display_id);

CREATE TABLE IF NOT EXISTS verifications (
    verification_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    work_order_id TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    status TEXT NOT NULL, -- PASSED, FAILED, SKIPPED
    executed_at TEXT NOT NULL,
    details_json TEXT
);

CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT,
    canonical TEXT,
    meta_robots TEXT,
    h1_text TEXT,
    status_code INTEGER,
    schema_hash TEXT,
    content_hash TEXT,
    metrics_json TEXT,
    captured_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_snapshots_url ON snapshots (url, captured_at);

CREATE TABLE IF NOT EXISTS snapshot_diffs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    before_snapshot_id TEXT NOT NULL,
    after_snapshot_id TEXT NOT NULL,
    url TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    category TEXT NOT NULL, -- FIXED, STILL_FAILING, NEW_ISSUE, IMPROVED, REGRESSED, UNCHANGED
    details_json TEXT
);

CREATE TABLE IF NOT EXISTS experiments (
    experiment_id TEXT PRIMARY KEY,
    annotation TEXT NOT NULL,
    template TEXT,
    deploy_date TEXT NOT NULL,
    pre_start TEXT,
    pre_end TEXT,
    post_start TEXT,
    post_end TEXT,
    test_urls_json TEXT,
    control_urls_json TEXT,
    result_summary_json TEXT
);

CREATE TABLE IF NOT EXISTS numeric_provenance (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    calculation_method TEXT NOT NULL,
    source_table TEXT NOT NULL,
    source_query TEXT,
    timestamp TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_num_prov ON numeric_provenance (run_id, metric_name);

CREATE TABLE IF NOT EXISTS detector_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    detector_id TEXT NOT NULL,
    precision_score REAL NOT NULL,
    recall_score REAL NOT NULL,
    sample_count INTEGER NOT NULL,
    passed_gate INTEGER DEFAULT 1,
    tested_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    url TEXT NOT NULL,
    user_action TEXT NOT NULL, -- false_positive, accepted, fixed, wontfix
    comment TEXT,
    recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_feedback_fp ON feedback (fingerprint);
