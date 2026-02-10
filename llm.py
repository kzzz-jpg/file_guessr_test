"""
LLM integration - Ollama API calls for keyword extraction, image description, and query expansion.
All outputs are in English for consistent indexing.
"""
import httpx
import base64
import json
import re
from typing import Optional

OLLAMA_BASE_URL = "http://localhost:11434"
MODEL_NAME = "gemma3:4b"
TIMEOUT = 120.0  # seconds - local model can be slow


async def _chat(prompt: str, image_path: Optional[str] = None) -> str:
    """Send a chat request to Ollama."""
    messages = [{"role": "user", "content": prompt}]

    # If image, encode as base64 and attach
    if image_path:
        with open(image_path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode("utf-8")
        messages[0]["images"] = [img_data]

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.3,  # Low temperature for consistent outputs
            "num_predict": 1024,
        }
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]


def _parse_json_response(text: str) -> dict:
    """Try to extract JSON from LLM response."""
    # Try to find JSON block in markdown code fence
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if json_match:
        text = json_match.group(1)

    # Try to find JSON object directly
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    # Fallback: return the whole text as summary
    return {"summary": text.strip(), "keywords": []}


async def extract_keywords(text: str, file_name: str) -> dict:
    """
    Extract keywords and summary from text content.
    Returns: {"summary": str, "keywords": [str]}
    """
    prompt = f"""Analyze this file and extract information for search indexing.
File name: {file_name}

CONTENT:
{text[:3000]}

INSTRUCTIONS:
- Respond ONLY with a JSON object, no other text
- All content must be in English
- If the original content is not in English, translate the key concepts
- Summary should be 1-3 sentences describing what this file is about
- Keywords should be comprehensive: include topics, names, places, technical terms, actions, and concepts
- Include 15-30 keywords

FORMAT:
{{"summary": "Brief description of the file content", "keywords": ["keyword1", "keyword2", "keyword3"]}}"""

    try:
        response = await _chat(prompt)
        result = _parse_json_response(response)
        # Ensure required fields
        if "summary" not in result:
            result["summary"] = ""
        if "keywords" not in result:
            result["keywords"] = []
        return result
    except Exception as e:
        print(f"[LLM] Error extracting keywords for {file_name}: {e}")
        return {"summary": f"Error processing file: {file_name}", "keywords": []}


async def describe_image(image_path: str, file_name: str) -> dict:
    """
    Describe an image in extreme detail using vision model.
    Returns: {"summary": str, "keywords": [str]}
    """
    prompt = f"""Describe this image in EXTREME DETAIL for search indexing purposes.
File name: {file_name}

You must describe EVERYTHING you can see:
- Objects and items (what they are, their colors, materials, sizes)
- People (appearance, actions, emotions, clothing, number of people)
- Scene and setting (indoor/outdoor, location type, time of day, weather)
- Text visible in the image (signs, labels, watermarks)
- Colors, lighting, and visual style
- Background elements
- Any symbols, logos, or icons
- The overall mood and atmosphere
- Type of image (photo, screenshot, diagram, chart, illustration, meme, etc.)

Be as detailed and descriptive as possible. Every detail matters for searchability.
Include related concepts and synonyms. For example, if there is a beach, also mention: ocean, sea, coast, shore, sand, waves, tropical.

IMPORTANT: Respond ONLY with a JSON object. All content must be in English.

FORMAT:
{{"summary": "Detailed 2-4 sentence description of the image", "keywords": ["keyword1", "keyword2", ...]}}

Include 20-40 keywords covering all aspects of the image."""

    try:
        response = await _chat(prompt, image_path=image_path)
        result = _parse_json_response(response)
        if "summary" not in result:
            result["summary"] = ""
        if "keywords" not in result:
            result["keywords"] = []
        return result
    except Exception as e:
        print(f"[LLM] Error describing image {file_name}: {e}")
        return {"summary": f"Image file: {file_name}", "keywords": []}


async def expand_query(user_query: str) -> str:
    """
    Expand a natural language query into comprehensive English search keywords.
    Returns a space-separated string of keywords for FTS5 search.
    """
    prompt = f"""You are a search query expansion assistant. The user wants to find files on their computer.

USER QUERY: {user_query}

INSTRUCTIONS:
- Convert the query into English search keywords
- Add synonyms, related concepts, and associated terms
- Include translations if the query is in another language
- Think about what words might appear in relevant files
- For visual concepts, include words that would describe such images
- Example: "沙灘照片" → beach sand ocean sea coast shore waves tropical photo sunny water palm summer vacation seaside

Respond with ONLY a single line of space-separated English keywords (15-25 keywords).
Do NOT include any explanation, just the keywords."""

    try:
        response = await _chat(prompt)
        # Clean up the response
        if not response:
            return user_query
            
        # Remove quotes if present
        keywords = response.strip().strip('"').strip("'")
        
        # Remove any lines that look like explanations ("Here are the keywords: ...")
        lines = keywords.split("\n")
        # Take the last line that looks like keywords (often LLMs put explanation first)
        for line in reversed(lines):
            line = line.strip()
            if line and len(line.split()) > 1:
                keywords = line
                # Stop if we found a good candidate (not empty, more than 1 word)
                break
        
        # Remove common prefixes LLMs might add
        keywords = re.sub(r'^(keywords:|answer:|result:)\s*', '', keywords, flags=re.IGNORECASE)
                
        return keywords
    except Exception as e:
        print(f"[LLM] Error expanding query: {e}")
        return user_query


async def check_ollama_status() -> dict:
    """Check if Ollama is running and model is available."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Check if Ollama is running
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
            models = resp.json().get("models", [])
            model_names = [m["name"] for m in models]

            has_model = any(MODEL_NAME.split(":")[0] in name for name in model_names)

            return {
                "ollama_running": True,
                "model_available": has_model,
                "available_models": model_names,
                "required_model": MODEL_NAME,
            }
    except Exception as e:
        return {
            "ollama_running": False,
            "model_available": False,
            "error": str(e),
            "required_model": MODEL_NAME,
        }
