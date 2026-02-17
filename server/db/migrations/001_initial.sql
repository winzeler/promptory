-- Promptory initial schema
-- SQLite is index/cache only; GitHub is source of truth for prompt content.

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS organizations (
    id TEXT PRIMARY KEY,
    github_owner TEXT NOT NULL UNIQUE,
    display_name TEXT,
    avatar_url TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS applications (
    id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    github_repo TEXT NOT NULL,
    subdirectory TEXT DEFAULT '',
    display_name TEXT,
    default_branch TEXT DEFAULT 'main',
    webhook_id INTEGER,
    webhook_secret TEXT,
    last_synced_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(org_id, github_repo, subdirectory)
);

CREATE TABLE IF NOT EXISTS prompts (
    id TEXT PRIMARY KEY,
    app_id TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    domain TEXT,
    description TEXT,
    type TEXT DEFAULT 'chat',
    modality_input TEXT DEFAULT 'text',
    modality_output TEXT DEFAULT 'text',
    default_model TEXT,
    environment TEXT DEFAULT 'development',
    tags TEXT,
    active INTEGER DEFAULT 1,
    version TEXT,
    git_sha TEXT,
    front_matter TEXT,
    body_hash TEXT,
    last_synced_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(app_id, name)
);

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    github_id INTEGER NOT NULL UNIQUE,
    github_login TEXT NOT NULL,
    display_name TEXT,
    email TEXT,
    avatar_url TEXT,
    access_token_encrypted TEXT,
    is_admin INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS api_keys (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    key_hash TEXT NOT NULL UNIQUE,
    key_prefix TEXT NOT NULL,
    name TEXT NOT NULL,
    scopes TEXT,
    expires_at TEXT,
    revoked_at TEXT,
    last_used_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS org_memberships (
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    org_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role TEXT DEFAULT 'member',
    synced_from_github INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, org_id)
);

CREATE TABLE IF NOT EXISTS eval_runs (
    id TEXT PRIMARY KEY,
    prompt_id TEXT NOT NULL REFERENCES prompts(id) ON DELETE CASCADE,
    prompt_version TEXT,
    provider TEXT,
    model TEXT,
    status TEXT DEFAULT 'pending',
    results TEXT,
    error_message TEXT,
    cost_usd REAL,
    duration_ms INTEGER,
    triggered_by TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS prompt_access_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id TEXT NOT NULL,
    prompt_name TEXT,
    api_key_id TEXT,
    version_served TEXT,
    cache_hit INTEGER DEFAULT 0,
    response_time_ms INTEGER,
    client_ip TEXT,
    user_agent TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_prompts_app_id ON prompts(app_id);
CREATE INDEX IF NOT EXISTS idx_prompts_name ON prompts(name);
CREATE INDEX IF NOT EXISTS idx_prompts_domain ON prompts(domain);
CREATE INDEX IF NOT EXISTS idx_prompts_environment ON prompts(environment);
CREATE INDEX IF NOT EXISTS idx_prompts_active ON prompts(active);
CREATE INDEX IF NOT EXISTS idx_prompts_type ON prompts(type);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix);
CREATE INDEX IF NOT EXISTS idx_eval_runs_prompt ON eval_runs(prompt_id, created_at);
CREATE INDEX IF NOT EXISTS idx_prompt_access_log_prompt ON prompt_access_log(prompt_id, created_at);
CREATE INDEX IF NOT EXISTS idx_prompt_access_log_key ON prompt_access_log(api_key_id, created_at);

INSERT OR IGNORE INTO schema_version (version) VALUES (1);
