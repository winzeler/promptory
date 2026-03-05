-- Migration 003: Provider configurations for per-app/user credentials
-- Secrets are Fernet-encrypted at rest and NEVER synced to GitHub.

CREATE TABLE IF NOT EXISTS provider_configs (
    id TEXT PRIMARY KEY,
    scope TEXT NOT NULL CHECK (scope IN ('user', 'app')),
    scope_id TEXT NOT NULL,          -- users.id or applications.id
    provider TEXT NOT NULL,          -- 'elevenlabs', 'openai', 'anthropic', 'google'
    environment TEXT DEFAULT NULL,   -- NULL = all envs, or 'development'/'staging'/'production'
    config_json TEXT DEFAULT '{}',   -- non-secret settings (default voice, model prefs)
    secrets_encrypted TEXT,          -- Fernet-encrypted JSON: {"api_key": "sk-..."}
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(scope, scope_id, provider, environment)
);

CREATE INDEX IF NOT EXISTS idx_provider_configs_scope
    ON provider_configs(scope, scope_id);
CREATE INDEX IF NOT EXISTS idx_provider_configs_env
    ON provider_configs(scope, scope_id, provider, environment);

-- Add model/provider preference columns to applications
-- allowed_models: JSON array of model strings the app can use
-- default_providers: JSON object mapping provider name to preference config
ALTER TABLE applications ADD COLUMN allowed_models TEXT DEFAULT NULL;
ALTER TABLE applications ADD COLUMN default_providers TEXT DEFAULT NULL;

INSERT OR IGNORE INTO schema_version (version, applied_at) VALUES (3, datetime('now'));
