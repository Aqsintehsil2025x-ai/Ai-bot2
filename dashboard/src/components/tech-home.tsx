import { useState } from 'react';
import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronRight,
  Copy,
  ExternalLink,
  MessageCircle,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { Link } from 'wouter';
import flowerBanner from './flower-banner.svg';
import './tech-home.css';

const BANNER_IMAGE = flowerBanner;
const BOT_ID = '1555918878268456970';
const SERVER_INVITE = 'https://discord.gg/5ST4gdjjc';
const BOT_INVITE =
  'https://discord.com/oauth2/authorize?client_id=1555918878268456970&permissions=8&integration_type=0&scope=bot';

export function TechHeader({ activePanel = false }: { activePanel?: boolean }) {
  const homePrefix = activePanel ? '/' : '';

  return (
    <header className="tech-nav">
      <a
        className="tech-brand"
        href={activePanel ? '/' : '#baslangic'}
        aria-label="Xyrin Flower ana sayfa"
        data-testid="link-home-brand"
      >
        <img src={BANNER_IMAGE} alt="Xyrin Flower AI" />
        <span className="tech-brand-name">
          XYRIN <b>FLOWER</b>
        </span>
      </a>
      <nav className="tech-nav-links" aria-label="Ana menü">
        <a href={`${homePrefix}#yetenekler`} data-testid="link-features">
          Yetenekler
        </a>
        <a href={`${homePrefix}#yaklasim`} data-testid="link-approach">
          Yaklaşım
        </a>
        <a href={`${homePrefix}#kimlik`} data-testid="link-bot-id">
          Bot kimliği
        </a>
        <Link
          className="tech-panel-link"
          href={activePanel ? '/' : '/panel'}
          data-testid={activePanel ? 'link-site-home' : 'link-panel'}
        >
          {activePanel ? 'Siteye dön' : 'Panel önizlemesi'}
          <ArrowUpRight size={14} />
        </Link>
      </nav>
      <a
        className="tech-nav-cta"
        href={SERVER_INVITE}
        target="_blank"
        rel="noopener noreferrer"
        data-testid="link-server-invite-nav"
      >
        Sunucuya katıl <ArrowRight size={15} />
      </a>
    </header>
  );
}

export function TechHome() {
  const [copied, setCopied] = useState(false);

  async function copyBotId() {
    try {
      await navigator.clipboard.writeText(BOT_ID);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2200);
    } catch {
      const field = document.createElement('textarea');
      field.value = BOT_ID;
      field.setAttribute('readonly', '');
      field.style.position = 'fixed';
      field.style.opacity = '0';
      document.body.appendChild(field);
      field.select();
      const success = document.execCommand('copy');
      field.remove();
      setCopied(success);
      window.setTimeout(() => setCopied(false), 2200);
    }
  }

  return (
    <main className="tech-page">
      <TechHeader />

      <section id="baslangic" className="tech-hero">
        <div className="tech-hero-grid" aria-hidden="true" />
        <div className="tech-orbit orbit-a" aria-hidden="true" />
        <div className="tech-orbit orbit-b" aria-hidden="true" />
        <div className="tech-hero-inner">
          <div className="tech-hero-copy">
            <p className="tech-kicker"><span className="kicker-spark" /> XYRIN FLOWER AI <span className="kicker-divider">/</span> DİJİTAL TOPLULUK ASİSTANI</p>
            <h1>
              Zekâ, düzen
              <br />
              ve <span>biraz çiçek.</span>
            </h1>
            <p className="tech-lede">
              Sohbete kulak veren yapay zekâ, sınırları gözeten moderasyon ve
              dozunda eğlence. Hepsi tek, özenli bir yardımcıda.
            </p>
            <div className="tech-hero-actions">
              <a className="tech-button tech-button-primary" href={BOT_INVITE} target="_blank" rel="noopener noreferrer" data-testid="link-add-bot">
                Botu sunucuna ekle <ArrowUpRight size={16} />
              </a>
              <a className="tech-button tech-button-quiet" href={SERVER_INVITE} target="_blank" rel="noopener noreferrer" data-testid="link-server-invite-hero">
                Discord sunucusuna katıl <ArrowRight size={16} />
              </a>
            </div>
            <p className="permission-note">
              <ShieldCheck size={14} />
              Bot daveti Discord’da Yönetici izni ister. İzinleri onaylamadan önce gözden geçirin.
            </p>
            <a className="hero-scroll" href="#yetenekler"><span>01 / 03</span> Aşağı kaydır <ArrowDown size={13} /></a>
          </div>

          <div className="tech-hero-art">
            <div className="art-topline"><span>XYRIN / FLOWER</span><span>AI ASSISTANT — TR</span></div>
            <div className="hero-image-frame">
              <div className="image-corner corner-tl" />
              <div className="image-corner corner-br" />
              <img src={BANNER_IMAGE} alt="Xyrin Flower AI" />
              <div className="image-scanline" />
            </div>
            <div className="art-orbit-label"><span className="orbit-cross">+</span> TEKNOLOJİ, NAZİK BİR DOKUNUŞLA</div>
            <div className="art-index">XF—001 <span>●</span> COMMUNITY SYSTEM</div>
            <div className="hero-art-caption">
              <span className="caption-rule" />
              <span>İyi bir yardımcı,<br />ne zaman konuşacağını bilir.</span>
            </div>
          </div>
        </div>
        <div className="hero-footline"><span>TOPLULUKLAR İÇİN TASARLANDI</span><span>XYRIN FLOWER AI <i>·</i> COMMUNITY SYSTEM</span></div>
      </section>

      <section id="yetenekler" className="tech-capabilities">
        <div className="tech-section-head">
          <div>
            <p className="tech-overline"><span>01</span> ÜÇ YÖNÜ, TEK KARAKTERİ</p>
            <h2>İhtiyaç duyduğun<br /><em>şeyler.</em> Fazlası değil.</h2>
          </div>
          <p className="section-aside">Her özellik kendi yerinde. Birbirinin önüne geçmeden, topluluğunun ritmine uyum sağlar.</p>
        </div>
        <div className="capability-list">
          <article className="capability-row">
            <span className="cap-number">01</span>
            <span className="cap-icon"><MessageCircle size={21} strokeWidth={1.6} /></span>
            <div className="cap-copy">
              <h3>Doğal sohbet</h3>
              <p>Sunucunun dilini yakalayan, sohbeti koparmadan yanıt veren yapay zekâ.</p>
            </div>
            <ul><li><Check size={13} /> Akıcı Türkçe sohbet</li><li><Check size={13} /> Yardımcı, ölçülü yanıtlar</li></ul>
            <ArrowUpRight className="cap-arrow" size={17} />
          </article>
          <article className="capability-row">
            <span className="cap-number">02</span>
            <span className="cap-icon"><ShieldCheck size={21} strokeWidth={1.6} /></span>
            <div className="cap-copy">
              <h3>Sessizce güvende</h3>
              <p>Topluluğun için belirlediğin sınırları tutarlı biçimde gözeten moderasyon.</p>
            </div>
            <ul><li><Check size={13} /> Düzenli ve güvenli ortam</li><li><Check size={13} /> Sunucu kurallarına saygı</li></ul>
            <ArrowUpRight className="cap-arrow" size={17} />
          </article>
          <article className="capability-row">
            <span className="cap-number">03</span>
            <span className="cap-icon"><Sparkles size={21} strokeWidth={1.6} /></span>
            <div className="cap-copy">
              <h3>Biraz neşe</h3>
              <p>Ortamın enerjisini yükselten, ama sohbeti gölgelemeyen küçük dokunuşlar.</p>
            </div>
            <ul><li><Check size={13} /> Hafif eğlence komutları</li><li><Check size={13} /> Sohbete uyumlu deneyim</li></ul>
            <ArrowUpRight className="cap-arrow" size={17} />
          </article>
        </div>
      </section>

      <section id="yaklasim" className="tech-approach">
        <div className="approach-graphic" aria-hidden="true">
          <div className="graphic-orbit graphic-orbit-1" />
          <div className="graphic-orbit graphic-orbit-2" />
          <div className="graphic-center"><img src={BANNER_IMAGE} alt="" /></div>
          <span className="graphic-tag tag-a">01 / DİNLE</span>
          <span className="graphic-tag tag-b">02 / KORU</span>
          <span className="graphic-tag tag-c">03 / EŞLİK ET</span>
          <span className="graphic-cross cross-a">+</span><span className="graphic-cross cross-b">+</span>
        </div>
        <div className="approach-copy">
          <p className="tech-overline"><span>02</span> BİZİM İÇİN İYİ BİR BOT</p>
          <h2>Dikkat çeken değil,<br /><em>işini bilen.</em></h2>
          <p className="approach-description">
            Xyrin Flower, sunucunda kendine yer açmaya değil; senin kurduğun
            yere uyum sağlamaya geliyor. Sohbet eder, düzeni korur ve
            gerektiğinde geri çekilir.
          </p>
          <div className="approach-quote">
            <span className="quote-mark">“</span>
            <p>İyi bir yardımcı,<br />ne zaman konuşacağını <em>bilir.</em></p>
            <span className="quote-attribution">XYRIN FLOWER <i>/</i> YAKLAŞIM</span>
          </div>
        </div>
      </section>

      <section className="tech-connect">
        <div className="connect-inner">
          <div className="connect-copy">
            <p className="tech-overline"><span>03</span> TOPLULUĞUNLA TANIŞTIR</p>
            <h2>İyi gelen bir<br /><em>başlangıç.</em></h2>
            <p>Xyrin Flower’ı sunucuna davet et ya da topluluğa katılıp tanış.</p>
          </div>
          <div className="connect-actions">
            <a className="connect-card connect-server" href={SERVER_INVITE} target="_blank" rel="noopener noreferrer" data-testid="link-server-invite-card">
              <span className="connect-card-icon"><ArrowUpRight size={18} /></span>
              <span className="connect-label">TOPLULUĞA KATIL</span>
              <strong>Discord sunucusuna<br />göz at.</strong>
              <span className="connect-link">Sunucuya katıl <ArrowRight size={15} /></span>
            </a>
            <div className="connect-card connect-bot">
              <span className="connect-card-icon"><ShieldCheck size={18} /></span>
              <span className="connect-label">SUNUCUNA EKLE</span>
              <strong>Yardımcıyı<br />davet et.</strong>
              <a className="connect-link" href={BOT_INVITE} target="_blank" rel="noopener noreferrer" data-testid="link-add-bot-card">
                Botu ekle <ArrowRight size={15} />
              </a>
              <p className="connect-disclosure">Davet bağlantısı Yönetici izni ister. Discord izin ekranında yetkileri kontrol edin.</p>
            </div>
          </div>
        </div>
      </section>

      <section id="kimlik" className="tech-id-section">
        <div className="id-heading">
          <p className="tech-overline"><span>04</span> GELİŞTİRİCİ BİLGİSİ</p>
          <h2>Bot kimliği</h2>
          <p>Xyrin Flower AI’ı Discord’da tanımlamak için bot ID’sini kullan.</p>
        </div>
          <div className="id-code-panel" data-testid="panel-bot-id">
          <div className="id-panel-top"><span><i /> BOT ID / PUBLIC</span><span>XYRIN FLOWER</span></div>
          <div className="id-code-line"><code data-testid="text-bot-id">{BOT_ID}</code><button className="copy-id" onClick={copyBotId} aria-label="Bot ID'sini kopyala" data-testid="button-copy-bot-id">
            {copied ? <Check size={16} /> : <Copy size={16} />}<span>{copied ? 'Kopyalandı' : 'Kopyala'}</span>
          </button></div>
          <div className="id-panel-foot"><span>APPLICATION IDENTIFIER</span><span>Discord Developer Portal</span></div>
        </div>
      </section>

      <footer className="tech-footer">
        <a className="footer-logo" href="#baslangic">
          <img src={BANNER_IMAGE} alt="Xyrin Flower AI" />
          <span>XYRIN <b>FLOWER</b></span>
        </a>
        <p>Toplulukların yanında, usulca.</p>
        <div className="footer-links">
          <a href={SERVER_INVITE} target="_blank" rel="noopener noreferrer" data-testid="link-server-invite-footer">Discord sunucusu <ExternalLink size={13} /></a>
          <Link href="/panel" data-testid="link-footer-panel">Panel önizlemesi <ChevronRight size={14} /></Link>
          <span>© XYRIN FLOWER AI</span>
        </div>
      </footer>
    </main>
  );
}
