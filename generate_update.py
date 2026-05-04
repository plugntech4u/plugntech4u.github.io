"""
PlugNTech Daily Tech Update Generator
Uses Google Gemini (free) to generate daily tech updates and injects into tech-updates.html
"""

import os
import re
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

# ── Config ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
NEWS_API_KEY   = os.environ.get("NEWS_API_KEY", "")   # optional but recommended
HTML_FILE      = "tech-updates.html"
IST            = timezone(timedelta(hours=5, minutes=30))
TODAY          = datetime.now(IST)
DATE_STR       = TODAY.strftime("%-d %B %Y")          # e.g. "4 May 2026"
DAY_NAME       = TODAY.strftime("%A")                  # e.g. "Monday"

# ── Step 1: Fetch headlines ───────────────────────────────────────────────────
def fetch_headlines():
    headlines = []

    if NEWS_API_KEY:
        try:
            url = (
                "https://newsapi.org/v2/top-headlines"
                "?category=technology&language=en&pageSize=10"
                f"&apiKey={NEWS_API_KEY}"
            )
            with urllib.request.urlopen(url, timeout=10) as r:
                data = json.loads(r.read())
            headlines = [
                f"- {a['title']} ({a.get('source', {}).get('name', '')})"
                for a in data.get("articles", [])[:10]
                if a.get("title") and "[Removed]" not in a["title"]
            ]
            print(f"✅ Fetched {len(headlines)} headlines from NewsAPI")
        except Exception as e:
            print(f"⚠️  NewsAPI failed: {e}")

    # Fallback: use GNews (no key required for basic use)
    if not headlines:
        try:
            url = "https://gnews.io/api/v4/top-headlines?category=technology&lang=en&max=10&apikey=free"
            with urllib.request.urlopen(url, timeout=10) as r:
                data = json.loads(r.read())
            headlines = [
                f"- {a['title']} ({a.get('source', {}).get('name', '')})"
                for a in data.get("articles", [])[:10]
                if a.get("title")
            ]
            print(f"✅ Fetched {len(headlines)} headlines from GNews")
        except Exception as e:
            print(f"⚠️  GNews failed: {e} — using generic prompt")

    return "\n".join(headlines) if headlines else "No live headlines available — use general recent tech knowledge."


# ── Step 2: Generate update with Gemini ──────────────────────────────────────
def generate_update(headlines: str) -> str:
    # Determine if it's a weekend
    is_weekend = TODAY.weekday() >= 5
    update_type = "Weekend Tech Briefing" if is_weekend else "Daily Tech Update"

    prompt = f"""You are the editor of PlugNTech, an Indian tech news blog.

Today is {DAY_NAME}, {DATE_STR}.

Here are today's top tech headlines:
{headlines}

Write a "{update_type}" section for the website tech-updates.html page.

Rules:
1. Focus on India-relevant tech news when possible (AI, smartphones, startups, policy, gadgets).
2. Pick the 5–7 most important stories from the headlines above.
3. Format EXACTLY like this example — use these exact HTML tags and emoji style:

<section class="update-entry">
  <h3>📅 {update_type} — {DATE_STR}</h3>
  <h4>[ONE CATCHY SUBTITLE SUMMARISING THE DAY'S THEME]</h4>
  <p>[2-sentence intro setting the context for today's news]</p>
  <p><strong>📌 Today's Tech Highlights</strong></p>
  <p>
    1️⃣ [Story 1 — 1 sentence]<br>
    2️⃣ [Story 2 — 1 sentence]<br>
    3️⃣ [Story 3 — 1 sentence]<br>
    4️⃣ [Story 4 — 1 sentence]<br>
    5️⃣ [Story 5 — 1 sentence]<br>
    6️⃣ [Story 6 — 1 sentence, if applicable]
  </p>
  <p><strong>🔥 PlugNTech Insight:</strong><br>[1–2 sentence sharp insight about what today's news means for India/tech/users]</p>
  <p><em>Updated: {DATE_STR}</em></p>
</section>

Output ONLY the HTML block above. No markdown, no explanation, no extra text.
"""

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024}
    }).encode()

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    )
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

    with urllib.request.urlopen(req, timeout=30) as r:
        resp = json.loads(r.read())

    text = resp["candidates"][0]["content"]["parts"][0]["text"].strip()

    # Strip any accidental markdown fences
    text = re.sub(r"^```html\s*", "", text)
    text = re.sub(r"```$", "", text).strip()

    print("✅ Gemini generated update successfully")
    return text


# ── Step 3: Inject into HTML ──────────────────────────────────────────────────
def inject_into_html(new_section: str):
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Insert after the opening <main> or after the page header / first <h1>
    # We look for the marker comment we'll add once, or fall back to after <body>
    MARKER = "<!-- UPDATES_START -->"

    if MARKER in content:
        insert_pos = content.index(MARKER) + len(MARKER)
        updated = content[:insert_pos] + "\n\n" + new_section + "\n" + content[insert_pos:]
    else:
        # Fallback: insert after first <h1> closing tag or after <body>
        match = re.search(r"</h1>", content)
        if not match:
            match = re.search(r"<body[^>]*>", content)
        if match:
            insert_pos = match.end()
            updated = content[:insert_pos] + "\n\n" + new_section + "\n" + content[insert_pos:]
        else:
            raise ValueError("Could not find injection point in HTML file.")

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(updated)

    print(f"✅ Injected update into {HTML_FILE}")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"🚀 Generating PlugNTech update for {DATE_STR}...")
    headlines  = fetch_headlines()
    new_section = generate_update(headlines)
    inject_into_html(new_section)
    print("🎉 Done! tech-updates.html updated.")
