from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import Dict, Optional
import os
import asyncio
from pathlib import Path

from backend.database import (
    init_db, create_user, get_user_by_username, get_user_by_email,
    get_all_tests_for_user, get_test_by_id, save_test,
    save_session_results, get_test_history_for_user,
    create_password_reset, verify_reset_code, update_user_password
)
from backend.scraper import extract_google_form_data
from backend.auth import get_password_hash, authenticate_user, create_access_token, get_current_user
from backend.email_utils import send_reset_email

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

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    reset_code: str
    new_password: str

# -------------------- AUTHENTICATION --------------------
@app.post("/api/register")
async def register(user: UserCreate):
    try:
        # اقتصاص كلمة المرور احتياطياً (لحل مشكلة bcrypt)
        user.password = user.password[:72]
        if get_user_by_username(user.username):
            raise HTTPException(400, "اسم المستخدم موجود مسبقاً")
        if get_user_by_email(user.email):
            raise HTTPException(400, "البريد الإلكتروني موجود مسبقاً")
        hashed = get_password_hash(user.password)
        user_id = create_user(user.username, user.email, hashed)
        token = create_access_token(data={"sub": str(user_id)})
        return {
            "access_token": token,
            "token_type": "bearer",
            "user_id": user_id,
            "username": user.username
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Registration error: {e}")
        raise HTTPException(500, f"خطأ داخلي: {str(e)}")

@app.post("/api/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        user = authenticate_user(form_data.username, form_data.password)
        if not user:
            raise HTTPException(400, "اسم المستخدم أو كلمة المرور غير صحيحة")
        token = create_access_token(data={"sub": str(user['id'])})
        return {
            "access_token": token,
            "token_type": "bearer",
            "user_id": user['id'],
            "username": user['username']
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(500, f"خطأ داخلي: {str(e)}")

@app.get("/api/users/me")
async def me(current_user: dict = Depends(get_current_user)):
    return current_user

# -------------------- PASSWORD RESET --------------------
@app.post("/api/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, background_tasks: BackgroundTasks):
    user = get_user_by_email(request.email)
    if not user:
        # لأسباب أمنية لا نكشف وجود البريد
        return {"message": "إذا كان البريد الإلكتروني مسجلاً، فسيتم إرسال كود التحقق"}
    
    reset_code = create_password_reset(user['id'])
    background_tasks.add_task(send_reset_email, request.email, reset_code)
    return {"message": "تم إرسال كود التحقق إلى بريدك الإلكتروني"}

@app.post("/api/reset-password")
async def reset_password(request: ResetPasswordRequest):
    user = get_user_by_email(request.email)
    if not user:
        raise HTTPException(status_code=400, detail="البريد الإلكتروني غير مسجل")
    
    if not verify_reset_code(user['id'], request.reset_code):
        raise HTTPException(status_code=400, detail="الكود غير صالح أو منتهي الصلاحية")
    
    new_hashed = get_password_hash(request.new_password[:72])
    update_user_password(user['id'], new_hashed)
    return {"message": "تم إعادة تعيين كلمة المرور بنجاح"}

# -------------------- API ENDPOINTS --------------------
@app.post("/api/scrape")
async def scrape(req: ScrapeRequest, current_user: dict = Depends(get_current_user)):
    try:
        data = await extract_google_form_data(req.url)
        test_id = save_test(
            data['title'], req.url, data.get('reading_passage', ''),
            data['questions'], current_user['id']
        )
        return {
            "test_id": test_id,
            "title": data['title'],
            "question_count": len(data['questions'])
        }
    except Exception as e:
        raise HTTPException(400, str(e))

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
    return save_session_results(
        req.test_id, req.time_spent_seconds, req.answers,
        req.time_limit_seconds, current_user['id']
    )

@app.get("/api/history")
async def history(current_user: dict = Depends(get_current_user)):
    return get_test_history_for_user(current_user['id'])

# -------------------- HTML PAGES (UI) --------------------
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
        
        <!-- نموذج تسجيل الدخول -->
        <div id="login-form">
            <input type="text" id="username" placeholder="اسم المستخدم" class="w-full p-3 rounded-lg mb-3 text-right bg-white/20 text-white placeholder-white/70 border border-white/30 focus:outline-none focus:ring-2 focus:ring-blue-400">
            <input type="password" id="password" placeholder="كلمة المرور" class="w-full p-3 rounded-lg mb-4 text-right bg-white/20 text-white placeholder-white/70 border border-white/30 focus:outline-none focus:ring-2 focus:ring-blue-400">
            <button onclick="login()" class="w-full bg-gradient-to-r from-blue-500 to-indigo-600 text-white py-3 rounded-lg font-bold hover:shadow-lg transition">تسجيل الدخول</button>
            <p class="text-center text-white/80 mt-3">ليس لديك حساب؟ <a href="#" onclick="showRegister()" class="text-blue-300">إنشاء حساب</a></p>
            <p class="text-center text-white/70 text-sm mt-2"><a href="#" onclick="showForgot()" class="text-blue-300">نسيت كلمة المرور؟</a></p>
        </div>
        
        <!-- نموذج إنشاء حساب -->
        <div id="register-form" style="display:none;">
            <input type="text" id="reg-username" placeholder="اسم المستخدم" class="w-full p-3 rounded-lg mb-3 text-right bg-white/20 text-white placeholder-white/70 border border-white/30">
            <input type="email" id="reg-email" placeholder="البريد الإلكتروني" class="w-full p-3 rounded-lg mb-3 text-right bg-white/20 text-white placeholder-white/70 border border-white/30">
            <input type="password" id="reg-password" placeholder="كلمة المرور" class="w-full p-3 rounded-lg mb-2 text-right bg-white/20 text-white placeholder-white/70 border border-white/30">
            <div class="text-right text-white/80 text-sm space-y-1 mt-2">
                <p class="font-bold mb-1">متطلبات كلمة المرور:</p>
                <div id="req-length"><span>🔴</span> 8 أحرف على الأقل</div>
                <div id="req-upper"><span>🔴</span> حرف كبير واحد على الأقل (A-Z)</div>
                <div id="req-lower"><span>🔴</span> حرف صغير واحد على الأقل (a-z)</div>
                <div id="req-digit"><span>🔴</span> رقم واحد على الأقل (0-9)</div>
            </div>
            <div id="reg-password-valid" class="text-green-400 text-center mt-2" style="display:none;">✅ كلمة المرور قوية</div>
            <button id="register-btn" onclick="register()" class="w-full bg-gradient-to-r from-green-500 to-emerald-600 text-white py-3 rounded-lg font-bold hover:shadow-lg transition mt-4 opacity-50 cursor-not-allowed" disabled>إنشاء حساب</button>
            <p class="text-center text-white/80 mt-4"><a href="#" onclick="showLogin()" class="text-blue-300">عودة لتسجيل الدخول</a></p>
        </div>
        
        <!-- نموذج طلب إعادة تعيين كلمة المرور -->
        <div id="forgot-form" style="display:none;">
            <input type="email" id="reset-email" placeholder="البريد الإلكتروني" class="w-full p-3 rounded-lg mb-4 text-right bg-white/20 text-white placeholder-white/70 border border-white/30 focus:outline-none focus:ring-2 focus:ring-blue-400">
            <button onclick="requestReset()" class="w-full bg-gradient-to-r from-yellow-500 to-orange-500 text-white py-3 rounded-lg font-bold hover:shadow-lg transition">إرسال كود التحقق</button>
            <p class="text-center text-white/80 mt-4"><a href="#" onclick="showLogin()" class="text-blue-300">← عودة لتسجيل الدخول</a></p>
            <div id="reset-message" class="mt-3 text-center text-sm hidden"></div>
        </div>
        
        <!-- نموذج إدخال الكود وكلمة المرور الجديدة -->
        <div id="verify-form" style="display:none;">
            <input type="hidden" id="verify-email">
            <input type="text" id="verify-code" placeholder="كود التحقق" class="w-full p-3 rounded-lg mb-3 text-right bg-white/20 text-white placeholder-white/70 border border-white/30">
            <input type="password" id="new-password" placeholder="كلمة المرور الجديدة" class="w-full p-3 rounded-lg mb-4 text-right bg-white/20 text-white placeholder-white/70 border border-white/30">
            <button onclick="resetPassword()" class="w-full bg-gradient-to-r from-green-500 to-emerald-600 text-white py-3 rounded-lg font-bold hover:shadow-lg transition">إعادة تعيين كلمة المرور</button>
            <p class="text-center text-white/80 mt-4"><a href="#" onclick="showLogin()" class="text-blue-300">← عودة لتسجيل الدخول</a></p>
            <div id="verify-message" class="mt-3 text-center text-sm hidden"></div>
        </div>
    </div>

    <script>
        let passwordValid = false;
        
        function checkPasswordStrength() {
            const pwd = document.getElementById('reg-password').value;
            const lengthOk = pwd.length >= 8;
            const upperOk = /[A-Z]/.test(pwd);
            const lowerOk = /[a-z]/.test(pwd);
            const digitOk = /[0-9]/.test(pwd);
            
            document.getElementById('req-length').innerHTML = (lengthOk ? '✅' : '🔴') + ' 8 أحرف على الأقل';
            document.getElementById('req-upper').innerHTML = (upperOk ? '✅' : '🔴') + ' حرف كبير واحد على الأقل (A-Z)';
            document.getElementById('req-lower').innerHTML = (lowerOk ? '✅' : '🔴') + ' حرف صغير واحد على الأقل (a-z)';
            document.getElementById('req-digit').innerHTML = (digitOk ? '✅' : '🔴') + ' رقم واحد على الأقل (0-9)';
            
            const allOk = lengthOk && upperOk && lowerOk && digitOk;
            const validDiv = document.getElementById('reg-password-valid');
            const registerBtn = document.getElementById('register-btn');
            
            if (allOk) {
                validDiv.style.display = 'block';
                registerBtn.disabled = false;
                registerBtn.classList.remove('opacity-50', 'cursor-not-allowed');
                passwordValid = true;
            } else {
                validDiv.style.display = 'none';
                registerBtn.disabled = true;
                registerBtn.classList.add('opacity-50', 'cursor-not-allowed');
                passwordValid = false;
            }
            return allOk;
        }
        
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
            }catch(e){showMessage('خطأ في الاتصال: '+e.message);}
        }
        
        async function register(){
            if(!passwordValid){
                showMessage('يرجى التأكد من أن كلمة المرور تستوفي جميع المتطلبات');
                return;
            }
            let u=document.getElementById('reg-username').value;
            let e=document.getElementById('reg-email').value;
            let p=document.getElementById('reg-password').value;
            if(!u || !e || !p){
                showMessage('جميع الحقول مطلوبة');
                return;
            }
            try{
                let res=await fetch('/api/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,email:e,password:p})});
                let data=await res.json();
                if(res.ok){
                    localStorage.setItem('token',data.access_token);
                    localStorage.setItem('username',data.username);
                    showMessage('✅ تم إنشاء الحساب بنجاح!',false);
                    setTimeout(()=>window.location.href='/dashboard',1000);
                }else{
                    showMessage(data.detail||'فشل إنشاء الحساب');
                }
            }catch(e){showMessage('خطأ في الاتصال: '+e.message);}
        }
        
        // Forgot password functions
        function showForgot(){
            document.getElementById('login-form').style.display='none';
            document.getElementById('register-form').style.display='none';
            document.getElementById('forgot-form').style.display='block';
            document.getElementById('verify-form').style.display='none';
        }
        
        async function requestReset(){
            let email = document.getElementById('reset-email').value;
            if(!email){
                showMessage('الرجاء إدخال البريد الإلكتروني', true);
                return;
            }
            try{
                let res = await fetch('/api/forgot-password', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({email: email})
                });
                let data = await res.json();
                if(res.ok){
                    showMessage('تم إرسال كود التحقق إلى بريدك الإلكتروني', false);
                    document.getElementById('verify-email').value = email;
                    document.getElementById('forgot-form').style.display='none';
                    document.getElementById('verify-form').style.display='block';
                } else {
                    showMessage(data.detail || 'حدث خطأ، حاول مرة أخرى');
                }
            } catch(e){
                showMessage('خطأ في الاتصال: '+e.message);
            }
        }
        
        async function resetPassword(){
            let email = document.getElementById('verify-email').value;
            let code = document.getElementById('verify-code').value;
            let newPwd = document.getElementById('new-password').value;
            if(!code || !newPwd){
                showMessage('الرجاء إدخال الكود وكلمة المرور الجديدة');
                return;
            }
            try{
                let res = await fetch('/api/reset-password', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({email: email, reset_code: code, new_password: newPwd})
                });
                let data = await res.json();
                if(res.ok){
                    showMessage('تم إعادة تعيين كلمة المرور بنجاح. يمكنك الآن تسجيل الدخول', false);
                    setTimeout(() => showLogin(), 2000);
                } else {
                    showMessage(data.detail || 'فشل إعادة التعيين');
                }
            } catch(e){
                showMessage('خطأ في الاتصال: '+e.message);
            }
        }
        
        function showRegister(){
            document.getElementById('login-form').style.display='none';
            document.getElementById('register-form').style.display='block';
            document.getElementById('forgot-form').style.display='none';
            document.getElementById('verify-form').style.display='none';
            document.getElementById('reg-password').addEventListener('input', checkPasswordStrength);
            checkPasswordStrength();
        }
        function showLogin(){
            document.getElementById('login-form').style.display='block';
            document.getElementById('register-form').style.display='none';
            document.getElementById('forgot-form').style.display='none';
            document.getElementById('verify-form').style.display='none';
        }
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
        const token = localStorage.getItem('token');
        if(!token) window.location.href = '/login-page';
        fetch('/api/users/me', {headers: {'Authorization': 'Bearer '+token}})
            .then(r => r.json())
            .then(user => { document.getElementById('user-info').innerHTML = `<strong class="text-white">${user.username}</strong> <span class="text-gray-300">(${user.email})</span>`; })
            .catch(() => window.location.href = '/login-page');
        fetch('/api/tests', {headers: {'Authorization': 'Bearer '+token}})
            .then(r => r.json())
            .then(tests => {
                let div = document.getElementById('tests-list');
                if(tests.length===0) div.innerHTML = '<p class="text-gray-300">لا توجد اختبارات بعد. أضف اختباراً عبر واجهة React لاحقاً.</p>';
                else tests.forEach(t => { div.innerHTML += `<div class="bg-white/5 border border-white/10 rounded-xl p-3 text-white">${t.title}</div>`; });
            });
        function logout(){ localStorage.removeItem('token'); window.location.href = '/login-page'; }
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

# -------------------- KEEP-ALIVE --------------------
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
