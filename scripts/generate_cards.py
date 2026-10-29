#!/usr/bin/env python3
"""Generate self-hosted, animated GitHub stat cards (no third-party image servers).

Usage:  GH_USER=AneeqUllahKhan [GH_TOKEN=...] python scripts/generate_cards.py
Writes: assets/stats.svg and assets/languages.svg
"""
import os
import sys
import json
import urllib.parse
import urllib.request
from html import escape

USER = os.environ.get("GH_USER") or (sys.argv[1] if len(sys.argv) > 1 else "")
TOKEN = os.environ.get("GH_TOKEN")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

if not USER:
    sys.exit("Set GH_USER or pass a username as the first argument.")


DEMO = os.environ.get("GH_DEMO") == "1"  # offline preview with made-up numbers (testing only)


def api(path, params=None):
    if DEMO:
        if path.startswith("/users/") and "/repos" not in path:
            return {"public_repos": 24, "followers": 18}
        if path.endswith("/repos"):
            return [{"name": "demo", "fork": False, "stargazers_count": 7}]
        if path.endswith("/languages"):
            return {"JavaScript": 52000, "TypeScript": 30000, "Python": 24000, "HTML": 15000, "CSS": 9000, "SCSS": 3000}
        return {"total_count": 578}
    url = "https://api.github.com" + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-cards"}
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        return json.load(r)


def safe(fn, default):
    try:
        return fn()
    except Exception as exc:  # keep going even if one call is rate-limited
        print("warning:", exc, file=sys.stderr)
        return default


profile = api("/users/" + USER)

repos = []
for page in range(1, 6):
    batch = api("/users/%s/repos" % USER, {"per_page": 100, "page": page, "type": "owner"})
    repos += batch
    if len(batch) < 100:
        break
own = [r for r in repos if not r.get("fork")]

stars = sum(r["stargazers_count"] for r in own)
commits = safe(lambda: api("/search/commits", {"q": "author:" + USER, "per_page": 1})["total_count"], 0)
prs = safe(lambda: api("/search/issues", {"q": "author:%s type:pr" % USER, "per_page": 1})["total_count"], 0)
issues = safe(lambda: api("/search/issues", {"q": "author:%s type:issue" % USER, "per_page": 1})["total_count"], 0)

langs = {}
for r in own:
    data = safe(lambda: api("/repos/%s/%s/languages" % (USER, r["name"])), {})
    for name, size in data.items():
        langs[name] = langs.get(name, 0) + size

COLORS = {
    "JavaScript": "#f1e05a", "TypeScript": "#3178c6", "Python": "#3572A5", "HTML": "#e34c26",
    "CSS": "#8a63d2", "SCSS": "#c6538c", "Java": "#b07219", "C++": "#f34b7d", "C": "#8d8d8d",
    "PHP": "#8892bf", "Shell": "#89e051", "Jupyter Notebook": "#DA5B0B", "Dart": "#00B4AB",
    "Vue": "#41b883", "Go": "#00ADD8", "Rust": "#dea584", "Kotlin": "#A97BFF",
}
FALLBACK = ["#38bdf8", "#94a3b8", "#64748b", "#cbd5e1", "#7dd3fc", "#475569"]

FONT = "'Segoe UI',Ubuntu,'Helvetica Neue',Arial,sans-serif"
BASE_CSS = f"""
  .card{{fill:#0d1117;stroke:#1e293b;stroke-width:1.5}}
  .title{{font:600 16px {FONT};fill:#e2e8f0}}
  .label{{font:400 12px {FONT};fill:#94a3b8}}
  .num{{font:700 22px {FONT};fill:#e2e8f0}}
  .lang{{font:500 12px {FONT};fill:#cbd5e1}}
  .pct{{font:400 12px {FONT};fill:#64748b}}
  .accent{{fill:#38bdf8}}
  .tile{{fill:#111827;stroke:#1e293b;stroke-width:1}}
  .track{{fill:#1e293b}}
  .in{{animation:rise .7s cubic-bezier(.2,.7,.2,1) both}}
  .bar{{transform-box:fill-box;transform-origin:0 50%;animation:grow 1.1s cubic-bezier(.2,.7,.2,1) both}}
  .pulse{{animation:pulse 2.8s ease-in-out infinite}}
  @keyframes rise{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}
  @keyframes grow{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
  @keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.35}}}}
"""


def fmt(n):
    return f"{n/1000:.1f}k" if n >= 10000 else f"{n:,}"


def svg(w, h, body, desc):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-label="{escape(desc)}"><style>{BASE_CSS}</style>'
        f'<rect class="card" x="0.75" y="0.75" width="{w-1.5}" height="{h-1.5}" rx="12"/>{body}</svg>'
    )


# ---------- Stats card ----------
tiles = [
    ("Stars earned", stars), ("Commits (public)", commits), ("Pull requests", prs),
    ("Issues opened", issues), ("Public repos", profile["public_repos"]), ("Followers", profile["followers"]),
]
body = '<circle class="accent pulse" cx="26" cy="29" r="4"/>'
body += '<text class="title" x="40" y="34">GitHub Overview</text>'
body += f'<text class="label" x="436" y="34" text-anchor="end">@{escape(USER)}</text>'
for i, (label, value) in enumerate(tiles):
    col, row = i % 3, i // 3
    x, y = 20 + col * 143, 56 + row * 68
    d = 0.1 + i * 0.1
    body += (
        f'<g class="in" style="animation-delay:{d:.1f}s">'
        f'<rect class="tile" x="{x}" y="{y}" width="134" height="58" rx="9"/>'
        f'<rect class="accent" x="{x}" y="{y+14}" width="3" height="30" rx="1.5"/>'
        f'<text class="num" x="{x+16}" y="{y+29}">{fmt(value)}</text>'
        f'<text class="label" x="{x+16}" y="{y+46}">{escape(label)}</text></g>'
    )
with open(os.path.join(OUT, "stats.svg"), "w", encoding="utf-8") as f:
    f.write(svg(460, 200, body, "GitHub overview statistics"))

# ---------- Languages card ----------
total = sum(langs.values()) or 1
top = sorted(langs.items(), key=lambda kv: kv[1], reverse=True)[:6]
H = 56 + 6 * 22 + 14
body = '<circle class="accent pulse" cx="26" cy="29" r="4"/>'
body += '<text class="title" x="40" y="34">Top Languages</text>'
biggest = top[0][1] if top else 1
for i, (name, size) in enumerate(top):
    pct = size / total * 100
    y = 58 + i * 22
    color = COLORS.get(name, FALLBACK[i % len(FALLBACK)])
    d = 0.1 + i * 0.12
    barw = max(4.0, 150.0 * size / biggest)  # bars scaled relative to the top language
    body += (
        f'<g class="in" style="animation-delay:{d:.2f}s">'
        f'<circle cx="26" cy="{y+4}" r="4" fill="{color}"/>'
        f'<text class="lang" x="40" y="{y+8}">{escape(name)}</text>'
        f'<rect class="track" x="150" y="{y}" width="150" height="8" rx="4"/>'
        f'<rect class="bar" x="150" y="{y}" width="{barw:.1f}" height="8" rx="4" fill="{color}" style="animation-delay:{d+.15:.2f}s"/>'
        f'<text class="pct" x="350" y="{y+8}" text-anchor="end">{pct:.1f}%</text></g>'
    )
with open(os.path.join(OUT, "languages.svg"), "w", encoding="utf-8") as f:
    f.write(svg(370, H, body, "Most used languages"))
print("Generated cards for", USER, "->", OUT)
