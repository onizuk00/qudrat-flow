FROM python:3.13-slim

# تثبيت g++ ومكتبات النظام الضرورية للبناء
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

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

RUN python -m playwright install chromium

COPY . .

EXPOSE 10000
CMD cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
