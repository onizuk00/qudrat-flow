from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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
        raise HTTPException(status_code=404, detail="index.html not found")
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("debug"):
            raise HTTPException(status_code=404)
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(frontend_dist / "index.html"))
else:
    print("WARNING: Frontend dist not found! API will work but UI won't.")

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
