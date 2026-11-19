const applicationId = process.env.DISCORD_APPLICATION_ID;
const token = process.env.DISCORD_TOKEN;
const guildId = process.env.DISCORD_TEST_GUILD_ID;

if (!applicationId || !token) {
  throw new Error("Set DISCORD_APPLICATION_ID and DISCORD_TOKEN for the dedicated test application.");
}

const commands = [
  { name: "ping", description: "Cloudflare test bot bağlantısını kontrol eder." },
  { name: "xfa", description: "XFA AI asistanına soru sorar.", options: [
{ type: 3, name: "prompt", description: "Sorun veya isteğin", required: true, max_length: 3500 },
{ type: 3, name: "provider", description: "AI sağlayıcısı", required: false, choices: [{ name: "Gemini", value: "gemini" }, { name: "NVIDIA", value: "nvidia" }] },
{ type: 3, name: "model", description: "İsteğe bağlı model kimliği", required: false, max_length: 120 }
] },
  {
    name: "kb",
    description: "Sunucu FAQ bilgi tabanını yönetir.",
    options: [
      {
        type: 1, name: "add", description: "FAQ kaydı ekler veya günceller.",
        options: [
          { type: 3, name: "question", description: "Sık sorulan soru", required: true, max_length: 180 },
          { type: 3, name: "answer", description: "Yanıt", required: true, max_length: 1500 }
        ]
      },
      {
        type: 1, name: "ask", description: "FAQ bilgi tabanında arama yapar.",
        options: [{ type: 3, name: "query", description: "Aranacak soru", required: true, max_length: 180 }]
      },
      { type: 1, name: "list", description: "FAQ sorularını listeler." },
      {
        type: 1, name: "remove", description: "FAQ kaydını siler.",
        options: [{ type: 3, name: "question", description: "Silinecek sorunun tam metni", required: true, max_length: 180 }]
      }
    ]
  }
];

const endpoint = guildId
  ? `https://discord.com/api/v10/applications/${applicationId}/guilds/${guildId}/commands`
  : `https://discord.com/api/v10/applications/${applicationId}/commands`;

const response = await fetch(endpoint, {
  method: "PUT",
  headers: { Authorization: `Bot ${token}`, "Content-Type": "application/json" },
  body: JSON.stringify(commands)
});

const payload = await response.json();
if (!response.ok) {
  throw new Error(`Discord command registration failed (${response.status}): ${JSON.stringify(payload)}`);
}
console.log(`Registered ${payload.length} commands for ${guildId ? "test guild" : "global application"}.`);
