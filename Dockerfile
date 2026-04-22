# مرحلة 1: بناء واجهة React
FROM node:18-slim AS frontend-builder

WORKDIR /frontend

# نسخ ملفات الحزمة أولاً لتثبيت الاعتماديات
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

# نسخ باقي ملفات الواجهة
COPY frontend/ .

# بناء التطبيق
RUN npm run build

# مرحلة 2: بناء خادم Python النهائي
FROM python:3.11-slim

# تثبيت المتطلبات الأساسية
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

# تعيين مسار العمل إلى المجلد الرئيسي للتطبيق
WORKDIR /app

# تعيين PYTHONPATH ليشمل المجلد الحالي
ENV PYTHONPATH=/app

# نسخ متطلبات Python وتثبيتها
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# تثبيت متصفح Playwright
RUN python -m playwright install chromium

# نسخ كود الخادم (Backend) كاملاً
COPY backend/ ./backend/

# نسخ ملفات الواجهة المبنية من المرحلة الأولى
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# تعيين متغير البيئة للمنفذ
ENV PORT=10000

# تشغيل الخادم (ملاحظة: الأمر هنا يتغير)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "10000"]
