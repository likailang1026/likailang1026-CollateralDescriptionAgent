# qwen_api.py — helper for ELTE vLLM endpoint (English‐only output)
"""Generate a Markdown collateral report in **English**.
Use for both first pass (captions + OCR) and second pass (with valuation context).
"""

from __future__ import annotations
import requests
import re

API_KEY  = "Bb7Ddtk7OyQCbW81is22"
BASE_URL = "http://mobydick.elte-dh.hu:24642/v1"
URL      = f"{BASE_URL}/completions"
MODEL_ID = "Qwen/Qwen3-32B-AWQ"      # adjust to the id listed by /v1/models if different

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type":  "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
}

SYSTEM_PROMPT = """You are a certified asset appraiser. Generate a structured asset description report in English with these exact sections:

### Identification & General Data
- Asset type, manufacturer, model
- Year of manufacture
- First registration date and country
- Engine/technical specifications
- Key measurements and parameters
- Documentation status

### Inspection Methods
- List methods used for assessment
- Tools and equipment used
- Documentation reviewed
- Data collection process

### Condition Assessment
- General condition evaluation
- Specific component assessments
- Any damage or wear noted
- Technical state description
- Maintenance history if available

### Valuation Principles
- Methodology used
- Market factors considered
- Value modifiers applied
- Special considerations

{EXTRA_SECTIONS}

### Documentation & Accessories
- Available documents
- Keys and accessories
- Supporting materials
- Additional notes

Use bullet points for clear organization. Keep descriptions factual and concise."""

CLEAN_SPACES = re.compile(r"[ \t]+")

def _norm(text: str) -> str:
    return CLEAN_SPACES.sub(" ", text.strip())

# ---------------------------------------------------------------------------

def generate_structured_description(caption: str,
                                    ocr_text: str,
                                    extra: str = "",
                                    *,
                                    temperature: float = 0.3,
                                    max_tokens: int = 1024) -> str | None:
    """Return English markdown report text; None on failure."""

    prompt_parts = [SYSTEM_PROMPT,
                    "\n\n### IMAGE CAPTIONS\n", _norm(caption),
                    "\n\n### OCR TEXT (cleaned)\n", _norm(ocr_text)]
    if extra:
        prompt_parts.extend(["\n\n### EXTRA CONTEXT\n", _norm(extra)])

    payload = {
        "model": MODEL_ID,
        "prompt": "".join(prompt_parts),
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    try:
        r = requests.post(URL, headers=HEADERS, json=payload, timeout=90)
        r.raise_for_status()
        return r.json().get("choices", [{}])[0].get("text")
    except Exception as exc:
        print("Qwen API error:", exc)
        return None

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test = generate_structured_description("BMW X5 photo", "VIN 123456", extra="- **Estimated average price:** 14 600 000 HUF")
    print(test or "[No response]")
