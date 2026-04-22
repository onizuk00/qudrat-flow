# مرحلة 1: بناء واجهة React
FROM node:18-slim AS frontend-builder

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ .
RUN npm run build

# مرحلة 2: بناء خادم Python النهائي
FROM python:3.11-slim

# تثبيت المتطلبات الأساسية (بما فيها g++ و Playwright)
RUN apt-get update && apt-get install -y \
    g++ \
    wget \
    gnupg \
    curl \
    libnss3 \
    libatk-bridge2.0-0 \
    libxkbcommon0 \
    libgtk-3-0 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# نسخ متطلبات Python وتثبيتها
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# تثبيت متصفح Playwright
RUN python -m playwright install chromium

# نسخ كود الخادم
COPY backend/ ./backend/
COPY backend/__init__.py ./backend/
COPY backend/main.py ./backend/
COPY backend/database.py ./backend/
COPY backend/scraper.py ./backend/

# نسخ واجهة React المبنية من المرحلة الأولى
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# تعيين متغير البيئة للمنفذ
ENV PORT=10000

# تشغيل الخادم
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
