import os, json, re, urllib.request, urllib.error
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

# ── Fallback formula ───────────────────────────────────────────────
CATEGORY_CONFIG = {
    "Tools":    {"base_rate_pct": 0.015, "deposit_pct": 0.30,
                 "seasonality": {1:1.0,2:1.0,3:1.1,4:1.1,5:1.2,6:1.2,
                                 7:1.1,8:1.1,9:1.0,10:1.0,11:1.0,12:0.9}},
    "Cleaning": {"base_rate_pct": 0.012, "deposit_pct": 0.25,
                 "seasonality": {1:1.2,2:1.1,3:1.3,4:1.1,5:1.0,6:1.0,
                                 7:0.9,8:0.9,9:1.0,10:1.0,11:1.0,12:1.2}},
    "Outdoor":  {"base_rate_pct": 0.018, "deposit_pct": 0.35,
                 "seasonality": {1:0.8,2:0.9,3:1.0,4:1.1,5:1.3,6:1.4,
                                 7:1.4,8:1.3,9:1.1,10:1.0,11:0.9,12:0.8}},
}
CONDITION_FACTORS = {"New": 1.0, "Good": 0.85, "Fair": 0.65, "Worn": 0.45}
MOCK_DEMAND       = {"Tools": 1.15, "Cleaning": 1.05, "Outdoor": 1.20}


def _formula_fallback(category: str, retail_value: float, condition: str) -> dict:
    cfg   = CATEGORY_CONFIG.get(category, CATEGORY_CONFIG["Tools"])
    month = datetime.now().month
    rate  = retail_value * cfg["base_rate_pct"]
    rate *= CONDITION_FACTORS.get(condition, 0.85)
    rate *= cfg["seasonality"][month]
    rate *= MOCK_DEMAND.get(category, 1.0)
    rate  = max(round(rate * 2) / 2, 2.0)
    dep   = max(round(retail_value * cfg["deposit_pct"] *
                      CONDITION_FACTORS.get(condition, 0.85)), 10)
    return {
        "daily_rate":           rate,
        "deposit":              dep,
        "monthly_earnings_est": round(rate * 3 * 2, 2),
        "seasonality_note":     "📊 Based on formula engine (Gemini unavailable)",
        "demand_note":          "✅ Moderate local demand",
        "confidence":           "Medium",
        "powered_by":           "formula",
        "reasoning":            "Gemini API unavailable — using rule-based formula as fallback."
    }


def _extract_text(response: dict) -> str:
    """Extract only the non-thought text parts from a Gemini response."""
    parts = (response.get("candidates", [{}])[0]
                     .get("content", {})
                     .get("parts", []))
    # Skip parts that are thinking (thought=True) — grab actual answer only
    texts = [p["text"] for p in parts
             if "text" in p and not p.get("thought", False)]
    return "\n".join(texts).strip()


def _call_gemini(item_name: str, category: str,
                 retail_value: float, condition: str) -> dict:
    month_name = datetime.now().strftime("%B")

    prompt = (
        f"You are a rental pricing expert for BorrowLoop, a peer-to-peer marketplace in Malaysia. "
        f"Item: {item_name or category + ' item'}, Category: {category}, "
        f"Retail value: RM {retail_value:.2f}, Condition: {condition}, Month: {month_name}. "
        f"Return ONLY a JSON object with these exact keys: "
        f"daily_rate (number, RM per day, 1-3% of retail rounded to 0.50), "
        f"deposit (integer RM, 25-40% of retail adjusted for condition), "
        f"monthly_earnings_est (number, daily_rate x 6), "
        f"seasonality_note (string with emoji), "
        f"demand_note (string with emoji), "
        f"confidence (High/Medium/Low), "
        f"reasoning (string, 2 sentences). "
        f"No markdown, no explanation, just the JSON."
    )

    url     = f"https://generativelanguage.googleapis.com/v1/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 2000,
            "responseMimeType": "application/json"
        }
    }).encode()

    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=20) as resp:
        raw_response = json.loads(resp.read())

    text = _extract_text(raw_response)

    # Strip markdown fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text.strip())

    data = json.loads(text)

    # Safe minimums
    data["daily_rate"]           = max(float(data["daily_rate"]), 2.0)
    data["deposit"]              = max(int(data["deposit"]), 10)
    data["monthly_earnings_est"] = float(data.get("monthly_earnings_est",
                                                   data["daily_rate"] * 6))
    data["powered_by"]           = f"gemini ({GEMINI_MODEL})"
    return data


def suggest_price(item_name: str, category: str,
                  retail_value: float, condition: str) -> dict:
    """Main entry — tries Gemini REST API, falls back to formula."""
    if GEMINI_API_KEY:
        try:
            return _call_gemini(item_name, category, retail_value, condition)
        except Exception as e:
            print(f"[pricing_engine] Gemini error: {e} — using formula fallback")
    return _formula_fallback(category, retail_value, condition)
