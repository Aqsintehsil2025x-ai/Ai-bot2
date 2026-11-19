const applicationId = process.env.DISCORD_APPLICATION_ID;
const token = process.env.DISCORD_TOKEN;
const guildId = process.env.DISCORD_TEST_GUILD_ID;

if (!applicationId || !token) {
  throw new Error("Set DISCORD_APPLICATION_ID and DISCORD_TOKEN for the dedicated test application.");
}

const commands = [
  { name: "ping", description: "Bot bağlantısını ve yanıtını kontrol eder." },
  { name: "yardim", description: "Cloudflare test sürümündeki komutları listeler." },
  { name: "kimlik", description: "Discord kullanıcı kimliğini gösterir." },
  { name: "sor", description: "Gemini ile yapay zekaya soru sor.", options: [{ type: 3, name: "soru", description: "Sormak istediğin şey", required: true, max_length: 3500 }] },
  { name: "zar", description: "Zar atar.", options: [{ type: 4, name: "max_sayi", description: "Zarın en yüksek değeri (varsayılan 100)", required: false, min_value: 2, max_value: 1000000 }] },
  { name: "yazitura", description: "Yazı tura atar." },
  { name: "kahve", description: "Kahve siparişi ver ☕", options: [{ type: 3, name: "kahve_turu", description: "Hangi kahve? (örn: Latte)", required: false, max_length: 40 }] },
  { name: "secim", description: "Seçeneklerin arasından rastgele birini seçer.", options: [{ type: 3, name: "secenekler", description: "Seçenekleri | işaretiyle ayır", required: true, max_length: 900 }] },
  { name: "sekiztop", description: "Soruna sihirli 8-top cevabı verir.", options: [{ type: 3, name: "soru", description: "Evet/hayır türünde sorun", required: true, max_length: 500 }] },
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

  { name: "kullanici", description: "Kullanıcı bilgilerini gösterir.", options: [{ type: 6, name: "member", description: "Bilgisine bakılacak üye", required: false }] },
  { name: "avatar", description: "Kullanıcının avatarını gösterir.", options: [{ type: 6, name: "member", description: "Avatarı gösterilecek üye", required: false }] },
  { name: "sunucu", description: "Sunucu bilgilerini gösterir." },
  { name: "rapor", description: "Sunucu ve Worker kullanım raporunu gösterir." },
  { name: "analytics", description: "Son 7 günlük Worker komut kullanımını gösterir." },
  { name: "oneri", description: "Yetkililere iletilmek üzere öneri kaydeder.", options: [{ type: 3, name: "metin", description: "Önerin", required: true, max_length: 1500 }] },
  { name: "ship", description: "İki üye için günlük eğlenceli uyum puanı üretir.", options: [{ type: 6, name: "member", description: "Eşleştirilecek üye", required: false }] },
  { name: "kick", description: "Üyeyi sunucudan atar.", options: [{ type: 6, name: "member", description: "Atılacak üye", required: true }] },
  { name: "ban", description: "Üyeyi sunucudan yasaklar.", options: [{ type: 6, name: "member", description: "Yasaklanacak üye", required: true }, { type: 4, name: "sil_gun", description: "Mesaj silme günü (0-7)", required: false, min_value: 0, max_value: 7 }] },
  { name: "unban", description: "Kullanıcı ID ile yasağı kaldırır.", options: [{ type: 3, name: "user_id", description: "Kullanıcı ID", required: true, min_length: 15, max_length: 22 }] },
  { name: "mute", description: "Üyeye zaman aşımı uygular.", options: [{ type: 6, name: "member", description: "Susturulacak üye", required: true }, { type: 3, name: "sure", description: "30s, 10m, 2h veya 1d", required: false }] },
  { name: "unmute", description: "Üyenin zaman aşımını kaldırır.", options: [{ type: 6, name: "member", description: "Susturması kaldırılacak üye", required: true }] },
  { name: "temizle", description: "Kanaldan son mesajları siler.", options: [{ type: 4, name: "adet", description: "1-100 arası mesaj sayısı", required: true, min_value: 1, max_value: 100 }] },
  { name: "slowmode", description: "Kanal yavaş modunu ayarlar.", options: [{ type: 4, name: "saniye", description: "0-21600 saniye", required: true, min_value: 0, max_value: 21600 }] },
  { name: "rolver", description: "Üyeye rol verir.", options: [{ type: 6, name: "member", description: "Üye", required: true }, { type: 8, name: "role", description: "Verilecek rol", required: true }] },
  { name: "rolal", description: "Üyeden rol alır.", options: [{ type: 6, name: "member", description: "Üye", required: true }, { type: 8, name: "role", description: "Alınacak rol", required: true }] },
  { name: "nick", description: "Üyenin takma adını değiştirir.", options: [{ type: 6, name: "member", description: "Üye", required: true }, { type: 3, name: "yeni_isim", description: "Yeni isim; boş bırakmak için -", required: false, max_length: 32 }] },
  { name: "duyuru", description: "Bu kanala duyuru gönderir.", options: [{ type: 3, name: "mesaj", description: "Duyuru metni", required: true, max_length: 1800 }] },
  { name: "gemini", description: "Sunucunun varsayılan XFA sağlayıcısını Gemini yapar." },
  { name: "nvidia", description: "Sunucunun varsayılan XFA sağlayıcısını NVIDIA yapar." }
];

const endpoint = guildId
  ? `https://discord.com/api/v10/applications/${applicationId}/guilds/${guildId}/commands`
  : `https://discord.com/api/v10/applications/${applicationId}/commands`;

const headers = { Authorization: `Bot ${token}`, "Content-Type": "application/json" };
const existingResponse = await fetch(endpoint, { headers });
const existing = await existingResponse.json();
if (!existingResponse.ok) throw new Error(`Could not read existing commands (${existingResponse.status}): ${JSON.stringify(existing)}`);
const byName = new Map(existing.map((command) => [command.name, command]));
let created = 0, updated = 0;
for (const command of commands) {
  const current = byName.get(command.name);
  const url = current ? endpoint + "/" + current.id : endpoint;
  const response = await fetch(url, {
    method: current ? "PATCH" : "POST",
    headers,
    body: JSON.stringify(command)
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(`Could not register /${command.name} (${response.status}): ${JSON.stringify(payload)}`);
  if (current) updated++; else created++;
}
console.log(`Safely registered ${commands.length} commands: ${created} new, ${updated} updated. Existing unrelated commands were preserved.`);
