FROM python:3.11-slim

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
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

RUN python -m playwright install chromium

COPY backend/ ./backend/
COPY backend/__init__.py ./backend/
COPY backend/main.py ./backend/
COPY backend/database.py ./backend/
COPY backend/scraper.py ./backend/

COPY --from=frontend-builder /frontend/dist ./frontend/dist

ENV PORT=10000
EXPOSE $PORT

# تشغيل مع 2 عامل (workers) لتحسين التوافقية
CMD cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT --workers 2
