// @ts-nocheck
import { DurableObject } from "cloudflare:workers";

export class DiscordGateway extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.socket = null;
    this.state = "offline";
    this.heartbeatTimer = null;
    this.awaitingAck = false;
    this.sequence = null;
    this.sessionId = null;
    this.resumeUrl = null;
    this.username = null;
    this.lastEventAt = null;
    this.reconnectTimer = null;
    ctx.blockConcurrencyWhile(async () => {
      this.sequence = await ctx.storage.get("sequence") ?? null;
      this.sessionId = await ctx.storage.get("session_id") ?? null;
      this.resumeUrl = await ctx.storage.get("resume_url") ?? null;
      this.username = await ctx.storage.get("username") ?? null;
    });
  }

  async status() {
    return {
      state: this.state,
      online: this.state === "ready",
      username: this.username,
      sessionResumable: Boolean(this.sessionId),
      lastEventAt: this.lastEventAt
    };
  }

  async start() {
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return this.status();
    }
    await this.connect();
    return this.status();
  }

  async connect() {
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) return;
    this.state = "connecting";
    const base = this.sessionId && this.resumeUrl ? this.resumeUrl : "wss://gateway.discord.gg/";
    const url = base + (base.includes("?") ? "&" : "?") + "v=10&encoding=json";
    let ws;
    try {
      ws = new WebSocket(url);
    } catch (error) {
      this.state = "offline";
      this.scheduleReconnect();
      throw error;
    }
    this.socket = ws;
    ws.addEventListener("open", () => { this.state = "connected"; });
    ws.addEventListener("message", event => {
      this.handleGatewayMessage(event.data).catch(error => {
        console.error("Gateway message handler failed", error);
      });
    });
    ws.addEventListener("error", () => {
      this.state = "error";
    });
    ws.addEventListener("close", event => {
      this.socket = null;
      this.stopHeartbeat();
      if ([4004, 4013, 4014].includes(event.code)) {
        this.state = "configuration_error";
        console.error("Discord Gateway rejected token or intents", event.code);
        return;
      }
      this.state = "offline";
      this.scheduleReconnect();
    });
  }

  scheduleReconnect() {
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect().catch(error => console.error("Gateway reconnect failed", error));
    }, 5000);
  }

  send(payload) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(payload));
      return true;
    }
    return false;
  }

  startHeartbeat(interval) {
    this.stopHeartbeat();
    this.awaitingAck = false;
    const firstDelay = Math.floor(Math.random() * interval);
    setTimeout(() => {
      this.heartbeat();
      this.heartbeatTimer = setInterval(() => this.heartbeat(), interval);
    }, firstDelay);
  }

  stopHeartbeat() {
    if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
    this.heartbeatTimer = null;
    this.awaitingAck = false;
  }

  heartbeat() {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return;
    if (this.awaitingAck) {
      this.socket.close(4000, "Heartbeat ACK timeout");
      return;
    }
    this.awaitingAck = true;
    this.send({ op: 1, d: this.sequence });
  }

  async handleGatewayMessage(raw) {
    const packet = JSON.parse(typeof raw === "string" ? raw : new TextDecoder().decode(raw));
    if (packet.s !== null && packet.s !== undefined) {
      this.sequence = packet.s;
      await this.ctx.storage.put("sequence", packet.s);
    }
    if (packet.op === 10) {
      const interval = Number(packet.d?.heartbeat_interval || 41250);
      this.startHeartbeat(interval);
      const token = await this.env.DISCORD_TOKEN.get();
      if (this.sessionId && this.sequence !== null) {
        this.send({ op: 6, d: { token, session_id: this.sessionId, seq: this.sequence } });
      } else {
        const intents = 1 | 2 | 512 | 32768;
        this.send({
          op: 2,
          d: {
            token,
            intents,
            properties: { os: "linux", browser: "Xyrin Flower Worker", device: "Xyrin Flower Worker" },
            presence: { status: "online", activities: [], afk: false }
          }
        });
      }
      return;
    }
    if (packet.op === 11) {
      this.awaitingAck = false;
      return;
    }
    if (packet.op === 1) {
      this.send({ op: 1, d: this.sequence });
      return;
    }
    if (packet.op === 7) {
      this.socket?.close(4000, "Discord requested reconnect");
      return;
    }
    if (packet.op === 9) {
      if (!packet.d) {
        this.sessionId = null;
        this.sequence = null;
        await this.ctx.storage.delete("session_id");
        await this.ctx.storage.delete("sequence");
      }
      this.socket?.close(4000, "Invalid session; reconnecting");
      return;
    }
    if (packet.op !== 0) return;
    this.lastEventAt = new Date().toISOString();
    if (packet.t === "READY") {
      this.sessionId = packet.d.session_id;
      this.resumeUrl = packet.d.resume_gateway_url;
      this.username = packet.d.user?.username || null;
      await this.ctx.storage.put("session_id", this.sessionId);
      await this.ctx.storage.put("resume_url", this.resumeUrl);
      await this.ctx.storage.put("username", this.username);
      this.state = "ready";
      console.log("Discord Gateway READY", this.username);
      return;
    }
    if (packet.t === "RESUMED") {
      this.state = "ready";
      console.log("Discord Gateway session resumed");
      return;
    }
    if (packet.t === "MESSAGE_CREATE") {
      await this.handleMessage(packet.d);
      return;
    }
    if (packet.t === "INTERACTION_CREATE") {
      await this.handleInteraction(packet.d);
      return;
    }
    if (packet.t === "GUILD_MEMBER_ADD") {
      await this.handleMemberJoin(packet.d);
    }
  }

  async discordRequest(path, method = "GET", body) {
    const token = await this.env.DISCORD_TOKEN.get();
    const response = await fetch("https://discord.com/api/v10" + path, {
      method,
      headers: { authorization: "Bot " + token, "content-type": "application/json" },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      signal: AbortSignal.timeout(10000)
    });
    if (!response.ok) throw new Error("Discord API HTTP " + response.status);
    return response.status === 204 ? null : response.json();
  }


  async interactionReply(interaction, data) {
    await fetch("https://discord.com/api/v10/interactions/" + interaction.id + "/" + interaction.token + "/callback", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(data),
      signal: AbortSignal.timeout(10000)
    });
  }

  async handleInteraction(interaction) {
    const name = interaction.data?.name;
    const options = interaction.data?.options || [];
    const uid = interaction.member?.user?.id || interaction.user?.id || "";
    const guild = interaction.guild_id || "";
    const get = (list, key) => list?.find(item => item.name === key);
    const send = (content, ephemeral = true) => this.interactionReply(interaction, {
      type: 4,
      data: { content: String(content).slice(0, 1900), ...(ephemeral ? { flags: 64 } : {}), allowed_mentions: { parse: [] } }
    });
    const manageGuild = (() => { try { return (BigInt(interaction.member?.permissions || "0") & 32n) === 32n; } catch { return false; } })();
    await this.env.DB.prepare("INSERT OR IGNORE INTO interaction_audit(interaction_id,command_name,guild_id,user_id,created_at) VALUES(?,?,?,?,?)")
      .bind(interaction.id, name || "unknown", guild || null, uid || null, new Date().toISOString()).run();
    if (name === "ping") return send("Pong! Xyrin Cloudflare Gateway aktif.");
    if (name === "yardim") return send("**Xyrin komutları**\n/ping • /yardim • /kimlik • /sor • /xfa • /kb • /zar • /yazitura • /kahve • /secim • /sekiztop");
    if (name === "kimlik") return send("Discord kullanıcı ID'n: " + uid);
    if (name === "zar") {
      const max = Math.max(2, Math.min(1000000, Number(get(options, "max_sayi")?.value || 100)));
      return send("🎲 <@" + uid + "> zar attı: **" + (Math.floor(Math.random() * max) + 1) + " / " + max + "**", false);
    }
    if (name === "yazitura") return send("🪙 Sonuç: **" + (Math.random() < .5 ? "Yazı" : "Tura") + "**", false);
    if (name === "kahve") return send("☕ Siparişin hazır: " + String(get(options, "kahve_turu")?.value || "Espresso"), false);
    if (name === "secim") {
      const values = String(get(options, "secenekler")?.value || "").split("|").map(x => x.trim()).filter(Boolean);
      return send(values.length < 2 || values.length > 10 ? "En az 2, en fazla 10 seçenek yaz; | ile ayır." : "🎯 Seçimim: **" + values[Math.floor(Math.random() * values.length)] + "**", false);
    }
    if (name === "sekiztop") {
      const question = String(get(options, "soru")?.value || "").trim();
      const answers = ["Kesinlikle!", "Büyük ihtimalle evet.", "Bence evet.", "Şu an söylemek zor.", "Daha sonra tekrar sor.", "Pek sanmıyorum.", "Cevabım hayır."];
      return send(question.length < 3 ? "Daha açıklayıcı bir soru yaz." : "🎱 **" + question.slice(0, 500) + "**\n" + answers[Math.floor(Math.random() * answers.length)], false);
    }
    if (name === "ship") {
      const other = String(get(options, "member")?.value || uid);
      const seed = (uid + other + new Date().toISOString().slice(0, 10)).split("").reduce((v, c) => ((v * 31 + c.charCodeAt(0)) >>> 0), 7);
      return send("💞 <@" + uid + "> + <@" + other + ">\nGünlük uyum puanı: **" + (seed % 101) + "%**", false);
    }

    if (name === "anket") {
      const raw=String(get(options,"metin")?.value||"").trim(), parts=raw.split("|").map(x=>x.trim()).filter(Boolean);
      if(parts.length<3||parts.length>11)return send("Anket biçimi: Soru | seçenek 1 | seçenek 2 (en fazla 10 seçenek).");
      const emojis=["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"];
      const content="📊 **"+parts[0].slice(0,250)+"**\n"+parts.slice(1).map((x,i)=>emojis[i]+" "+x.slice(0,120)).join("\n");
      const message=await this.discordRequest("/channels/"+interaction.channel_id+"/messages","POST",{content,allowed_mentions:{parse:[]}});
      for(let i=1;i<parts.length;i++)await this.discordRequest("/channels/"+interaction.channel_id+"/messages/"+message.id+"/reactions/"+encodeURIComponent(emojis[i-1])+"/@me","PUT");
      return send("Anket oluşturuldu: "+message.id);
    }

    if (name === "oneri") {
      const value = String(get(options, "metin")?.value || "").trim();
      if (!value || value.length > 1500) return send("Öneri 1–1500 karakter olmalı.");
      await this.env.DB.prepare("INSERT INTO suggestions(guild_id,user_id,content,created_at) VALUES(?,?,?,?)").bind(guild || "dm", uid, value, new Date().toISOString()).run();
      return send("💡 Önerin kaydedildi. Teşekkürler!");
    }
    if (name === "gemini" || name === "nvidia") {
      if (!guild || !manageGuild) return send("Sunucuyu Yönet yetkisi gerekiyor.");
      await this.env.DB.prepare("INSERT INTO guild_settings(guild_id,setting_key,value,updated_at) VALUES(?,?,?,?) ON CONFLICT(guild_id,setting_key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at").bind(guild, "ai_provider", name, new Date().toISOString()).run();
      return send("XFA sağlayıcısı " + name.toUpperCase() + " olarak ayarlandı.");
    }

    if (name === "hosgeldin" || name === "modlog") {
      if (!guild || !manageGuild) return send("Sunucuyu Yönet yetkisi gerekiyor.");
      const key = name === "hosgeldin" ? "welcome_channel" : "modlog_channel";
      await this.env.DB.prepare("INSERT INTO guild_settings(guild_id,setting_key,value,updated_at) VALUES(?,?,?,?) ON CONFLICT(guild_id,setting_key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at").bind(guild,key,interaction.channel_id,new Date().toISOString()).run();
      return send(name === "hosgeldin" ? "Karşılama kanalı ayarlandı." : "Moderasyon log kanalı ayarlandı.");
    }
    if (name === "afk") {
      if (!guild) return send("Bu komut yalnızca sunucuda kullanılabilir.");
      const reason = String(get(options,"sebep")?.value || "AFK").trim().slice(0,180);
      await this.env.DB.prepare("INSERT INTO guild_settings(guild_id,setting_key,value,updated_at) VALUES(?,?,?,?) ON CONFLICT(guild_id,setting_key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at").bind(guild,"afk:"+uid,reason,new Date().toISOString()).run();
      return send("💤 AFK durumu ayarlandı: "+reason);
    }
    if (name === "antiraid") {
      if (!guild || !manageGuild) return send("Sunucuyu Yönet yetkisi gerekiyor.");
      const enabled = Boolean(get(options[0]?.options,"enabled")?.value);
      await this.env.DB.prepare("INSERT INTO guild_settings(guild_id,setting_key,value,updated_at) VALUES(?,?,?,?) ON CONFLICT(guild_id,setting_key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at").bind(guild,"anti_raid_enabled",enabled?"true":"false",new Date().toISOString()).run();
      return send(enabled?"Anti-raid uyarıları açıldı; otomatik ceza uygulanmaz.":"Anti-raid uyarıları kapatıldı.");
    }
    if (name === "kullanici" || name === "avatar") {
      const target=String(get(options,"member")?.value||uid), u=await this.discordRequest("/users/"+target);
      const avatar=u.avatar?"https://cdn.discordapp.com/avatars/"+u.id+"/"+u.avatar+"."+(u.avatar.startsWith("a_")?"gif":"png")+"?size=1024":"https://cdn.discordapp.com/embed/avatars/0.png";
      return send(name==="avatar"?"🖼️ "+avatar:"**Kullanıcı bilgisi**\nAd: "+(u.global_name||u.username)+"\nID: "+u.id+"\nBot: "+(u.bot?"Evet":"Hayır")+"\nAvatar: "+avatar,false);
    }
    if (name === "sunucu" || name === "rapor") {
      if(!guild)return send("Bu komut yalnızca sunucuda kullanılabilir.");
      const g=await this.discordRequest("/guilds/"+guild+"?with_counts=true");
      const count=await this.env.DB.prepare("SELECT COUNT(*) AS total FROM interaction_audit WHERE guild_id=? AND created_at>=?").bind(guild,new Date(Date.now()-604800000).toISOString()).first();
      return send("**"+g.name+"**\nÜye sayısı: **"+(g.approximate_member_count||g.member_count||"—")+"**\nSon 7 gün Worker komutu: **"+(count?.total||0)+"**",false);
    }
    const permissions = {kick:2n,ban:4n,manageChannels:16n,manageMessages:8192n,manageRoles:268435456n,manageNicknames:67108864n,moderate:1099511627776n};
    const permitted = bit => { try { const p=BigInt(interaction.member?.permissions||"0"); return (p&8n)!==0n || (p&bit)===bit; } catch { return false; } };
    const selected=String(get(options,"member")?.value||uid), channel=interaction.channel_id;
    if (["kick","ban","unban","mute","unmute","temizle","slowmode","rolver","rolal","nick","duyuru","kilitle","kilita","kanalolustur","rololustur"].includes(name)) {
      if(!guild)return send("Bu komut yalnızca sunucuda kullanılabilir.");
      try {
        if(name==="kick"){if(!permitted(permissions.kick))return send("Üyeleri At yetkisi gerekiyor.");await this.discordRequest("/guilds/"+guild+"/members/"+selected,"DELETE");return send("Üye sunucudan atıldı.");}
        if(name==="ban"){if(!permitted(permissions.ban))return send("Üyeleri Yasakla yetkisi gerekiyor.");const days=Math.max(0,Math.min(7,Number(get(options,"sil_gun")?.value||0)));await this.discordRequest("/guilds/"+guild+"/bans/"+selected,"PUT",{delete_message_seconds:days*86400});return send("Üye yasaklandı.");}
        if(name==="unban"){if(!permitted(permissions.ban))return send("Üyeleri Yasakla yetkisi gerekiyor.");const id=String(get(options,"user_id")?.value||"");if(!/^\d{15,22}$/.test(id))return send("Geçerli kullanıcı ID'si gir.");await this.discordRequest("/guilds/"+guild+"/bans/"+id,"DELETE");return send("Kullanıcının yasağı kaldırıldı.");}
        if(name==="mute"||name==="unmute"){if(!permitted(permissions.moderate))return send("Üyelere Zaman Aşımı Uygula yetkisi gerekiyor.");let until=null;if(name==="mute"){const m=String(get(options,"sure")?.value||"10m").match(/^(\d{1,3})(s|m|h|d)$/i);if(!m)return send("Süre biçimi: 30s, 10m, 2h veya 1d.");const ms=Number(m[1])*({s:1000,m:60000,h:3600000,d:86400000}[m[2].toLowerCase()]);if(ms<1000||ms>2419200000)return send("Süre 1 saniye ile 28 gün arasında olmalı.");until=new Date(Date.now()+ms).toISOString();}await this.discordRequest("/guilds/"+guild+"/members/"+selected,"PATCH",{communication_disabled_until:until});return send(name==="mute"?"Üyeye zaman aşımı uygulandı.":"Zaman aşımı kaldırıldı.");}
        if(name==="temizle"){if(!permitted(permissions.manageMessages))return send("Mesajları Yönet yetkisi gerekiyor.");const amount=Math.max(1,Math.min(100,Number(get(options,"adet")?.value||1))),msgs=await this.discordRequest("/channels/"+channel+"/messages?limit="+amount),ids=msgs.filter(x=>Date.now()-Date.parse(x.timestamp)<1209600000).map(x=>x.id);if(!ids.length)return send("Silinebilir mesaj bulunamadı.");if(ids.length===1)await this.discordRequest("/channels/"+channel+"/messages/"+ids[0],"DELETE");else await this.discordRequest("/channels/"+channel+"/messages/bulk-delete","POST",{messages:ids});return send("🧹 "+ids.length+" mesaj silindi.");}
        if(name==="slowmode"){if(!permitted(permissions.manageChannels))return send("Kanalları Yönet yetkisi gerekiyor.");const sec=Math.max(0,Math.min(21600,Number(get(options,"saniye")?.value||0)));await this.discordRequest("/channels/"+channel,"PATCH",{rate_limit_per_user:sec});return send("Yavaş mod "+sec+" saniye olarak ayarlandı.");}
        if(name==="rolver"||name==="rolal"){if(!permitted(permissions.manageRoles))return send("Rolleri Yönet yetkisi gerekiyor.");const role=String(get(options,"role")?.value||"");if(!role)return send("Rol seçmelisin.");await this.discordRequest("/guilds/"+guild+"/members/"+selected+"/roles/"+role,name==="rolver"?"PUT":"DELETE");return send(name==="rolver"?"Rol verildi.":"Rol alındı.");}
        if(name==="nick"){if(!permitted(permissions.manageNicknames))return send("Takma Adları Yönet yetkisi gerekiyor.");const raw=String(get(options,"yeni_isim")?.value||"").trim(),nick=raw==="-"?"":raw;await this.discordRequest("/guilds/"+guild+"/members/"+selected,"PATCH",{nick:nick||null});return send("Takma ad güncellendi.");}
        if(name==="duyuru"){if(!manageGuild)return send("Sunucuyu Yönet yetkisi gerekiyor.");const text=String(get(options,"mesaj")?.value||"").trim();if(!text||text.length>1800)return send("Duyuru 1–1800 karakter olmalı.");await this.discordRequest("/channels/"+channel+"/messages","POST",{content:"📢 **Duyuru**\n"+text,allowed_mentions:{parse:[]}});return send("Duyuru gönderildi.");}
        if(name==="kilitle"||name==="kilita"){if(!permitted(permissions.manageChannels))return send("Kanalları Yönet yetkisi gerekiyor.");const data=await this.discordRequest("/channels/"+channel),everyone=String(guild),old=(data.permission_overwrites||[]).find(x=>x.id===everyone)||{id:everyone,type:0,allow:"0",deny:"0"},sendBit=2048n,allow=BigInt(old.allow||"0"),deny=BigInt(old.deny||"0"),next={...old,allow:(name==="kilita"?(allow|sendBit):(allow&~sendBit)).toString(),deny:(name==="kilitle"?(deny|sendBit):(deny&~sendBit)).toString()},over=(data.permission_overwrites||[]).filter(x=>x.id!==everyone);over.push(next);await this.discordRequest("/channels/"+channel,"PATCH",{permission_overwrites:over});return send(name==="kilitle"?"Kanal kilitlendi.":"Kanal kilidi açıldı.");}
        if(name==="kanalolustur"){if(!permitted(permissions.manageChannels))return send("Kanalları Yönet yetkisi gerekiyor.");const channelName=String(get(options,"kanal_adi")?.value||"").toLowerCase().replace(/[^a-z0-9-]/g,"-").slice(0,90);if(!channelName)return send("Kanal adı gir.");const created=await this.discordRequest("/guilds/"+guild+"/channels","POST",{name:channelName,type:0});return send("Kanal oluşturuldu: <#"+created.id+">");}
        if(name==="rololustur"){if(!permitted(permissions.manageRoles))return send("Rolleri Yönet yetkisi gerekiyor.");const roleName=String(get(options,"rol_adi")?.value||"").trim().slice(0,100);if(!roleName)return send("Rol adı gir.");const created=await this.discordRequest("/guilds/"+guild+"/roles","POST",{name:roleName,permissions:"0",mentionable:false,hoist:false});return send("Rol oluşturuldu: <@&"+created.id+">");}
      } catch(error) { return send("Discord işlemi başarısız: "+(error instanceof Error?error.message:"Bilinmeyen hata")); }
    }

    if (name === "kb") {
      if (!guild) return send("Bu komut yalnızca sunucuda kullanılabilir.");
      const sub = options[0], action = sub?.name, args = sub?.options || [];
      if (action === "add") {
        if (!manageGuild) return send("Sunucuyu Yönet yetkisi gerekiyor.");
        const q = String(get(args, "question")?.value || "").trim(), answer = String(get(args, "answer")?.value || "").trim();
        if (!q || q.length > 180 || !answer || answer.length > 1500) return send("Soru 1–180, yanıt 1–1500 karakter olmalı.");
        const now = new Date().toISOString();
        await this.env.DB.prepare("INSERT INTO knowledge_base(guild_id,question,normalized_question,answer,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(guild_id,normalized_question) DO UPDATE SET question=excluded.question,answer=excluded.answer,updated_at=excluded.updated_at").bind(guild,q,q.normalize("NFKC").toLocaleLowerCase("tr").replace(/\\s+/g," ").trim(),answer,uid,now,now).run();
        return send("FAQ kaydı eklendi/güncellendi.");
      }
      if (action === "ask") {
        const q = String(get(args, "query")?.value || "").trim(), n = q.normalize("NFKC").toLocaleLowerCase("tr").replace(/\\s+/g," ").trim();
        const rows = await this.env.DB.prepare("SELECT question,answer,normalized_question FROM knowledge_base WHERE guild_id=? ORDER BY updated_at DESC LIMIT 100").bind(guild).all();
        const hit = rows.results.find(x => x.normalized_question === n) || rows.results.find(x => x.normalized_question.includes(n) || n.includes(x.normalized_question));
        return send(hit ? "**" + hit.question + "**\n" + hit.answer : "Bilgi tabanında kayıt bulunamadı.", false);
      }
      if (action === "list") {
        if (!manageGuild) return send("Sunucuyu Yönet yetkisi gerekiyor.");
        const rows = await this.env.DB.prepare("SELECT question FROM knowledge_base WHERE guild_id=? ORDER BY question LIMIT 25").bind(guild).all();
        return send(rows.results.length ? rows.results.map((x, i) => (i + 1) + ". " + x.question).join("\n") : "Bilgi tabanı boş.");
      }
      if (action === "remove") {
        if (!manageGuild) return send("Sunucuyu Yönet yetkisi gerekiyor.");
        const q = String(get(args, "question")?.value || "").trim().normalize("NFKC").toLocaleLowerCase("tr").replace(/\\s+/g," ").trim();
        const result = await this.env.DB.prepare("DELETE FROM knowledge_base WHERE guild_id=? AND normalized_question=?").bind(guild,q).run();
        return send(result.meta.changes ? "FAQ kaydı silindi." : "Kayıt bulunamadı.");
      }
      return send("Bilinmeyen FAQ işlemi.");
    }
    if (name === "sor" || name === "xfa") {
      const prompt = String(get(options, name === "sor" ? "soru" : "prompt")?.value || "").trim();
      if (!prompt || prompt.length > 3500) return send("Soru 1–3500 karakter olmalı.");
      await this.interactionReply(interaction, { type: 5, data: { flags: 64 } });
      let answer;
      try {
        const provider = name === "xfa" && get(options, "provider")?.value === "nvidia" ? "nvidia" : "gemini";
        if (provider === "gemini") {
          const key = await this.env.GEMINI_API_KEY.get(), model = String(get(options, "model")?.value || "gemini-2.5-flash");
          const r = await fetch("https://generativelanguage.googleapis.com/v1beta/models/" + encodeURIComponent(model) + ":generateContent?key=" + encodeURIComponent(key), { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ contents: [{ role: "user", parts: [{ text: prompt }] }], generationConfig: { maxOutputTokens: 900 } }), signal: AbortSignal.timeout(25000) });
          const d = await r.json(); if (!r.ok) throw Error(d.error?.message || "Gemini HTTP " + r.status);
          answer = d.candidates?.[0]?.content?.parts?.map(x => x.text || "").join("").trim();
        } else {
          const key = await this.env.NVIDIA_API_KEY.get(), model = String(get(options, "model")?.value || "meta/llama-3.3-70b-instruct");
          const r = await fetch("https://integrate.api.nvidia.com/v1/chat/completions", { method: "POST", headers: { authorization: "Bearer " + key, "content-type": "application/json" }, body: JSON.stringify({ model, messages: [{ role: "user", content: prompt }], max_tokens: 900 }), signal: AbortSignal.timeout(25000) });
          const d = await r.json(); if (!r.ok) throw Error(d.error?.message || "NVIDIA HTTP " + r.status);
          answer = d.choices?.[0]?.message?.content;
        }
      } catch (error) { answer = "AI sağlayıcı hatası: " + (error instanceof Error ? error.message : "Bilinmeyen hata"); }
      await fetch("https://discord.com/api/v10/webhooks/" + interaction.application_id + "/" + interaction.token + "/messages/@original", { method: "PATCH", headers: { "content-type": "application/json" }, body: JSON.stringify({ content: String(answer || "AI boş yanıt döndürdü.").slice(0, 1900), allowed_mentions: { parse: [] } }) });
      return;
    }
  }

  async handleMessage(message) {
    if (!message.guild_id || message.author?.bot || !message.content) return;
    const content = message.content.trim();
    const prefix = "!";
    if (!content.startsWith(prefix)) return;
    const parts = content.slice(prefix.length).trim().split(/\s+/);
    const command = (parts.shift() || "").toLocaleLowerCase("tr");
    let response = null;
    const mention = "<@" + message.author.id + ">";
    if (command === "ping") response = "Pong! Xyrin Cloudflare Gateway aktif.";
    else if (command === "kimlik" || command === "id") response = "Discord kullanıcı ID'n: " + message.author.id;
    else if (command === "yardim" || command === "help" || command === "komutlar") response = "**Xyrin prefix komutları**\n!ping • !yardim • !kimlik • !zar • !yazitura • !kahve • !secim • !sekiztop";
    else if (command === "zar") {
      const max = Math.max(2, Math.min(1000000, Number(parts[0]) || 100));
      response = "🎲 " + mention + " zar attı: **" + (Math.floor(Math.random() * max) + 1) + " / " + max + "**";
    } else if (command === "yazitura") response = "🪙 " + mention + ", sonuç: **" + (Math.random() < 0.5 ? "Yazı" : "Tura") + "**!";
    else if (command === "kahve") response = "☕ " + mention + ", " + (parts.join(" ").slice(0, 40) || "Espresso") + " siparişin hazır!";
    else if (command === "secim") {
      const choices = content.slice(prefix.length + command.length).trim().split("|").map(x => x.trim()).filter(Boolean);
      if (choices.length < 2 || choices.length > 10) response = "En az 2, en fazla 10 seçeneği | ile ayır.";
      else response = "🎯 Seçimim: **" + choices[Math.floor(Math.random() * choices.length)] + "**";
    } else if (command === "sekiztop" || command === "8ball") {
      const question = parts.join(" ").slice(0, 400);
      const answers = ["Kesinlikle!", "Büyük ihtimalle evet.", "Bence evet.", "Şu an söylemek zor.", "Daha sonra tekrar sor.", "Pek sanmıyorum.", "Cevabım hayır."];
      response = question.length < 3 ? "Biraz daha açıklayıcı bir soru yaz." : "🎱 **" + question + "**\n" + answers[Math.floor(Math.random() * answers.length)];
    }
    if (response) {
      await this.discordRequest("/channels/" + message.channel_id + "/messages", "POST", {
        content: response.slice(0, 1900),
        message_reference: { message_id: message.id, fail_if_not_exists: false },
        allowed_mentions: { parse: [], replied_user: false }
      });
    }
    const mentioned = [...(message.mentions || [])].filter(x => !x.bot);
    for (const user of mentioned.slice(0, 5)) {
      const row = await this.env.DB.prepare("SELECT value FROM guild_settings WHERE guild_id=? AND setting_key=?").bind(message.guild_id, "afk:" + user.id).first();
      if (row?.value) {
        await this.discordRequest("/channels/" + message.channel_id + "/messages", "POST", {
          content: "<@" + user.id + "> şu anda AFK: " + String(row.value).slice(0, 180),
          allowed_mentions: { parse: [], users: [user.id] }
        });
      }
    }
  }

  async handleMemberJoin(member) {
    const guild = member.guild_id;
    if (!guild || member.user?.bot) return;
    const welcome = await this.env.DB.prepare("SELECT value FROM guild_settings WHERE guild_id=? AND setting_key='welcome_channel'").bind(guild).first();
    if (welcome?.value) {
      await this.discordRequest("/channels/" + welcome.value + "/messages", "POST", {
        content: "🌸 Hoş geldin <@" + member.user.id + ">! Sunucumuza katıldığın için mutluyuz.",
        allowed_mentions: { parse: [], users: [member.user.id] }
      });
    }
    const now = new Date().toISOString();
    await this.env.DB.prepare("INSERT INTO guild_join_events(guild_id,user_id,created_at) VALUES(?,?,?)").bind(guild,member.user.id,now).run();
    await this.env.DB.prepare("DELETE FROM guild_join_events WHERE guild_id=? AND created_at<?").bind(guild,new Date(Date.now()-60000).toISOString()).run();
    const count = await this.env.DB.prepare("SELECT COUNT(*) AS total FROM guild_join_events WHERE guild_id=?").bind(guild).first();
    const cfg = await this.env.DB.prepare("SELECT value FROM guild_settings WHERE guild_id=? AND setting_key='anti_raid_enabled'").bind(guild).first();
    const modlog = await this.env.DB.prepare("SELECT value FROM guild_settings WHERE guild_id=? AND setting_key='modlog_channel'").bind(guild).first();
    if (cfg?.value === "true" && Number(count?.total || 0) >= 6 && modlog?.value) {
      await this.discordRequest("/channels/" + modlog.value + "/messages", "POST", {
        content: "⚠️ Şüpheli katılım artışı: Son 60 saniyede " + count.total + " yeni üye katıldı. Bu yalnızca uyarıdır; otomatik ceza uygulanmadı.",
        allowed_mentions: { parse: [] }
      });
    }
  }
}
