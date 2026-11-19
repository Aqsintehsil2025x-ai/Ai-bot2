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
  const mention = /^\d+$/.test(userId) ? `<@${userId}>` : "Kullanıcı";
  if (name === "kimlik") {
    return reply("🪪 Discord kullanıcı ID'n: `" + userId + "`", true);
  }
  if (name === "yardim") {
    return reply("**Cloudflare test komutları**\n/ping • /xfa • /sor • /kb\n/zar • /yazitura • /kahve • /secim • /sekiztop\nKomutlar taşındıkça bu liste genişletilecek.", true);
  }
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

const REST_PERMS = { manageChannels:16n, kick:2n, ban:4n, manageRoles:268435456n, manageMessages:8192n, moderate:1099511627776n, manageNicknames:67108864n, administrator:8n };
function hasPermission(interaction, bit) {
  try { const p=BigInt(interaction.member?.permissions ?? "0"); return (p & REST_PERMS.administrator) !== 0n || (p & bit) === bit; }
  catch { return false; }
}
async function discordApi(env, path, method="GET", body) {
  const token = await env.DISCORD_TOKEN.get();
  const response = await fetch("https://discord.com/api/v10"+path, {
    method, headers:{authorization:"Bot "+token,"content-type":"application/json"},
    ...(body === undefined ? {} : {body:JSON.stringify(body)}), signal:AbortSignal.timeout(12000)
  });
  const raw=await response.text(); let data=null; try { data=raw?JSON.parse(raw):null; } catch {}
  if(!response.ok) throw new Error(data?.message || "Discord API HTTP "+response.status);
  return data;
}
async function handleMoreCommands(i, env) {
  const name=i.data?.name, opts=i.data?.options || [], guild=i.guild_id, channel=i.channel_id;
  const selected=String(option(opts,"member")?.value || i.member?.user?.id || i.user?.id || "");
  const require=(bit,label)=>hasPermission(i,bit)?null:reply("Bu işlem için "+label+" yetkisi gerekiyor.");
  try {
    if(name==="kullanici" || name==="avatar") {
      const u=await discordApi(env,"/users/"+selected);
      const avatar=u.avatar ? "https://cdn.discordapp.com/avatars/"+u.id+"/"+u.avatar+"."+(u.avatar.startsWith("a_")?"gif":"png")+"?size=1024" : "https://cdn.discordapp.com/embed/avatars/0.png";
      if(name==="avatar") return reply("🖼️ "+avatar,false);
      return reply("**Kullanıcı bilgisi**\nAd: "+(u.global_name||u.username)+"\nID: "+u.id+"\nBot: "+(u.bot?"Evet":"Hayır")+"\nAvatar: "+avatar,false);
    }
    if(name==="sunucu" || name==="rapor") {
      if(!guild) return reply("Bu komut yalnızca sunucuda kullanılabilir.");
      const x=await discordApi(env,"/guilds/"+guild+"?with_counts=true");
      const row=await env.DB.prepare("SELECT COUNT(*) AS total FROM interaction_audit WHERE guild_id=? AND created_at>=?").bind(guild,new Date(Date.now()-604800000).toISOString()).first();
      return reply("**"+x.name+"**\nID: "+x.id+"\nÜye: **"+(x.approximate_member_count||x.member_count||"—")+"**\nSon 7 gün Worker komutu: **"+(row?.total||0)+"**",false);
    }
    if(name==="gemini" || name==="nvidia") {
      if(!guild)return reply("Bu komut yalnızca sunucuda kullanılabilir.");
      if(!hasPermission(i,32n))return reply("Sunucuyu Yönet yetkisi gerekiyor.");
      await env.DB.prepare("INSERT INTO guild_settings(guild_id,setting_key,value,updated_at) VALUES(?,?,?,?) ON CONFLICT(guild_id,setting_key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at").bind(guild,"ai_provider",name,new Date().toISOString()).run();
      return reply("Bu sunucunun XFA sağlayıcısı "+name.toUpperCase()+" olarak ayarlandı.");
    }
    if(name==="ship") {
      const a=i.member?.user?.id||i.user?.id||"", b=String(option(opts,"member")?.value||a);
      const seed=(a+b+new Date().toISOString().slice(0,10)).split("").reduce((v,c)=>((v*31+c.charCodeAt(0))>>>0),7);
      return reply("💞 <@"+a+"> + <@"+b+">\nGünlük uyum puanı: **"+(seed%101)+"%**",false);
    }
    if(name==="kilitle" || name==="kilita") {
      const p=require(REST_PERMS.manageChannels,"Kanalları Yönet"); if(p)return p;
      const channelData=await discordApi(env,"/channels/"+channel);
      const everyone=String(guild), old=(channelData.permission_overwrites||[]).find(x=>x.id===everyone)||{id:everyone,type:0,allow:"0",deny:"0"};
      const send=2048n, allow=BigInt(old.allow||"0"), deny=BigInt(old.deny||"0");
      const next={...old,allow:(name==="kilita"?(allow|send):(allow&~send)).toString(),deny:(name==="kilitle"?(deny|send):(deny&~send)).toString()};
      const overwrites=(channelData.permission_overwrites||[]).filter(x=>x.id!==everyone); overwrites.push(next);
      await discordApi(env,"/channels/"+channel,"PATCH",{permission_overwrites:overwrites});
      return reply(name==="kilitle"?"Kanal kilitlendi.":"Kanal kilidi açıldı.");
    }
    if(name==="kanalolustur") {
      const p=require(REST_PERMS.manageChannels,"Kanalları Yönet"); if(p)return p;
      const channelName=String(option(opts,"kanal_adi")?.value||"").toLowerCase().replace(/[^a-z0-9-]/g,"-").slice(0,90);
      if(!channelName)return reply("Geçerli kanal adı gir.");
      const created=await discordApi(env,"/guilds/"+guild+"/channels","POST",{name:channelName,type:0});
      return reply("Kanal oluşturuldu: <#"+created.id+">");
    }
    if(name==="rololustur") {
      const p=require(REST_PERMS.manageRoles,"Rolleri Yönet"); if(p)return p;
      const roleName=String(option(opts,"rol_adi")?.value||"").trim().slice(0,100);
      if(!roleName)return reply("Rol adı gir.");
      const created=await discordApi(env,"/guilds/"+guild+"/roles","POST",{name:roleName,permissions:"0",mentionable:false,hoist:false});
      return reply("Rol oluşturuldu: <@&"+created.id+">");
    }
    if(name==="oneri") {
      const text=String(option(opts,"metin")?.value||"").trim();
      if(!text||text.length>1500) return reply("Öneri 1–1500 karakter olmalı.");
      await env.DB.prepare("INSERT INTO suggestions(guild_id,user_id,content,created_at) VALUES(?,?,?,?)").bind(guild||"dm",i.member?.user?.id||i.user?.id||"",text,new Date().toISOString()).run();
      return reply("💡 Önerin kaydedildi. Teşekkürler!");
    }
    if(name==="analytics") {
      const p=require(32n,"Sunucuyu Yönet"); if(p)return p;
      const row=await env.DB.prepare("SELECT COUNT(*) AS total FROM interaction_audit WHERE guild_id=? AND created_at>=?").bind(guild,new Date(Date.now()-604800000).toISOString()).first();
      return reply("📊 Son 7 günde Worker üzerinden **"+(row?.total||0)+"** komut kullanıldı. Bu rapor mesaj trafiğini veya Gateway olaylarını içermez.");
    }
    if(name==="kick") {
      const p=require(REST_PERMS.kick,"Üyeleri At"); if(p)return p;
      await discordApi(env,"/guilds/"+guild+"/members/"+selected,"DELETE");
      return reply("Üye sunucudan atıldı.");
    }
    if(name==="ban") {
      const p=require(REST_PERMS.ban,"Üyeleri Yasakla"); if(p)return p;
      const days=Math.max(0,Math.min(7,Number(option(opts,"sil_gun")?.value||0)));
      await discordApi(env,"/guilds/"+guild+"/bans/"+selected,"PUT",{delete_message_seconds:days*86400});
      return reply("Üye yasaklandı.");
    }
    if(name==="unban") {
      const p=require(REST_PERMS.ban,"Üyeleri Yasakla"); if(p)return p;
      const id=String(option(opts,"user_id")?.value||"");
      if(!/^\d{15,22}$/.test(id))return reply("Geçerli kullanıcı ID'si gir.");
      await discordApi(env,"/guilds/"+guild+"/bans/"+id,"DELETE");
      return reply("Kullanıcının yasağı kaldırıldı.");
    }
    if(name==="mute" || name==="unmute") {
      const p=require(REST_PERMS.moderate,"Üyelere Zaman Aşımı Uygula"); if(p)return p;
      let until=null;
      if(name==="mute") {
        const raw=String(option(opts,"sure")?.value||"10m"),m=raw.match(/^(\d{1,3})(s|m|h|d)$/i);
        if(!m)return reply("Süre biçimi: 30s, 10m, 2h veya 1d.");
        const ms=Number(m[1])*({s:1000,m:60000,h:3600000,d:86400000}[m[2].toLowerCase()]);
        if(ms<1000||ms>2419200000)return reply("Süre 1 saniye ile 28 gün arasında olmalı.");
        until=new Date(Date.now()+ms).toISOString();
      }
      await discordApi(env,"/guilds/"+guild+"/members/"+selected,"PATCH",{communication_disabled_until:until});
      return reply(name==="mute"?"Üyeye zaman aşımı uygulandı.":"Üyenin zaman aşımı kaldırıldı.");
    }
    if(name==="temizle") {
      const p=require(REST_PERMS.manageMessages,"Mesajları Yönet"); if(p)return p;
      const count=Math.max(1,Math.min(100,Number(option(opts,"adet")?.value||1)));
      const messages=await discordApi(env,"/channels/"+channel+"/messages?limit="+count);
      const ids=messages.filter(m=>Date.now()-Date.parse(m.timestamp)<1209600000).map(m=>m.id);
      if(!ids.length)return reply("Silinebilir mesaj bulunamadı.");
      if(ids.length===1)await discordApi(env,"/channels/"+channel+"/messages/"+ids[0],"DELETE");
      else await discordApi(env,"/channels/"+channel+"/messages/bulk-delete","POST",{messages:ids});
      return reply("🧹 "+ids.length+" mesaj silindi.");
    }
    if(name==="slowmode") {
      const p=require(REST_PERMS.manageChannels,"Kanalları Yönet"); if(p)return p;
      const seconds=Math.max(0,Math.min(21600,Number(option(opts,"saniye")?.value||0)));
      await discordApi(env,"/channels/"+channel,"PATCH",{rate_limit_per_user:seconds});
      return reply("Yavaş mod "+seconds+" saniye olarak ayarlandı.");
    }
    if(name==="rolver" || name==="rolal") {
      const p=require(REST_PERMS.manageRoles,"Rolleri Yönet"); if(p)return p;
      const role=String(option(opts,"role")?.value||"");
      if(!selected||!role)return reply("Üye ve rol seçmelisin.");
      await discordApi(env,"/guilds/"+guild+"/members/"+selected+"/roles/"+role,name==="rolver"?"PUT":"DELETE");
      return reply(name==="rolver"?"Rol verildi.":"Rol alındı.");
    }
    if(name==="nick") {
      const p=require(REST_PERMS.manageNicknames,"Takma Adları Yönet"); if(p)return p;
      const rawNick=String(option(opts,"yeni_isim")?.value||"").trim();
      const nick=rawNick==="-"?"":rawNick;
      await discordApi(env,"/guilds/"+guild+"/members/"+selected,"PATCH",{nick:nick||null});
      return reply("Takma ad güncellendi.");
    }
    if(name==="duyuru") {
      const p=require(32n,"Sunucuyu Yönet"); if(p)return p;
      const message=String(option(opts,"mesaj")?.value||"").trim();
      if(!message||message.length>1800)return reply("Duyuru 1–1800 karakter olmalı.");
      await discordApi(env,"/channels/"+channel+"/messages","POST",{content:"📢 **Duyuru**\n"+message,allowed_mentions:{parse:[]}});
      return reply("Duyuru gönderildi.");
    }
  } catch(error) {
    return reply("Discord işlemi başarısız: "+(error instanceof Error?error.message:"Bilinmeyen hata"));
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
    if (command === "sor") {
      const prompt = String(option(interaction.data?.options, "soru")?.value ?? "").trim();
      if (prompt.length < 1 || prompt.length > 3500) return reply("Soru 1–3500 karakter olmalıdır.");
      ctx.waitUntil(runDeferredAI(interaction, env, "gemini", "gemini-2.5-flash", prompt));
      return json({ type: 5, data: { flags: EPHEMERAL } });
    }
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
    const moreResponse = await handleMoreCommands(interaction, env);
    if (moreResponse) return moreResponse;
    const utilityResponse = handleUtilityCommand(interaction);
    if (utilityResponse) return utilityResponse;
    return reply("Bu komut Cloudflare test sürümünde henüz taşınmadı.");
  },
};
