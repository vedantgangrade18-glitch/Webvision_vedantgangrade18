# Karu API + workers image (Python 3.12, ffmpeg for video keyframes, Noto fonts + libraqm
# for correctly shaped Indic text on share images and tag sheets).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg libraqm0 fonts-noto-core fonts-noto-ui-core curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN useradd --create-home karu && mkdir -p /app/var && chown -R karu /app/var
USER karu

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
