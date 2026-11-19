export interface Env {
  DB: D1Database;
  DISCORD_PUBLIC_KEY: string;
  DISCORD_APPLICATION_ID?: string;
  GEMINI_API_KEY?: string;
  NVIDIA_API_KEY?: string;
  FLASK_SECRET_KEY?: string;
  XFA_ACCESS_TOKEN?: string;
  XFA_TOKEN_ENCRYPTION_KEY?: string;
}

const encoder = new TextEncoder();

function hexToBytes(value: string): Uint8Array {
  if (!/^[0-9a-f]{128}$/i.test(value)) throw new Error("Invalid signature encoding");
  return new Uint8Array(value.match(/.{2}/g)!.map((part) => Number.parseInt(part, 16)));
}

async function verifyDiscordRequest(request: Request, body: string, publicKey: string): Promise<boolean> {
  const signature = request.headers.get("x-signature-ed25519");
  const timestamp = request.headers.get("x-signature-timestamp");
  if (!signature || !timestamp || !/^\d{10,}$/.test(timestamp)) return false;

  const key = await crypto.subtle.importKey(
    "raw",
    hexToBytes(publicKey),
    { name: "Ed25519" },
    false,
    ["verify"],
  );
  return crypto.subtle.verify(
    { name: "Ed25519" },
    key,
    hexToBytes(signature),
    encoder.encode(timestamp + body),
  );
}

function json(data: unknown, status = 200): Response {
  return Response.json(data, { status, headers: { "cache-control": "no-store" } });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health") {
      return json({ ok: true, service: "xfa-discord-interactions", runtime: "cloudflare-workers" });
    }

    if (request.method !== "POST" || url.pathname !== "/discord/interactions") {
      return json({ error: "Not found" }, 404);
    }
    if (!env.DISCORD_PUBLIC_KEY) return json({ error: "Discord public key is not configured" }, 503);

    const body = await request.text();
    try {
      if (!(await verifyDiscordRequest(request, body, env.DISCORD_PUBLIC_KEY))) {
        return json({ error: "Invalid request signature" }, 401);
      }
    } catch {
      return json({ error: "Invalid request signature" }, 401);
    }

    let interaction: {
      type?: number;
      data?: { name?: string; options?: Array<{ name: string; value: string | number | boolean }> };
      member?: { user?: { id?: string } };
      user?: { id?: string };
      guild_id?: string;
      id?: string;
    };
    try {
      interaction = JSON.parse(body);
    } catch {
      return json({ error: "Invalid JSON" }, 400);
    }

    // Discord PING handshake.
    if (interaction.type === 1) return json({ type: 1 });

    // Slash-command interactions.
    if (interaction.type === 2) {
      const command = interaction.data?.name;
      const userId = interaction.member?.user?.id ?? interaction.user?.id ?? null;
      const guildId = interaction.guild_id ?? null;

      if (command === "ping") {
        return json({ type: 4, data: { content: "Pong! Cloudflare test bot is online.", flags: 64 } });
      }

      if (command === "xfa") {
        await env.DB.prepare(
          "INSERT INTO interaction_audit (interaction_id, command_name, guild_id, user_id, created_at) VALUES (?, ?, ?, ?, ?)",
        ).bind(interaction.id ?? null, command, guildId, userId, new Date().toISOString()).run();

        return json({
          type: 4,
          data: {
            content: "XFA Cloudflare test endpoint is online. AI actions are not enabled in this test build yet.",
            flags: 64,
          },
        });
      }

      return json({ type: 4, data: { content: "This command is not available in the Cloudflare test build yet.", flags: 64 } });
    }

    return json({ error: "Unsupported interaction type" }, 400);
  },
};
