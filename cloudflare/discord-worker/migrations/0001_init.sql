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

CREATE TABLE IF NOT EXISTS knowledge_base (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  guild_id TEXT NOT NULL,
  question TEXT NOT NULL,
  normalized_question TEXT NOT NULL,
  answer TEXT NOT NULL,
  created_by TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(guild_id, normalized_question)
);

CREATE INDEX IF NOT EXISTS idx_knowledge_base_guild
  ON knowledge_base (guild_id);
