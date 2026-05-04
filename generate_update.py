"""
PlugNTech Daily Tech Update Generator
Uses Google Gemini 1.5 Flash (free tier) — most reliable free model
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
DATE_STR       = TODAY.strftime("%-d %B %Y")   # e.g. "4 May 2026"
DAY_NAME       = TODAY.strftime("%A")           # e.g. "Monday"

# Try these models in order until one works
MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
]


# ── Generate update with Gemini ───────────────────────────────────────────────
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

    with urllib.request.urlopen(req, timeout=40) as r:
        resp = json.loads(r.read())

    candidates = resp.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"No candidates returned by {model}")

    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts).strip()


def generate_update() -> str:
    is_weekend  = TODAY.weekday() >= 5
    update_type = "Weekend Tech Briefing" if is_weekend else "Daily Tech Update"

    prompt = f"""You are the editor of PlugNTech, an Indian tech news blog for Indian readers.

Today is {DAY_NAME}, {DATE_STR}.

Write a "{update_type}" section based on the most important technology news happening around this date. Focus on:
- India tech news (AI, startups, government policy, telecom)
- Smartphone and gadget launches in India
- Big global tech news (Apple, Google, Samsung, Meta, Microsoft, OpenAI)
- AI and software developments

Format your response EXACTLY like this HTML. Do not add anything before or after it:

<section class="update-entry">
  <h3>📅 {update_type} — {DATE_STR}</h3>
  <h4>[CATCHY ONE-LINE THEME FOR TODAY]</h4>
  <p>[2 sentences setting context for today's tech news cycle]</p>
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
</section>

IMPORTANT: Output ONLY the HTML above. No markdown. No triple backticks. No extra words.
"""

    last_error = None
    for model in MODELS:
        try:
            print(f"⏳ Trying model: {model}")
            text = call_gemini(model, prompt)
            # Strip accidental markdown fences
            text = re.sub(r"^```html\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"```\s*$", "", text).strip()
            print(f"✅ Success with model: {model}")
            return text
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"⚠️  {model} failed ({e.code}): {body[:200]}")
            last_error = body
            if e.code == 429:
                print("   Rate limited — waiting 10s before trying next model...")
                time.sleep(10)
        except Exception as e:
            print(f"⚠️  {model} failed: {e}")
            last_error = str(e)

    raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")


# ── Inject into HTML ──────────────────────────────────────────────────────────
def inject_into_html(new_section: str):
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    MARKER = "<!-- UPDATES_START -->"

    if MARKER in content:
        insert_pos = content.index(MARKER) + len(MARKER)
        updated = (
            content[:insert_pos]
            + "\n\n"
            + new_section
            + "\n"
            + content[insert_pos:]
        )
    else:
        match = re.search(r"</h1>", content)
        if not match:
            match = re.search(r"<body[^>]*>", content)
        if match:
            insert_pos = match.end()
            updated = (
                content[:insert_pos]
                + "\n\n"
                + new_section
                + "\n"
                + content[insert_pos:]
            )
        else:
            raise ValueError(
                "Could not find <!-- UPDATES_START --> marker in tech-updates.html\n"
                "Please add <!-- UPDATES_START --> to your HTML file where you want updates to appear."
            )

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(updated)

    print(f"✅ Injected new update into {HTML_FILE}")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"🚀 Generating PlugNTech update for {DATE_STR}...")
    new_section = generate_update()
    print("\n--- Generated HTML Preview (first 300 chars) ---")
    print(new_section[:300])
    print("---\n")
    inject_into_html(new_section)
    print("🎉 Done! tech-updates.html has been updated.")
