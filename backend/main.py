from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, List, Optional
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

from backend.database import init_db, save_test, get_all_tests, get_test_by_id, save_session_results, get_test_history, get_mistakes_by_test, get_distinct_wrong_question_ids, get_questions_by_ids
from backend.scraper import extract_google_form_data

# Initialize database
init_db()

app = FastAPI(title="Qudrat-Flow API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thread pool for blocking operations
executor = ThreadPoolExecutor(max_workers=4)

# Request/Response Models
class ScrapeRequest(BaseModel):
    url: str

class SubmitRequest(BaseModel):
    test_id: int
    time_spent_seconds: int
    time_limit_seconds: int
    answers: Dict[str, int]  # question_id -> selected_index

class ScrapeResponse(BaseModel):
    test_id: int
    title: str
    question_count: int

class TestResponse(BaseModel):
    id: int
    title: str
    reading_passage: Optional[str]
    questions: List[dict]

# API Endpoints
@app.post("/api/scrape")
async def scrape_google_form(request: ScrapeRequest):
    """Scrape a Google Form and save to database"""
    try:
        # Run scraper in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        form_data = await loop.run_in_executor(
            executor, 
            extract_google_form_data, 
            request.url
        )
        
        # Save to database
        test_id = save_test(
            title=form_data['title'],
            url=request.url,
            reading_passage=form_data.get('reading_passage', ''),
            questions_data=form_data['questions']
        )
        
        return ScrapeResponse(
            test_id=test_id,
            title=form_data['title'],
            question_count=len(form_data['questions'])
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/tests")
async def get_tests():
    """Get all tests with session history"""
    return get_all_tests()

@app.get("/api/tests/{test_id}")
async def get_test(test_id: int):
    """Get a specific test with all questions"""
    test = get_test_by_id(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    return test

@app.post("/api/submit")
async def submit_test(request: SubmitRequest):
    """Submit test answers and get results"""
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
    """Get all test session history"""
    return get_test_history()

@app.get("/api/mistakes")
async def get_mistakes(test_id: Optional[int] = None):
    """Get mistakes, optionally filtered by test"""
    return get_mistakes_by_test(test_id)

@app.post("/api/retest/{test_id}")
async def retest_mistakes(test_id: int):
    """Get only questions that were previously answered incorrectly"""
    wrong_question_ids = get_distinct_wrong_question_ids(test_id)
    
    if not wrong_question_ids:
        raise HTTPException(status_code=404, detail="No mistakes found for this test")
    
    questions = get_questions_by_ids(wrong_question_ids)
    
    # Get original test info
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

# Serve React Frontend (after build)
# Check if static files exist, otherwise serve API only
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
        return FileResponse(f"{static_dir}/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
