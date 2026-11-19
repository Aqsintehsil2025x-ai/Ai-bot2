CREATE TABLE IF NOT EXISTS interaction_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  interaction_id TEXT UNIQUE,
  command_name TEXT NOT NULL,
  guild_id TEXT,
  user_id TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_interaction_audit_guild_created
  ON interaction_audit (guild_id, created_at);
