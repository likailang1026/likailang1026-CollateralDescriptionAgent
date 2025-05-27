# valuation_agent.py – EU Market Scraper + Field Extractor
# -----------------------------------------------------------------------------
# Exports  ▸  estimate_value · extract_fields · format_sample_block
# -----------------------------------------------------------------------------
# 1) Build keyword list per asset‑type (vehicle / truck / machine / train…)
# 2) Google search restricted to EU marketplaces (mobile.de, autoscout24.com, hasznaltauto.hu …)
# 3) Parse HTML → pull numeric prices + currency context
# 4) Return summary dict in EUR and HUF
# -----------------------------------------------------------------------------

import re, json, random, time, html
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0 Safari/537.36"
    )
}
EUR_TO_HUF = 390  # quick mid‑rate; adjust if required

# -----------------------------------------------------------------------------
# 1) Keyword generation
# -----------------------------------------------------------------------------

def generate_keywords(item_type: str, make: str, model: str, year: str = "", mileage: str = ""):
    base = f"{make} {model} {year}".strip()
    kw = []
    if item_type == "car":
        kw = [
            f"{base} site:mobile.de",
            f"{base} site:autoscout24.com",
            f"{base} site:hasznaltauto.hu",
        ]
    elif item_type == "truck":
        kw = [
            f"{base} site:trucks.autoscout24.com",
            f"{base} site:kleyntrucks.com",
        ]
    elif item_type == "train":
        kw = [f"{base} locomotive for sale"]
    else:  # machine / other
        kw = [f"{base} used for sale Europe"]
    return kw

# -----------------------------------------------------------------------------
# 2) Google fetch + simple price extraction
# -----------------------------------------------------------------------------

def fetch_html(q: str) -> str:
    url = "https://www.google.com/search?q=" + requests.utils.quote(q)
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.text

# 修改价格提取正则表达式,使其更精确
PRICE_RE = re.compile(r"(?:EUR|€|HUF|Ft)\s*([\d.,]+)|(\d[\d\s.,]*)\s*(?:EUR|€|HUF|Ft)")

def extract_prices(html_text: str):
    soup = BeautifulSoup(html_text, "html.parser")
    texts = [html.unescape(t.strip()) for t in soup.stripped_strings]
    prices, samples = [], []
    
    for idx, txt in enumerate(texts):
        matches = PRICE_RE.finditer(txt)
        for m in matches:
            try:
                # 提取价格数字
                price_str = m.group(1) or m.group(2)
                price_str = price_str.replace(" ", "").replace(".", "").replace(",", "")
                num = int(price_str)
                
                # 过滤异常值
                if num < 1000:  # 过滤掉太小的值
                    continue
                    
                cur = "EUR" if any(c in txt for c in ("EUR", "€")) else "HUF"
                if cur == "HUF":
                    num_eur = round(num / EUR_TO_HUF)
                else:
                    num_eur = num
                    
                # 过滤不合理的欧元价格    
                if num_eur < 5000 or num_eur > 200000:
                    continue
                    
                prices.append(num_eur)
                
                # 获取价格上下文
                start_idx = max(0, idx-2)
                end_idx = min(len(texts), idx+3)
                context = " ".join(texts[start_idx:end_idx])
                context = context[:200] # 限制长度
                
                samples.append({
                    "price_eur": num_eur,
                    "currency": cur,
                    "context": context
                })
                
            except (ValueError, AttributeError):
                continue
                
    return prices, samples

# -----------------------------------------------------------------------------
# 3) Public API
# -----------------------------------------------------------------------------

def estimate_value(item_type: str, make: str, model: str, year: str = "", mileage: str = ""):
    all_prices = []
    all_samples = []
    
    for kw in generate_keywords(item_type, make, model, year, mileage):
        try:
            html_text = fetch_html(kw)
            prices, samples = extract_prices(html_text)
            all_prices.extend(prices)
            all_samples.extend(samples)
            time.sleep(random.uniform(1, 2))
        except Exception as exc:
            print(f"Search failed for {kw}: {exc}")
            continue
            
    if not all_prices:
        return {"result": None, "samples": []}
        
    # 对价格进行统计
    all_prices.sort()
    avg_price = sum(all_prices) // len(all_prices)
    
    result = {
        "estimated_average": avg_price,
        "price_range_eur": [all_prices[0], all_prices[-1]],
        "approx_huf": int(avg_price * EUR_TO_HUF),
        "listings": len(all_prices)
    }
    
    return {
        "result": result,
        "samples": sorted(all_samples, key=lambda x: x["price_eur"])[:5]
    }

# -----------------------------------------------------------------------------
# 4) Field‑extraction helpers  (regex‑based, crude but effective)
# -----------------------------------------------------------------------------

FIELD_PATTERNS = {
    "make": r"Make\s*[:\-]\s*([A-Z][A-Za-z0-9\- ]{2,})",
    "model": r"Model\s*[:\-]\s*([A-Za-z0-9\- ]{2,})",
    "year": r"Year of Manufacture\s*[:\-]\s*(\d{4})",
    "mileage": r"Mileage\s*[:\-]\s*([\d,.]+)\s*km",
    "vin": r"VIN\s*[:\-]\s*([A-Z0-9]{5,})",
}


def _grab(pattern: str, text: str):
    m = re.search(pattern, text, re.I)
    return m.group(1).strip() if m else ""


def extract_fields(structured_md: str):
    return {k: _grab(p, structured_md) for k, p in FIELD_PATTERNS.items()}

# -----------------------------------------------------------------------------
# 5) Sample block formatter → markdown list
# -----------------------------------------------------------------------------

def format_sample_block(samples):
    if not samples:
        return ""
    
    lines = []
    for s in samples:
        # 清理和格式化上下文
        context = re.sub(r'[^\w\s,.-]', '', s["context"])
        context = re.sub(r'\s+', ' ', context).strip()
        
        lines.append(
            f"- {context[:100]}... ; "
            f"**{s['price_eur']:,} EUR** "
            f"(~{int(s['price_eur'] * EUR_TO_HUF):,} HUF)"
        )
    
    return "\n".join(lines)

# -----------------------------------------------------------------------------
# Stand‑alone quick test
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    md = """### Identification & General Data\n- Make: BMW\n- Model: X5 xDrive30d\n- Year of Manufacture: 2021\n- Mileage: 63,833 km"""
    fields = extract_fields(md)
    print(fields)
    est = estimate_value("car", fields['make'], fields['model'], fields['year'], fields['mileage'])
    print(json.dumps(est, indent=2))
