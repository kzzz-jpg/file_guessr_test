"""
Indexer - Scan folders, parse files, extract keywords via LLM, and store in database.
"""
import os
import time
import asyncio
from typing import Callable, Optional

from file_parser import parse_file, get_file_category
from llm import extract_keywords, describe_image
from database import upsert_file, get_file_modified_time, add_watched_folder

# Skip files larger than 50MB
MAX_FILE_SIZE = 50 * 1024 * 1024

# Skip these directories
SKIP_DIRS = {
    "__pycache__", ".git", ".svn", "node_modules", ".venv", "venv",
    ".idea", ".vscode", ".vs", "dist", "build", ".next",
}

# Progress state (global for simplicity)
indexing_state = {
    "is_indexing": False,
    "folder": "",
    "total_files": 0,
    "processed_files": 0,
    "current_file": "",
    "errors": [],
    "start_time": 0,
}


def scan_folder(folder_path: str) -> list[str]:
    """Recursively scan a folder and return all file paths."""
    files = []
    for root, dirs, filenames in os.walk(folder_path):
        # Skip hidden/system directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]

        for filename in filenames:
            if filename.startswith("."):
                continue
            file_path = os.path.join(root, filename)
            try:
                size = os.path.getsize(file_path)
                if size > MAX_FILE_SIZE or size == 0:
                    continue
                files.append(file_path)
            except OSError:
                continue
    return files


async def index_file(file_path: str) -> bool:
    """
    Index a single file: parse -> LLM -> database.
    Returns True if successful, False otherwise.
    """
    try:
        file_name = os.path.basename(file_path)
        file_type = os.path.splitext(file_path)[1].lower()
        file_size = os.path.getsize(file_path)
        modified_time = os.path.getmtime(file_path)

        # Check if file needs re-indexing
        stored_mtime = get_file_modified_time(file_path)
        if stored_mtime is not None and abs(stored_mtime - modified_time) < 1:
            return True  # Already indexed and not modified

        category = get_file_category(file_path)

        if category == "image":
            # Use vision model directly
            result = await describe_image(file_path, file_name)
            raw_text = ""
        else:
            # Parse text content first
            text_content, parsed_category = parse_file(file_path)
            if text_content is None and parsed_category == "error":
                return False
            if text_content is None or not text_content.strip():
                # Empty file, store with minimal info
                upsert_file(
                    file_path=file_path,
                    file_name=file_name,
                    file_type=file_type,
                    file_size=file_size,
                    modified_time=modified_time,
                    summary=f"Empty or binary file: {file_name}",
                    keywords=file_name,
                    raw_text="",
                )
                return True

            raw_text = text_content
            result = await extract_keywords(text_content, file_name)

        # Store in database
        keywords_str = " ".join(result.get("keywords", []))
        upsert_file(
            file_path=file_path,
            file_name=file_name,
            file_type=file_type,
            file_size=file_size,
            modified_time=modified_time,
            summary=result.get("summary", ""),
            keywords=keywords_str,
            raw_text=raw_text if category != "image" else "",
        )
        return True

    except Exception as e:
        print(f"[Indexer] Error indexing {file_path}: {e}")
        return False


async def index_folder(folder_path: str):
    """
    Index all files in a folder. Updates global indexing_state for progress tracking.
    """
    global indexing_state

    if indexing_state["is_indexing"]:
        return

    indexing_state.update({
        "is_indexing": True,
        "folder": folder_path,
        "total_files": 0,
        "processed_files": 0,
        "current_file": "Scanning folder...",
        "errors": [],
        "start_time": time.time(),
    })

    try:
        # Scan for files
        files = scan_folder(folder_path)
        indexing_state["total_files"] = len(files)
        
        # Add to watched folders
        add_watched_folder(folder_path)
        
        # Start watching immediately if watcher is running
        try:
            from watcher import watcher
            watcher.add_watch(folder_path)
        except ImportError:
            pass

        # Index files one by one (local LLM = sequential is better)
        for i, file_path in enumerate(files):
            indexing_state["current_file"] = os.path.basename(file_path)
            indexing_state["processed_files"] = i

            success = await index_file(file_path)
            if not success:
                indexing_state["errors"].append(file_path)

        indexing_state["processed_files"] = len(files)
        indexing_state["current_file"] = "Done!"

    except Exception as e:
        indexing_state["errors"].append(f"Fatal error: {e}")
    finally:
        indexing_state["is_indexing"] = False


def get_index_status() -> dict:
    """Get current indexing status."""
    elapsed = 0
    if indexing_state["start_time"] > 0:
        if indexing_state["is_indexing"]:
            elapsed = time.time() - indexing_state["start_time"]
        else:
            elapsed = indexing_state.get("_end_time", time.time()) - indexing_state["start_time"]

    return {
        **indexing_state,
        "elapsed_seconds": round(elapsed, 1),
    }
