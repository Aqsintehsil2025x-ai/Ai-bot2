export interface Env {
  DB: D1Database;
  DISCORD_PUBLIC_KEY?: string;
}

type Option = { name: string; type?: number; value?: string | number | boolean; options?: Option[] };
type Interaction = {
  id?: string;
  type?: number;
  token?: string;
  application_id?: string;
  guild_id?: string;
  member?: { user?: { id?: string }; permissions?: string };
  user?: { id?: string };
  data?: { name?: string; options?: Option[] };
};

const encoder = new TextEncoder();
const EPHEMERAL = 64;
const MANAGE_GUILD = 32n;

function hexToBytes(value: string): Uint8Array {
  if (!/^[0-9a-f]{128}$/i.test(value)) throw new Error("Invalid signature encoding");
  return new Uint8Array(value.match(/.{2}/g)!.map((part) => Number.parseInt(part, 16)));
}

async function verifyDiscordRequest(request: Request, body: string, publicKey: string): Promise<boolean> {
  const signature = request.headers.get("x-signature-ed25519");
  const timestamp = request.headers.get("x-signature-timestamp");
  if (!signature || !timestamp || !/^\d{10,}$/.test(timestamp)) return false;
  const key = await crypto.subtle.importKey("raw", hexToBytes(publicKey), { name: "Ed25519" }, false, ["verify"]);
  return crypto.subtle.verify({ name: "Ed25519" }, key, hexToBytes(signature), encoder.encode(timestamp + body));
}

function json(data: unknown, status = 200): Response {
  return Response.json(data, { status, headers: { "cache-control": "no-store" } });
}

function reply(content: string, ephemeral = true): Response {
  return json({ type: 4, data: { content: content.slice(0, 1900), ...(ephemeral ? { flags: EPHEMERAL } : {}) } });
}

function option(options: Option[] | undefined, name: string): Option | undefined {
  return options?.find((item) => item.name === name);
}

function normalize(value: string): string {
  return value.normalize("NFKC").toLocaleLowerCase("tr").replace(/\s+/g, " ").trim();
}

function canManageGuild(interaction: Interaction): boolean {
  try {
    return (BigInt(interaction.member?.permissions ?? "0") & MANAGE_GUILD) === MANAGE_GUILD;
  } catch {
    return false;
  }
}

async function handleKnowledgeBase(interaction: Interaction, env: Env): Promise<Response> {
  const guildId = interaction.guild_id;
  if (!guildId) return reply("Bu komut yalnızca sunucuda kullanılabilir.");
  const sub = interaction.data?.options?.[0];
  const name = sub?.name;
  const options = sub?.options ?? [];
  const userId = interaction.member?.user?.id ?? interaction.user?.id ?? null;

  if (name === "add") {
    if (!canManageGuild(interaction)) return reply("Bu işlem için Sunucuyu Yönet yetkisi gerekiyor.");
    const question = String(option(options, "question")?.value ?? "").trim();
    const answer = String(option(options, "answer")?.value ?? "").trim();
    if (!question || question.length > 180 || !answer || answer.length > 1500) {
      return reply("Soru 1–180, yanıt 1–1500 karakter olmalıdır.");
    }
    await env.DB.prepare(`INSERT INTO knowledge_base (guild_id, question, normalized_question, answer, created_by, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(guild_id, normalized_question) DO UPDATE SET question=excluded.question, answer=excluded.answer, updated_at=excluded.updated_at`)
      .bind(guildId, question, normalize(question), answer, userId, new Date().toISOString(), new Date().toISOString()).run();
    return reply("FAQ kaydı eklendi/güncellendi.");
  }

  if (name === "ask") {
    const query = String(option(options, "query")?.value ?? "").trim();
    if (!query || query.length > 180) return reply("Arama metni 1–180 karakter olmalıdır.");
    const rows = await env.DB.prepare("SELECT question, answer FROM knowledge_base WHERE guild_id = ? ORDER BY updated_at DESC LIMIT 100")
      .bind(guildId).all<{ question: string; answer: string }>();
    const needle = normalize(query);
    const exact = rows.results.find((row) => normalize(row.question) === needle);
    const starts = exact ?? rows.results.find((row) => normalize(row.question).includes(needle) || needle.includes(normalize(row.question)));
    if (!starts) return reply("Bilgi tabanında tam/benzer bir kayıt bulamadım.");
    return reply(`**${starts.question}**\n${starts.answer}`, false);
  }

  if (name === "list") {
    if (!canManageGuild(interaction)) return reply("Bu işlem için Sunucuyu Yönet yetkisi gerekiyor.");
    const rows = await env.DB.prepare("SELECT question FROM knowledge_base WHERE guild_id = ? ORDER BY question LIMIT 25")
      .bind(guildId).all<{ question: string }>();
    return reply(rows.results.length ? rows.results.map((row, i) => `${i + 1}. ${row.question}`).join("\n") : "Bilgi tabanı boş.");
  }

  if (name === "remove") {
    if (!canManageGuild(interaction)) return reply("Bu işlem için Sunucuyu Yönet yetkisi gerekiyor.");
    const question = String(option(options, "question")?.value ?? "").trim();
    if (!question || question.length > 180) return reply("Soru 1–180 karakter olmalıdır.");
    const result = await env.DB.prepare("DELETE FROM knowledge_base WHERE guild_id = ? AND normalized_question = ?")
      .bind(guildId, normalize(question)).run();
    return reply(result.meta.changes ? "FAQ kaydı silindi." : "Bu soru için kayıt bulunamadı.");
  }
  return reply("Bilinmeyen FAQ işlemi.");
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health") {
      return json({ ok: true, service: "xfa-discord-test", runtime: "cloudflare-workers", language: "typescript" });
    }
    if (request.method !== "POST" || url.pathname !== "/discord/interactions") return json({ error: "Not found" }, 404);
    if (!env.DISCORD_PUBLIC_KEY) return json({ error: "Discord public key is not configured" }, 503);

    const body = await request.text();
    try {
      if (!(await verifyDiscordRequest(request, body, env.DISCORD_PUBLIC_KEY))) return json({ error: "Invalid request signature" }, 401);
    } catch {
      return json({ error: "Invalid request signature" }, 401);
    }

    let interaction: Interaction;
    try { interaction = JSON.parse(body) as Interaction; }
    catch { return json({ error: "Invalid JSON" }, 400); }

    if (interaction.type === 1) return json({ type: 1 });
    if (interaction.type !== 2) return json({ error: "Unsupported interaction type" }, 400);

    const command = interaction.data?.name;
    const guildId = interaction.guild_id ?? null;
    const userId = interaction.member?.user?.id ?? interaction.user?.id ?? null;
    await env.DB.prepare("INSERT OR IGNORE INTO interaction_audit (interaction_id, command_name, guild_id, user_id, created_at) VALUES (?, ?, ?, ?, ?)")
      .bind(interaction.id ?? null, command ?? "unknown", guildId, userId, new Date().toISOString()).run();

    if (command === "ping") return reply("Pong! Cloudflare TypeScript test bot is online.");
    if (command === "xfa") return reply("XFA Cloudflare test endpoint is online. TypeScript + D1 aktif.");
    if (command === "kb") return handleKnowledgeBase(interaction, env);
    return reply("Bu komut Cloudflare test sürümünde henüz taşınmadı.");
  },
};
