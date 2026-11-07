# 🗺️ Xyrin Bot — Geliştirme Haritası (Türkçe)

Mevcut dosya `xyrin_bot.py` tek dosyalık (~4550 satır) ve sorunsuz çalışıyor.
Aşağıdaki adımlarla onu modüler, dağıtılabilir ve genişletilebilir hale getirebilirsin.

---

## 1. Altyapı (Hemen yapabilirsin)

Bu klasörde zaten oluşturduğum dosyalar:

| Dosya | Açıklama |
|-------|----------|
| `.env.example` | Tüm gizli anahtarların şablonu |
| `requirements.txt` | Python paketleri |
| `Dockerfile` | Render / VPS / her yerde çalışır |
| `docker-compose.yml` | Yerel test ve konteynerleştirme |
| `cogs/__init__.py` | Komut modülü paketi |
| `cogs/economy.py` | Tek bir komut grubunun cogs'a nasıl taşınacağı |

**Kullanım:**
```bash
cp .env.example .env
# .env içine kendi tokenlerini gir
docker-compose up --build
```

---

## 2. Modülerleştirme (Cogs) — Önerilen sıra

`xyrin_bot.py` tek dosyadır ve büyüdükçe zorlaşır. Şu sırayla böl:

1. **`cogs/general.py`** — `yardim`, `ping`, `kimlik`, `kahve`, `hologram`, `rapor`, `seslen`, `ayrıl`
2. **`cogs/economy.py`** — `bakiye`, `seviye`, `gunluk`, `transfer`, `market`, `satinal`, `zar`, `yazitura`, `bahis`, `siralama`, `calis`, `suc`, `soy`
3. **`cogs/ai.py`** — `sor`, `ara`, `ozetle`, `sifirla`
4. **`cogs/moderation.py`** — `kanaloluştur`, `rololuştur`, `kick`, `ban`, `mute`, `temizle`, `kilitle`, `rolver`, `kufur`, `modlog`, `hosgeldin`
5. **`cogs/utility.py`** — `afk`, `kullanici`, `sunucu`, `avatar`, `anket`, `oneri`, `hatirlat`, `etkinlik`, `cekilis`, `evrim`, `yedekle`, `sync`
6. **`cogs/events.py`** — `on_message`, `on_ready`, `on_member_join`, vb.

Her cog'ın en altına:
```python
async def setup(bot):
    await bot.add_cog( XxxCog(bot) )
```
eklenir ve `xyrin_bot.py`'de:
```python
await bot.load_extension("cogs.economy")
```
şeklinde yüklenir.

---

## 3. Veritabanı İyileştirmesi

Şu an tüm veri JSON dosyalarında (`JsonStore`). Sunucu/üye sayısı arttıkça:

- **Kısa vadeli:** JSON yedekleme zaten var (`BACKUP_CHANNEL_ID`), devam et.
- **Orta vadeli:** `SQLite` (`aiosqlite`) veya `PostgreSQL` geçişi yap. `EconomyManager`, `StrikeManager`, `ReminderManager` gibi sınıfları veritabanına taşı.
- **Uzun vadeli:** Web dashboard (FastAPI/Flask) ile bakiye, ayarları webden yönet.

---

## 4. Yeni Komut Önerileri

- 🎵 Müzik çalar (YouTube / Spotify, ses kanalı)
- 🎫 Ticket / destek sistemi
- 🎂 Doğum günü takvimi ve otomatik rol
- 🎮 Oyun statı izleme (Steam, Valorant, LoL)
- 🎭 Oto-rol (yeni gelenlere otomatik rol ver)
- 🖼️ Görsel üretim (DALL-E / Midjourney API entegrasyonu)
- 🔊 Seslendirme (TTS)

---

## 5. Render Dağıtım İpuçları

- **Free tier:** 15 dk istek yoksa uyur. `/health` endpoint'ine UptimeRobot ile 5 dakikada bir ping at.
- **Disk:** Free Render'da disk silinir. `BACKUP_CHANNEL_ID` ile Discord kanalına yedekleme zaten var — bunu koru.
- **Worker:** Sadece Discord botuysan Render'da "Background Worker" olarak da çalıştırabilirsin (`PORT` ile uğraşmana gerek kalmaz).

---

## 6. Güvenlik

- `.env` dosyasını asla GitHub'a yükleme.
- `.gitignore` oluştur:
  ```
  .env
  __pycache__/
  *.pyc
  data/
  *.log
  ```
- Token sızarsa Discord Developer Panel'de hemen yenile.

---

## Sıradaki Adım

Hangi bölüme başlamak istersin?
1. `cogs` yapısına tam geçiş yapabilirim (tüm komutları ayırırım).
2. `SQLite` veritabanına geçiş yapabilirim.
3. Yeni bir komut ekleyebilirim (hangi türde?).
4. Docker/Render ayarlarını-netleştirebilirim.

Söyle, devam edelim.