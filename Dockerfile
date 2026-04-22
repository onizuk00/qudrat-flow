# مرحلة بناء واجهة React
FROM node:18-alpine AS frontend-builder

WORKDIR /frontend

# نسخ ملفات الحزمة
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --only=production || npm install

# نسخ باقي ملفات الواجهة وبناؤها
COPY frontend/ .
RUN npm run build

# مرحلة الخادم النهائي
FROM python:3.11-slim

# تثبيت المتطلبات الأساسية
RUN apt-get update && apt-get install -y \
    g++ \
    wget \
    curl \
    libnss3 \
    libatk-bridge2.0-0 \
    libxkbcommon0 \
    libgtk-3-0 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
WORKDIR /app

# نسخ وتثبيت متطلبات Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# تثبيت متصفح Playwright
RUN python -m playwright install chromium

# نسخ كود الخادم
COPY backend/ ./backend/

# نسخ الواجهة المبنية
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# تعيين متغيرات البيئة
ENV PORT=10000
ENV PYTHONPATH=/app

# تشغيل التطبيق
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "10000"]
