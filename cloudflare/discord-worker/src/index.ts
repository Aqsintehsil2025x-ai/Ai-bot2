export interface SecretStoreBinding { get(): Promise<string>; }
export interface Env {
  DB: D1Database;
  DISCORD_PUBLIC_KEY?: string;
  DISCORD_TOKEN: SecretStoreBinding;
  DISCORD_CLIENT_ID: SecretStoreBinding;
  DISCORD_CLIENT_SECRET: SecretStoreBinding;
  GEMINI_API_KEY: SecretStoreBinding;
  NVIDIA_API_KEY: SecretStoreBinding;
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

type AIProvider = "gemini" | "nvidia";
async function generateAI(env: Env, provider: AIProvider, model: string, prompt: string): Promise<string> {
  if (provider === "gemini") {
    const apiKey = await env.GEMINI_API_KEY.get();
    const endpoint = "https://generativelanguage.googleapis.com/v1beta/models/" + encodeURIComponent(model) + ":generateContent?key=" + encodeURIComponent(apiKey);
    const response = await fetch(endpoint, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ contents: [{ role: "user", parts: [{ text: prompt }] }], generationConfig: { maxOutputTokens: 900, temperature: 0.7 } }), signal: AbortSignal.timeout(25000) });
    const data = await response.json() as { candidates?: { content?: { parts?: { text?: string }[] } }[]; error?: { message?: string } };
    if (!response.ok) throw new Error(data.error?.message || "Gemini API HTTP " + response.status);
    const answer = data.candidates?.[0]?.content?.parts?.map((part) => part.text ?? "").join("").trim();
    if (!answer) throw new Error("Gemini boş yanıt döndürdü.");
    return answer.slice(0, 1850);
  }
  const apiKey = await env.NVIDIA_API_KEY.get();
  const response = await fetch("https://integrate.api.nvidia.com/v1/chat/completions", { method: "POST", headers: { authorization: "Bearer " + apiKey, "content-type": "application/json" }, body: JSON.stringify({ model, messages: [{ role: "user", content: prompt }], max_tokens: 900, temperature: 0.7, stream: false }), signal: AbortSignal.timeout(25000) });
  const data = await response.json() as { choices?: { message?: { content?: string } }[]; error?: { message?: string } };
  if (!response.ok) throw new Error(data.error?.message || "NVIDIA API HTTP " + response.status);
  const answer = data.choices?.[0]?.message?.content?.trim();
  if (!answer) throw new Error("NVIDIA boş yanıt döndürdü.");
  return answer.slice(0, 1850);
}
async function runDeferredAI(interaction: Interaction, env: Env, provider: AIProvider, model: string, prompt: string): Promise<void> {
  if (!interaction.application_id || !interaction.token) return;
  let content: string;
  try { content = await generateAI(env, provider, model, prompt); }
  catch (error) { content = "AI sağlayıcı hatası: " + (error instanceof Error ? error.message : "Bilinmeyen hata"); }
  await fetch("https://discord.com/api/v10/webhooks/" + interaction.application_id + "/" + interaction.token + "/messages/@original", { method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify({ content: content.slice(0, 1900), allowed_mentions: { parse: [] } }) });
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

function handleUtilityCommand(interaction: Interaction): Response | null {
  const name = interaction.data?.name;
  const opts = interaction.data?.options;
  const userId = interaction.member?.user?.id ?? interaction.user?.id ?? "kullanıcı";
  const mention = /^\\d+$/.test(userId) ? `<@${userId}>` : "Kullanıcı";
  if (name === "zar") {
    const raw = Number(option(opts, "max_sayi")?.value ?? 100);
    const max = Number.isInteger(raw) ? Math.min(1000000, Math.max(2, raw)) : 100;
    return reply(`🎲 ${mention} zar attı: **${Math.floor(Math.random() * max) + 1} / ${max}**`, false);
  }
  if (name === "yazitura") return reply(`🪙 ${mention}, sonuç: **${Math.random() < 0.5 ? "Yazı" : "Tura"}**!`, false);
  if (name === "kahve") {
    const coffee = String(option(opts, "kahve_turu")?.value ?? "Espresso").trim().slice(0, 40) || "Espresso";
    return reply(`☕ ${mention}, ${coffee} siparişin hazır! Afiyet olsun.`, false);
  }
  if (name === "secim") {
    const raw = String(option(opts, "secenekler")?.value ?? "");
    const choices = raw.split("|").map((item) => item.trim()).filter(Boolean);
    if (choices.length < 2 || choices.length > 10) return reply("En az 2, en fazla 10 seçeneği | işaretiyle ayırmalısın.");
    if (choices.some((item) => item.length > 100)) return reply("Her seçenek en fazla 100 karakter olabilir.");
    return reply(`🎯 Seçimim: **${choices[Math.floor(Math.random() * choices.length)]}**`, false);
  }
  if (name === "sekiztop") {
    const question = String(option(opts, "soru")?.value ?? "").trim();
    if (question.length < 3) return reply("Biraz daha açıklayıcı bir soru yaz.");
    const answers = ["Kesinlikle!", "Büyük ihtimalle evet.", "Bence evet.", "İşaretler olumlu.", "Şu an söylemek zor.", "Daha sonra tekrar sor.", "Pek sanmıyorum.", "Cevabım hayır."];
    return reply(`🎱 **${question.slice(0, 500)}**\n${answers[Math.floor(Math.random() * answers.length)]}`, false);
  }
  return null;
}
export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
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
    if (command === "xfa") {
      const prompt = String(option(interaction.data?.options, "prompt")?.value ?? "").trim();
      if (!prompt) return reply("XFA AI hazır. Komutu bir prompt ile kullan.");
      if (prompt.length > 3500) return reply("İstek en fazla 3500 karakter olabilir.");
      const providerValue = String(option(interaction.data?.options, "provider")?.value ?? "gemini");
      const provider: AIProvider = providerValue === "nvidia" ? "nvidia" : "gemini";
      const model = String(option(interaction.data?.options, "model")?.value ?? (provider === "gemini" ? "gemini-2.5-flash" : "meta/llama-3.3-70b-instruct"));
      const validModel = provider === "gemini" ? /^gemini-[a-zA-Z0-9.-]{1,80}$/.test(model) : /^[a-zA-Z0-9._/-]{1,120}$/.test(model);
      if (!validModel) return reply("Model adı geçersiz.");
      ctx.waitUntil(runDeferredAI(interaction, env, provider, model, prompt));
      return json({ type: 5, data: { flags: EPHEMERAL } });
    }
    if (command === "kb") return handleKnowledgeBase(interaction, env);
    const utilityResponse = handleUtilityCommand(interaction);
    if (utilityResponse) return utilityResponse;
    return reply("Bu komut Cloudflare test sürümünde henüz taşınmadı.");
  },
};
