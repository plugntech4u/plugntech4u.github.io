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
MAX_RETRIES = 5
RETRY_WAIT  = 20


# ── Call Gemini API ───────────────────────────────────────────────────────────
def call_gemini(model: str, prompt: str) -> str:
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1024
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
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                resp = json.loads(raw)

            print(f"   Raw response keys: {list(resp.keys())}")

            # Check for blocked/safety filtered response
            candidates = resp.get("candidates", [])
            if not candidates:
                print(f"   ⚠️  No candidates in response: {json.dumps(resp)[:500]}")
                raise RuntimeError("No candidates returned")

            candidate = candidates[0]
            finish_reason = candidate.get("finishReason", "")
            print(f"   Finish reason: {finish_reason}")

            # Handle safety block or recitation
            if finish_reason in ("SAFETY", "RECITATION", "BLOCKLIST"):
                raise RuntimeError(f"Blocked by Gemini safety filter: {finish_reason}")

            content = candidate.get("content", {})
            parts = content.get("parts", [])
            print(f"   Parts count: {len(parts)}")

            if not parts:
                print(f"   ⚠️  Empty parts. Full candidate: {json.dumps(candidate)[:500]}")
                raise RuntimeError("Empty parts in response")

            text = "".join(p.get("text", "") for p in parts).strip()
            print(f"   Text length: {len(text)} chars")

            if not text:
                print(f"   ⚠️  Empty text after joining parts")
                raise RuntimeError("Empty text in response")

            return text

        except urllib.error.HTTPError as e:
            body = e.read().decode()
            if e.code in (503, 429):
                print(f"   ⏳ Attempt {attempt}/{MAX_RETRIES} — error {e.code}, waiting {RETRY_WAIT}s...")
                time.sleep(RETRY_WAIT)
                continue
            raise RuntimeError(f"HTTP {e.code}: {body[:300]}")

        except RuntimeError as e:
            if "Empty" in str(e) or "No candidates" in str(e):
                if attempt < MAX_RETRIES:
                    print(f"   ⏳ Attempt {attempt}/{MAX_RETRIES} — retrying in {RETRY_WAIT}s...")
                    time.sleep(RETRY_WAIT)
                    continue
            raise

    raise RuntimeError(f"{model} failed after {MAX_RETRIES} attempts")


# ── Generate the update ───────────────────────────────────────────────────────
def generate_update() -> str:
    is_weekend  = TODAY.weekday() >= 5
    update_type = "Weekend Tech Briefing" if is_weekend else "Daily Tech Update"

    prompt = f"""You are the editor of PlugNTech, an Indian tech news blog.

Today is {DAY_NAME}, {DATE_STR}.

Write a "{update_type}" HTML section covering today's top technology news. Focus on India tech, smartphones, AI, and global tech companies.

You MUST output ONLY the following HTML. Replace everything in square brackets with real content. Do NOT output anything else — no introduction, no explanation, no markdown:

<section class="update-entry">
  <h3>📅 {update_type} — {DATE_STR}</h3>
  <h4>WRITE A CATCHY SUBTITLE HERE</h4>
  <p>WRITE 2 SENTENCES OF INTRO HERE</p>
  <p><strong>📌 Today's Tech Highlights</strong></p>
  <p>
    1️⃣ WRITE STORY 1 HERE<br>
    2️⃣ WRITE STORY 2 HERE<br>
    3️⃣ WRITE STORY 3 HERE<br>
    4️⃣ WRITE STORY 4 HERE<br>
    5️⃣ WRITE STORY 5 HERE<br>
    6️⃣ WRITE STORY 6 HERE
  </p>
  <p><strong>🔥 PlugNTech Insight:</strong><br>WRITE 1-2 SENTENCE INSIGHT HERE</p>
  <p><em>Updated: {DATE_STR}</em></p>
</section>"""

    last_error = None
    for model in MODELS:
        try:
            print(f"⏳ Trying model: {model}")
            text = call_gemini(model, prompt)
            # Strip accidental markdown fences
            text = re.sub(r"^```html\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"^```\s*",     "", text, flags=re.IGNORECASE)
            text = re.sub(r"```\s*$",     "", text).strip()
            if not text:
                raise RuntimeError("Empty after cleanup")
            print(f"✅ Success with model: {model}")
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

    print(f"✅ Injected new update into {HTML_FILE}")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"🚀 Generating PlugNTech update for {DATE_STR}...")
    new_section = generate_update()
    print(f"\n--- Preview (first 500 chars) ---\n{new_section[:500]}\n---\n")
    inject_into_html(new_section)
    print("🎉 Done! tech-updates.html has been updated.")
