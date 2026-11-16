import { useEffect, useRef, useState, type FormEvent } from 'react';
import { ArrowLeft, ArrowRight, Maximize2, Sparkles, Orbit, Activity, MessageCircle, Bot, Grid3X3, Search, Settings, Zap, Send, Plus, Smile, Cpu, X, BookOpen, Paperclip, FileText, Volume2, Globe, Mic, Square } from 'lucide-react';
import { Link } from 'wouter';
import './universe.css';

function SpaceCanvas({ quality }: { quality: 'ultra' | 'balanced' | 'eco' }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext('2d', { alpha: true, desynchronized: true });
    if (!canvas || !context) return;
    let raf = 0, width = 0, height = 0, dpr = 1, time = 0, last = 0;
    let stars: { x: number; y: number; r: number; alpha: number; phase: number; speed: number; layer: number }[] = [];
    let dust: { x: number; y: number; r: number; vx: number; vy: number; alpha: number }[] = [];
    let meteors: { x: number; y: number; vx: number; vy: number; life: number; max: number }[] = [];
    const resize = () => {
      const rect = canvas.getBoundingClientRect(); width = Math.max(1, rect.width); height = Math.max(1, rect.height);
      const pixelBudget = 6000000; dpr = Math.min(window.devicePixelRatio || 1, 2.25, Math.sqrt(pixelBudget / (width * height)));
      canvas.width = Math.round(width * dpr); canvas.height = Math.round(height * dpr); context.setTransform(dpr, 0, 0, dpr, 0, 0);
      const starLimit = quality === 'ultra' ? 1100 : quality === 'balanced' ? 650 : 300;
      const density = quality === 'ultra' ? 1250 : quality === 'balanced' ? 2100 : 3800;
      stars = Array.from({ length: Math.min(starLimit, Math.floor(width * height / density)) }, () => { const layer = Math.random(); return { x: Math.random() * width, y: Math.random() * height, r: .25 + Math.random() * (layer > .92 ? 1.65 : .8), alpha: .22 + Math.random() * .72, phase: Math.random() * Math.PI * 2, speed: .25 + Math.random() * 1.2, layer }; });
      dust = Array.from({ length: Math.min(quality === 'ultra' ? 180 : quality === 'balanced' ? 90 : 35, Math.floor(width * height / (quality === 'ultra' ? 9000 : quality === 'balanced' ? 18000 : 36000))) }, () => ({ x: Math.random() * width, y: Math.random() * height, r: .5 + Math.random() * 1.8, vx: (Math.random() - .5) * .13, vy: -.08 - Math.random() * .18, alpha: .08 + Math.random() * .22 }));
    };
    const nebula = (x: number, y: number, radius: number, color: string, drift: number) => {
      context.save(); context.translate(x + Math.sin(time * drift) * 24, y + Math.cos(time * drift * .7) * 16);
      const g = context.createRadialGradient(0, 0, 0, 0, 0, radius); g.addColorStop(0, color); g.addColorStop(.45, 'rgba(91,30,150,.10)'); g.addColorStop(1, 'rgba(18,5,35,0)');
      context.fillStyle = g; context.fillRect(-radius, -radius, radius * 2, radius * 2); context.restore();
    };
    const draw = (now: number) => {
      if (document.hidden) { raf = 0; return; }
      const delta = Math.min(2.2, (now - (last || now)) / 16.67); last = now; time += delta * .008;
      context.clearRect(0, 0, width, height);
      const base = context.createLinearGradient(0, 0, width, height); base.addColorStop(0, 'rgba(5,2,13,.18)'); base.addColorStop(.5, 'rgba(20,6,37,.16)'); base.addColorStop(1, 'rgba(4,2,12,.3)'); context.fillStyle = base; context.fillRect(0, 0, width, height);
      nebula(width * .32, height * .34, Math.max(width, height) * .42, 'rgba(102,34,171,.19)', .12);
      nebula(width * .77, height * .7, Math.max(width, height) * .34, 'rgba(77,31,145,.17)', -.1);
      nebula(width * .56, height * .12, Math.max(width, height) * .25, 'rgba(151,55,190,.1)', .08);
      for (const star of stars) { const twinkle = .62 + .38 * Math.sin(time * star.speed * 12 + star.phase); const x = (star.x + time * 9 * (star.layer - .5) * .12 + width) % width; const y = (star.y - time * 5 * (star.layer - .5) * .12 + height) % height; context.globalAlpha = star.alpha * twinkle; context.fillStyle = star.layer > .93 ? '#f0d9ff' : '#d8c5ff'; context.beginPath(); context.arc(x, y, star.r, 0, Math.PI * 2); context.fill(); if (star.layer > .985) { context.globalAlpha = .16 * twinkle; context.strokeStyle = '#d9a5ff'; context.lineWidth = .7; context.beginPath(); context.moveTo(x - 5, y); context.lineTo(x + 5, y); context.moveTo(x, y - 5); context.lineTo(x, y + 5); context.stroke(); } }
      context.globalAlpha = 1;
      for (const p of dust) { p.x += p.vx * delta; p.y += p.vy * delta; if (p.y < -5) { p.y = height + 5; p.x = Math.random() * width; } context.globalAlpha = p.alpha; context.fillStyle = '#c58aff'; context.beginPath(); context.arc(p.x, p.y, p.r, 0, Math.PI * 2); context.fill(); } context.globalAlpha = 1;
      if (Math.random() < .012 && meteors.length < 3) meteors.push({ x: Math.random() * width * .8 + width * .1, y: Math.random() * height * .55, vx: 7 + Math.random() * 5, vy: 2.5 + Math.random() * 2.5, life: 0, max: 38 });
      meteors = meteors.filter((m) => m.life < m.max);
      for (const m of meteors) { m.x += m.vx * delta; m.y += m.vy * delta; m.life += delta; const fade = Math.sin((m.life / m.max) * Math.PI); context.strokeStyle = 'rgba(238,218,255,' + (fade * .8) + ')'; context.lineWidth = 1.2; context.beginPath(); context.moveTo(m.x - m.vx * 12, m.y - m.vy * 12); context.lineTo(m.x, m.y); context.stroke(); }
      raf = window.requestAnimationFrame(draw);
    };
    resize(); const observer = new ResizeObserver(resize); observer.observe(canvas);
    const onVisibility = () => { if (!document.hidden && !raf) { last = 0; raf = window.requestAnimationFrame(draw); } };
    document.addEventListener('visibilitychange', onVisibility); raf = window.requestAnimationFrame(draw);
    return () => { window.cancelAnimationFrame(raf); observer.disconnect(); document.removeEventListener('visibilitychange', onVisibility); };
  }, [quality]);
  return <canvas ref={canvasRef} className="universe-canvas" aria-label="Animasyonlu derin uzay yıldız alanı" />;
}
export default function UniversePage() {
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<{ role: 'user' | 'model'; content: string; sources?: { title: string; url: string; snippet: string }[] }[]>([
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
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [scene, setScene] = useState<'deep-space' | 'black-hole' | 'pulsar' | 'nebula'>('deep-space');
  const [quality, setQuality] = useState<'ultra' | 'balanced' | 'eco'>('ultra');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState('');
  const [providerOptions, setProviderOptions] = useState<{ id: string; name: string; models: string[]; default_model: string; note: string; connected: boolean; model: string }[]>([]);
  const [activeProvider, setActiveProvider] = useState('gemini');
  const [activeModel, setActiveModel] = useState('gemini-2.5-flash');
  const [providerError, setProviderError] = useState('');
  const [memoryOpen, setMemoryOpen] = useState(false);
  const [memoryItems, setMemoryItems] = useState<{ id: string; title: string; content: string; tags: string[] }[]>([]);
  const [memoryTitle, setMemoryTitle] = useState('');
  const [memoryContent, setMemoryContent] = useState('');
  const [memoryBusy, setMemoryBusy] = useState(false);
  const [memoryError, setMemoryError] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [webSearchEnabled, setWebSearchEnabled] = useState(false);
  const [agentMode, setAgentMode] = useState(false);
  const [recording, setRecording] = useState(false);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const recordingStreamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const rootRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => () => {
    if (recorderRef.current?.state === 'recording') recorderRef.current.stop();
    recordingStreamRef.current?.getTracks().forEach((track) => track.stop());
  }, []);

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

  async function refreshProviders() {
    const response = await fetch('/xfa/api/providers', { credentials: 'same-origin' });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || 'AI modelleri yüklənə bilmədi.');
    const options = Array.isArray(data.connected) ? data.connected : [];
    setProviderOptions(options);
    const selected = options.find((item: { id: string; connected: boolean }) => item.id === data.active && item.connected)
      || options.find((item: { connected: boolean }) => item.connected);
    if (!selected) {
      setProviderError('XFA serverində aktiv Gemini və ya NVIDIA modeli yoxdur.');
      return;
    }
    const model = selected.id === data.active && selected.models.includes(data.model)
      ? data.model : selected.default_model;
    setActiveProvider(selected.id);
    setActiveModel(model);
    setProviderError('');
  }

  async function selectAiProvider(provider: string, model: string) {
    setProviderError('');
    const response = await fetch('/xfa/api/providers/select', {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': auth.csrf },
      body: JSON.stringify({ provider, model }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || 'Model seçilemedi.');
    setActiveProvider(provider);
    setActiveModel(model);
  }


  useEffect(() => {
    if (auth.authenticated) {
      refreshProviders().catch((err) => setProviderError(err instanceof Error ? err.message : 'AI sağlayıcıları yüklenemedi.'));
    } else {
      setProviderOptions([]);
      setActiveProvider('gemini');
      setActiveModel('gemini-2.5-flash');
    }
  }, [auth.authenticated]);


  async function refreshMemory() {
    const response = await fetch('/xfa/api/memory', { credentials: 'same-origin' });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || 'Yaddaş yüklənmədi.');
    setMemoryItems(Array.isArray(data.items) ? data.items : []);
  }

  async function saveMemory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (memoryBusy || !memoryTitle.trim() || !memoryContent.trim()) return;
    setMemoryBusy(true);
    setMemoryError('');
    try {
      const response = await fetch('/xfa/api/memory', {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': auth.csrf },
        body: JSON.stringify({ title: memoryTitle, content: memoryContent }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || 'Yaddaş saxlanmadı.');
      setMemoryItems((items) => [data.item, ...items]);
      setMemoryTitle('');
      setMemoryContent('');
    } catch (err) {
      setMemoryError(err instanceof Error ? err.message : 'Yaddaş saxlanmadı.');
    } finally { setMemoryBusy(false); }
  }

  async function removeMemory(itemId: string) {
    setMemoryBusy(true);
    setMemoryError('');
    try {
      const response = await fetch('/xfa/api/memory/' + encodeURIComponent(itemId), {
        method: 'DELETE', credentials: 'same-origin',
        headers: { 'X-CSRF-Token': auth.csrf },
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || 'Yaddaş silinmədi.');
      setMemoryItems((items) => items.filter((item) => item.id !== itemId));
    } catch (err) {
      setMemoryError(err instanceof Error ? err.message : 'Yaddaş silinmədi.');
    } finally { setMemoryBusy(false); }
  }

  useEffect(() => {
    if (memoryOpen && auth.authenticated) {
      refreshMemory().catch((err) => setMemoryError(err instanceof Error ? err.message : 'Yaddaş yüklənmədi.'));
    }
  }, [memoryOpen, auth.authenticated]);

  async function submitAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (authBusy) return;
    setAuthBusy(true);
    setAuthError('');
    try {
      const response = await fetch(authMode === 'register' ? '/auth/register' : '/auth/login/password', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': auth.csrf },
        body: JSON.stringify({ email: email.trim(), password }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || `Giriş başarısız (HTTP ${response.status}).`);
      const sessionResponse = await fetch('/auth/me', { credentials: 'same-origin' });
      const sessionData = await sessionResponse.json().catch(() => ({}));
      if (!sessionResponse.ok || sessionData.authenticated !== true) {
        throw new Error(sessionData.error || 'Oturum doğrulanamadı. Sayfayı yenileyip tekrar dene.');
      }
      setAuth({
        loading: false,
        authenticated: true,
        csrf: typeof sessionData.csrf_token === 'string' ? sessionData.csrf_token : '',
        name: sessionData.user?.name || email.split('@')[0],
        google: auth.google,
      });
      setPassword('');
      setError('');
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : 'Hesap işlemi başarısız oldu.');
    } finally {
      setAuthBusy(false);
    }
  }

  async function logout() {
    setAuthError('');
    try {
      const response = await fetch('/auth/logout', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'X-CSRF-Token': auth.csrf },
      });
      if (!response.ok) throw new Error('Oturum kapatılamadı. Sayfayı yenileyip tekrar dene.');
      const sessionResponse = await fetch('/auth/me', { credentials: 'same-origin' });
      const data = await sessionResponse.json().catch(() => ({}));
      setAuth({
        loading: false,
        authenticated: false,
        csrf: typeof data.csrf_token === 'string' ? data.csrf_token : '',
        name: '',
        google: auth.google,
      });
      setMessages([{ role: 'model', content: 'Merhaba! Ben XFA. Bir fikir, soru veya görev yaz; birlikte başlayalım.' }]);
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : 'Oturum kapatılamadı.');
    }
  }

  async function toggleFullscreen() {
    if (!document.fullscreenElement) await rootRef.current?.requestFullscreen?.();
    else await document.exitFullscreen();
  }

  async function sendMessage(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    const content = message.trim();
    const attachment = selectedFile;
    if ((!content && !attachment) || busy) return;
    if (!auth.authenticated) {
      setError('Söhbət üçün əvvəlcə XFA hesabına daxil ol.');
      return;
    }
    const visibleContent = attachment
      ? (content ? `📎 ${attachment.name}: ${content}` : `📎 ${attachment.name}`)
      : content;
    const next = [...messages, { role: 'user' as const, content: visibleContent }];
    setMessages(next);
    setMessage('');
    setBusy(true);
    setError('');
    try {
      const response = attachment
        ? await (() => {
            const form = new FormData();
            form.append('file', attachment);
            form.append('prompt', content);
            form.append('provider', activeProvider);
            form.append('model', activeModel);
            return fetch('/xfa/api/files/analyze', {
              method: 'POST', credentials: 'same-origin',
              headers: { 'X-CSRF-Token': auth.csrf },
              body: form,
            });
          })()
        : agentMode
          ? await fetch('/xfa/api/tasks/run', {
              method: 'POST', credentials: 'same-origin',
              headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': auth.csrf },
              body: JSON.stringify({ task: content }),
            })
          : await fetch('/xfa/api/chat', {
              method: 'POST', credentials: 'same-origin',
              headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': auth.csrf },
              body: JSON.stringify({ messages: next.slice(-20), provider: activeProvider, model: activeModel, web_search: webSearchEnabled }),
            });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || `XFA sorğusu uğursuz oldu (HTTP ${response.status}).`);
      setMessages((current) => [...current, { role: 'model', content: data.reply || data.answer || 'Şu anda yanıt oluşturamadım.', sources: Array.isArray(data.sources) ? data.sources : [] }]);
      if (attachment) setSelectedFile(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'XFA bağlantısı başarısız oldu.');
    } finally {
      setBusy(false);
      inputRef.current?.focus();
    }
  }

  async function startVoiceRecording() {
    if (!navigator.mediaDevices?.getUserMedia || !('MediaRecorder' in window)) {
      setError('Bu brauzer səs yazma funksiyasını dəstəkləmir.');
      return;
    }
    try {
      setError('');
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      recordingStreamRef.current = stream;
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/ogg;codecs=opus') ? 'audio/ogg;codecs=opus' : '';
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      audioChunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };
      recorder.onerror = () => {
        setError('Səs yazılarkən xəta baş verdi.');
        stream.getTracks().forEach((track) => track.stop());
        recordingStreamRef.current = null;
        setRecording(false);
      };
      recorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: recorder.mimeType || 'audio/webm' });
        const extension = blob.type.includes('ogg') ? '.ogg' : blob.type.includes('mp4') ? '.m4a' : '.webm';
        if (blob.size > 8 * 1024 * 1024) {
          setError('Səs yazısı 8 MB limitini keçdi.');
        } else if (blob.size > 0) {
          setSelectedFile(new File([blob], 'xfa-voice' + extension, { type: blob.type }));
        }
        stream.getTracks().forEach((track) => track.stop());
        recordingStreamRef.current = null;
        recorderRef.current = null;
        setRecording(false);
      };
      recorderRef.current = recorder;
      recorder.start();
      setRecording(true);
    } catch {
      setError('Mikrofon icazəsi alınmadı və ya cihaz əlçatan deyil.');
      recordingStreamRef.current?.getTracks().forEach((track) => track.stop());
      recordingStreamRef.current = null;
      setRecording(false);
    }
  }

  function stopVoiceRecording() {
    if (recorderRef.current?.state === 'recording') recorderRef.current.stop();
  }

  function speakMessage(content: string) {
    if (!('speechSynthesis' in window)) {
      setError('Bu brauzer səsli oxuma funksiyasını dəstəkləmir.');
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(content);
    utterance.lang = 'tr-TR';
    utterance.rate = 1;
    window.speechSynthesis.speak(utterance);
  }

  const quickPrompts = ['Nebulalar nasıl oluşur?', 'Bana bir Python örneği yaz', 'Yeni bir proje fikri bul', 'Bugünkü hedeflerimi planla'];

  return (
    <main className="universe-page" ref={rootRef}>
      <SpaceCanvas quality={quality} />
      <div className="universe-vignette" />
      {scene === 'black-hole' && (
        <div className="universe-blackhole" aria-label="Animasyonlu kara delik manzarası" role="img">
          <div className="blackhole-nebula" />
          <div className="blackhole-disk blackhole-disk-back" />
          <div className="blackhole-lensing" />
          <div className="blackhole-core"><span /></div>
          <div className="blackhole-disk blackhole-disk-front" />
          <div className="blackhole-particles"><i/><i/><i/><i/><i/><i/><i/><i/></div>
        </div>
      )}
      {scene === 'pulsar' && <div className="universe-pulsar" role="img" aria-label="Fırlanan pulsar ulduzu animasiyası"><div className="pulsar-beam pulsar-beam-a"/><div className="pulsar-beam pulsar-beam-b"/><div className="pulsar-halo"/><div className="pulsar-star"><i/><i/><i/><i/></div><div className="pulsar-rings"/></div>}
      {scene === 'nebula' && <div className="universe-nebula-scene" aria-hidden="true"><i/><i/><i/><i/><span/></div>}
      <aside className="universe-sidebar">
        <Link href="/" className="universe-brand"><span className="universe-flower">✿</span><strong>XFA</strong><small>XYRIN FLOWER AI</small></Link>
        <div className="universe-nav-label">ÇALIŞMA ALANI</div>
        <a className="universe-nav-item active" href="#chat"><MessageCircle size={16}/> Sohbet</a>
        <button className="universe-nav-item" type="button" onClick={() => { if (!auth.authenticated) { setError("Yaddaş üçün əvvəlcə hesabına daxil ol."); return; } setMemoryOpen(true); setMemoryError(""); }}><BookOpen size={16}/> Yaddaş</button><a className="universe-nav-item" href="#chat"><Bot size={16}/> Yapay Zekâ Ajanı</a>
        <a className="universe-nav-item" href="/panel"><Grid3X3 size={16}/> Çalışma Alanı</a>
        <a className="universe-nav-item" href="/panel"><Settings size={16}/> Ayarlar</a>
        <div className="universe-premium"><strong>👑 XFA</strong><p>Herkes için ücretsiz yapay zekâ deneyimi.</p><a href="/panel">Kontrol paneli →</a></div>
        <div className="universe-sidebar-foot">© 2026 XFA.<br/>Herkes için geliştirildi. ♡</div>
      </aside>
      <header className="universe-topbar">
        <Link href="/welcome" className="universe-back"><ArrowLeft size={15}/> Tanıtım sayfası</Link>
        <button className="universe-search" type="button" onClick={() => inputRef.current?.focus()}><Search size={14}/> Mesaj yazmak için tıkla...</button>
        <div className="universe-status"><i className={stats.ready ? '' : 'offline'}/> {auth.authenticated ? (auth.name || 'Hesabım') : 'Misafir'} <span>◉</span><b>{auth.name ? auth.name.slice(0,1).toUpperCase() : 'A'}</b>{auth.authenticated && <button type="button" className="universe-logout" onClick={logout}>Çıkış</button>}</div>
      </header>
      <section className="universe-center">
        <div className="universe-brand-title"><h1>XFA</h1><h2>Xyrin Flower AI</h2><p>Sonsuz imkânlar. Tamamen <em>ücretsiz.</em></p><div className="universe-pills"><span>∞ Ücretsiz erişim</span><span>♢ Güvenli çalışma</span><span>ϟ Canlı AI sohbeti</span></div></div>
        <div className="universe-chat" id="chat">
          <div className="universe-chat-head"><span className="universe-avatar">✿</span><div><strong>{auth.authenticated ? `Merhaba, ${auth.name || 'gezgin'}! 👋` : 'XFA Universe’e hoş geldin! 👋'}</strong><small>{auth.authenticated ? 'XFA hazır. Ne yapmak istersin?' : 'AI sohbetini kullanmak için hesabına giriş yap.'}</small></div></div>
          {!auth.authenticated && !auth.loading && (
            <form className="universe-auth" onSubmit={submitAuth}>
              <div className="universe-auth-heading">
                <strong>{authMode === 'login' ? 'Hesabına giriş yap' : 'Ücretsiz XFA hesabı oluştur'}</strong>
                <span>{authMode === 'login' ? 'Sohbeti sürdürmek için giriş yap.' : 'E-posta adresinle XFA’ya katıl.'}</span>
              </div>
              <label className="universe-auth-label" htmlFor="xfa-email">E-posta</label>
              <input id="xfa-email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="ornek@eposta.com" required />
              <label className="universe-auth-label" htmlFor="xfa-password">Parola</label>
              <input id="xfa-password" type="password" autoComplete={authMode === 'login' ? 'current-password' : 'new-password'} minLength={12} maxLength={1024} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="En az 12 karakter" required />
              {authError && <p className="universe-error" role="alert">{authError}</p>}
              <div className="universe-auth-actions">
                <button className="universe-auth-submit" type="submit" disabled={authBusy || !auth.csrf}>{authBusy ? 'Bekle…' : authMode === 'login' ? 'Giriş yap' : 'Hesap oluştur'}</button>
                <button className="universe-auth-toggle" type="button" onClick={() => { setAuthMode(authMode === 'login' ? 'register' : 'login'); setAuthError(''); }}>{authMode === 'login' ? 'Hesap oluştur' : 'Zaten hesabım var'}</button>
              </div>
              {auth.google && <a className="universe-google-login" href="/auth/login/google">Google ile giriş yap <ArrowRight size={14}/></a>}
              {!auth.csrf && <small className="universe-auth-note">Giriş hizmeti şu anda yapılandırılmamış olabilir.</small>}
            </form>
          )}
          {auth.authenticated && <div className="universe-model-controls">
            <label><Cpu size={14}/> XFA MODELLERİ</label>
            <select value={activeProvider} onChange={(event) => {
              const option = providerOptions.find((item) => item.id === event.target.value);
              if (!option?.connected) return;
              selectAiProvider(event.target.value, option.default_model).catch((err) => setProviderError(err instanceof Error ? err.message : 'Model seçilemedi.'));
            }}>
              {providerOptions.map((option) => <option key={option.id} value={option.id} disabled={!option.connected}>{option.name}{option.connected ? ' ✓' : ' • Sunucuda aktiv deyil'}</option>)}
            </select>
            <select value={activeModel} onChange={(event) => selectAiProvider(activeProvider, event.target.value).catch((err) => setProviderError(err instanceof Error ? err.message : 'Model seçilemedi.'))}>
              {(providerOptions.find((item) => item.id === activeProvider)?.models || [activeModel]).map((model) => <option key={model} value={model}>{model}</option>)}
            </select>
            <small>XFA serverinin Gemini və NVIDIA bağlantıları</small>
            {providerError && <p className="universe-error" role="alert">{providerError}</p>}
          </div>}

          {memoryOpen && auth.authenticated && <div className="universe-provider-overlay" role="dialog" aria-modal="true" aria-label="XFA yaddaşı">
            <section className="universe-provider-modal universe-memory-modal">
              <header><div><strong><BookOpen size={17}/> XFA yaddaşı</strong><small>Yalnız sənin əlavə etdiyin qeydlər saxlanılır. Avtomatik yaddaş aktiv deyil.</small></div><button type="button" aria-label="Kapat" onClick={() => setMemoryOpen(false)}><X size={18}/></button></header>
              <form className="universe-provider-form" onSubmit={saveMemory}>
                <strong>Yeni yaddaş qeydi</strong>
                <label>Başlıq</label>
                <input value={memoryTitle} onChange={(event) => setMemoryTitle(event.target.value)} maxLength={120} placeholder="Məsələn: XFA UI seçimi" />
                <label>Məlumat</label>
                <textarea value={memoryContent} onChange={(event) => setMemoryContent(event.target.value)} maxLength={6000} rows={4} placeholder="XFA-nın gələcək söhbətlərdə nəzərə almasını istədiyin məlumat..." />
                <div className="universe-provider-actions"><button type="submit" disabled={memoryBusy || !memoryTitle.trim() || !memoryContent.trim()}>{memoryBusy ? 'Saxlanır…' : 'Yadda saxla'}</button></div>
              </form>
              {memoryError && <p className="universe-error" role="alert">{memoryError}</p>}
              <div className="universe-memory-list">
                <strong>Saxlanılan qeydlər ({memoryItems.length}/100)</strong>
                {memoryItems.map((item) => <article className="universe-memory-item" key={item.id}>
                  <div><strong>{item.title}</strong><p>{item.content}</p></div>
                  <button type="button" disabled={memoryBusy} onClick={() => removeMemory(item.id)}>Sil</button>
                </article>)}
                {!memoryItems.length && <p className="universe-provider-empty">Hələ yaddaş qeydi yoxdur.</p>}
              </div>
            </section>
          </div>}
          <div className="universe-quick">{quickPrompts.map((prompt) => <button key={prompt} type="button" onClick={() => { setMessage(prompt); inputRef.current?.focus(); }}>✦ {prompt}</button>)}</div>
          <div className="universe-transcript" aria-live="polite">
            {messages.map((item, index) => <div className={item.role === 'user' ? 'universe-user-message' : 'universe-message'} key={index}>{item.role === 'model' && <small className="universe-message-label">XFA <button type="button" aria-label="Cavabı səsləndir" onClick={() => speakMessage(item.content)}><Volume2 size={12}/></button></small>}{item.content}{item.role === 'model' && !!item.sources?.length && <div className="universe-source-list"><strong>Mənbələr</strong>{item.sources.map((source, sourceIndex) => <a key={source.url} href={source.url} target="_blank" rel="noopener noreferrer">[{sourceIndex + 1}] {source.title}</a>)}</div>}</div>)}
            {busy && <div className="universe-message universe-thinking"><small>XFA</small><span className="universe-dots">Yanıt hazırlanıyor</span></div>}
          </div>
          {error && <p className="universe-error" role="alert">{error}</p>}
          {selectedFile && <div className="universe-attachment-strip"><FileText size={15}/><span>{selectedFile.name}<small>{(selectedFile.size / 1024).toFixed(0)} KB</small></span><button type="button" aria-label="Faylı sil" onClick={() => setSelectedFile(null)}><X size={14}/></button></div>}
          <form className="universe-input" onSubmit={sendMessage}>
            <input ref={fileInputRef} type="file" hidden accept=".png,.jpg,.jpeg,.webp,.mp3,.wav,.ogg,.webm,.m4a,.pdf,.docx,.pptx,.xlsx,.csv,.txt,.md,.py,.js,.jsx,.ts,.tsx,.css,.json,.yaml,.yml,.toml,.sql,.sh,.java,.c,.cpp,.h,.go,.rs,.rb,.php,.xml,.log" onChange={(event) => { const file = event.target.files?.[0] || null; setSelectedFile(file); if (file) setError(''); event.currentTarget.value = ''; }} />
            <button type="button" aria-label="Fayl əlavə et" disabled={!auth.authenticated || busy || recording} onClick={() => fileInputRef.current?.click()}><Paperclip size={18}/></button>{recording ? <button type="button" className="universe-recording" aria-label="Səs yazısını dayandır" onClick={stopVoiceRecording}><Square size={15}/></button> : <button type="button" aria-label="Səs yazmağa başla" disabled={!auth.authenticated || busy || !!selectedFile} onClick={startVoiceRecording}><Mic size={17}/></button>}<button type="button" className={agentMode ? 'universe-agent-toggle active' : 'universe-agent-toggle'} aria-label="Araşdırma agentini aktivləşdir" aria-pressed={agentMode} disabled={!auth.authenticated || busy || !!selectedFile} onClick={() => { setAgentMode((value) => !value); setWebSearchEnabled(false); }}><Bot size={16}/></button><button type="button" className={webSearchEnabled ? 'universe-web-toggle active' : 'universe-web-toggle'} aria-label="İnternet axtarışını aktivləşdir" aria-pressed={webSearchEnabled} disabled={!auth.authenticated || busy || !!selectedFile || agentMode} onClick={() => setWebSearchEnabled((value) => !value)}><Globe size={16}/></button><button type="button" aria-label="Nümunə istək əlavə et" onClick={() => setMessage('Lütfən bunu addım-addım izah et: ')}><Smile size={18}/></button><input ref={inputRef} value={message} onChange={(event) => setMessage(event.target.value)} placeholder={auth.authenticated ? 'XFA’ya mesajını yaz...' : 'Önce giriş yapmalısın...'} disabled={!auth.authenticated || busy} /><button className="universe-send" type="submit" disabled={!auth.authenticated || busy || (!message.trim() && !selectedFile)} aria-label="Mesajı göndər"><Send size={19}/></button>
          </form>
        </div>
      </section>
      <aside className="universe-right" id="status">
        <section className="universe-stat-card"><h3>▥ &nbsp; XFA Canlı İstatistikleri</h3><div><Sparkles/><strong>{stats.members.toLocaleString('tr-TR')}<small>Discord Üyesi</small></strong></div><div><Grid3X3/><strong>{stats.guilds}<small>Sunucu</small></strong></div><div><Zap/><strong>{stats.ready ? `${stats.latency} ms` : 'Çevrimdışı'}<small>Bot gecikmesi</small></strong></div><svg viewBox="0 0 260 75" preserveAspectRatio="none"><path d="M0 65 C30 61 35 59 55 51 S82 49 100 42 S126 49 148 32 S177 35 193 22 S221 18 260 2" fill="none" stroke="#b34dff" strokeWidth="2.5"/></svg></section>
        <section className="universe-ecosystem"><h3><Orbit size={15}/> XFA Ekosistemi <span>CANLI</span></h3><p>◉ &nbsp; Discord Bot <small>{stats.ready ? '● Çevrimiçi' : '● Çevrimdışı'}</small></p><p>◎ &nbsp; Web Platformu <small>● Çevrimiçi</small></p><p>▣ &nbsp; XFA Ajan API <small>{auth.authenticated ? '● Oturum açık' : '● Giriş gerekli'}</small></p></section>
      </aside>
      <div className="universe-quality"><label htmlFor="universe-quality-select">GRAFİK</label><select id="universe-quality-select" value={quality} onChange={(event) => setQuality(event.target.value as 'ultra' | 'balanced' | 'eco')}><option value="ultra">Ultra</option><option value="balanced">Balanced</option><option value="eco">Eco</option></select></div>
      <div className="universe-scene-switch"><div><strong>{scene === 'deep-space' ? 'Deep Space' : scene === 'black-hole' ? 'Black Hole' : scene === 'pulsar' ? 'Pulsar' : 'Nebula'}</strong><small>Kosmik səhnəni seç</small></div><div className="universe-scene-buttons"><button type="button" className={scene === 'deep-space' ? 'selected' : ''} aria-pressed={scene === 'deep-space'} onClick={() => setScene('deep-space')}>Deep Space</button><button type="button" className={scene === 'black-hole' ? 'selected' : ''} aria-pressed={scene === 'black-hole'} onClick={() => setScene(scene === 'black-hole' ? 'deep-space' : 'black-hole')}>Kara delik</button><button type="button" className={scene === 'pulsar' ? 'selected' : ''} aria-pressed={scene === 'pulsar'} onClick={() => setScene('pulsar')}>Pulsar</button><button type="button" className={scene === 'nebula' ? 'selected' : ''} aria-pressed={scene === 'nebula'} onClick={() => setScene('nebula')}>Nebula</button></div><button className="universe-fullscreen" onClick={toggleFullscreen} aria-label="Tam ekran"><Maximize2 size={17}/></button></div>
      <div className="universe-live"><Activity size={13}/> CANLI ANİMASİYA</div>
    </main>
  );
}
