"""
File parser - Extract text content from various file types.
"""
import os
import chardet
from typing import Optional

# Max characters to extract from a file
MAX_TEXT_LENGTH = 4000

# File extensions by category
TEXT_EXTENSIONS = {
    ".txt", ".md", ".csv", ".json", ".xml", ".log", ".ini", ".yaml", ".yml",
    ".toml", ".cfg", ".conf", ".env", ".gitignore", ".dockerfile",
    ".rst", ".tex", ".bib",
}

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".htm", ".css", ".scss",
    ".java", ".c", ".cpp", ".h", ".hpp", ".cs", ".go", ".rs", ".rb",
    ".php", ".swift", ".kt", ".scala", ".lua", ".r", ".m", ".sql",
    ".sh", ".bat", ".ps1", ".makefile", ".cmake",
    ".vue", ".svelte", ".astro",
}

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif", ".ico",
}

DOCUMENT_EXTENSIONS = {
    ".pdf", ".docx", ".xlsx", ".pptx",
}


def get_file_category(file_path: str) -> str:
    """Determine the file category based on extension."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in TEXT_EXTENSIONS:
        return "text"
    if ext in CODE_EXTENSIONS:
        return "code"
    if ext in DOCUMENT_EXTENSIONS:
        return "document"
    return "unknown"


def parse_file(file_path: str) -> tuple[Optional[str], str]:
    """
    Parse a file and return (text_content, category).
    For images, text_content is None (handled by vision model).
    """
    category = get_file_category(file_path)

    if category == "image":
        return None, "image"

    try:
        if category in ("text", "code"):
            return _read_text_file(file_path), category
        elif category == "document":
            return _parse_document(file_path), category
        else:
            # Unknown: try to read as text
            return _read_text_file(file_path), "text"
    except Exception as e:
        print(f"[Parser] Failed to parse {file_path}: {e}")
        return None, "error"


def _read_text_file(file_path: str) -> Optional[str]:
    """Read a text file with encoding detection."""
    try:
        with open(file_path, "rb") as f:
            raw = f.read(100000)  # Read up to 100KB for detection

        if not raw:
            return None

        detected = chardet.detect(raw)
        encoding = detected.get("encoding", "utf-8") or "utf-8"

        try:
            text = raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            text = raw.decode("utf-8", errors="replace")

        return text[:MAX_TEXT_LENGTH] if text.strip() else None
    except Exception:
        return None


def _parse_document(file_path: str) -> Optional[str]:
    """Parse document files (PDF, DOCX, XLSX, PPTX)."""
    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext == ".pdf":
            return _parse_pdf(file_path)
        elif ext == ".docx":
            return _parse_docx(file_path)
        elif ext == ".xlsx":
            return _parse_xlsx(file_path)
        elif ext == ".pptx":
            return _parse_pptx(file_path)
    except Exception as e:
        print(f"[Parser] Error parsing document {file_path}: {e}")
    return None


def _parse_pdf(file_path: str) -> Optional[str]:
    """Extract text from PDF using pypdf."""
    import pypdf

    text_parts = []
    try:
        reader = pypdf.PdfReader(file_path)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
    except Exception as e:
        print(f"[Parser] PDF error: {e}")
        return None

    text = "\n".join(text_parts)
    return text[:MAX_TEXT_LENGTH] if text.strip() else None


def _parse_docx(file_path: str) -> Optional[str]:
    """Extract text from DOCX."""
    from docx import Document

    doc = Document(file_path)
    text_parts = [para.text for para in doc.paragraphs if para.text.strip()]
    text = "\n".join(text_parts)
    return text[:MAX_TEXT_LENGTH] if text.strip() else None


def _parse_xlsx(file_path: str) -> Optional[str]:
    """Extract text from XLSX."""
    from openpyxl import load_workbook

    wb = load_workbook(file_path, read_only=True, data_only=True)
    text_parts = []
    for sheet in wb.sheetnames:
        ws = wb[sheet]
        text_parts.append(f"[Sheet: {sheet}]")
        for row in ws.iter_rows(values_only=True):
            values = [str(cell) for cell in row if cell is not None]
            if values:
                text_parts.append(" | ".join(values))
    wb.close()

    text = "\n".join(text_parts)
    return text[:MAX_TEXT_LENGTH] if text.strip() else None


def _parse_pptx(file_path: str) -> Optional[str]:
    """Extract text from PPTX."""
    from pptx import Presentation

    prs = Presentation(file_path)
    text_parts = []
    for slide_num, slide in enumerate(prs.slides, 1):
        text_parts.append(f"[Slide {slide_num}]")
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    if para.text.strip():
                        text_parts.append(para.text)

    text = "\n".join(text_parts)
    return text[:MAX_TEXT_LENGTH] if text.strip() else None
