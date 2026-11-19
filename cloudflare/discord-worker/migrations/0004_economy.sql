CREATE TABLE IF NOT EXISTS economy_accounts (
  guild_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  balance INTEGER NOT NULL DEFAULT 0,
  xp INTEGER NOT NULL DEFAULT 0,
  level INTEGER NOT NULL DEFAULT 0,
  streak INTEGER NOT NULL DEFAULT 0,
  last_daily TEXT,
  last_work TEXT,
  last_xp TEXT,
  inventory TEXT NOT NULL DEFAULT '[]',
  updated_at TEXT NOT NULL,
  PRIMARY KEY (guild_id, user_id)
);
CREATE TABLE IF NOT EXISTS economy_transfers (
  id TEXT PRIMARY KEY,
  guild_id TEXT NOT NULL,
  sender_id TEXT NOT NULL,
  receiver_id TEXT NOT NULL,
  amount INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_economy_accounts_balance ON economy_accounts(guild_id, balance DESC);
CREATE INDEX IF NOT EXISTS idx_economy_accounts_xp ON economy_accounts(guild_id, xp DESC);
