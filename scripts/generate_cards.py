#!/usr/bin/env python3
"""
Generates assets/languages.svg and assets/stats.svg for the profile README
from live GitHub API data. Runs inside GitHub Actions (uses GITHUB_TOKEN).

Usage:
    python scripts/generate_cards.py                 # live data
    python scripts/generate_cards.py --demo          # offline sample data
"""
import json
import os
import sys
import urllib.request
from html import escape

USER = os.environ.get("GH_USER", "mdgolamrabbi22")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
EXCLUDE_REPOS = {USER}                      # skip the profile repo itself
EXCLUDE_LANGS = set()                       # e.g. {"HTML", "CSS"} to hide markup

COLORS = {
    "Python": "#3572A5", "Java": "#b07219", "PHP": "#4F5D95", "C++": "#f34b7d",
    "C": "#555555", "JavaScript": "#f1e05a", "TypeScript": "#3178c6",
    "HTML": "#e34c26", "CSS": "#563d7c", "Jupyter Notebook": "#DA5B0B",
    "Shell": "#89e051", "Arduino": "#00979D", "Dart": "#00B4AB",
}
FALLBACK = ["#00d2ff", "#7c3aed", "#0ea5e9", "#4ade80", "#f472b6", "#fbbf24"]
FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"


def api(path):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={"Accept": "application/vnd.github+json",
                 "User-Agent": "profile-cards",
                 **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_live():
    repos, page = [], 1
    while True:
        chunk = api(f"/users/{USER}/repos?per_page=100&type=owner&page={page}")
        repos += chunk
        if len(chunk) < 100:
            break
        page += 1
    repos = [r for r in repos if not r["fork"] and r["name"] not in EXCLUDE_REPOS]
    langs = {}
    for r in repos:
        for lang, n in api(f"/repos/{USER}/{r['name']}/languages").items():
            if lang not in EXCLUDE_LANGS:
                langs[lang] = langs.get(lang, 0) + n
    user = api(f"/users/{USER}")
    stats = {
        "Public Repos": user["public_repos"],
        "Total Stars": sum(r["stargazers_count"] for r in repos),
        "Followers": user["followers"],
        "Following": user["following"],
    }
    return langs, stats


def demo():
    return ({"Python": 5200, "Java": 3100, "PHP": 2400, "C++": 1300},
            {"Public Repos": 15, "Total Stars": 0, "Followers": 6, "Following": 7})


def card(title, w, h, body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#00d2ff"/><stop offset="1" stop-color="#7c3aed"/>
    </linearGradient>
  </defs>
  <rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="10" fill="#0d1117" stroke="#1e293b"/>
  <rect x="20" y="52" width="48" height="3" rx="1.5" fill="url(#g)"/>
  <text x="20" y="36" font-family="{FONT}" font-size="18" font-weight="700" fill="#00d2ff">{escape(title)}</text>
{body}
</svg>
'''


def languages_svg(langs):
    total = sum(langs.values()) or 1
    items = sorted(langs.items(), key=lambda kv: -kv[1])
    top, rest = items[:6], sum(v for _, v in items[6:])
    if rest:
        top.append(("Other", rest))
    w, bar_x, bar_w = 420, 20, 380
    h = 100 + 26 * ((len(top) + 1) // 2)
    parts, x, i = [], bar_x, 0
    parts.append(f'  <clipPath id="c"><rect x="{bar_x}" y="68" width="{bar_w}" height="10" rx="5"/></clipPath>')
    parts.append('  <g clip-path="url(#c)">')
    for name, val in top:
        color = COLORS.get(name, FALLBACK[i % len(FALLBACK)]) if name != "Other" else "#64748b"
        seg = bar_w * val / total
        parts.append(f'    <rect x="{x:.2f}" y="68" width="{seg + 0.5:.2f}" height="10" fill="{color}"/>')
        x += seg
        i += 1
    parts.append("  </g>")
    i = 0
    for idx, (name, val) in enumerate(top):
        color = COLORS.get(name, FALLBACK[i % len(FALLBACK)]) if name != "Other" else "#64748b"
        i += 1
        cx = 20 + (idx % 2) * 200
        cy = 106 + (idx // 2) * 26
        parts.append(f'  <circle cx="{cx + 5}" cy="{cy - 4}" r="5" fill="{color}"/>')
        parts.append(f'  <text x="{cx + 16}" y="{cy}" font-family="{FONT}" font-size="13" fill="#c9d1d9">{escape(name)}'
                     f'<tspan fill="#64748b" dx="6">{val / total * 100:.1f}%</tspan></text>')
    return card("Most Used Languages", w, h, "\n".join(parts))


def stats_svg(stats):
    w, h = 420, 205
    parts = []
    for idx, (label, val) in enumerate(stats.items()):
        cx = 20 + (idx % 2) * 200
        cy = 92 + (idx // 2) * 56
        parts.append(f'  <text x="{cx}" y="{cy}" font-family="{FONT}" font-size="26" font-weight="700" fill="#f8fafc">{val}</text>')
        parts.append(f'  <text x="{cx}" y="{cy + 18}" font-family="{FONT}" font-size="12" fill="#94a3b8">{escape(label)}</text>')
    return card("GitHub Snapshot", w, h, "\n".join(parts))


def main():
    langs, stats = demo() if "--demo" in sys.argv else fetch_live()
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "languages.svg"), "w", encoding="utf-8") as f:
        f.write(languages_svg(langs))
    with open(os.path.join(OUT, "stats.svg"), "w", encoding="utf-8") as f:
        f.write(stats_svg(stats))
    print("Languages:", {k: v for k, v in sorted(langs.items(), key=lambda kv: -kv[1])})
    print("Stats:", stats)


if __name__ == "__main__":
    main()
