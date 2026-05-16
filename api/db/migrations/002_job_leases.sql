ALTER TABLE jobs ADD COLUMN lease_token TEXT;
ALTER TABLE jobs ADD COLUMN lease_heartbeat_at INTEGER;
ALTER TABLE jobs ADD COLUMN lease_expires_at INTEGER;
ALTER TABLE jobs ADD COLUMN max_attempts INTEGER NOT NULL DEFAULT 25;

CREATE INDEX IF NOT EXISTS idx_jobs_claim
ON jobs(status, lease_expires_at, retry_count);
