"""
PlugNTech Daily Tech Update Generator
Uses OpenRouter API (100% free)
Models verified from OpenRouter free list on 16 June 2026
Strips thinking/reasoning tags to ensure clean HTML output
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

# Verified free models on OpenRouter as of June 2026
MODELS = [
    "openrouter/owl-alpha",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "openai/gpt-oss-120b:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "openai/gpt-oss-20b:free",
    "moonshotai/kimi-k2.6:free",
]

MAX_RETRIES = 3
RETRY_WAIT  = 20


# ── Clean the response — strip thinking/reasoning blocks ─────────────────────
def clean_response(text: str) -> str:
    # Strip <think>...</think> or <thinking>...</thinking> blocks
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL)
    # Strip markdown fences
    text = re.sub(r"^```html\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"```\s*$", "", text)
    # Extract only the <section>...</section> block if present
    match = re.search(r'(<section class="update-entry">.*?</section>)', text, flags=re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


# ── Call OpenRouter API ───────────────────────────────────────────────────────
def call_openrouter(model: str, prompt: str) -> str:
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.85,
        "max_tokens": 1500,
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
                msg  = err.get("message", "")
                if code in (402, 404):
                    raise RuntimeError(f"Skip — {code}: {msg[:80]}")
                if code in (429, 503):
                    print(f"   ⏳ Attempt {attempt}/{MAX_RETRIES} — rate limited, waiting {RETRY_WAIT}s...")
                    time.sleep(RETRY_WAIT)
                    continue
                raise RuntimeError(f"API error {code}: {msg[:80]}")

            choices = resp.get("choices", [])
            if not choices:
                raise RuntimeError("No choices in response")

            text = choices[0].get("message", {}).get("content", "").strip()
            if not text:
                raise RuntimeError("Empty content")

            print(f"   ✅ Model used: {resp.get('model', model)}")
            return text

        except urllib.error.HTTPError as e:
            body = e.read().decode()
            if e.code in (429, 503):
                print(f"   ⏳ Attempt {attempt}/{MAX_RETRIES} — HTTP {e.code}, waiting {RETRY_WAIT}s...")
                time.sleep(RETRY_WAIT)
                continue
            if e.code in (402, 404):
                raise RuntimeError(f"Skip — HTTP {e.code}: {body[:80]}")
            raise RuntimeError(f"HTTP {e.code}: {body[:200]}")

        except RuntimeError:
            raise

    raise RuntimeError(f"{model} failed after {MAX_RETRIES} attempts")


# ── Generate the update ───────────────────────────────────────────────────────
def generate_update() -> str:
    is_weekend  = TODAY.weekday() >= 5
    update_type = "Weekend Tech Briefing" if is_weekend else "Daily Tech Update"

    prompt = (
        f"You are the editor of PlugNTech, a tech blog famous for covering stories "
        f"that NO other tech blog covers. Your readers come here for fresh, unusual, "
        f"thought-provoking tech stories they cannot find anywhere else.\n\n"
        f"Today is {DAY_NAME}, {DATE_STR}.\n\n"
        f"Write a '{update_type}' with 7 stories — one per category below.\n"
        f"Be wildly specific. Real place names, real numbers, real company names.\n"
        f"Think: tech in unexpected places, weird science, gadgets changing lives.\n\n"
        f"CATEGORIES:\n"
        f"🌍 INTERNATIONAL — Unusual global tech story most blogs ignore\n"
        f"🇮🇳 INDIA TECH — Indian startup, innovation, government tech, or local invention\n"
        f"🚀 LAUNCH — Upcoming or just-launched smartphone, gadget, or breakthrough device\n"
        f"🧠 ADVANCEMENT — Surprising scientific or engineering breakthrough\n"
        f"🏥 HEALTHCARE — Medical AI, biotech, wearable health device, or digital health\n"
        f"💡 HIDDEN GEM — Completely underreported story tech lovers would find fascinating\n"
        f"🔮 FUTURE WATCH — Technology or trend that will matter in the next 1-3 years\n\n"
        f"STRICT FORMAT RULES:\n"
        f"1. Output ONLY the HTML section below — nothing before it, nothing after it\n"
        f"2. No thinking, no explanation, no markdown, no backticks\n"
        f"3. Each story line: emoji first, then one vivid specific sentence. NO bold labels.\n"
        f"4. The h4 headline should be witty and capture the most surprising story of the day\n"
        f"5. The intro paragraph should be fun, conversational, like talking to a curious friend\n"
        f"6. The PlugNTech Insight should be sharp, opinionated, India-relevant\n\n"
        f"OUTPUT THIS EXACT HTML (fill in all CAPS placeholders):\n\n"
        f'<section class="update-entry">\n'
        f"  <h3>📅 {update_type} — {DATE_STR}</h3>\n"
        f"  <h4>CATCHY WITTY HEADLINE ABOUT TODAY'S MOST SURPRISING STORY</h4>\n"
        f"  <p>SENTENCE ONE MAKING READER EXCITED. SENTENCE TWO TEASING WHAT'S INSIDE.</p>\n"
        f"  <p><strong>📌 Today's Tech Highlights</strong></p>\n"
        f"  <p>\n"
        f"    🌍 ONE VIVID SPECIFIC SENTENCE ABOUT THE INTERNATIONAL STORY<br>\n"
        f"    🇮🇳 ONE VIVID SPECIFIC SENTENCE ABOUT THE INDIA STORY<br>\n"
        f"    🚀 ONE VIVID SPECIFIC SENTENCE ABOUT THE LAUNCH<br>\n"
        f"    🧠 ONE VIVID SPECIFIC SENTENCE ABOUT THE ADVANCEMENT<br>\n"
        f"    🏥 ONE VIVID SPECIFIC SENTENCE ABOUT THE HEALTHCARE STORY<br>\n"
        f"    💡 ONE VIVID SPECIFIC SENTENCE ABOUT THE HIDDEN GEM<br>\n"
        f"    🔮 ONE VIVID SPECIFIC SENTENCE ABOUT THE FUTURE WATCH\n"
        f"  </p>\n"
        f"  <p><strong>🔥 PlugNTech Insight:</strong><br>1-2 SHARP OPINIONATED SENTENCES ABOUT WHAT THIS MEANS FOR INDIA OR THE FUTURE</p>\n"
        f"  <p><em>Updated: {DATE_STR}</em></p>\n"
        f"</section>"
    )

    last_error = None
    for model in MODELS:
        try:
            print(f"⏳ Trying model: {model}")
            raw  = call_openrouter(model, prompt)
            text = clean_response(raw)
            if not text or "<section" not in text:
                raise RuntimeError(f"No valid HTML section found in output")
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
