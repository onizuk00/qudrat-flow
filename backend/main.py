from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Optional
import os
import asyncio
from pathlib import Path

# Import from backend package
from backend.database import init_db, save_test, get_all_tests, get_test_by_id, save_session_results, get_test_history, get_mistakes_by_test, get_distinct_wrong_question_ids, get_questions_by_ids
from backend.scraper import extract_google_form_data

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

# ------------------- API Endpoints -------------------

@app.post("/api/scrape")
async def scrape_google_form(request: ScrapeRequest):
    try:
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

# ------------------- Debug endpoint to check frontend files -------------------

@app.get("/debug")
async def debug_info():
    current = Path(__file__).resolve().parent
    parent = current.parent
    frontend_dist = parent / "frontend" / "dist"
    
    info = {
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

# ------------------- Serve Frontend Static Files -------------------

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
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(frontend_dist / "index.html"))
else:
    print("WARNING: Frontend dist not found! API will work but UI won't.")

# ------------------- Keep-Alive (prevent Render from sleeping) -------------------

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
