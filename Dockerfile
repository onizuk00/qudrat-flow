# مرحلة بناء واجهة React
FROM node:18-slim AS frontend-builder
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ .
RUN npm run build

# مرحلة الخادم النهائي
FROM python:3.11-slim
RUN apt-get update && apt-get install -y \
    g++ wget gnupg curl libnss3 libatk-bridge2.0-0 libxkbcommon0 libgtk-3-0 libasound2 \
    && rm -rf /var/lib/apt/lists/*

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt
RUN python -m playwright install chromium

# نسخ مجلد backend بالكامل
COPY backend/ ./backend/

# نسخ الواجهة المبنية من المرحلة الأولى
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# طباعة هيكل الملفات للتأكد (للتشخيص)
RUN ls -la ./frontend/dist/ || echo "frontend/dist not found"
RUN ls -la ./backend/ || echo "backend not found"

ENV PORT=10000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "10000"]
