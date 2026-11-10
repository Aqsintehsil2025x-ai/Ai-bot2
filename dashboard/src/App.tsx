import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { ErrorBoundary } from '@/components/error-boundary';
import { TechHeader, TechHome } from '@/components/tech-home';
import NotFound from '@/pages/not-found';
import {
  ArrowRight,
  Bot,
  Check,
  ChevronRight,
  Flower2,
  Heart,
  LockKeyhole,
  ShieldCheck,
  Sparkles,
  WandSparkles,
} from 'lucide-react';
import { Link, Route, Switch, useLocation, Router as WouterRouter } from 'wouter';



interface PanelSettings {
  ai: boolean;
  moderation: boolean;
  entertainment: boolean;
  prefix: string;
  language: string;
  welcome: string;
}
type PanelSettingsInput = PanelSettings;
interface PanelPayload {
  guild: { id: string; name: string };
  stats: { guilds: number; latency: number };
  settings: PanelSettings;
}

async function panelRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  const response = await fetch(path, { ...init, headers, credentials: 'same-origin' });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = data && typeof data === 'object' && 'error' in data
      ? String((data as { error: unknown }).error)
      : `İstek başarısız (HTTP ${response.status}).`;
    throw Object.assign(new Error(message), { status: response.status, data });
  }
  return data as T;
}

const getPanelSettings = () => panelRequest<PanelPayload>('/api/panel/settings');
const redeemPanel = (body: { code: string }) =>
  panelRequest<PanelPayload>('/api/panel/redeem', { method: 'POST', body: JSON.stringify(body) });
const savePanelSettings = (body: PanelSettingsInput) =>
  panelRequest<PanelPayload>('/api/panel/settings', { method: 'POST', body: JSON.stringify(body) });
const logoutPanel = () =>
  panelRequest<{ success: boolean }>('/api/panel/logout', { method: 'POST' });

const defaults: PanelSettings = {
  ai: true,
  moderation: true,
  entertainment: true,
  prefix: '!',
  language: 'Türkçe',
  welcome: 'Aramıza hoş geldin, {kullanıcı}!',
};

type PanelStatus = 'checking' | 'unauthenticated' | 'connected' | 'error';

function getApiErrorStatus(error: unknown): number | undefined {
  if (!error || typeof error !== 'object' || !('status' in error)) return undefined;
  const status = (error as { status?: unknown }).status;
  return typeof status === 'number' ? status : undefined;
}

function getApiErrorMessage(error: unknown, fallback: string): string {
  if (error && typeof error === 'object' && 'data' in error) {
    const data = (error as { data?: unknown }).data;
    if (data && typeof data === 'object' && 'error' in data) {
      const message = (data as { error?: unknown }).error;
      if (typeof message === 'string') return message;
    }
  }
  return error instanceof Error ? error.message : fallback;
}

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link href="/" className="brand-link focus-ring" data-testid="link-home-brand" aria-label="Xyrin Flower ana sayfa">
      <span className="brand-mark"><Flower2 size={19} strokeWidth={1.8} /></span>
      {!compact && <span className="brand-wordmark">xyrin<span>flower</span></span>}
    </Link>
  );
}

function SiteNav({ active = 'home' }: { active?: 'home' | 'panel' }) {
  return (
    <header className="site-nav">
      <div className="page-wrap nav-inner">
        <Brand />
        <nav className="nav-links" aria-label="Ana menü">
          <a href="/#ozellikler" className="nav-anchor" data-testid="link-features">Özellikler</a>
          <a href="/#yaklasim" className="nav-anchor" data-testid="link-approach">Yaklaşımımız</a>
          <Link href="/panel" className={`nav-panel ${active === 'panel' ? 'nav-panel-active' : ''}`} data-testid="link-panel">
            <span>Panel önizlemesi</span><ArrowRight size={15} />
          </Link>
        </nav>
      </div>
    </header>
  );
}

function BotanicalArt() {
  return (
    <div className="botanical-stage grain" aria-hidden="true">
      <div className="art-disc art-disc-one" />
      <div className="art-disc art-disc-two" />
      <svg className="flower-art" viewBox="0 0 400 440" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M201 238C206 295 174 347 139 391" stroke="#315941" strokeWidth="5" strokeLinecap="round"/>
        <path d="M199 291C229 256 265 253 294 261C272 291 244 312 201 310" fill="#739875" stroke="#315941" strokeWidth="3" strokeLinejoin="round"/>
        <path d="M174 345C142 319 108 320 82 333C109 357 138 372 173 364" fill="#9CB59A" stroke="#315941" strokeWidth="3" strokeLinejoin="round"/>
        <path d="M201 244C164 212 149 175 161 139C189 156 207 187 207 226" fill="#E9A8B6" stroke="#804F5B" strokeWidth="3"/>
        <path d="M207 225C199 176 213 138 249 118C260 154 251 191 222 225" fill="#F3BFC5" stroke="#804F5B" strokeWidth="3"/>
        <path d="M218 227C241 183 278 165 316 175C299 209 267 231 228 237" fill="#DD91A5" stroke="#804F5B" strokeWidth="3"/>
        <path d="M215 237C261 225 301 237 322 270C287 282 250 273 219 247" fill="#F0B7BB" stroke="#804F5B" strokeWidth="3"/>
        <path d="M205 242C217 284 203 319 170 340C153 307 162 271 194 243" fill="#D9859D" stroke="#804F5B" strokeWidth="3"/>
        <path d="M193 235C155 248 119 239 96 209C127 193 166 199 196 222" fill="#F1C4C4" stroke="#804F5B" strokeWidth="3"/>
        <circle cx="207" cy="231" r="18" fill="#D47A51" stroke="#804F5B" strokeWidth="3"/>
        <circle cx="205" cy="227" r="4" fill="#F3D8A2"/><circle cx="216" cy="235" r="3" fill="#F3D8A2"/><circle cx="198" cy="239" r="3" fill="#F3D8A2"/>
        <path d="M300 113C317 97 342 94 361 105" stroke="#315941" strokeWidth="2" strokeLinecap="round"/>
        <circle cx="363" cy="105" r="5" fill="#E57C5F"/>
        <path d="M90 123C103 107 124 102 144 108" stroke="#315941" strokeWidth="2" strokeLinecap="round"/>
        <circle cx="146" cy="108" r="4" fill="#E57C5F"/>
      </svg>
      <div className="art-caption"><span className="caption-dot" />DİJİTAL TOPLULUKLAR İÇİN</div>
      <div className="art-label"><span>iyi hissettiren</span><br/>bir yardımcı.</div>
    </div>
  );
}

function FeatureBlock({ index, title, description, icon, tone, items }: {
  index: string; title: string; description: string; icon: ReactNode; tone: string; items: string[];
}) {
  return (
    <article className={`feature-block ${tone}`} data-testid={`feature-${index}`}>
      <div className="feature-top"><span className="feature-index">{index}</span><span className="feature-icon">{icon}</span></div>
      <h3>{title}</h3>
      <p>{description}</p>
      <ul>{items.map((item) => <li key={item}><Check size={14} />{item}</li>)}</ul>
      <span className="feature-orbit" aria-hidden="true" />
    </article>
  );
}

function Home() {
  return <TechHome />;
}

function ToggleRow({ title, description, icon, enabled, onChange, testId }: {
  title: string; description: string; icon: ReactNode; enabled: boolean; onChange: () => void; testId: string;
}) {
  return (
    <div className="toggle-row">
      <div className="toggle-icon">{icon}</div>
      <div className="toggle-copy"><div className="toggle-title">{title}</div><div className="toggle-description">{description}</div></div>
      <button type="button" role="switch" aria-checked={enabled} aria-label={`${title} özelliğini ${enabled ? 'kapat' : 'aç'}`} onClick={onChange} className={`switch ${enabled ? 'switch-on' : ''} focus-ring`} data-testid={testId}>
        <span className="toggle-track"><span className="toggle-knob"/></span>
      </button>
      <span className={`switch-state ${enabled ? 'state-on' : ''}`}>{enabled ? 'Açık' : 'Kapalı'}</span>
    </div>
  );
}

function Panel() {
  const [settings, setSettings] = useState<PanelSettings>(defaults);
  const [savedSettings, setSavedSettings] = useState<PanelSettings>(defaults);
  const [payload, setPayload] = useState<PanelPayload | null>(null);
  const [status, setStatus] = useState<PanelStatus>('checking');
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [saveMessage, setSaveMessage] = useState('');

  useEffect(() => {
    let active = true;
    getPanelSettings()
      .then((data) => {
        if (!active) return;
        setPayload(data);
        setSettings(data.settings);
        setSavedSettings(data.settings);
        setStatus('connected');
      })
      .catch((error: unknown) => {
        if (!active) return;
        setStatus(getApiErrorStatus(error) === 401 ? 'unauthenticated' : 'error');
        setSaveMessage(getApiErrorMessage(error, 'Bot servisine bağlanılamadı.'));
      });
    return () => { active = false; };
  }, []);

  const toggle = (key: 'ai' | 'moderation' | 'entertainment') => {
    setSettings((current) => ({ ...current, [key]: !current[key] }));
    setSaveMessage('');
  };

  const setField = (key: 'prefix' | 'language' | 'welcome', value: string) => {
    setSettings((current) => ({ ...current, [key]: value }));
    setSaveMessage('');
  };

  const redeemCode = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedCode = code.trim().toUpperCase();
    if (!/^[A-F0-9]{6}$/.test(normalizedCode)) {
      setSaveMessage('Discord üzerinden aldığın 6 haneli kodu gir.');
      return;
    }
    setBusy(true);
    setSaveMessage('');
    try {
      const data = await redeemPanel({ code: normalizedCode });
      setPayload(data);
      setSettings(data.settings);
      setSavedSettings(data.settings);
      setStatus('connected');
      setCode('');
    } catch (error) {
      setSaveMessage(getApiErrorMessage(error, 'Kod doğrulanamadı. Yeni kod almak için Discord’da !panel yaz.'));
    } finally {
      setBusy(false);
    }
  };

  const saveBasics = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setSaveMessage('');
    try {
      const input: PanelSettingsInput = { ...settings };
      const data = await savePanelSettings(input);
      setPayload(data);
      setSettings(data.settings);
      setSavedSettings(data.settings);
      setSaveMessage('Ayarlar canlı bota kaydedildi.');
    } catch (error) {
      if (getApiErrorStatus(error) === 401) setStatus('unauthenticated');
      setSaveMessage(getApiErrorMessage(error, 'Ayarları kaydetmək mümkün olmadı.'));
    } finally {
      setBusy(false);
    }
  };

  const reset = () => {
    setSettings({ ...defaults });
    setSaveMessage('Varsayılanlar seçildi. Kalıcı olması için Kaydet’e bas.');
  };

  const logout = async () => {
    setBusy(true);
    try {
      await logoutPanel();
    } catch {
      // Clear the local view even if the remote session has already expired.
    } finally {
      setPayload(null);
      setSettings({ ...defaults });
      setSavedSettings({ ...defaults });
      setStatus('unauthenticated');
      setCode('');
      setSaveMessage('Oturum kapatıldı.');
      setBusy(false);
    }
  };

  if (status === 'checking') {
    return (
      <main className="panel-page tech-panel-page">
        <TechHeader activePanel />
        <div className="panel-wrap"><div className="panel-heading"><div><div className="eyebrow"><span className="eyebrow-line"/>KONTROL ALANI</div><h1 className="font-display">Bağlantı <em>kontrol ediliyor.</em></h1><p>Bot oturumun doğrulanıyor.</p></div></div></div>
      </main>
    );
  }

  if (status !== 'connected' || !payload) {
    return (
      <main className="panel-page tech-panel-page">
        <TechHeader activePanel />
        <div className="panel-wrap">
          <div className="panel-breadcrumb"><Link href="/">Ana sayfa</Link><ChevronRight size={14}/><span>Kontrol paneli</span></div>
          <div className="panel-heading">
            <div><div className="eyebrow"><span className="eyebrow-line"/>GÜVENLİ GİRİŞ</div><h1 className="font-display">Botuna <em>bağlan.</em></h1><p>Discord sunucunda <strong>!panel</strong> komutunu kullan ve sana gönderilen 6 haneli kodu gir.</p></div>
            <div className="preview-status"><span className="status-ring"><span/></span><div><strong>{status === 'error' ? 'Sunucuya ulaşılamıyor' : 'Oturum açılmadı'}</strong><small>Discord kodu gerekli</small></div></div>
          </div>
          <section className="panel-card settings-card" style={{maxWidth: 560}}>
            <div className="card-heading"><div><div className="card-kicker font-mono">PANEL GİRİŞİ</div><h2>Tek kullanımlık kod</h2><p>Kod 10 dakika geçerlidir ve yalnızca bir kez kullanılabilir.</p></div><span className="card-symbol"><LockKeyhole size={20}/></span></div>
            <form onSubmit={redeemCode} className="settings-form">
              <label className="field-label" htmlFor="panel-code">6 haneli Discord kodu<span>Örnek biçim: A1B2C3</span></label>
              <input id="panel-code" type="text" inputMode="text" autoComplete="one-time-code" maxLength={6} minLength={6} pattern="[A-Fa-f0-9]{6}" value={code} onChange={(event) => setCode(event.target.value.toUpperCase())} className="form-select focus-ring" aria-label="6 haneli panel kodu" required />
              <div className="form-footer"><span className="form-hint" role="status">{saveMessage || (status === 'error' ? 'Bağlantıyı ve sunucu ayarlarını kontrol et.' : 'Kodunu kimseyle paylaşma.')}</span><button className="button-primary save-button focus-ring" type="submit" disabled={busy}>{busy ? 'Kontrol ediliyor…' : 'Panele bağlan'} <ArrowRight size={15}/></button></div>
            </form>
          </section>
        </div>
      </main>
    );
  }

  const isSaved = JSON.stringify(savedSettings) === JSON.stringify(settings);

  return (
    <main className="panel-page tech-panel-page">
      <TechHeader activePanel />
      <div className="panel-wrap">
        <div className="panel-breadcrumb"><Link href="/">Ana sayfa</Link><ChevronRight size={14}/><span>Canlı kontrol paneli</span></div>
        <div className="panel-heading">
          <div><div className="eyebrow"><span className="eyebrow-line"/>KONTROL ALANI / CANLI</div><h1 className="font-display">Botunu <em>tanı.</em></h1><p><strong>{payload.guild.name}</strong> sunucusunun ayarlarını buradan yönet.</p></div>
          <div className="preview-status"><span className="status-ring"><span/></span><div><strong>Bot bağlantısı aktif</strong><small>{payload.stats.guilds} sunucu · {payload.stats.latency} ms gecikme</small></div></div>
        </div>

        <div className="panel-alert" role="status" data-testid="status-live-connection">
          <span className="alert-icon"><Check size={17}/></span>
          <div><strong>Canlı Discord botuna bağlı</strong><p>Değişiklikleri kaydettiğinde seçili sunucunun ayarları botta güncellenir.</p></div>
          <span className="alert-label">CANLI BAĞLANTI</span>
        </div>

        <div className="panel-layout">
          <div className="panel-main">
            <section className="panel-card modules-card">
              <div className="card-heading"><div><div className="card-kicker font-mono">01 — MODÜLLER</div><h2>Hangi tarafı açık?</h2><p>Değişiklikleri kaydetmeyi unutma.</p></div><span className="card-symbol"><WandSparkles size={20}/></span></div>
              <div className="toggle-list">
                <ToggleRow title="Yapay zekâ sohbeti" description="Doğal ve yardımcı sohbet deneyimi" icon={<Bot size={19}/>} enabled={settings.ai} onChange={() => toggle('ai')} testId="switch-ai"/>
                <ToggleRow title="Akıllı moderasyon" description="Topluluk düzeni için koruma araçları" icon={<ShieldCheck size={19}/>} enabled={settings.moderation} onChange={() => toggle('moderation')} testId="switch-moderation"/>
                <ToggleRow title="Eğlence" description="Sohbete küçük, keyifli dokunuşlar" icon={<Sparkles size={19}/>} enabled={settings.entertainment} onChange={() => toggle('entertainment')} testId="switch-entertainment"/>
              </div>
              <div className="module-foot"><span className="tiny-status"/>{Object.values({ai: settings.ai, moderation: settings.moderation, entertainment: settings.entertainment}).filter(Boolean).length} modül açık <span className="module-foot-note">— canlı bot ayarları</span></div>
            </section>

            <section className="panel-card settings-card">
              <div className="card-heading"><div><div className="card-kicker font-mono">02 — TEMEL AYARLAR</div><h2>İnce ayar senin.</h2><p>Bu değerler Discord botuna kaydedilir.</p></div><span className="card-symbol card-symbol-rose"><Heart size={19}/></span></div>
              <form onSubmit={saveBasics} className="settings-form">
                <label className="field-label" htmlFor="prefix">Komut öneki<span>1–5 karakter, boşluk ve / kullanılamaz</span></label>
                <div className="input-wrap prefix-wrap"><span className="input-prefix">ÖR.</span><input id="prefix" type="text" maxLength={5} value={settings.prefix} onChange={(event) => setField('prefix', event.target.value)} data-testid="input-prefix" aria-label="Komut öneki"/></div>
                <label className="field-label" htmlFor="language">Yanıt dili<span>Botun konuşacağı dil</span></label>
                <select id="language" value={settings.language} onChange={(event) => setField('language', event.target.value)} className="form-select focus-ring" data-testid="select-language">
                  <option>Türkçe</option><option>English</option><option>Azərbaycanca</option>
                </select>
                <label className="field-label" htmlFor="welcome">Karşılama mesajı<span><code>{'{kullanıcı}'}</code> veya <code>{'{kullanici}'}</code> yer tutucusunu kullanabilirsin</span></label>
                <textarea id="welcome" rows={3} maxLength={300} value={settings.welcome} onChange={(event) => setField('welcome', event.target.value)} className="form-textarea focus-ring" data-testid="input-welcome"/>
                <div className="form-footer"><span className="form-hint" role="status">{saveMessage || (isSaved ? 'Tüm ayarlar kayıtlı.' : 'Kaydedilmemiş değişikliklerin var.')}</span><button className="button-primary save-button focus-ring" type="submit" disabled={busy}>{busy ? 'Kaydediliyor…' : 'Canlı bota kaydet'} <Check size={15}/></button></div>
              </form>
            </section>
          </div>

          <aside className="panel-aside">
            <section className="connection-card">
              <div className="connection-top"><span className="connection-icon"><Bot size={21}/></span><span className="connection-badge"><span/>BAĞLANDI</span></div>
              <div className="card-kicker font-mono">03 — SUNUCU BİLGİSİ</div>
              <h2>{payload.guild.name}</h2>
              <p>Yönetim iznin doğrulandı. Bu oturum yalnızca bu Discord sunucusu için geçerlidir.</p>
              <div className="connection-rule"/>
              <div className="connection-next"><span className="next-number">01</span><span>{payload.stats.guilds} sunucu<br/>{payload.stats.latency} ms gecikme</span></div>
              <button type="button" className="reset-button focus-ring" onClick={logout} disabled={busy}><LockKeyhole size={15}/>Oturumu kapat</button>
              <span className="connection-foot">XYRIN FLOWER / CANLI PANEL</span>
            </section>
            <button type="button" className="reset-button focus-ring" onClick={reset}>Varsayılanları yükle <ArrowRight size={14}/></button>
            <div className="saved-summary" data-testid="text-saved-state"><span className="summary-dot"/>{isSaved ? 'Temel ayarlar kayıtlı' : 'Kaydedilmemiş değişiklik var'}</div>
          </aside>
        </div>
        <div className="panel-bottom-note"><span>XYRIN FLOWER / CANLI PANEL</span><span>Değişiklikler {payload.guild.name} sunucusuna uygulanır.</span><Link href="/">Siteye dön <ArrowRight size={13}/></Link></div>
      </div>
    </main>
  );
}

function Router() {
  return (
    <RoutedErrorBoundary>
      <Switch>
        <Route path="/" component={Home}/>
        <Route path="/panel" component={Panel}/>
        <Route component={NotFound}/>
      </Switch>
    </RoutedErrorBoundary>
  );
}

function RoutedErrorBoundary({ children }: { children: ReactNode }) {
  const [location] = useLocation();
  return <ErrorBoundary resetKey={location}>{children}</ErrorBoundary>;
}

function App() {
  return (
    <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, '')}>
      <Router/>
    </WouterRouter>
  );
}

export default App;
