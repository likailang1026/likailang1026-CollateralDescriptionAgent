# app.py — Collateral Description & Valuation Pipeline (EUR / HUF)
# ---------------------------------------------------------------------------
# 1. Load images from ./images
# 2. BLIP‑2 caption + cleaned OCR extraction (regex filter)
# 3. Qwen pass‑1  → structured markdown in English
# 4. Google scraping (EU marketplaces) → price in EUR; convert to HUF
# 5. Qwen pass‑2  → inject valuation into Determined Values & Market Comparison Samples
# 6. Save outputs/summaries.json and outputs/annotations.md
# ---------------------------------------------------------------------------

import os
import json
import re
import sys
import logging
from utils.image_loader import load_images_from_folder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from ocr_full import extract_ocr_text
except ImportError as e:
    logger.error(f"Failed to import OCR module: {e}")
    logger.info("Please make sure all dependencies are installed correctly")
    sys.exit(1)

from qwen_api import generate_structured_description
from valuation_agent import estimate_value, extract_fields, format_sample_block

IMAGE_DIR = "images"
OUT_DIR   = "outputs"
OUT_JSON  = os.path.join(OUT_DIR, "summaries.json")
OUT_MD    = os.path.join(OUT_DIR, "annotations.md")
EUR_TO_HUF = 390  # same as valuation_agent

os.makedirs(OUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# OCR cleaning helpers
# ---------------------------------------------------------------------------

KEEP_PATTERNS = [
    r"\bBMW\b", r"\bMercedes\b", r"\bDAF\b", r"\bVIN\b|[A-Z0-9]{6,}",
    r"\b\d{4}[./]\d{2}[./]\d{2}\b",     # dates
    r"\b\d{1,3}[.,]?\d{0,3}\s?km\b",     # mileage
    r"\b\d{3,5}\s?kg\b",                  # weight
    r"\bl/100km\b", r"\bService\b|\bSzerviz",
    r"\bNV\d{5}\b"
]
compiled_keep = [re.compile(p, re.I) for p in KEEP_PATTERNS]
DROP_PATTERNS = [re.compile(r"^[A-Z]\.\d{1,3}:") , re.compile(r"^[A-Z0-9]{1,3}=\S+$")]

def _keep(line: str) -> bool:
    return any(p.search(line) for p in compiled_keep)

def clean_ocr(raw: str) -> str:
    lines = []
    for ln in raw.splitlines():
        ln = ln.strip()
        if len(ln) < 4 or ln.lower().startswith("no text"):
            continue
        if any(p.match(ln) for p in DROP_PATTERNS):
            continue
        if _keep(ln):
            lines.append(ln)
    return "\n".join(lines)

def main():
    try:
        # ---------------------------------------------------------------------------
        # 1) Collect OCR text
        # ---------------------------------------------------------------------------
        ocr_text = ""
        for img_path in load_images_from_folder(IMAGE_DIR):
            text = extract_ocr_text(img_path)  # 使用OCR提取文本
            if text and not text.isspace():
                ocr_text += text + "\n\n"

        # ---------------------------------------------------------------------------
        # 2) First Qwen pass - generate initial description
        # ---------------------------------------------------------------------------
        initial_md = generate_structured_description(ocr_text) or ""
        fields = extract_fields(initial_md)

        # ---------------------------------------------------------------------------
        # 3) Price estimation (EUR + HUF)
        # ---------------------------------------------------------------------------
        asset_type = "machine" if "machine" in ocr_text.lower() else "car"
        valuation = estimate_value(asset_type,
                                 fields["make"], fields["model"],
                                 fields["year"], fields["mileage"])

        val_text = sample_block = ""
        if valuation.get("result"):
            res = valuation["result"]
            if res["listings"] > 0:
                val_text = (
                    f"- **Market Value:** {res['estimated_average']:,} EUR "
                    f"(~{res['approx_huf']:,} HUF)\n"
                    f"- **Price Range:** {res['price_range_eur'][0]:,} – {res['price_range_eur'][1]:,} EUR\n"
                    f"- **Analyzed Listings:** {res['listings']}\n"
                )
                sample_block = format_sample_block(valuation.get("samples", []))

        # ---------------------------------------------------------------------------
        # 4) Second Qwen pass - final structured output
        # ---------------------------------------------------------------------------
        extra = ""
        if val_text:
            extra = (
                "### Determined Values\n" + val_text +
                "\n### Market Comparison Samples\n" + sample_block
            )

        final_md = generate_structured_description(ocr_text, extra=extra)
        if not final_md:
            final_md = "[Error: Qwen API call failed]"

        # ---------------------------------------------------------------------------
        # 6) Save outputs
        # ---------------------------------------------------------------------------

        summary = {
            "ocr_text": ocr_text,
            "initial_qwen": initial_md,
            "valuation_text": val_text,
            "sample_block": sample_block,
            "structured_description": final_md
        }

        with open(OUT_JSON, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        with open(OUT_MD, "w", encoding="utf-8") as f:
            f.write("## Collateral_Object_001\n\n")
            f.write(final_md)
            f.write("\n")

        print("✅ Pipeline completed — outputs saved to 'outputs/' directory.")
    except Exception as e:
        logger.error(f"Error during execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
