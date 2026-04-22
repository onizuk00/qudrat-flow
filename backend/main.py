from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse  # <-- تمت الإضافة
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Dict, Optional
import os
import asyncio
from pathlib import Path

# Import from backend package
from backend.database import (
    init_db, save_test, get_all_tests_for_user, get_test_by_id, 
    save_session_results, get_test_history_for_user, 
    get_mistakes_by_test_for_user, get_distinct_wrong_question_ids_for_user, 
    get_questions_by_ids, create_user, get_user_by_username, get_user_by_email,
    get_all_users_for_admin, promote_to_admin, demote_from_admin, 
    delete_user_by_admin, delete_test_by_admin, get_all_tests_for_admin,
    get_all_sessions_for_admin, get_admin_logs, get_admin_stats
)
from backend.scraper import extract_google_form_data
from backend.auth import get_password_hash, authenticate_user, create_access_token, get_current_user, get_current_admin

# Initialize database
init_db()

app = FastAPI(title="Qudrat-Flow API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data Models
class ScrapeRequest(BaseModel):
    url: str

class SubmitRequest(BaseModel):
    test_id: int
    time_spent_seconds: int
    time_limit_seconds: int
    answers: Dict[str, int]

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

# ==================== AUTHENTICATION ENDPOINTS ====================

@app.post("/api/register")
async def register(user_data: UserCreate):
    # Check if user exists
    if get_user_by_username(user_data.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    if get_user_by_email(user_data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user_data.password)
    user_id = create_user(user_data.username, user_data.email, hashed_password)
    access_token = create_access_token(data={"sub": str(user_id)})
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "user_id": user_id, 
        "username": user_data.username
    }

@app.post("/api/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": str(user['id'])})
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "user_id": user['id'], 
        "username": user['username']
    }

@app.get("/api/users/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user

# ==================== SIMPLE HTML PAGES (TEMPORARY UI) ====================

@app.get("/login-page")
async def login_page():
    html_content = """
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>قدرات فلو - تسجيل الدخول</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap" rel="stylesheet">
        <style>body { font-family: 'Tajawal', sans-serif; }</style>
    </head>
    <body class="bg-gradient-to-br from-blue-50 to-teal-50 min-h-screen flex items-center justify-center p-4">
        <div class="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full">
            <h1 class="text-3xl font-bold text-center text-blue-700 mb-6">🔐 قدرات فلو</h1>
            
            <div id="message" class="mb-4 text-center text-sm hidden"></div>
            
            <div id="login-form">
                <input type="text" id="username" placeholder="اسم المستخدم" class="w-full p-3 border rounded-lg mb-3 text-right">
                <input type="password" id="password" placeholder="كلمة المرور" class="w-full p-3 border rounded-lg mb-4 text-right">
                <button onclick="login()" class="w-full bg-blue-600 text-white py-3 rounded-lg font-bold hover:bg-blue-700 transition">تسجيل الدخول</button>
                <p class="text-center text-gray-500 mt-4">ليس لديك حساب؟ <a href="#" onclick="showRegister()" class="text-blue-600">إنشاء حساب</a></p>
            </div>

            <div id="register-form" style="display:none;">
                <input type="text" id="reg-username" placeholder="اسم المستخدم" class="w-full p-3 border rounded-lg mb-3 text-right">
                <input type="email" id="reg-email" placeholder="البريد الإلكتروني" class="w-full p-3 border rounded-lg mb-3 text-right">
                <input type="password" id="reg-password" placeholder="كلمة المرور" class="w-full p-3 border rounded-lg mb-4 text-right">
                <button onclick="register()" class="w-full bg-green-600 text-white py-3 rounded-lg font-bold hover:bg-green-700 transition">إنشاء حساب</button>
                <p class="text-center text-gray-500 mt-4"><a href="#" onclick="showLogin()" class="text-blue-600">عودة لتسجيل الدخول</a></p>
            </div>
        </div>

        <script>
            function showMessage(msg, isError=true) {
                const msgDiv = document.getElementById('message');
                msgDiv.innerText = msg;
                msgDiv.className = 'mb-4 text-center text-sm p-2 rounded ' + (isError ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700');
                msgDiv.classList.remove('hidden');
                setTimeout(() => msgDiv.classList.add('hidden'), 3000);
            }

            async function login() {
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                const formData = new URLSearchParams();
                formData.append('username', username);
                formData.append('password', password);
                try {
                    const res = await fetch('/api/token', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: formData });
                    const data = await res.json();
                    if (res.ok) {
                        localStorage.setItem('token', data.access_token);
                        localStorage.setItem('username', data.username);
                        showMessage('✅ تم تسجيل الدخول بنجاح! جاري التحويل...', false);
                        setTimeout(() => { window.location.href = '/dashboard'; }, 1000);
                    } else {
                        showMessage(data.detail || 'فشل تسجيل الدخول');
                    }
                } catch(e) { showMessage('خطأ في الاتصال'); }
            }

            async function register() {
                const username = document.getElementById('reg-username').value;
                const email = document.getElementById('reg-email').value;
                const password = document.getElementById('reg-password').value;
                try {
                    const res = await fetch('/api/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, email, password }) });
                    const data = await res.json();
                    if (res.ok) {
                        localStorage.setItem('token', data.access_token);
                        localStorage.setItem('username', data.username);
                        showMessage('✅ تم إنشاء الحساب وتسجيل الدخول!', false);
                        setTimeout(() => { window.location.href = '/dashboard'; }, 1000);
                    } else {
                        showMessage(data.detail || 'فشل إنشاء الحساب');
                    }
                } catch(e) { showMessage('خطأ في الاتصال'); }
            }

            function showRegister() { document.getElementById('login-form').style.display='none'; document.getElementById('register-form').style.display='block'; }
            function showLogin() { document.getElementById('register-form').style.display='none'; document.getElementById('login-form').style.display='block'; }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/dashboard")
async def dashboard():
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html dir="rtl">
    <head><meta charset="UTF-8"><title>لوحة التحكم - قدرات فلو</title><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-gray-100 p-8">
        <div class="max-w-4xl mx-auto bg-white rounded-xl shadow p-6">
            <div class="flex justify-between items-center mb-4">
                <button onclick="logout()" class="bg-red-500 text-white px-4 py-2 rounded">تسجيل خروج</button>
                <h1 class="text-2xl font-bold">📚 قدرات فلو</h1>
            </div>
            <p id="user-info" class="mb-4 text-gray-600">جاري تحميل البيانات...</p>
            <hr class="my-4">
            <h2 class="text-xl font-bold">اختباراتي</h2>
            <div id="tests-list" class="mt-2"></div>
            <div class="mt-6">
                <a href="/login-page" class="text-blue-600">← تسجيل الدخول بحساب آخر</a>
            </div>
        </div>
        <script>
            const token = localStorage.getItem('token');
            if (!token) window.location.href = '/login-page';
            fetch('/api/users/me', { headers: { 'Authorization': 'Bearer ' + token } })
                .then(r => r.json()).then(user => { 
                    document.getElementById('user-info').innerHTML = `<strong>${user.username}</strong> (${user.email})`; 
                }).catch(() => window.location.href = '/login-page');
            fetch('/api/tests', { headers: { 'Authorization': 'Bearer ' + token } })
                .then(r => r.json()).then(tests => { 
                    const div = document.getElementById('tests-list');
                    if(tests.length===0) div.innerHTML = '<p class="text-gray-500">لا توجد اختبارات بعد. أضف اختباراً عبر واجهة React لاحقاً.</p>';
                    else tests.forEach(t => { div.innerHTML += `<div class="border p-3 my-2 rounded-lg bg-gray-50">${t.title}</div>`; });
                });
            function logout() { localStorage.removeItem('token'); window.location.href = '/login-page'; }
        </script>
    </body>
    </html>
    """)

# ==================== TEST ENDPOINTS (Protected) ====================

@app.post("/api/scrape")
async def scrape_google_form(request: ScrapeRequest, current_user: dict = Depends(get_current_user)):
    try:
        form_data = await extract_google_form_data(request.url)
        test_id = save_test(
            title=form_data['title'],
            url=request.url,
            reading_passage=form_data.get('reading_passage', ''),
            questions_data=form_data['questions'],
            user_id=current_user['id']
        )
        return {
            "test_id": test_id,
            "title": form_data['title'],
            "question_count": len(form_data['questions'])
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/tests")
async def get_tests(current_user: dict = Depends(get_current_user)):
    return get_all_tests_for_user(current_user['id'])

@app.get("/api/tests/{test_id}")
async def get_test(test_id: int, current_user: dict = Depends(get_current_user)):
    test = get_test_by_id(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    # Optional: Check if test belongs to user (for extra security)
    return test

@app.post("/api/submit")
async def submit_test(request: SubmitRequest, current_user: dict = Depends(get_current_user)):
    try:
        result = save_session_results(
            test_id=request.test_id,
            time_spent_seconds=request.time_spent_seconds,
            answers=request.answers,
            time_limit_seconds=request.time_limit_seconds,
            user_id=current_user['id']
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/history")
async def get_history(current_user: dict = Depends(get_current_user)):
    return get_test_history_for_user(current_user['id'])

@app.get("/api/mistakes")
async def get_mistakes(test_id: Optional[int] = None, current_user: dict = Depends(get_current_user)):
    if test_id:
        return get_mistakes_by_test_for_user(test_id, current_user['id'])
    # If no test_id, return all mistakes across all tests for this user
    # (You may want to implement a function for that, but for now return empty)
    return []

@app.post("/api/retest/{test_id}")
async def retest_mistakes(test_id: int, current_user: dict = Depends(get_current_user)):
    wrong_question_ids = get_distinct_wrong_question_ids_for_user(test_id, current_user['id'])
    if not wrong_question_ids:
        raise HTTPException(status_code=404, detail="No mistakes found for this test")
    questions = get_questions_by_ids(wrong_question_ids)
    test = get_test_by_id(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    return {
        "id": test_id,
        "title": f"{test['title']} (Mistakes Only)",
        "reading_passage": test.get('reading_passage', ''),
        "questions": questions,
        "is_retest": True
    }

# ==================== ADMIN ENDPOINTS ====================

@app.get("/api/admin/users")
async def admin_get_users(admin: dict = Depends(get_current_admin)):
    return get_all_users_for_admin()

@app.post("/api/admin/users/{user_id}/promote")
async def admin_promote_user(user_id: int, admin: dict = Depends(get_current_admin)):
    promote_to_admin(user_id, admin['id'])
    return {"message": f"User {user_id} promoted to admin"}

@app.post("/api/admin/users/{user_id}/demote")
async def admin_demote_user(user_id: int, admin: dict = Depends(get_current_admin)):
    demote_from_admin(user_id, admin['id'])
    return {"message": f"User {user_id} demoted from admin"}

@app.delete("/api/admin/users/{user_id}")
async def admin_delete_user(user_id: int, admin: dict = Depends(get_current_admin)):
    delete_user_by_admin(user_id, admin['id'])
    return {"message": f"User {user_id} deleted"}

@app.get("/api/admin/tests")
async def admin_get_tests(admin: dict = Depends(get_current_admin)):
    return get_all_tests_for_admin()

@app.delete("/api/admin/tests/{test_id}")
async def admin_delete_test(test_id: int, admin: dict = Depends(get_current_admin)):
    delete_test_by_admin(test_id, admin['id'])
    return {"message": f"Test {test_id} deleted"}

@app.get("/api/admin/sessions")
async def admin_get_sessions(admin: dict = Depends(get_current_admin)):
    return get_all_sessions_for_admin()

@app.get("/api/admin/logs")
async def admin_get_logs(admin: dict = Depends(get_current_admin)):
    return get_admin_logs(limit=100)

@app.get("/api/admin/stats")
async def admin_get_stats(admin: dict = Depends(get_current_admin)):
    return get_admin_stats()

# ==================== DEBUG ENDPOINT ====================

@app.get("/debug")
async def debug_info(current_user: dict = Depends(get_current_user)):
    current = Path(__file__).resolve().parent
    parent = current.parent
    frontend_dist = parent / "frontend" / "dist"
    
    info = {
        "user": current_user,
        "current_dir": str(current),
        "parent_dir": str(parent),
        "frontend_dist_exists": frontend_dist.exists(),
        "frontend_dist_is_dir": frontend_dist.is_dir() if frontend_dist.exists() else False,
        "index_html_exists": (frontend_dist / "index.html").exists() if frontend_dist.exists() else False,
        "assets_dir_exists": (frontend_dist / "assets").exists() if frontend_dist.exists() else False,
        "files_in_dist": []
    }
    
    if frontend_dist.exists() and frontend_dist.is_dir():
        try:
            for item in frontend_dist.iterdir():
                info["files_in_dist"].append(item.name)
        except:
            pass
    
    return info

# ==================== SERVE FRONTEND STATIC FILES ====================

current_dir = Path(__file__).resolve().parent.parent
frontend_dist = current_dir / "frontend" / "dist"

print(f"Looking for frontend at: {frontend_dist}")
print(f"Exists: {frontend_dist.exists()}")

if frontend_dist.exists() and frontend_dist.is_dir():
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    
    @app.get("/")
    async def serve_root():
        index_file = frontend_dist / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        # إذا لم توجد الواجهة، انتقل إلى صفحة تسجيل الدخول البسيطة
        return HTMLResponse(status_code=302, headers={"Location": "/login-page"})
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # تجنب التعارض مع المسارات الجديدة
        if full_path.startswith("api/") or full_path.startswith("debug") or full_path.startswith("login-page") or full_path.startswith("dashboard"):
            raise HTTPException(status_code=404)
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(frontend_dist / "index.html"))
else:
    print("WARNING: Frontend dist not found! Using fallback HTML pages.")
    # إذا لم توجد الواجهة، نستخدم صفحاتنا البديلة
    @app.get("/")
    async def root_fallback():
        return HTMLResponse(status_code=302, headers={"Location": "/login-page"})

# ==================== KEEP-ALIVE ====================

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(keep_alive())

async def keep_alive():
    while True:
        await asyncio.sleep(840)  # 14 minutes
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.get(f"http://localhost:{os.getenv('PORT', 8000)}/api/tests")
        except Exception:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
