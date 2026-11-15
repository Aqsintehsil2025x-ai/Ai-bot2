import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, Maximize2, Sparkles, Orbit, Activity, MessageCircle, Bot, Grid3X3, Search, Settings, Zap, Send, Plus, Smile } from 'lucide-react';
import { Link } from 'wouter';
import './universe.css';

type Scene = 'black-hole' | 'pulsar';

function SpaceCanvas({ scene }: { scene: Scene }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext('2d');
    if (!canvas || !context) return;
    let frame = 0;
    let raf = 0;
    let width = 0;
    let height = 0;
    let dpr = 1;
    let stars: { x: number; y: number; r: number; a: number; p: number }[] = [];

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = rect.width;
      height = rect.height;
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      context.setTransform(dpr, 0, 0, dpr, 0, 0);
      const count = Math.min(520, Math.floor((width * height) / 2100));
      stars = Array.from({ length: count }, () => ({
        x: Math.random() * width, y: Math.random() * height,
        r: Math.random() * 1.35 + .2, a: Math.random() * .75 + .15, p: Math.random() * Math.PI * 2,
      }));
    };

    const glow = (x: number, y: number, radius: number, color: string) => {
      const g = context.createRadialGradient(x, y, 0, x, y, radius);
      g.addColorStop(0, color); g.addColorStop(1, 'rgba(20,5,38,0)');
      context.fillStyle = g; context.fillRect(x - radius, y - radius, radius * 2, radius * 2);
    };

    const draw = () => {
      frame += .008;
      context.clearRect(0, 0, width, height);
      const bg = context.createLinearGradient(0, 0, width, height);
      bg.addColorStop(0, '#05030d'); bg.addColorStop(.48, '#10051e'); bg.addColorStop(1, '#070312');
      context.fillStyle = bg; context.fillRect(0, 0, width, height);
      glow(width * .48, height * .47, Math.max(width, height) * .58, 'rgba(91,22,160,.28)');
      glow(width * .12, height * .78, width * .32, 'rgba(87,24,180,.2)');
      stars.forEach((s) => {
        const twinkle = .55 + .45 * Math.sin(frame * 2 + s.p);
        context.fillStyle = `rgba(218,190,255,${s.a * twinkle})`;
        context.beginPath(); context.arc(s.x, s.y, s.r, 0, Math.PI * 2); context.fill();
      });

      if (scene === 'black-hole') {
        const cx = width * .64, cy = height * .43;
        const scale = Math.min(width, height);
        glow(cx, cy, scale * .42, 'rgba(130,38,255,.22)');
        context.save(); context.translate(cx, cy); context.rotate(-.12 + Math.sin(frame * .2) * .018);
        context.scale(1, .31);
        for (let i = 0; i < 7; i++) {
          context.beginPath(); context.ellipse(0, 0, scale * (.17 + i * .026), scale * (.17 + i * .026), 0, 0, Math.PI * 2);
          context.strokeStyle = `rgba(255,${120 + i * 12},${70 + i * 10},${.12 + (6-i)*.025})`;
          context.lineWidth = 3 + (6-i)*1.2; context.shadowBlur = 22; context.shadowColor = '#ff7b36'; context.stroke();
        }
        context.restore();
        context.save(); context.translate(cx, cy); context.rotate(-.12);
        context.scale(1, .34);
        const disk = context.createRadialGradient(0, 0, scale * .09, 0, 0, scale * .34);
        disk.addColorStop(0, '#05020a'); disk.addColorStop(.3, '#1b0826'); disk.addColorStop(.58, '#ff6b35'); disk.addColorStop(.7, '#f8c17d'); disk.addColorStop(.78, 'rgba(174,75,255,.65)'); disk.addColorStop(1, 'rgba(50,8,90,0)');
        context.fillStyle = disk; context.beginPath(); context.ellipse(0, 0, scale * .35, scale * .35, 0, 0, Math.PI * 2); context.fill();
        context.restore();
        glow(cx, cy, scale * .09, 'rgba(0,0,0,.96)');
        context.beginPath(); context.arc(cx, cy, scale * .105, 0, Math.PI * 2); context.fillStyle = '#020106'; context.fill();
        context.beginPath(); context.arc(cx, cy, scale * .112, 0, Math.PI * 2); context.strokeStyle = 'rgba(255,205,160,.85)'; context.lineWidth = 2; context.shadowBlur = 28; context.shadowColor = '#ff8b45'; context.stroke(); context.shadowBlur = 0;
        // Bright, gravitationally-lensed upper and lower arcs.
        context.beginPath(); context.ellipse(cx, cy - scale * .012, scale * .23, scale * .075, -.12, Math.PI * 1.05, Math.PI * 1.92);
        context.strokeStyle = '#ffd5a2'; context.lineWidth = 5; context.shadowBlur = 25; context.shadowColor = '#ff8a42'; context.stroke(); context.shadowBlur = 0;
        for (let i = 0; i < 90; i++) {
          const a = i * 2.399 + frame * (i % 2 ? .25 : -.16);
          const r = scale * (.15 + (i % 17) / 100);
          const x = cx + Math.cos(a) * r, y = cy + Math.sin(a) * r * .32;
          context.fillStyle = i % 3 ? 'rgba(255,180,130,.65)' : 'rgba(202,130,255,.8)';
          context.beginPath(); context.arc(x, y, (i % 3) + .5, 0, Math.PI * 2); context.fill();
        }
      } else {
        const cx = width * .48, cy = height * .48;
        const scale = Math.min(width, height);
        glow(cx, cy, scale * .3, 'rgba(100,36,255,.35)');
        // Magnetic field lines
        context.save(); context.translate(cx, cy);
        for (let i = 0; i < 12; i++) {
          const a = (i / 12) * Math.PI + frame * .16;
          context.save(); context.rotate(a);
          context.beginPath(); context.moveTo(0, -scale * .075); context.bezierCurveTo(scale * .24, -scale * .3, scale * .24, scale * .3, 0, scale * .075);
          context.strokeStyle = 'rgba(117,106,255,.36)'; context.lineWidth = 1.3; context.shadowBlur = 12; context.shadowColor = '#795bff'; context.stroke(); context.restore();
        }
        context.restore();
        // Sweeping polar beams
        for (const direction of [-1, 1]) {
          context.save(); context.translate(cx, cy); context.rotate(frame * 1.8);
          const beam = context.createLinearGradient(0, 0, 0, direction * scale * .65);
          beam.addColorStop(0, 'rgba(255,255,255,.9)'); beam.addColorStop(.12, 'rgba(120,100,255,.42)'); beam.addColorStop(1, 'rgba(112,70,255,0)');
          context.fillStyle = beam; context.beginPath(); context.moveTo(-scale * .018, 0); context.lineTo(-scale * .12, direction * scale * .65); context.lineTo(scale * .12, direction * scale * .65); context.lineTo(scale * .018, 0); context.closePath(); context.fill(); context.restore();
        }
        glow(cx, cy, scale * .105, 'rgba(111,65,255,.85)');
        const star = context.createRadialGradient(cx - scale * .025, cy - scale * .025, 0, cx, cy, scale * .075);
        star.addColorStop(0, '#fff'); star.addColorStop(.25, '#d7c9ff'); star.addColorStop(.62, '#8255ff'); star.addColorStop(1, '#1c0b52');
        context.fillStyle = star; context.beginPath(); context.arc(cx, cy, scale * .067, 0, Math.PI * 2); context.fill();
        context.strokeStyle = 'rgba(225,210,255,.9)'; context.lineWidth = 2; context.shadowBlur = 25; context.shadowColor = '#a875ff'; context.stroke(); context.shadowBlur = 0;
        for (let i = 0; i < 50; i++) {
          const a = i * 2.4 + frame * .6, r = scale * (.09 + (i % 12) * .018);
          context.fillStyle = 'rgba(175,140,255,.7)'; context.beginPath(); context.arc(cx + Math.cos(a) * r, cy + Math.sin(a) * r, 1 + (i % 2), 0, Math.PI * 2); context.fill();
        }
      }
      raf = window.requestAnimationFrame(draw);
    };
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    raf = window.requestAnimationFrame(draw);
    return () => { window.cancelAnimationFrame(raf); observer.disconnect(); };
  }, [scene]);

  return <canvas ref={canvasRef} className="universe-canvas" aria-label={scene === 'black-hole' ? 'Animasyonlu qara dəlik' : 'Animasyonlu pulsar ulduzu'} />;
}

export default function UniversePage() {
  const [scene, setScene] = useState<Scene>('black-hole');
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<{ role: 'user' | 'model'; content: string }[]>([
    { role: 'model', content: 'Merhaba! Ben XFA. Bir fikir, soru veya görev yaz; birlikte başlayalım.' },
  ]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [auth, setAuth] = useState<{ loading: boolean; authenticated: boolean; csrf: string; name: string; google: boolean }>({
    loading: true, authenticated: false, csrf: '', name: '', google: false,
  });
  const [stats, setStats] = useState<{ guilds: number; members: number; latency: number; ready: boolean }>({
    guilds: 0, members: 0, latency: 0, ready: false,
  });
  const rootRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let active = true;
    fetch('/auth/me', { credentials: 'same-origin' })
      .then(async (response) => ({ response, data: await response.json() }))
      .then(({ response, data }) => {
        if (!active) return;
        setAuth({
          loading: false,
          authenticated: response.ok && data.authenticated === true,
          csrf: typeof data.csrf_token === 'string' ? data.csrf_token : '',
          name: data.user?.name || '',
          google: false,
        });
      })
      .catch(() => { if (active) setAuth((current) => ({ ...current, loading: false })); });
    fetch('/auth/providers', { credentials: 'same-origin' })
      .then((response) => response.json())
      .then((data) => { if (active) setAuth((current) => ({ ...current, google: data.google === true })); })
      .catch(() => undefined);
    const loadStats = () => fetch('/api/stats', { credentials: 'same-origin' })
      .then((response) => response.json())
      .then((data) => { if (active) setStats({ guilds: Number(data.guilds) || 0, members: Number(data.members) || 0, latency: Number(data.latency) || 0, ready: data.ready === true }); })
      .catch(() => undefined);
    void loadStats();
    const timer = window.setInterval(loadStats, 30000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);

  async function toggleFullscreen() {
    if (!document.fullscreenElement) await rootRef.current?.requestFullscreen?.();
    else await document.exitFullscreen();
  }

  async function sendMessage(event?: React.FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    const content = message.trim();
    if (!content || busy) return;
    if (!auth.authenticated) {
      setError('Söhbət üçün əvvəlcə XFA hesabına daxil ol.');
      return;
    }
    const next = [...messages, { role: 'user' as const, content }];
    setMessages(next);
    setMessage('');
    setBusy(true);
    setError('');
    try {
      const response = await fetch('/xfa/api/chat', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': auth.csrf },
        body: JSON.stringify({ messages: next.slice(-20) }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || `Sohbet isteği başarısız (HTTP ${response.status}).`);
      setMessages((current) => [...current, { role: 'model', content: data.reply || 'Şu anda yanıt oluşturamadım.' }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'XFA bağlantısı başarısız oldu.');
    } finally {
      setBusy(false);
      inputRef.current?.focus();
    }
  }

  const quickPrompts = ['Kara delikler nasıl oluşur?', 'Bana bir Python örneği yaz', 'Yeni bir proje fikri bul', 'Bugünkü hedeflerimi planla'];

  return (
    <main className="universe-page" ref={rootRef}>
      <SpaceCanvas scene={scene} />
      <div className="universe-vignette" />
      <aside className="universe-sidebar">
        <Link href="/" className="universe-brand"><span className="universe-flower">✿</span><strong>XFA</strong><small>XYRIN FLOWER AI</small></Link>
        <div className="universe-nav-label">ÇALIŞMA ALANI</div>
        <a className="universe-nav-item active" href="#chat"><MessageCircle size={16}/> Sohbet</a>
        <a className="universe-nav-item" href="/xfa"><Bot size={16}/> Yapay Zekâ Ajanı</a>
        <a className="universe-nav-item" href="/panel"><Grid3X3 size={16}/> Çalışma Alanı</a>
        <a className="universe-nav-item" href="/xfa"><Search size={16}/> Web inceleme</a>
        <a className="universe-nav-item" href="/panel"><Settings size={16}/> Ayarlar</a>
        <div className="universe-premium"><strong>👑 XFA</strong><p>Herkes için ücretsiz yapay zekâ deneyimi.</p><a href="/panel">Kontrol paneli →</a></div>
        <div className="universe-sidebar-foot">© 2026 XFA.<br/>Herkes için geliştirildi. ♡</div>
      </aside>
      <header className="universe-topbar">
        <Link href="/" className="universe-back"><ArrowLeft size={15}/> XFA'ya dön</Link>
        <button className="universe-search" type="button" onClick={() => inputRef.current?.focus()}><Search size={14}/> Sohbette ara veya mesaj yaz... <kbd>Ctrl + K</kbd></button>
        <div className="universe-status"><i className={stats.ready ? '' : 'offline'}/> {auth.authenticated ? (auth.name || 'Hesabım') : 'Misafir'} <span>◉</span><b>{auth.name ? auth.name.slice(0,1).toUpperCase() : 'A'}</b></div>
      </header>
      <section className="universe-center">
        <div className="universe-brand-title"><h1>XFA</h1><h2>Xyrin Flower AI</h2><p>Sonsuz imkânlar. Tamamen <em>ücretsiz.</em></p><div className="universe-pills"><span>∞ Ücretsiz erişim</span><span>♢ Güvenli çalışma</span><span>ϟ Canlı AI sohbeti</span></div></div>
        <div className="universe-chat" id="chat">
          <div className="universe-chat-head"><span className="universe-avatar">✿</span><div><strong>{auth.authenticated ? `Merhaba, ${auth.name || 'gezgin'}! 👋` : 'XFA Universe’e hoş geldin! 👋'}</strong><small>{auth.authenticated ? 'XFA hazır. Ne yapmak istersin?' : 'AI sohbetini kullanmak için hesabına giriş yap.'}</small></div></div>
          {!auth.authenticated && !auth.loading && <div className="universe-login"><span>Giriş yapmadan sohbet başlatılamaz.</span><a href={auth.google ? '/auth/login/google' : '/xfa'}>{auth.google ? 'Google ile giriş yap' : 'XFA giriş sayfasını aç'} <ArrowRight size={14}/></a></div>}
          <div className="universe-quick">{quickPrompts.map((prompt) => <button key={prompt} type="button" onClick={() => { setMessage(prompt); inputRef.current?.focus(); }}>✦ {prompt}</button>)}</div>
          <div className="universe-transcript" aria-live="polite">
            {messages.map((item, index) => <div className={item.role === 'user' ? 'universe-user-message' : 'universe-message'} key={index}>{item.role === 'model' && <small>XFA</small>}{item.content}</div>)}
            {busy && <div className="universe-message universe-thinking"><small>XFA</small><span className="universe-dots">Yanıt hazırlanıyor</span></div>}
          </div>
          {error && <p className="universe-error" role="alert">{error}</p>}
          <form className="universe-input" onSubmit={sendMessage}>
            <button type="button" aria-label="Mesaj alanına odaklan" onClick={() => inputRef.current?.focus()}><Plus size={19}/></button><button type="button" aria-label="Örnek istem ekle" onClick={() => setMessage('Lütfen bunu adım adım açıkla: ')}><Smile size={18}/></button><input ref={inputRef} value={message} onChange={(event) => setMessage(event.target.value)} placeholder={auth.authenticated ? 'XFA’ya mesajını yaz...' : 'Önce giriş yapmalısın...'} disabled={!auth.authenticated || busy} /><button className="universe-send" type="submit" disabled={!auth.authenticated || busy || !message.trim()} aria-label="Mesajı gönder"><Send size={19}/></button>
          </form>
        </div>
      </section>
      <aside className="universe-right">
        <section className="universe-stat-card"><h3>▥ &nbsp; XFA Canlı İstatistikleri</h3><div><Sparkles/><strong>{stats.members.toLocaleString('tr-TR')}<small>Discord Üyesi</small></strong></div><div><Grid3X3/><strong>{stats.guilds}<small>Sunucu</small></strong></div><div><Zap/><strong>{stats.ready ? `${stats.latency} ms` : 'Çevrimdışı'}<small>Bot gecikmesi</small></strong></div><svg viewBox="0 0 260 75" preserveAspectRatio="none"><path d="M0 65 C30 61 35 59 55 51 S82 49 100 42 S126 49 148 32 S177 35 193 22 S221 18 260 2" fill="none" stroke="#b34dff" strokeWidth="2.5"/></svg></section>
        <section className="universe-ecosystem"><h3><Orbit size={15}/> XFA Ekosistemi <span>CANLI</span></h3><p>◉ &nbsp; Discord Bot <small>{stats.ready ? '● Çevrimiçi' : '● Çevrimdışı'}</small></p><p>◎ &nbsp; Web Platformu <small>● Çevrimiçi</small></p><p>▣ &nbsp; XFA Ajan API <small>{auth.authenticated ? '● Oturum açık' : '● Giriş gerekli'}</small></p></section>
      </aside>
      <div className="universe-quality"><strong>HD</strong><span>ADAPTİF YÜKSEK ÇÖZÜNÜRLÜK<br/><small>EKRANINA GÖRE RENDER</small></span><i/></div>
      <div className="universe-scene-switch"><div><strong>{scene === 'black-hole' ? 'Qara Dəlik' : 'Pulsar Ulduzu'}</strong><small>Canlı kosmik simulyasiya</small></div><button className={scene === 'black-hole' ? 'selected' : ''} onClick={() => setScene('black-hole')}>Qara dəlik</button><button className={scene === 'pulsar' ? 'selected' : ''} onClick={() => setScene('pulsar')}>Pulsar</button><button className="universe-fullscreen" onClick={toggleFullscreen} aria-label="Tam ekran"><Maximize2 size={17}/></button></div>
      <div className="universe-live"><Activity size={13}/> CANLI ANİMASİYA</div>
    </main>
  );
}
