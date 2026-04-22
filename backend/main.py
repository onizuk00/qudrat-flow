from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Optional
import os
import asyncio
from pathlib import Path
import sys

from backend.database import ...
from backend.scraper import ...كحزمة
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# --- الآن أصبحت الاستيرادات المطلقة تعمل بشكل صحيح ---
from backend.database import init_db, save_test, get_all_tests, get_test_by_id, save_session_results, get_test_history, get_mistakes_by_test, get_distinct_wrong_question_ids, get_questions_by_ids
from backend.scraper import extract_google_form_data
# -------------------------------------------------------

# تهيئة قاعدة البيانات
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

# ------------------- نماذج البيانات -------------------
class ScrapeRequest(BaseModel):
    url: str

class SubmitRequest(BaseModel):
    test_id: int
    time_spent_seconds: int
    time_limit_seconds: int
    answers: Dict[str, int]

# ------------------- API Endpoints -------------------
@app.post("/api/scrape")
async def scrape_google_form(request: ScrapeRequest):
    try:
        # الدالة أصبحت غير متزامنة، لذا نستخدم await
        form_data = await extract_google_form_data(request.url)
        test_id = save_test(
            title=form_data['title'],
            url=request.url,
            reading_passage=form_data.get('reading_passage', ''),
            questions_data=form_data['questions']
        )
        return {
            "test_id": test_id,
            "title": form_data['title'],
            "question_count": len(form_data['questions'])
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/tests")
async def get_tests():
    return get_all_tests()

@app.get("/api/tests/{test_id}")
async def get_test(test_id: int):
    test = get_test_by_id(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    return test

@app.post("/api/submit")
async def submit_test(request: SubmitRequest):
    try:
        result = save_session_results(
            test_id=request.test_id,
            time_spent_seconds=request.time_spent_seconds,
            answers=request.answers,
            time_limit_seconds=request.time_limit_seconds
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/history")
async def get_history():
    return get_test_history()

@app.get("/api/mistakes")
async def get_mistakes(test_id: Optional[int] = None):
    return get_mistakes_by_test(test_id)

@app.post("/api/retest/{test_id}")
async def retest_mistakes(test_id: int):
    wrong_question_ids = get_distinct_wrong_question_ids(test_id)
    if not wrong_question_ids:
        raise HTTPException(status_code=404, detail="No mistakes found")
    questions = get_questions_by_ids(wrong_question_ids)
    test = get_test_by_id(test_id)
    return {
        "id": test_id,
        "title": f"{test['title']} (Mistakes Only)",
        "reading_passage": test.get('reading_passage', ''),
        "questions": questions,
        "is_retest": True
    }

# ------------------- خدمة الملفات الثابتة (Frontend) -------------------
current_dir = Path(__file__).resolve().parent.parent
frontend_dist = current_dir / "frontend" / "dist"
if frontend_dist.exists() and frontend_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")
    @app.get("/")
    async def serve_root():
        return FileResponse(str(frontend_dist / "index.html"))
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(frontend_dist / "index.html"))

# ------------------- منع السكون (Keep-Alive) -------------------
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
