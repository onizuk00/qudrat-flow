from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Optional, List
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from datetime import datetime, timedelta
import time

from backend.database import init_db, save_test, get_all_tests, get_test_by_id, save_session_results, get_test_history, get_mistakes_by_test, get_distinct_wrong_question_ids, get_questions_by_ids
from backend.scraper import extract_google_form_data

# --- Initialize DB ---
init_db()

app = FastAPI(title="Qudrat-Flow API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Simple Cache for scraped URLs (TTL 1 hour) ---
scrape_cache = {}
CACHE_TTL_SECONDS = 3600

def get_cached_scrape(url: str):
    if url in scrape_cache:
        entry = scrape_cache[url]
        if datetime.now() - entry['timestamp'] < timedelta(seconds=CACHE_TTL_SECONDS):
            return entry['data']
        else:
            del scrape_cache[url]
    return None

def set_cached_scrape(url: str, data):
    scrape_cache[url] = {'data': data, 'timestamp': datetime.now()}

# --- Background task for scraping ---
executor = ThreadPoolExecutor(max_workers=2)

async def run_scrape(url: str):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, extract_google_form_data, url)

# --- Models ---
class ScrapeRequest(BaseModel):
    url: str

class SubmitRequest(BaseModel):
    test_id: int
    time_spent_seconds: int
    time_limit_seconds: int
    answers: Dict[str, int]

# --- API Endpoints ---
@app.get("/api/ping")
async def ping():
    """Endpoint to keep the service alive."""
    return {"status": "alive", "timestamp": time.time()}

@app.post("/api/scrape")
async def scrape_google_form(request: ScrapeRequest, background_tasks: BackgroundTasks):
    # Check cache first
    cached = get_cached_scrape(request.url)
    if cached:
        # save to DB and return
        test_id = save_test(
            title=cached['title'],
            url=request.url,
            reading_passage=cached.get('reading_passage', ''),
            questions_data=cached['questions']
        )
        return {"test_id": test_id, "title": cached['title'], "question_count": len(cached['questions']), "cached": True}
    
    # Otherwise scrape in background (but we need to wait for result? Better to scrape async with timeout)
    # For simplicity, we'll scrape directly but with timeout and speed optimizations.
    # To avoid long wait, we can use a task and return a job ID, but for MVP let's keep direct with increased timeout.
    try:
        form_data = await asyncio.wait_for(run_scrape(request.url), timeout=45.0)
        # Cache it
        set_cached_scrape(request.url, form_data)
        test_id = save_test(
            title=form_data['title'],
            url=request.url,
            reading_passage=form_data.get('reading_passage', ''),
            questions_data=form_data['questions']
        )
        return {"test_id": test_id, "title": form_data['title'], "question_count": len(form_data['questions']), "cached": False}
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="استغرقت عملية الاستخراج أكثر من 45 ثانية. الرابط قد يكون معقداً أو بطيئاً.")
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
    wrong_ids = get_distinct_wrong_question_ids(test_id)
    if not wrong_ids:
        raise HTTPException(status_code=404, detail="No mistakes found")
    questions = get_questions_by_ids(wrong_ids)
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

# Serve frontend static files
static_dir = "../frontend/dist"
if os.path.exists(static_dir):
    app.mount("/assets", StaticFiles(directory=f"{static_dir}/assets"), name="assets")
    @app.get("/")
    async def serve_root():
        return FileResponse(f"{static_dir}/index.html")
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        file_path = f"{static_dir}/{full_path}"
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(f"{static_dir}/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=2)
