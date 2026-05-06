"""
PlugNTech Daily Tech Update Generator
Uses Groq API (100% free, no billing needed)
Covers: India tech, global tech, AI, smartphones, healthcare tech
"""

import os
import re
import json
import time
import urllib.request
from datetime import datetime, timezone, timedelta

# ── Config ────────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
HTML_FILE    = "tech-updates.html"
IST          = timezone(timedelta(hours=5, minutes=30))
TODAY        = datetime.now(IST)
DATE_STR     = TODAY.strftime("%-d %B %Y")   # e.g. "6 May 2026"
DAY_NAME     = TODAY.strftime("%A")           # e.g. "Wednesday"

# Groq free models (in order of preference)
MODELS = [
    "llama-3.3-70b-versatile",
    "llama3-70b-8192",
    "mixtral-8x7b-32768",
]

MAX_RETRIES = 4
RETRY_WAIT  = 15


# ── Call Groq API ─────────────────────────────────────────────────────────────
def call_groq(model: str, prompt: str) -> str:
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 1024,
    }).encode()

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GROQ_API_KEY}",
        },
        method="POST"
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                resp = json.loads(r.read())

            choices = resp.get("choices", [])
            if not choices:
                raise RuntimeError(f"No choices in response: {resp}")

            text = choices[0].get("message", {}).get("content", "").strip()
            if not text:
                raise RuntimeError("Empty content in response")

            return text

        except urllib.error.HTTPError as e:
            body = e.read().decode()
            if e.code in (429, 503):
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

    prompt = (
        f"You are the editor of PlugNTech, an Indian tech news blog.\n"
        f"Today is {DAY_NAME}, {DATE_STR}.\n\n"
        f"Write a '{update_type}' HTML section with 7 real tech stories covering:\n"
        f"- India tech news (AI, startups, government policy, telecom)\n"
        f"- Smartphone or gadget launches\n"
        f"- Global tech news (Apple, Google, Samsung, Meta, Microsoft, OpenAI)\n"
        f"- AI developments\n"
        f"- Healthcare technology (medical AI, health apps, digital health, biotech)\n\n"
        f"Output ONLY this HTML block, nothing else, no markdown, no backticks:\n\n"
        f'<section class="update-entry">\n'
        f"  <h3>📅 {update_type} — {DATE_STR}</h3>\n"
        f"  <h4>WRITE A CATCHY SUBTITLE HERE</h4>\n"
        f"  <p>WRITE 2 SENTENCE INTRO HERE</p>\n"
        f"  <p><strong>📌 Today's Tech Highlights</strong></p>\n"
        f"  <p>\n"
        f"    1️⃣ WRITE INDIA TECH STORY HERE<br>\n"
        f"    2️⃣ WRITE SMARTPHONE/GADGET STORY HERE<br>\n"
        f"    3️⃣ WRITE AI STORY HERE<br>\n"
        f"    4️⃣ WRITE GLOBAL TECH STORY HERE<br>\n"
        f"    5️⃣ WRITE ANOTHER TECH STORY HERE<br>\n"
        f"    6️⃣ WRITE ANOTHER TECH STORY HERE<br>\n"
        f"    🏥 WRITE ONE HEALTHCARE TECH STORY HERE\n"
        f"  </p>\n"
        f"  <p><strong>🔥 PlugNTech Insight:</strong><br>WRITE 1-2 SENTENCE INSIGHT HERE</p>\n"
        f"  <p><em>Updated: {DATE_STR}</em></p>\n"
        f"</section>"
    )

    last_error = None
    for model in MODELS:
        try:
            print(f"⏳ Trying model: {model}")
            text = call_groq(model, prompt)
            # Strip any accidental markdown fences
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

    raise RuntimeError(f"All Groq models failed. Last error: {last_error}")


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
