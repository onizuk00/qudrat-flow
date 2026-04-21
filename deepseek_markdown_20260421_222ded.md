# قدرات فلو | Qudrat-Flow

منصة اختبارات قدرات متكاملة تسمح باستيراد اختبارات Google Forms وتحويلها إلى بيئة اختبار احترافية.

## النشر على Render

1. ارفع الكود إلى GitHub.
2. في Render، اختر New Web Service.
3. استخدم الإعدادات التالية:
   - Build Command: `pip install -r requirements.txt && playwright install chromium && cd frontend && npm install && npm run build && cd ..`
   - Start Command: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Environment Variable: `PLAYWRIGHT_BROWSERS_PATH` = `/opt/render/.cache/ms-playwright`