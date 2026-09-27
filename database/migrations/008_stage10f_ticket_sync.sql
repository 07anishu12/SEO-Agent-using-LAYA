-- Migration 008: Bi-directional Ticket Sync Events Ledger (Stage 10f)

CREATE TABLE IF NOT EXISTS ticket_sync_events (
    id VARCHAR(128) PRIMARY KEY,
    org_id VARCHAR(64) NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
    work_order_id VARCHAR(128) NOT NULL REFERENCES work_orders(id) ON DELETE CASCADE,
    provider VARCHAR(32) NOT NULL, -- github, jira, linear
    external_ticket_id VARCHAR(128) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    previous_status VARCHAR(64),
    new_status VARCHAR(64),
    verification_id VARCHAR(128),
    verification_result VARCHAR(32), -- Verified, Verification failed, Skipped
    failure_reason TEXT,
    payload_json JSONB DEFAULT '{}',
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_ticket_event_idempotency UNIQUE (org_id, provider, external_ticket_id, new_status)
);

CREATE INDEX IF NOT EXISTS idx_ticket_sync_wo ON ticket_sync_events(org_id, work_order_id);
CREATE INDEX IF NOT EXISTS idx_ticket_sync_org ON ticket_sync_events(org_id, processed_at);
