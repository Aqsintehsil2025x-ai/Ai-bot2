CREATE TABLE IF NOT EXISTS guild_join_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  guild_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_guild_join_events_guild_created ON guild_join_events(guild_id, created_at);
