"""
PlugNTech Daily Tech Update Generator
Uses Google Gemini 2.5 (free tier, 2026)
"""

import os
import re
import json
import time
import urllib.request
from datetime import datetime, timezone, timedelta

# ── Config ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
HTML_FILE      = "tech-updates.html"
IST            = timezone(timedelta(hours=5, minutes=30))
TODAY          = datetime.now(IST)
DATE_STR       = TODAY.strftime("%-d %B %Y")
DAY_NAME       = TODAY.strftime("%A")

MODELS      = ["gemini-2.5-flash", "gemini-2.5-pro"]
MAX_RETRIES = 4
RETRY_WAIT  = 25


# ── Call Gemini API ───────────────────────────────────────────────────────────
def call_gemini(model: str, prompt: str) -> str:
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2048
        }
    }).encode()

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={GEMINI_API_KEY}"
    )

    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                resp = json.loads(r.read())

            candidates = resp.get("candidates", [])
            if not candidates:
                raise RuntimeError(f"No candidates: {json.dumps(resp)[:300]}")

            candidate  = candidates[0]
            finish     = candidate.get("finishReason", "")
            parts      = candidate.get("content", {}).get("parts", [])

            print(f"   Finish: {finish} | Parts: {len(parts)}")

            if finish == "MAX_TOKENS" and not parts:
                raise RuntimeError("MAX_TOKENS with empty parts — model overloaded")

            text = "".join(p.get("text", "") for p in parts).strip()
            if not text:
                raise RuntimeError(f"Empty text (finish={finish})")

            return text

        except urllib.error.HTTPError as e:
            body = e.read().decode()
            if e.code in (503, 429):
                print(f"   ⏳ Attempt {attempt}/{MAX_RETRIES} — HTTP {e.code}, waiting {RETRY_WAIT}s...")
                time.sleep(RETRY_WAIT)
                continue
            raise RuntimeError(f"HTTP {e.code}: {body[:300]}")

        except RuntimeError as e:
            if attempt < MAX_RETRIES:
                print(f"   ⏳ Attempt {attempt}/{MAX_RETRIES} — {e}, retrying in {RETRY_WAIT}s...")
                time.sleep(RETRY_WAIT)
                continue
            raise

    raise RuntimeError(f"{model} failed after {MAX_RETRIES} attempts")


# ── Generate the update ───────────────────────────────────────────────────────
def generate_update() -> str:
    is_weekend  = TODAY.weekday() >= 5
    update_type = "Weekend Tech Briefing" if is_weekend else "Daily Tech Update"

    # SHORT prompt — avoids MAX_TOKENS issue
    prompt = (
        f"Write a tech news HTML section for PlugNTech, an Indian tech blog. "
        f"Today: {DAY_NAME} {DATE_STR}. "
        f"Cover 6 real tech stories from today (India + global). "
        f"Output ONLY this HTML, no extra text:\n\n"
        f'<section class="update-entry">\n'
        f"  <h3>📅 {update_type} — {DATE_STR}</h3>\n"
        f"  <h4>[catchy subtitle]</h4>\n"
        f"  <p>[2 sentence intro]</p>\n"
        f"  <p><strong>📌 Today's Tech Highlights</strong></p>\n"
        f"  <p>\n"
        f"    1️⃣ [story 1]<br>\n"
        f"    2️⃣ [story 2]<br>\n"
        f"    3️⃣ [story 3]<br>\n"
        f"    4️⃣ [story 4]<br>\n"
        f"    5️⃣ [story 5]<br>\n"
        f"    6️⃣ [story 6]\n"
        f"  </p>\n"
        f"  <p><strong>🔥 PlugNTech Insight:</strong><br>[insight]</p>\n"
        f"  <p><em>Updated: {DATE_STR}</em></p>\n"
        f"</section>"
    )

    last_error = None
    for model in MODELS:
        try:
            print(f"⏳ Trying model: {model}")
            text = call_gemini(model, prompt)
            # Strip accidental markdown fences
            text = re.sub(r"^```html\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"^```\s*",     "", text)
            text = re.sub(r"```\s*$",     "", text).strip()
            if not text:
                raise RuntimeError("Empty after cleanup")
            print(f"✅ Success with {model} ({len(text)} chars)")
            return text
        except Exception as e:
            print(f"⚠️  {model} failed: {e}")
            last_error = str(e)

    raise RuntimeError(f"All models failed. Last error: {last_error}")


# ── Inject into HTML ──────────────────────────────────────────────────────────
def inject_into_html(new_section: str):
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    MARKER = "<!-- UPDATES_START -->"

    if MARKER in content:
        insert_pos = content.index(MARKER) + len(MARKER)
        updated = content[:insert_pos] + "\n\n" + new_section + "\n" + content[insert_pos:]
    else:
        match = re.search(r"</h1>", content) or re.search(r"<body[^>]*>", content)
        if match:
            insert_pos = match.end()
            updated = content[:insert_pos] + "\n\n" + new_section + "\n" + content[insert_pos:]
        else:
            raise ValueError("Cannot find injection point. Add <!-- UPDATES_START --> to tech-updates.html")

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(updated)

    print(f"✅ Injected into {HTML_FILE}")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"🚀 Generating PlugNTech update for {DATE_STR}...")
    new_section = generate_update()
    print(f"\n--- Preview ---\n{new_section[:600]}\n---\n")
    inject_into_html(new_section)
    print("🎉 Done!")
