"""
File Guessr - Natural Language File Search Tool
FastAPI application with Web UI.
"""
import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, BackgroundTasks, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

import database
from indexer import index_folder, get_index_status
from searcher import search_files
from llm import check_ollama_status

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database on startup
    database.init_db()
    
    # Start file watcher
    from watcher import watcher
    watcher.start()
    
    yield
    
    # Stop watcher
    watcher.stop()


app = FastAPI(title="File Guessr", lifespan=lifespan)

# Serve static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ──── Pages ────

@app.get("/")
async def serve_frontend():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


# ──── API Endpoints ────

@app.post("/api/index")
async def start_indexing(body: dict, background_tasks: BackgroundTasks):
    """Start indexing a folder."""
    folder_path = body.get("folder_path", "").strip()

    if not folder_path:
        return JSONResponse({"error": "folder_path is required"}, status_code=400)

    if not os.path.isdir(folder_path):
        return JSONResponse({"error": f"Folder not found: {folder_path}"}, status_code=400)

    status = get_index_status()
    if status["is_indexing"]:
        return JSONResponse({"error": "Indexing is already in progress"}, status_code=409)

    # Run indexing in background
    background_tasks.add_task(index_folder, folder_path)

    return {"message": "Indexing started", "folder": folder_path}


@app.get("/api/index/status")
async def indexing_status():
    """Get current indexing progress."""
    return get_index_status()


@app.get("/api/search")
async def search(q: str = Query(..., min_length=1)):
    """Search files with natural language query."""
    result = await search_files(q)
    return result


@app.get("/api/stats")
async def stats():
    """Get index statistics."""
    return database.get_stats()


@app.get("/api/health")
async def health():
    """Check Ollama and model status."""
    return await check_ollama_status()


@app.post("/api/clear")
async def clear_index():
    """Clear all indexed data."""
    status = get_index_status()
    if status["is_indexing"]:
        return JSONResponse({"error": "Cannot clear while indexing"}, status_code=409)
    database.clear_db()
    return {"message": "Index cleared"}


@app.get("/api/file/preview")
async def file_preview(path: str = Query(...)):
    """Serve a file for preview (mainly for images)."""
    if not os.path.isfile(path):
        return JSONResponse({"error": "File not found"}, status_code=404)

    return FileResponse(path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
