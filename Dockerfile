# ==============================================================================
# XYRIN BOT — DOCKERFILE
# Render, Railway, VPS veya kendi sunucunuzda çalıştırmak için.
# ==============================================================================
FROM python:3.11-slim

WORKDIR /app

# Sistem bağımlılıkları (gerekirse derleme araçları)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python bağımlılıkları
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyaları
COPY . .

# Çıktı buffering kapat (loglar anında gelsin)
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Render PORT'u otomatik olarak ayarlar; docker-compose içinde de override edilebilir.
ENV PORT=10000
ENV DATA_DIR=/app/data

# Veri kalıcılığı için volume (isteğe bağlı)
VOLUME ["/app/data"]

CMD ["python", "xyrin_bot.py"]