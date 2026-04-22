from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Dict, Optional
import os
import asyncio
from pathlib import Path

from database import init_db, create_user, get_user_by_username, get_user_by_email, get_all_tests_for_user, get_test_by_id, save_test, save_session_results, get_test_history_for_user
from scraper import extract_google_form_data
from auth import get_password_hash, authenticate_user, create_access_token, get_current_user

# -------------------- INIT --------------------
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

# -------------------- MODELS --------------------
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

# -------------------- AUTHENTICATION --------------------
@app.post("/api/register")
async def register(user: UserCreate):
    if get_user_by_username(user.username):
        raise HTTPException(400, "Username already registered")
    if get_user_by_email(user.email):
        raise HTTPException(400, "Email already registered")
    hashed = get_password_hash(user.password)
    user_id = create_user(user.username, user.email, hashed)
    token = create_access_token(data={"sub": str(user_id)})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user_id,
        "username": user.username
    }

@app.post("/api/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(400, "Incorrect username or password")
    token = create_access_token(data={"sub": str(user['id'])})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user['id'],
        "username": user['username']
    }

@app.get("/api/users/me")
async def me(current_user: dict = Depends(get_current_user)):
    return current_user

# -------------------- API ENDPOINTS --------------------
@app.post("/api/scrape")
async def scrape(req: ScrapeRequest, current_user: dict = Depends(get_current_user)):
    data = await extract_google_form_data(req.url)
    test_id = save_test(data['title'], req.url, data.get('reading_passage', ''), data['questions'], current_user['id'])
    return {
        "test_id": test_id,
        "title": data['title'],
        "question_count": len(data['questions'])
    }

@app.get("/api/tests")
async def tests(current_user: dict = Depends(get_current_user)):
    return get_all_tests_for_user(current_user['id'])

@app.get("/api/tests/{test_id}")
async def get_test(test_id: int, current_user: dict = Depends(get_current_user)):
    test = get_test_by_id(test_id)
    if not test:
        raise HTTPException(404, "Test not found")
    return test

@app.post("/api/submit")
async def submit(req: SubmitRequest, current_user: dict = Depends(get_current_user)):
    return save_session_results(req.test_id, req.time_spent_seconds, req.answers, req.time_limit_seconds, current_user['id'])

@app.get("/api/history")
async def history(current_user: dict = Depends(get_current_user)):
    return get_test_history_for_user(current_user['id'])

# -------------------- HTML PAGES --------------------
LOGIN_PAGE_HTML = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>قدرات فلو - تسجيل الدخول</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap" rel="stylesheet">
    <style>body{font-family:'Tajawal',sans-serif;}</style>
</head>
<body class="bg-gradient-to-br from-blue-900 via-purple-800 to-indigo-900 min-h-screen flex items-center justify-center p-4">
    <div class="bg-white/10 backdrop-blur-lg rounded-2xl shadow-2xl p-8 max-w-md w-full border border-white/20">
        <h1 class="text-4xl font-bold text-center text-white mb-6">🔐 قدرات فلو</h1>
        <div id="message" class="mb-4 text-center text-sm hidden"></div>
        <div id="login-form">
            <input type="text" id="username" placeholder="اسم المستخدم" class="w-full p-3 rounded-lg mb-3 text-right bg-white/20 text-white placeholder-white/70 border border-white/30 focus:outline-none focus:ring-2 focus:ring-blue-400">
            <input type="password" id="password" placeholder="كلمة المرور" class="w-full p-3 rounded-lg mb-4 text-right bg-white/20 text-white placeholder-white/70 border border-white/30 focus:outline-none focus:ring-2 focus:ring-blue-400">
            <button onclick="login()" class="w-full bg-gradient-to-r from-blue-500 to-indigo-600 text-white py-3 rounded-lg font-bold hover:shadow-lg transition">تسجيل الدخول</button>
            <p class="text-center text-white/80 mt-4">ليس لديك حساب؟ <a href="#" onclick="showRegister()" class="text-blue-300">إنشاء حساب</a></p>
        </div>
        <div id="register-form" style="display:none;">
            <input type="text" id="reg-username" placeholder="اسم المستخدم" class="w-full p-3 rounded-lg mb-3 text-right bg-white/20 text-white placeholder-white/70 border border-white/30">
            <input type="email" id="reg-email" placeholder="البريد الإلكتروني" class="w-full p-3 rounded-lg mb-3 text-right bg-white/20 text-white placeholder-white/70 border border-white/30">
            <input type="password" id="reg-password" placeholder="كلمة المرور" class="w-full p-3 rounded-lg mb-4 text-right bg-white/20 text-white placeholder-white/70 border border-white/30">
            <button onclick="register()" class="w-full bg-gradient-to-r from-green-500 to-emerald-600 text-white py-3 rounded-lg font-bold hover:shadow-lg transition">إنشاء حساب</button>
            <p class="text-center text-white/80 mt-4"><a href="#" onclick="showLogin()" class="text-blue-300">عودة لتسجيل الدخول</a></p>
        </div>
    </div>
    <script>
        function showMessage(msg, isError=true){
            let d=document.getElementById('message');
            d.innerText=msg;
            d.className='mb-4 text-center text-sm p-2 rounded '+(isError?'bg-red-500/80 text-white':'bg-green-500/80 text-white');
            d.classList.remove('hidden');
            setTimeout(()=>d.classList.add('hidden'),3000);
        }
        async function login(){
            let u=document.getElementById('username').value,p=document.getElementById('password').value;
            let fd=new URLSearchParams();
            fd.append('username',u);
            fd.append('password',p);
            try{
                let res=await fetch('/api/token',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:fd});
                let data=await res.json();
                if(res.ok){
                    localStorage.setItem('token',data.access_token);
                    localStorage.setItem('username',data.username);
                    showMessage('✅ تم تسجيل الدخول بنجاح!',false);
                    setTimeout(()=>window.location.href='/dashboard',1000);
                }else showMessage(data.detail||'فشل تسجيل الدخول');
            }catch(e){showMessage('خطأ في الاتصال');}
        }
        async function register(){
            let u=document.getElementById('reg-username').value,e=document.getElementById('reg-email').value,p=document.getElementById('reg-password').value;
            try{
                let res=await fetch('/api/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,email:e,password:p})});
                let data=await res.json();
                if(res.ok){
                    localStorage.setItem('token',data.access_token);
                    localStorage.setItem('username',data.username);
                    showMessage('✅ تم إنشاء الحساب بنجاح!',false);
                    setTimeout(()=>window.location.href='/dashboard',1000);
                }else showMessage(data.detail||'فشل إنشاء الحساب');
            }catch(e){showMessage('خطأ في الاتصال');}
        }
        function showRegister(){document.getElementById('login-form').style.display='none';document.getElementById('register-form').style.display='block';}
        function showLogin(){document.getElementById('register-form').style.display='none';document.getElementById('login-form').style.display='block';}
    </script>
</body>
</html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>لوحة التحكم - قدرات فلو</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gradient-to-br from-gray-900 to-gray-800 p-8">
    <div class="max-w-5xl mx-auto">
        <div class="bg-white/10 backdrop-blur-lg rounded-2xl shadow-2xl p-6 border border-white/20">
            <div class="flex justify-between items-center mb-4">
                <button onclick="logout()" class="bg-red-500/80 hover:bg-red-600 text-white px-4 py-2 rounded-lg">تسجيل خروج</button>
                <h1 class="text-3xl font-bold text-white">📚 قدرات فلو</h1>
            </div>
            <p id="user-info" class="text-white/80 mb-4">جاري التحميل...</p>
            <hr class="my-4 border-white/20">
            <h2 class="text-xl font-bold text-white mb-2">اختباراتي</h2>
            <div id="tests-list" class="space-y-2"></div>
            <div class="mt-6 text-center"><a href="/login-page" class="text-blue-300">← تسجيل الدخول بحساب آخر</a></div>
        </div>
    </div>
    <script>
        const token=localStorage.getItem('token');
        if(!token)window.location.href='/login-page';
        fetch('/api/users/me',{headers:{'Authorization':'Bearer '+token}}).then(r=>r.json()).then(user=>{document.getElementById('user-info').innerHTML=`<strong class="text-white">${user.username}</strong> <span class="text-gray-300">(${user.email})</span>`;}).catch(()=>window.location.href='/login-page');
        fetch('/api/tests',{headers:{'Authorization':'Bearer '+token}}).then(r=>r.json()).then(tests=>{let div=document.getElementById('tests-list');if(tests.length===0)div.innerHTML='<p class="text-gray-300">لا توجد اختبارات بعد. أضف اختباراً عبر واجهة React لاحقاً.</p>';else tests.forEach(t=>{div.innerHTML+=`<div class="bg-white/5 border border-white/10 rounded-xl p-3 text-white">${t.title}</div>`;});});
        function logout(){localStorage.removeItem('token');window.location.href='/login-page';}
    </script>
</body>
</html>
"""

@app.get("/")
async def root():
    return RedirectResponse(url="/login-page", status_code=302)

@app.get("/login-page")
async def login_page():
    return HTMLResponse(content=LOGIN_PAGE_HTML)

@app.get("/dashboard")
async def dashboard():
    return HTMLResponse(content=DASHBOARD_HTML)

# -------------------- KEEP-ALIVE (OPTIONAL) --------------------
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(keep_alive())

async def keep_alive():
    while True:
        await asyncio.sleep(840)
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.get(f"http://localhost:{os.getenv('PORT', 8000)}/api/tests")
        except Exception:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
