"""
PlugNTech Daily Tech Update Generator
Uses Google Gemini 2.5 Flash (free tier, 2026)
Retries automatically on 503 busy errors
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
DATE_STR       = TODAY.strftime("%-d %B %Y")   # e.g. "5 May 2026"
DAY_NAME       = TODAY.strftime("%A")           # e.g. "Tuesday"

# Current free-tier models as of May 2026
MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.5-flash-preview-05-20",
]

MAX_RETRIES = 5          # how many times to retry each model on 503
RETRY_WAIT  = 20         # seconds to wait between retries


# ── Call Gemini API (with retry) ──────────────────────────────────────────────
def call_gemini(model: str, prompt: str) -> str:
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 900
        }
    }).encode()

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={GEMINI_API_KEY}"
    )

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                resp = json.loads(r.read())

            candidates = resp.get("candidates", [])
            if not candidates:
                raise RuntimeError(f"No candidates returned: {resp}")

            parts = candidates[0].get("content", {}).get("parts", [])
            return "".join(p.get("text", "") for p in parts).strip()

        except urllib.error.HTTPError as e:
            body = e.read().decode()

            if e.code == 503:
                print(f"   ⏳ Attempt {attempt}/{MAX_RETRIES} — server busy (503), waiting {RETRY_WAIT}s...")
                time.sleep(RETRY_WAIT)
                continue  # retry same model

            elif e.code == 429:
                print(f"   ⚠️  Rate limited (429) — waiting {RETRY_WAIT}s...")
                time.sleep(RETRY_WAIT)
                continue

            else:
                # 404 or other — no point retrying
                raise urllib.error.HTTPError(
                    e.url, e.code, body, e.headers, None
                )

    raise RuntimeError(f"Model {model} failed after {MAX_RETRIES} retries (server busy)")


# ── Generate the update ───────────────────────────────────────────────────────
def generate_update() -> str:
    is_weekend  = TODAY.weekday() >= 5
    update_type = "Weekend Tech Briefing" if is_weekend else "Daily Tech Update"

    prompt = f"""You are the editor of PlugNTech, an Indian tech news blog for Indian readers.

Today is {DAY_NAME}, {DATE_STR}.

Write a "{update_type}" section with the most important technology news around this date. Focus on:
- India tech news (AI, startups, government policy, telecom, 5G)
- Smartphone and gadget launches in India
- Big global tech news (Apple, Google, Samsung, Meta, Microsoft, OpenAI)
- AI and software developments

Format your response EXACTLY as this HTML block. Output ONLY the HTML — no markdown, no backticks, no explanation:

<section class="update-entry">
  <h3>📅 {update_type} — {DATE_STR}</h3>
  <h4>[CATCHY ONE-LINE THEME FOR TODAY]</h4>
  <p>[2 sentences setting context for today's tech news]</p>
  <p><strong>📌 Today's Tech Highlights</strong></p>
  <p>
    1️⃣ [Story 1 — one clear sentence]<br>
    2️⃣ [Story 2 — one clear sentence]<br>
    3️⃣ [Story 3 — one clear sentence]<br>
    4️⃣ [Story 4 — one clear sentence]<br>
    5️⃣ [Story 5 — one clear sentence]<br>
    6️⃣ [Story 6 — one clear sentence]
  </p>
  <p><strong>🔥 PlugNTech Insight:</strong><br>[1-2 sentence insight on what this means for India/users]</p>
  <p><em>Updated: {DATE_STR}</em></p>
</section>"""

    last_error = None
    for model in MODELS:
        try:
            print(f"⏳ Trying model: {model}")
            text = call_gemini(model, prompt)
            # Strip any accidental markdown fences
            text = re.sub(r"^```html\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"```\s*$", "", text).strip()
            print(f"✅ Success with model: {model}")
            return text
        except RuntimeError as e:
            print(f"⚠️  {model} gave up: {e}")
            last_error = str(e)
        except urllib.error.HTTPError as e:
            print(f"⚠️  {model} failed ({e.code})")
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
        match = re.search(r"</h1>", content)
        if not match:
            match = re.search(r"<body[^>]*>", content)
        if match:
            insert_pos = match.end()
            updated = content[:insert_pos] + "\n\n" + new_section + "\n" + content[insert_pos:]
        else:
            raise ValueError(
                "Could not find <!-- UPDATES_START --> in tech-updates.html\n"
                "Please add <!-- UPDATES_START --> where you want updates to appear."
            )

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(updated)

    print(f"✅ Injected new update into {HTML_FILE}")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"🚀 Generating PlugNTech update for {DATE_STR}...")
    new_section = generate_update()
    print("\n--- Preview (first 300 chars) ---")
    print(new_section[:300])
    print("---\n")
    inject_into_html(new_section)
    print("🎉 Done! tech-updates.html has been updated.")
