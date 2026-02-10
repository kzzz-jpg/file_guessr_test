"""
Database layer - SQLite FTS5 for full-text search.
"""
import sqlite3
import os
import time
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "file_guessr.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create tables and FTS5 virtual table."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT UNIQUE NOT NULL,
            file_name TEXT NOT NULL,
            file_type TEXT,
            file_size INTEGER,
            modified_time REAL,
            summary TEXT,
            keywords TEXT,
            raw_text TEXT,
            indexed_at REAL
        )
    """)

    # FTS5 virtual table for full-text search
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
            file_name,
            summary,
            keywords,
            raw_text,
            content='files',
            content_rowid='id'
        )
    """)

    # Triggers to keep FTS in sync with main table
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS files_ai AFTER INSERT ON files BEGIN
            INSERT INTO files_fts(rowid, file_name, summary, keywords, raw_text)
            VALUES (new.id, new.file_name, new.summary, new.keywords, new.raw_text);
        END
    """)

    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS files_ad AFTER DELETE ON files BEGIN
            INSERT INTO files_fts(files_fts, rowid, file_name, summary, keywords, raw_text)
            VALUES ('delete', old.id, old.file_name, old.summary, old.keywords, old.raw_text);
        END
    """)

    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS files_au AFTER UPDATE ON files BEGIN
            INSERT INTO files_fts(files_fts, rowid, file_name, summary, keywords, raw_text)
            VALUES ('delete', old.id, old.file_name, old.summary, old.keywords, old.raw_text);
            INSERT INTO files_fts(rowid, file_name, summary, keywords, raw_text)
            VALUES (new.id, new.file_name, new.summary, new.keywords, new.raw_text);
        END
    """)
    
    # Store monitored folders
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS watched_folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_path TEXT UNIQUE NOT NULL,
            added_at REAL
        )
    """)

    conn.commit()
    conn.close()


def upsert_file(file_path: str, file_name: str, file_type: str,
                file_size: int, modified_time: float,
                summary: str, keywords: str, raw_text: str):
    """Insert or update a file record."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO files (file_path, file_name, file_type, file_size, modified_time,
                           summary, keywords, raw_text, indexed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(file_path) DO UPDATE SET
            file_name=excluded.file_name,
            file_type=excluded.file_type,
            file_size=excluded.file_size,
            modified_time=excluded.modified_time,
            summary=excluded.summary,
            keywords=excluded.keywords,
            raw_text=excluded.raw_text,
            indexed_at=excluded.indexed_at
    """, (file_path, file_name, file_type, file_size, modified_time,
          summary, keywords, raw_text, time.time()))
    conn.commit()
    conn.close()


def search(query: str, limit: int = 20) -> list[dict]:
    """
    Search files using FTS5 with BM25 ranking.
    The query should be space-separated keywords.
    """
    conn = get_connection()

    # Build FTS5 query: each keyword combined with OR for broader results
    safe_query = _sanitize_query(query)
    terms = safe_query.split()
    if not terms:
        return []

    # Use OR to match any keyword, BM25 for ranking
    # Enclose in double quotes to handle terms with special chars safely
    fts_query = " OR ".join(f'"{t}"' for t in terms)

    try:
        rows = conn.execute("""
            SELECT f.id, f.file_path, f.file_name, f.file_type, f.file_size,
                   f.summary, f.keywords, f.modified_time,
                   rank AS relevance
            FROM files_fts
            JOIN files f ON f.id = files_fts.rowid
            WHERE files_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (fts_query, limit)).fetchall()
    except Exception:
        # Fallback: try each term individually
        rows = []
        for term in terms:
            try:
                partial = conn.execute("""
                    SELECT f.id, f.file_path, f.file_name, f.file_type, f.file_size,
                           f.summary, f.keywords, f.modified_time,
                           rank AS relevance
                    FROM files_fts
                    JOIN files f ON f.id = files_fts.rowid
                    WHERE files_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """, (f'"{term}"', limit)).fetchall()
                rows.extend(partial)
            except Exception:
                continue

    conn.close()

    # Deduplicate and convert to dicts
    seen = set()
    results = []
    for row in rows:
        if row["file_path"] not in seen:
            seen.add(row["file_path"])
            results.append(dict(row))
    return results[:limit]


def _sanitize_query(query: str) -> str:
    """Sanitize query for FTS5."""
    # Remove FTS5 operators that might cause syntax errors if misused
    # Allow OR, AND, NOT, but remove special chars like *, ^, :, etc.
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-")
    
    # Remove quotes first to simplify logic (we add them back in search)
    query = query.replace('"', '').replace("'", "")
    
    # Keep only safe chars
    safe = "".join(c if c in allowed else " " for c in query)
    return " ".join(safe.split())


def get_file_modified_time(file_path: str) -> Optional[float]:
    """Get the stored modified_time for a file, or None if not indexed."""
    conn = get_connection()
    row = conn.execute(
        "SELECT modified_time FROM files WHERE file_path = ?", (file_path,)
    ).fetchone()
    conn.close()
    return row["modified_time"] if row else None


def get_stats() -> dict:
    """Get indexing statistics."""
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) as c FROM files").fetchone()["c"]

    type_counts = conn.execute(
        "SELECT file_type, COUNT(*) as c FROM files GROUP BY file_type ORDER BY c DESC"
    ).fetchall()

    conn.close()
    return {
        "total_files": total,
        "by_type": {row["file_type"]: row["c"] for row in type_counts}
    }


def clear_db():
    """Clear all indexed data."""
    conn = get_connection()
    conn.execute("DELETE FROM files")
    conn.execute("DELETE FROM watched_folders")
    conn.execute("INSERT INTO files_fts(files_fts) VALUES('rebuild')")
    conn.commit()
    conn.close()


def add_watched_folder(folder_path: str):
    """Add a folder to watch list."""
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO watched_folders (folder_path, added_at) VALUES (?, ?)",
        (folder_path, time.time())
    )
    conn.commit()
    conn.close()


def get_watched_folders() -> list[str]:
    """Get all watched folders."""
    conn = get_connection()
    rows = conn.execute("SELECT folder_path FROM watched_folders").fetchall()
    conn.close()
    return [row["folder_path"] for row in rows]


def remove_file(file_path: str):
    """Remove a file from index."""
    conn = get_connection()
    conn.execute("DELETE FROM files WHERE file_path = ?", (file_path,))
    conn.commit()
    conn.close()
