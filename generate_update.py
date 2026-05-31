"""
PlugNTech Daily Tech Update Generator
Uses OpenRouter API (100% free)
Unique topic categories — not your typical AI news roundup!
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
        "temperature": 0.85,
        "max_tokens": 1200,
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
                err  = resp["error"]
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

            print(f"   Model used: {resp.get('model', model)}")
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
        f"You are the editor of PlugNTech, a tech blog famous for covering stories "
        f"that NO other tech blog covers. Your readers come here specifically because "
        f"they find fresh, unusual, thought-provoking tech stories they cannot find anywhere else.\n\n"
        f"Today is {DAY_NAME}, {DATE_STR}.\n\n"
        f"Write a '{update_type}' section with exactly 7 stories, one per category.\n"
        f"Be specific, surprising and interesting. Make readers say 'I had no idea this existed!'\n\n"
        f"CATEGORY RULES:\n"
        f"🌍 INTERNATIONAL TECH — One unusual global tech story most blogs ignore. "
        f"Think tech in unexpected places, weird science applications, futuristic infrastructure.\n"
        f"🇮🇳 INDIA TECH — One India-specific story: startup, innovation, government tech, telecom, or local invention.\n"
        f"🚀 LAUNCH — One upcoming or just-launched gadget, mobile phone, or awaited tech product "
        f"launching in India or internationally. Focus on smartphones, wearables, gadgets, or breakthrough devices.\n"
        f"🧠 ADVANCEMENT — One surprising scientific or engineering breakthrough: "
        f"new material, battery, space, quantum computing, robotics, or energy.\n"
        f"🏥 HEALTHCARE — One medical technology story: health AI, biotech, wearable health device, digital health.\n"
        f"💡 HIDDEN GEM — One completely underreported story that tech lovers would find fascinating.\n"
        f"🔮 FUTURE WATCH — One upcoming technology or trend that will matter in the next 1-3 years.\n\n"
        f"FORMAT RULES (very important):\n"
        f"- Each story starts with its emoji only — NO bold labels like **International:** or **Launch:**\n"
        f"- Each story is exactly one clear, specific, interesting sentence\n"
        f"- Output ONLY the HTML below. No markdown. No backticks. No extra text:\n\n"
        f'<section class="update-entry">\n'
        f"  <h3>📅 {update_type} — {DATE_STR}</h3>\n"
        f"  <h4>WRITE ONE CATCHY HEADLINE CAPTURING TODAY'S MOST INTERESTING STORY</h4>\n"
        f"  <p>WRITE 2 ENGAGING SENTENCES making the reader excited to read today's updates.</p>\n"
        f"  <p><strong>📌 Today's Tech Highlights</strong></p>\n"
        f"  <p>\n"
        f"    🌍 INTERNATIONAL TECH STORY IN ONE SENTENCE<br>\n"
        f"    🇮🇳 INDIA TECH STORY IN ONE SENTENCE<br>\n"
        f"    🚀 GADGET OR MOBILE LAUNCH STORY IN ONE SENTENCE<br>\n"
        f"    🧠 TECH ADVANCEMENT STORY IN ONE SENTENCE<br>\n"
        f"    🏥 HEALTHCARE TECH STORY IN ONE SENTENCE<br>\n"
        f"    💡 HIDDEN GEM STORY IN ONE SENTENCE<br>\n"
        f"    🔮 FUTURE WATCH STORY IN ONE SENTENCE\n"
        f"  </p>\n"
        f"  <p><strong>🔥 PlugNTech Insight:</strong><br>"
        f"WRITE 1-2 SENTENCES — a sharp original thought about what today's news means "
        f"for the future or for Indian readers specifically.</p>\n"
        f"  <p><em>Updated: {DATE_STR}</em></p>\n"
        f"</section>"
    )

    last_error = None
    for model in MODELS:
        try:
            print(f"⏳ Trying model: {model}")
            text = call_openrouter(model, prompt)
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
