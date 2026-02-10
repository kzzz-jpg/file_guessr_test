# File Guessr 📂🔍

A local file search tool powered by **Ollama (Gemma 3 4B)** and **SQLite FTS5**.
Search your files using natural language descriptions like "red sports car" or "budget report from last week".

![Screenshot](screenshot.png)

## Features

- 🧠 **Local AI Power**: Uses `gemma3:4b` to understand text and images privacy-first.
- 🔍 **Natural Language Search**: No need for exact filenames. Describe what you're looking for.
- 🖼️ **Image Understanding**: Automatically generates descriptions for images to make them searchable.
- ⚡ **Instant Search**: Powered by SQLite FTS5 for sub-millisecond search results.
- 📂 **Dynamic Monitoring**: Automatically indexes new or modified files in watched folders.
- 🚀 **One-Click Deploy**: Includes `run.bat` for easy setup on Windows.

## Requirements

- **Windows 10/11**
- **Python 3.10+**
- **Ollama** (Running locally with `gemma3:4b` model)
  - Install from [ollama.com](https://ollama.com/)
  - Run `ollama pull gemma3:4b`

## Quick Start (Windows)

1. Clone or download this repository.
2. Double-click **`run.bat`**.
   - It will set up the Python environment, install dependencies, pull the model, and launch the app.
3. Open browser at `http://127.0.0.1:8000`.

## Manual Installation

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Pull required model
ollama pull gemma3:4b

# 4. Run the server
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

## Usage

1. Go to **Settings** (Top right gear icon).
2. Enter a folder path to index (e.g., `D:\Photos`).
3. Click **Start Indexing**.
4. Once indexed, type your query in the search bar!

## Architecture

- **Backend**: FastAPI
- **Database**: SQLite + FTS5
- **LLM**: Ollama API
- **Frontend**: Vanilla JS + CSS (Glassmorphism UI)

## License

MIT
