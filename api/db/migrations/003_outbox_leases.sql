ALTER TABLE outbox ADD COLUMN event_id TEXT;
ALTER TABLE outbox ADD COLUMN routing_key TEXT;
ALTER TABLE outbox ADD COLUMN lease_owner TEXT;
ALTER TABLE outbox ADD COLUMN lease_token TEXT;
ALTER TABLE outbox ADD COLUMN lease_expires_at INTEGER;
ALTER TABLE outbox ADD COLUMN next_attempt_at INTEGER DEFAULT 0;
ALTER TABLE outbox ADD COLUMN max_attempts INTEGER NOT NULL DEFAULT 10;

CREATE UNIQUE INDEX IF NOT EXISTS idx_outbox_event_id ON outbox(event_id);
CREATE INDEX IF NOT EXISTS idx_outbox_claim ON outbox(status, next_attempt_at, lease_expires_at);
