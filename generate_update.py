"""
PlugNTech Daily Tech Update Generator
Uses OpenRouter API (100% free)
Uses openrouter/free auto-router — always picks a working free model automatically
"""

import os
import re
import json
import time
import urllib.request
from datetime import datetime, timezone, timedelta

# ── Config ────────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]
HTML_FILE          = "tech-updates.html"
IST                = timezone(timedelta(hours=5, minutes=30))
TODAY              = datetime.now(IST)
DATE_STR           = TODAY.strftime("%-d %B %Y")
DAY_NAME           = TODAY.strftime("%A")

# openrouter/free auto-picks any available free model
# Specific models as fallback
MODELS = [
    "openrouter/auto",
    "meta-llama/llama-3.3-70b-instruct:free",
    "deepseek/deepseek-r1:free",
    "qwen/qwen3-235b-a22b:free",
]

MAX_RETRIES = 4
RETRY_WAIT  = 20


# ── Call OpenRouter API ───────────────────────────────────────────────────────
def call_openrouter(model: str, prompt: str) -> str:
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 1024,
    }).encode()

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://plugntech4u.github.io",
            "X-Title": "PlugNTech Daily Update",
        },
        method="POST"
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                resp = json.loads(r.read())

            if "error" in resp:
                err = resp["error"]
                code = err.get("code", 0)
                if code in (429, 503):
                    print(f"   ⏳ Attempt {attempt}/{MAX_RETRIES} — rate limited, waiting {RETRY_WAIT}s...")
                    time.sleep(RETRY_WAIT)
                    continue
                raise RuntimeError(f"API error: {err}")

            choices = resp.get("choices", [])
            if not choices:
                raise RuntimeError(f"No choices: {resp}")

            text = choices[0].get("message", {}).get("content", "").strip()
            if not text:
                raise RuntimeError("Empty content")

            # Show which model actually responded
            model_used = resp.get("model", model)
            print(f"   Model used: {model_used}")
            return text

        except urllib.error.HTTPError as e:
            body = e.read().decode()
            if e.code in (429, 503):
                print(f"   ⏳ Attempt {attempt}/{MAX_RETRIES} — HTTP {e.code}, waiting {RETRY_WAIT}s...")
                time.sleep(RETRY_WAIT)
                continue
            raise RuntimeError(f"HTTP {e.code}: {body[:300]}")

        except RuntimeError:
            raise

    raise RuntimeError(f"{model} failed after {MAX_RETRIES} attempts")


# ── Generate the update ───────────────────────────────────────────────────────
def generate_update() -> str:
    is_weekend  = TODAY.weekday() >= 5
    update_type = "Weekend Tech Briefing" if is_weekend else "Daily Tech Update"

    prompt = (
        f"You are the editor of PlugNTech, an Indian tech news blog.\n"
        f"Today is {DAY_NAME}, {DATE_STR}.\n\n"
        f"Write a '{update_type}' HTML section with 7 tech stories covering:\n"
        f"- India tech news (AI, startups, government policy, telecom)\n"
        f"- Smartphone or gadget launches in India\n"
        f"- Global tech news (Apple, Google, Samsung, Meta, Microsoft, OpenAI)\n"
        f"- AI developments\n"
        f"- Healthcare technology (medical AI, health apps, digital health, biotech)\n\n"
        f"Output ONLY this HTML block. No markdown. No backticks. No explanation:\n\n"
        f'<section class="update-entry">\n'
        f"  <h3>📅 {update_type} — {DATE_STR}</h3>\n"
        f"  <h4>WRITE A CATCHY SUBTITLE HERE</h4>\n"
        f"  <p>WRITE 2 SENTENCE INTRO HERE</p>\n"
        f"  <p><strong>📌 Today's Tech Highlights</strong></p>\n"
        f"  <p>\n"
        f"    1️⃣ WRITE INDIA TECH STORY HERE<br>\n"
        f"    2️⃣ WRITE SMARTPHONE OR GADGET STORY HERE<br>\n"
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
            text = call_openrouter(model, prompt)
            # Strip any accidental markdown fences
            text = re.sub(r"^```html\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"^```\s*",     "", text)
            text = re.sub(r"```\s*$",     "", text).strip()
            if not text:
                raise RuntimeError("Empty after cleanup")
            print(f"✅ Success! ({len(text)} chars)")
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
