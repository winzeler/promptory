-- Migration 002: Add prompt body storage, FTS5 full-text search, webhook idempotency

-- Store prompt body in SQLite to avoid GitHub dependency on reads
ALTER TABLE prompts ADD COLUMN body TEXT;

-- FTS5 virtual table for full-text search over prompts
CREATE VIRTUAL TABLE IF NOT EXISTS prompts_fts USING fts5(
    name,
    description,
    tags,
    body,
    content='prompts',
    content_rowid='rowid'
);

-- Triggers to keep FTS index in sync with prompts table
CREATE TRIGGER IF NOT EXISTS prompts_fts_insert AFTER INSERT ON prompts BEGIN
    INSERT INTO prompts_fts(rowid, name, description, tags, body)
    VALUES (new.rowid, new.name, new.description, new.tags, new.body);
END;

CREATE TRIGGER IF NOT EXISTS prompts_fts_delete AFTER DELETE ON prompts BEGIN
    INSERT INTO prompts_fts(prompts_fts, rowid, name, description, tags, body)
    VALUES ('delete', old.rowid, old.name, old.description, old.tags, old.body);
END;

CREATE TRIGGER IF NOT EXISTS prompts_fts_update AFTER UPDATE ON prompts BEGIN
    INSERT INTO prompts_fts(prompts_fts, rowid, name, description, tags, body)
    VALUES ('delete', old.rowid, old.name, old.description, old.tags, old.body);
    INSERT INTO prompts_fts(rowid, name, description, tags, body)
    VALUES (new.rowid, new.name, new.description, new.tags, new.body);
END;

-- Webhook delivery tracking for idempotency
CREATE TABLE IF NOT EXISTS webhook_deliveries (
    delivery_id TEXT PRIMARY KEY,
    app_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    processed_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_app
    ON webhook_deliveries(app_id, processed_at);

-- Clean up old deliveries (keep 7 days) — run via periodic task
-- DELETE FROM webhook_deliveries WHERE processed_at < datetime('now', '-7 days');

INSERT OR IGNORE INTO schema_version (version) VALUES (2);
