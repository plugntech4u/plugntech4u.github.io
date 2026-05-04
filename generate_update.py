"""
PlugNTech Daily Tech Update Generator
Uses Google Gemini (free) with built-in Google Search grounding
No News API needed — Gemini searches the web itself!
"""

import os
import re
import json
import urllib.request
from datetime import datetime, timezone, timedelta

# ── Config ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
HTML_FILE      = "tech-updates.html"
IST            = timezone(timedelta(hours=5, minutes=30))
TODAY          = datetime.now(IST)
DATE_STR       = TODAY.strftime("%-d %B %Y")   # e.g. "4 May 2026"
DAY_NAME       = TODAY.strftime("%A")           # e.g. "Monday"


# ── Generate update with Gemini (Gemini searches web by itself) ───────────────
def generate_update() -> str:
    is_weekend  = TODAY.weekday() >= 5
    update_type = "Weekend Tech Briefing" if is_weekend else "Daily Tech Update"

    prompt = f"""You are the editor of PlugNTech, an Indian tech news blog targeting Indian readers.

Today is {DAY_NAME}, {DATE_STR}.

Search the web RIGHT NOW for today's top technology news, especially:
- India tech news (AI investments, startup funding, government tech policy)
- New smartphone / gadget launches in India
- Big global tech news (Apple, Google, Samsung, Meta, Microsoft, etc.)
- AI developments
- Telecom / 5G news in India

Then write a "{update_type}" section for our website.

Format EXACTLY like this — use these exact HTML tags and emoji style:

<section class="update-entry">
  <h3>📅 {update_type} — {DATE_STR}</h3>
  <h4>[ONE CATCHY SUBTITLE SUMMARISING THE DAY'S THEME]</h4>
  <p>[2-sentence intro setting the context for today's news]</p>
  <p><strong>📌 Today's Tech Highlights</strong></p>
  <p>
    1️⃣ [Story 1 — 1 clear sentence]<br>
    2️⃣ [Story 2 — 1 clear sentence]<br>
    3️⃣ [Story 3 — 1 clear sentence]<br>
    4️⃣ [Story 4 — 1 clear sentence]<br>
    5️⃣ [Story 5 — 1 clear sentence]<br>
    6️⃣ [Story 6 — 1 clear sentence if available]
  </p>
  <p><strong>🔥 PlugNTech Insight:</strong><br>[1-2 sentence sharp insight about what today's news means for India/tech/users]</p>
  <p><em>Updated: {DATE_STR}</em></p>
</section>

Output ONLY the HTML block above. No markdown. No explanation. No extra text. No code fences.
"""

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1024
        },
        "tools": [{"google_search": {}}]
    }).encode()

    # gemini-2.0-flash supports google_search grounding on free tier
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    )

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"Gemini API error {e.code}: {body}")

    # Extract text from response
    candidates = resp.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"No candidates in Gemini response: {resp}")

    parts = candidates[0].get("content", {}).get("parts", [])
    text  = "".join(p.get("text", "") for p in parts).strip()

    # Strip any accidental markdown fences
    text = re.sub(r"^```html\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```\s*$",     "", text).strip()

    print("✅ Gemini generated update successfully")
    return text


# ── Inject into HTML ──────────────────────────────────────────────────────────
def inject_into_html(new_section: str):
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    MARKER = "<!-- UPDATES_START -->"

    if MARKER in content:
        insert_pos = content.index(MARKER) + len(MARKER)
        updated = content[:insert_pos] + "\n\n" + new_section + "\n" + content[insert_pos:]
    else:
        # Fallback: insert after </h1> or after <body>
        match = re.search(r"</h1>", content)
        if not match:
            match = re.search(r"<body[^>]*>", content)
        if match:
            insert_pos = match.end()
            updated = content[:insert_pos] + "\n\n" + new_section + "\n" + content[insert_pos:]
        else:
            raise ValueError("Could not find injection point in tech-updates.html")

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(updated)

    print(f"✅ Injected update into {HTML_FILE}")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"🚀 Generating PlugNTech update for {DATE_STR}...")
    new_section = generate_update()
    inject_into_html(new_section)
    print("🎉 Done! tech-updates.html updated.")
