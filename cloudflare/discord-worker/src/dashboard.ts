import { generateAI, type AIProvider } from "./ai";

interface SecretBinding { get(): Promise<string>; }
interface DashboardEnv {
  DB: D1Database;
  DISCORD_TOKEN: SecretBinding;
  DISCORD_CLIENT_ID: SecretBinding;
  DISCORD_CLIENT_SECRET: SecretBinding;
  DASHBOARD_SESSION_SECRET: SecretBinding;
  GEMINI_API_KEY: SecretBinding;
  NVIDIA_API_KEY: SecretBinding;
}
type Session = { userId: string; username: string; accessToken: string; expiresAt: number; csrf: string };
const COOKIE = "xfa_dashboard";
const encoder = new TextEncoder();
const decoder = new TextDecoder();
const API = "https://discord.com/api/v10";

function b64(value: Uint8Array | string): string {
  const bytes = typeof value === "string" ? encoder.encode(value) : value;
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
}
function unb64(value: string): string {
  const raw = atob(value.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - value.length % 4) % 4));
  return decoder.decode(Uint8Array.from(raw, c => c.charCodeAt(0)));
}
async function sign(value: string, secret: string): Promise<string> {
  const key = await crypto.subtle.importKey("raw", encoder.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return b64(new Uint8Array(await crypto.subtle.sign("HMAC", key, encoder.encode(value))));
}
async function seal(data: Session, secret: string): Promise<string> {
  const payload = b64(JSON.stringify(data));
  return payload + "." + await sign(payload, secret);
}
async function openSession(request: Request, env: DashboardEnv): Promise<Session | null> {
  const cookie = request.headers.get("cookie") || "";
  const token = cookie.split(";").map(v => v.trim()).find(v => v.startsWith(COOKIE + "="))?.slice(COOKIE.length + 1);
  if (!token) return null;
  const [payload, signature] = token.split(".");
  if (!payload || !signature) return null;
  const expected = await sign(payload, await env.DASHBOARD_SESSION_SECRET.get());
  if (signature !== expected) return null;
  try {
    const session = JSON.parse(unb64(payload)) as Session;
    return session.expiresAt > Date.now() ? session : null;
  } catch { return null; }
}
function response(data: unknown, status = 200): Response {
  return Response.json(data, { status, headers: { "cache-control": "no-store" } });
}
function cookie(value: string, maxAge: number): string {
  return COOKIE + "=" + value + "; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=" + maxAge;
}
async function discord(path: string, token: string, init: RequestInit = {}): Promise<any> {
  const result = await fetch(API + path, {
    ...init,
    headers: { authorization: "Bearer " + token, ...(init.body ? { "content-type": "application/json" } : {}), ...init.headers },
    signal: AbortSignal.timeout(12000),
  });
  const body = await result.json().catch(() => ({}));
  if (!result.ok) throw new Error("Discord API HTTP " + result.status);
  return body;
}
async function botRequest(env: DashboardEnv, path: string, init: RequestInit = {}): Promise<any> {
  const token = await env.DISCORD_TOKEN.get();
  const result = await fetch(API + path, {
    ...init,
    headers: { authorization: "Bot " + token, ...(init.body ? { "content-type": "application/json" } : {}), ...init.headers },
    signal: AbortSignal.timeout(12000),
  });
  const body = await result.json().catch(() => ({}));
  if (!result.ok) throw new Error("Bot API HTTP " + result.status);
  return body;
}
async function managedGuild(session: Session, env: DashboardEnv, guildId: string): Promise<any> {
  const guilds = await discord("/users/@me/guilds", session.accessToken) as any[];
  const guild = guilds.find(item => item.id === guildId && (BigInt(item.permissions || "0") & 32n) === 32n);
  if (!guild) throw new Error("Bu sunucu için Sunucuyu Yönet yetkin yok.");
  await botRequest(env, "/guilds/" + guildId);
  return guild;
}
async function getSettings(env: DashboardEnv, guildId: string): Promise<Record<string, string>> {
  const rows = await env.DB.prepare("SELECT setting_key,value FROM guild_settings WHERE guild_id=?").bind(guildId).all<{setting_key:string;value:string}>();
  return Object.fromEntries(rows.results.map(row => [row.setting_key, row.value]));
}
async function saveSettings(env: DashboardEnv, guildId: string, values: Record<string, string>): Promise<void> {
  const allowed = new Set(["ai_provider", "welcome_message", "module_ai", "module_moderation", "module_entertainment", "language", "prefix"]);
  const now = new Date().toISOString();
  const statements = Object.entries(values).filter(([key, value]) => allowed.has(key) && typeof value === "string" && value.length <= 500)
    .map(([key, value]) => env.DB.prepare("INSERT INTO guild_settings(guild_id,setting_key,value,updated_at) VALUES(?,?,?,?) ON CONFLICT(guild_id,setting_key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at").bind(guildId,key,value,now));
  if (statements.length) await env.DB.batch(statements);
}
const PAGE = `<!doctype html><html lang="tr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Xyrin Flower • Kontrol Merkezi</title><style>
:root{color-scheme:dark;--bg:#090d14;--panel:#111a24;--line:#263746;--pink:#f09bb8;--mint:#9ce7cb;--muted:#9baeba}*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 15% 0,#243d3b 0,transparent 40%),var(--bg);color:#edf5f4;font:15px Inter,system-ui,sans-serif}header{padding:22px max(5vw,20px);border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center}h1{font-size:clamp(26px,4vw,42px);margin:8px 0}h2{font-size:19px}small,.muted{color:var(--muted)}main{max-width:1100px;margin:38px auto;padding:0 20px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:16px}.card{background:#111a24eF;border:1px solid var(--line);border-radius:18px;padding:20px;margin:14px 0}.brand{font-weight:800;letter-spacing:.04em}.brand span{color:var(--pink)}button,select,input,textarea{background:#0b131c;color:#edf5f4;border:1px solid #344b5a;border-radius:10px;padding:11px;font:inherit}button{cursor:pointer;background:#d98ca9;color:#111;font-weight:700;border:0}button.secondary{background:#233440;color:#eaf5f2}button:disabled{opacity:.5}select,input,textarea{width:100%;margin:7px 0 14px}textarea{min-height:100px;resize:vertical}.row{display:flex;gap:12px;align-items:center;flex-wrap:wrap}.row>*{flex:1}.hidden{display:none}.status{color:var(--mint);min-height:24px}.chatlog{height:280px;overflow:auto;background:#09111a;border:1px solid var(--line);padding:12px;border-radius:12px;white-space:pre-wrap}.pill{display:inline-block;padding:5px 9px;border:1px solid var(--line);border-radius:99px;color:var(--mint);font-size:12px}@media(max-width:600px){header{align-items:flex-start;gap:10px;flex-direction:column}}
</style><header><div class="brand">✿ XYRIN <span>FLOWER</span> <small>CONTROL</small></div><div class="row" style="max-width:260px"><span id="who" class="muted">Bağlantı gözlənilir…</span><button id="login">Discord ilə giriş</button><button id="logout" class="secondary hidden">Çıxış</button></div></header><main><p class="pill">DISCORD BOT + WEB • UNIFIED CONTROL</p><h1>Bir mərkəzdən idarə et.</h1><p class="muted">Discord botunun ayarları, kanal mesajları ve AI sohbeti aynı altyapıyı kullanır.</p><section id="app" class="hidden"><div class="card"><div class="row"><div><h2>Sunucu seçimi</h2><select id="guild"></select></div><div><h2>Bağlantı</h2><p id="botstatus" class="status">Kontrol ediliyor…</p></div></div></div><div class="grid"><div class="card"><h2>Bot ayarları</h2><label>AI sağlayıcısı</label><select id="provider"><option value="gemini">Gemini</option><option value="nvidia">NVIDIA</option></select><label>Karşılama mesajı</label><input id="welcome" maxlength="500"><label>Komut öneki</label><input id="prefix" maxlength="3"><label>Dil</label><select id="language"><option>Türkçe</option><option>Azərbaycanca</option><option>English</option></select><label><input id="module_ai" type="checkbox" style="width:auto"> AI modülü</label><label><input id="module_moderation" type="checkbox" style="width:auto"> Moderasyon modülü</label><label><input id="module_entertainment" type="checkbox" style="width:auto"> Eğlence modülü</label><button id="save">Ayarları kaydet</button><p id="settingsstatus" class="status"></p></div><div class="card"><h2>Web AI sohbeti</h2><div id="chatlog" class="chatlog">XFA hazır. Bir soru yazabilirsin.</div><textarea id="prompt" maxlength="3500" placeholder="Botuna bir soru sor…"></textarea><button id="ask">Gönder</button><p id="chatstatus" class="status"></p></div></div><div class="card"><h2>Discord kanalına mesaj gönder</h2><select id="channel"></select><textarea id="message" maxlength="1900" placeholder="Sunucuya gönderilecek mesaj…"></textarea><button id="send">Discord'a gönder</button><p id="sendstatus" class="status"></p></div></section><section id="intro" class="card"><h2>Güvenli Discord bağlantısı</h2><p class="muted">Discord hesabınla giriş yap. Yalnızca Sunucuyu Yönet yetkin olan ve botun bulunduğu sunucular görünür.</p><button id="login2">Discord ile bağlan</button></section></main><script>
const $=id=>document.getElementById(id);let guildId="",csrf="";
async function api(path,options={}){const r=await fetch(path,{...options,credentials:"same-origin",headers:{"content-type":"application/json",...(options.headers||{})}});const d=await r.json().catch(()=>({}));if(!r.ok)throw Error(d.error||"İstek başarısız: "+r.status);return d}
function login(){location.href="/dashboard/login"}$("login").onclick=login;$("login2").onclick=login;
async function load(){try{const me=await api("/api/dashboard/me");if(!me.authenticated){$("who").textContent="Giriş gerekli";return}csrf=me.csrf;$("who").textContent=me.username;$("login").classList.add("hidden");$("logout").classList.remove("hidden");$("intro").classList.add("hidden");$("app").classList.remove("hidden");const data=await api("/api/dashboard/guilds");$("guild").innerHTML=data.guilds.map(g=>'<option value="'+g.id+'">'+g.name.replace(/[<>&"]/g,'')+'</option>').join("");if(data.guilds.length){guildId=data.guilds[0].id;await selectGuild()}}catch(e){$("who").textContent=e.message}}
async function selectGuild(){guildId=$("guild").value;const d=await api("/api/dashboard/guild/"+guildId+"/settings");$("botstatus").textContent="Bot sunucuda • "+d.guild.name;$("provider").value=d.settings.ai_provider||"gemini";$("welcome").value=d.settings.welcome_message||"Aramıza hoş geldin, {kullanıcı}!";$("prefix").value=d.settings.prefix||"!";$("language").value=d.settings.language||"Türkçe";for(const k of ["module_ai","module_moderation","module_entertainment"])$(k).checked=(d.settings[k]??"true")==="true";$("channel").innerHTML=d.channels.map(c=>'<option value="'+c.id+'">#'+c.name.replace(/[<>&"]/g,'')+'</option>').join("")}
$("guild").onchange=()=>selectGuild().catch(e=>$("botstatus").textContent=e.message);
$("save").onclick=async()=>{try{const values={ai_provider:$("provider").value,welcome_message:$("welcome").value,prefix:$("prefix").value,language:$("language").value};for(const k of ["module_ai","module_moderation","module_entertainment"])values[k]=$(k).checked?"true":"false";await api("/api/dashboard/guild/"+guildId+"/settings",{method:"PUT",headers:{"x-csrf-token":csrf},body:JSON.stringify(values)});$("settingsstatus").textContent="Kaydedildi. Bot ayarları D1 üzerinden güncellendi."}catch(e){$("settingsstatus").textContent=e.message}};
$("ask").onclick=async()=>{const prompt=$("prompt").value.trim();if(!prompt)return;$("ask").disabled=true;$("chatlog").textContent+="\n\nSen: "+prompt;$("prompt").value="";try{const d=await api("/api/dashboard/guild/"+guildId+"/chat",{method:"POST",headers:{"x-csrf-token":csrf},body:JSON.stringify({prompt})});$("chatlog").textContent+="\n\nXFA ("+d.provider+"): "+d.answer;$("chatstatus").textContent=d.fallback?"Yedek sağlayıcı kullanıldı.":"Yanıt alındı."}catch(e){$("chatstatus").textContent=e.message}finally{$("ask").disabled=false}};
$("send").onclick=async()=>{try{await api("/api/dashboard/guild/"+guildId+"/send",{method:"POST",headers:{"x-csrf-token":csrf},body:JSON.stringify({channel_id:$("channel").value,message:$("message").value})});$("sendstatus").textContent="Mesaj Discord kanalına gönderildi.";$("message").value=""}catch(e){$("sendstatus").textContent=e.message}};
$("logout").onclick=async()=>{await api("/api/dashboard/logout",{method:"POST",headers:{"x-csrf-token":csrf}});location.reload()};load();
</script></html>`;

export async function handleDashboard(request: Request, env: DashboardEnv): Promise<Response | null> {
  const url = new URL(request.url);
  if (url.pathname === "/manage" || url.pathname === "/manage/") return new Response(PAGE, { headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" } });
  if (url.pathname === "/dashboard/login" && request.method === "GET") {
    const state = b64(crypto.getRandomValues(new Uint8Array(24)));
    const clientId = await env.DISCORD_CLIENT_ID.get();
    const redirect = url.origin + "/dashboard/callback";
    const location = "https://discord.com/oauth2/authorize?client_id=" + encodeURIComponent(clientId) + "&response_type=code&redirect_uri=" + encodeURIComponent(redirect) + "&scope=identify%20guilds";
    return new Response(null, { status: 302, headers: { location: location + "&state=" + state, "set-cookie": "xfa_oauth_state=" + state + "; Path=/dashboard; HttpOnly; Secure; SameSite=Lax; Max-Age=600", "cache-control": "no-store" } });
  }
  if (url.pathname === "/dashboard/callback" && request.method === "GET") {
    const state = url.searchParams.get("state") || "";
    const code = url.searchParams.get("code") || "";
    const stored = (request.headers.get("cookie") || "").split(";").map(v=>v.trim()).find(v=>v.startsWith("xfa_oauth_state="))?.slice(16) || "";
    if (!state || !stored || state !== stored || !code) return new Response("OAuth state doğrulaması başarısız. Yenidən başla.", {status:400});
    const clientId = await env.DISCORD_CLIENT_ID.get(), clientSecret = await env.DISCORD_CLIENT_SECRET.get();
    const form = new URLSearchParams({client_id:clientId,client_secret:clientSecret,grant_type:"authorization_code",code,redirect_uri:url.origin+"/dashboard/callback"});
    const tokenResponse = await fetch("https://discord.com/api/v10/oauth2/token",{method:"POST",headers:{"content-type":"application/x-www-form-urlencoded"},body:form,signal:AbortSignal.timeout(12000)});
    const tokenData = await tokenResponse.json() as any;
    if (!tokenResponse.ok || !tokenData.access_token) return new Response("Discord giriş doğrulanamadı.",{status:401});
    const user = await discord("/users/@me",tokenData.access_token);
    const session:Session={userId:user.id,username:user.global_name||user.username,accessToken:tokenData.access_token,expiresAt:Date.now()+Math.min(Number(tokenData.expires_in)||604800,604800)*1000,csrf:b64(crypto.getRandomValues(new Uint8Array(24)))};
    const signed=await seal(session,await env.DASHBOARD_SESSION_SECRET.get());
    const headers = new Headers({ location: "/manage", "cache-control": "no-store" });\n    headers.append("set-cookie", cookie(signed, Math.floor((session.expiresAt-Date.now())/1000)));\n    headers.append("set-cookie", "xfa_oauth_state=; Path=/dashboard; HttpOnly; Secure; SameSite=Lax; Max-Age=0");\n    return new Response(null, { status: 302, headers });
  }
  if (!url.pathname.startsWith("/api/dashboard/")) return null;
  if (request.method === "OPTIONS") return new Response(null,{status:204,headers:{"access-control-allow-origin":url.origin,"access-control-allow-methods":"GET,POST,PUT,OPTIONS","access-control-allow-headers":"content-type,x-csrf-token","access-control-allow-credentials":"true","vary":"Origin"}});
  const session=await openSession(request,env);
  if(url.pathname==="/api/dashboard/me"&&request.method==="GET")return response(session?{authenticated:true,username:session.username,csrf:session.csrf}:{authenticated:false});
  if(url.pathname==="/api/dashboard/logout"&&request.method==="POST"){
    if(!session||request.headers.get("x-csrf-token")!==session.csrf)return response({error:"CSRF doğrulaması başarısız."},403);
    return new Response(JSON.stringify({ok:true}),{headers:{"content-type":"application/json","set-cookie":cookie("",0),"cache-control":"no-store"}});
  }
  if(!session)return response({error:"Önce Discord hesabınla giriş yap."},401);
  if(["POST","PUT","DELETE"].includes(request.method)&&request.headers.get("x-csrf-token")!==session.csrf)return response({error:"CSRF doğrulaması başarısız."},403);
  try{
    if(url.pathname==="/api/dashboard/guilds"&&request.method==="GET"){
      const guilds=await discord("/users/@me/guilds",session.accessToken) as any[];
      const manageable=guilds.filter(g=>(BigInt(g.permissions||"0")&32n)===32n);
      const present=[] as any[];
      for(const guild of manageable.slice(0,100)){try{await botRequest(env,"/guilds/"+guild.id);present.push({id:guild.id,name:guild.name})}catch{}}
      return response({guilds:present});
    }
    const match=url.pathname.match(/^\/api\/dashboard\/guild\/(\d+)\/(settings|chat|channels|send)$/);
    if(!match)return response({error:"Endpoint bulunamadı."},404);
    const guildId=match[1],action=match[2];
    const guild=await managedGuild(session,env,guildId);
    if(action==="settings"&&request.method==="GET")return response({guild:{id:guild.id,name:guild.name},settings:await getSettings(env,guildId),channels:await botRequest(env,"/guilds/"+guildId+"/channels")});
    if(action==="settings"&&request.method==="PUT"){
      const body=await request.json() as Record<string,string>;
      if(!body||typeof body!=="object"||Array.isArray(body))return response({error:"Geçersiz ayarlar."},400);
      await saveSettings(env,guildId,body);
      return response({ok:true,settings:await getSettings(env,guildId)});
    }
    if(action==="chat"&&request.method==="POST"){
      const body=await request.json() as {prompt?:string};
      const prompt=typeof body.prompt==="string"?body.prompt.trim():"";
      if(!prompt||prompt.length>3500)return response({error:"Soru 1–3500 karakter olmalıdır."},400);
      const settings=await getSettings(env,guildId);
      const provider:AIProvider=settings.ai_provider==="nvidia"?"nvidia":"gemini";
      const result=await generateAI(env,provider,prompt);
      return response({answer:result.text,provider:result.provider,fallback:result.fallback,model:result.model});
    }
    if(action==="send"&&request.method==="POST"){
      const body=await request.json() as {channel_id?:string;message?:string};
      const channelId=body.channel_id||"",message=body.message?.trim()||"";
      if(!/^\d{17,20}$/.test(channelId)||!message||message.length>1900)return response({error:"Kanal veya mesaj geçersiz."},400);
      const channels=await botRequest(env,"/guilds/"+guildId+"/channels") as any[];
      if(!channels.some(c=>c.id===channelId&&c.guild_id===guildId&&[0,5].includes(c.type)))return response({error:"Kanal bu sunucuya ait değil."},403);
      await botRequest(env,"/channels/"+channelId+"/messages",{method:"POST",body:JSON.stringify({content:message,allowed_mentions:{parse:[]}})});
      return response({ok:true});
    }
  }catch(error){return response({error:error instanceof Error?error.message:"İşlem başarısız."},400)}
  return response({error:"Method not allowed."},405);
}
