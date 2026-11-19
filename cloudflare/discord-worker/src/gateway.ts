// @ts-nocheck
import { DurableObject } from "cloudflare:workers";
import { dispatchInteraction } from "./index";

export class DiscordGateway extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.socket = null;
    this.state = "offline";
    this.heartbeatTimer = null;
    this.heartbeatStartTimer = null;
    this.awaitingAck = false;
    this.reconnectAttempts = 0;
    this.lastCloseCode = null;
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
      lastEventAt: this.lastEventAt,
      lastCloseCode: this.lastCloseCode,
      reconnectAttempts: this.reconnectAttempts
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
      // Keep async Gateway work alive while commands (especially AI) call external APIs.
      this.ctx.waitUntil(this.handleGatewayMessage(event.data).catch(error => {
        console.error("Gateway message handler failed", error);
      }));
    });
    ws.addEventListener("error", () => {
      this.state = "error";
      try { ws.close(4000, "Gateway socket error"); } catch {}
    });
    ws.addEventListener("close", async event => {
      this.socket = null;
      this.lastCloseCode = event.code;
      this.stopHeartbeat();
      if ([4007, 4009].includes(event.code)) {
        this.sessionId = null;
        this.sequence = null;
        this.resumeUrl = null;
        await this.ctx.storage.delete("session_id");
        await this.ctx.storage.delete("sequence");
        await this.ctx.storage.delete("resume_url");
      }
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
    this.reconnectAttempts = Math.min(this.reconnectAttempts + 1, 8);
    const baseDelay = Math.min(60000, 1000 * (2 ** (this.reconnectAttempts - 1)));
    const delay = Math.round(baseDelay * (0.8 + Math.random() * 0.4));
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect().catch(error => console.error("Gateway reconnect failed", error));
    }, delay);
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
    this.heartbeatStartTimer = setTimeout(() => {
      this.heartbeatStartTimer = null;
      if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return;
      this.heartbeat();
      this.heartbeatTimer = setInterval(() => this.heartbeat(), interval);
    }, firstDelay);
  }

  stopHeartbeat() {
    if (this.heartbeatStartTimer) clearTimeout(this.heartbeatStartTimer);
    if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
    this.heartbeatStartTimer = null;
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
      this.reconnectAttempts = 0;
      console.log("Discord Gateway READY", this.username);
      return;
    }
    if (packet.t === "RESUMED") {
      this.state = "ready";
      this.reconnectAttempts = 0;
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
    const response = await fetch("https://discord.com/api/v10/interactions/" + interaction.id + "/" + interaction.token + "/callback", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(data),
      signal: AbortSignal.timeout(10000)
    });
    if (!response.ok) {
      const detail = await response.text().catch(() => "");
      throw new Error("Discord interaction callback HTTP " + response.status + (detail ? ": " + detail.slice(0, 300) : ""));
    }
  }

  async handleInteraction(interaction) {
    try {
      const response = await dispatchInteraction(
        interaction,
        this.env,
        (task) => this.ctx.waitUntil(task),
      );
      const payload = await response.json();
      await this.interactionReply(interaction, payload);
    } catch (error) {
      console.error("Shared interaction dispatcher failed", error);
      await this.interactionReply(interaction, {
        type: 4,
        data: {
          content: "Komut işlenirken beklenmeyen bir hata oluştu. Lütfen tekrar dene.",
          flags: 64,
          allowed_mentions: { parse: [] },
        },
      });
    }
  }

  async handleMessage(message) {
    if (!message.guild_id || message.author?.bot || !message.content) return;
    const content = message.content.trim();
    const now = new Date().toISOString();
    await this.env.DB.prepare("INSERT OR IGNORE INTO economy_accounts(guild_id,user_id,updated_at) VALUES(?,?,?)").bind(message.guild_id,message.author.id,now).run();
    const xpGain = 5 + Math.floor(Math.random()*11);
    await this.env.DB.prepare("UPDATE economy_accounts SET xp=xp+?,level=CAST((xp+?)/150 AS INTEGER),last_xp=?,updated_at=? WHERE guild_id=? AND user_id=? AND (last_xp IS NULL OR last_xp<=?)").bind(xpGain,xpGain,now,now,message.guild_id,message.author.id,new Date(Date.now()-60000).toISOString()).run();
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
