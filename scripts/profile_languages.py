#!/usr/bin/env python3
"""Render file-size language breakdown for public, owned, non-fork GitHub repos.

Data source: GitHub REST /users/{login}/repos and /repos/{owner}/{repo}/languages.
Uses GitHub Linguist byte counts, not commit counts or a developer skill rating.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

LOGIN = "imsayon"
API = "https://api.github.com"
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "languages-by-size.svg"

COLORS = {
    "TypeScript": "#3178c6",
    "JavaScript": "#f7df1e",
    "C++": "#72b3e1",
    "C": "#92a7ba",
    "Python": "#ffcb61",
    "HTML": "#e67c55",
    "CSS": "#5a88e5",
    "Java": "#d3a475",
    "Shell": "#80be86",
    "Go": "#57b9ca",
    "Rust": "#d29773",
    "Zig": "#f0ae6a",
    "SCSS": "#c987ad",
    "Svelte": "#f27a4f",
    "Vue": "#62bf8c",
}
OTHER = "#697c75"


def fetch_json(url: str, token: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "imsayon-profile-language-breakdown",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=25) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError) as exc:
        code = getattr(exc, "code", "network")
        raise RuntimeError(f"Could not fetch GitHub language data (HTTP {code})") from exc


def collect(token: str) -> tuple[Counter, int]:
    totals = Counter()
    checked = 0
    for page in range(1, 21):
        repos = fetch_json(
            f"{API}/users/{LOGIN}/repos?type=owner&per_page=100&page={page}", token
        )
        if not isinstance(repos, list):
            raise RuntimeError("Expected a repository list from GitHub")
        for repo in repos:
            if repo.get("owner", {}).get("login", "").lower() != LOGIN:
                continue
            if repo.get("fork") or repo.get("private"):
                continue
            language_url = repo.get("languages_url")
            if not isinstance(language_url, str) or not language_url.startswith(
                f"{API}/repos/{LOGIN}/"
            ):
                raise RuntimeError("Unexpected GitHub repository language endpoint")
            languages = fetch_json(language_url, token)
            if not isinstance(languages, dict):
                raise RuntimeError("Missing language-byte data from GitHub")
            for name, size in languages.items():
                if not isinstance(name, str) or type(size) is not int or size < 0:
                    raise RuntimeError("Invalid language-byte count")
                totals[name] += size
            checked += 1
        if len(repos) < 100:
            break
    else:
        raise RuntimeError("Repository pagination exceeded safety bound")
    if checked == 0 or sum(totals.values()) == 0:
        raise RuntimeError("No public non-fork repository language bytes returned")
    return totals, checked


def render(totals: Counter, repo_count: int, synced: str) -> str:
    if not isinstance(repo_count, int) or repo_count < 1:
        raise ValueError("Invalid repository count")
    items = sorted(totals.items(), key=lambda pair: (-pair[1], pair[0]))
    if not items or any(type(v) is not int or v < 0 for _, v in items):
        raise ValueError("Invalid language data")
    total = sum(size for _, size in items)
    if total == 0:
        raise ValueError("Empty language sizes")
    leaders = items[:7]
    other_bytes = sum(size for _, size in items[7:])
    if other_bytes:
        leaders.append(("Other", other_bytes))

    pieces, legend = [], []
    x = 40.0
    palette = []
    for index, (name, size) in enumerate(leaders):
        color = COLORS.get(name, OTHER if name == "Other" else ["#80c3a0", "#c2b487", "#bf9aa6", "#849db7"][index % 4])
        palette.append(color)
        width = 1080.0 * size / total
        if index == len(leaders) - 1:
            width = max(0.0, 1120.0 - x)
        pieces.append(
            f'<g><title>{escape(name)}: {size * 100 / total:.1f}%</title>'
            f'<rect x="{x:.2f}" y="80" width="{width:.2f}" height="21" fill="{color}"/></g>'
        )
        x += width

    for i, (name, size) in enumerate(leaders):
        col, row = i % 4, i // 4
        lx, ly = 42 + col * 275, 145 + row * 57
        pct = 100.0 * size / total
        legend.append(f'<g transform="translate({lx},{ly})">'
                      f'<circle cx="0" cy="-4" r="5" fill="{palette[i]}"/>'
                      f'<text x="16" y="0" class="name">{escape(name)}</text>'
                      f'<text x="16" y="23" class="pct">{pct:.1f}%</text></g>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1160 290" role="img" aria-labelledby="title desc">
<title id="title">Languages used by file size</title>
<desc id="desc">GitHub Linguist language bytes aggregated over {repo_count} public, owned, non-fork repositories. The chart reflects repository file sizes, not skill levels or commits.</desc>
<defs>
  <linearGradient id="background" x1="0" y1="0" x2="1" y2="1">
    <stop stop-color="#13221c"/><stop offset="1" stop-color="#0b1310"/>
  </linearGradient>
  <clipPath id="bar"><rect x="40" y="80" width="1080" height="21" rx="6"/></clipPath>
  <style>
    .mono{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}
    .name{{font-family:system-ui,Segoe UI,Arial,sans-serif;font-size:17px;font-weight:600;fill:#d2e5d8}}
    .pct{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:15px;fill:#94ac9c}}
  </style>
</defs>
<rect width="1160" height="290" rx="16" fill="url(#background)"/>
<rect x="1" y="1" width="1158" height="288" rx="15" fill="none" stroke="#345843" stroke-width="1.5"/>
<text x="40" y="37" class="mono" font-size="14" font-weight="600" letter-spacing="1.7" fill="#b6dfc5">LANGUAGES / BY FILE SIZE</text>
<text x="1120" y="37" text-anchor="end" class="mono" font-size="11" fill="#91b39f">{repo_count} PUBLIC REPOS</text>
<line x1="40" y1="62" x2="1120" y2="62" stroke="#284535" stroke-width="1.4"/>
<g clip-path="url(#bar)">{''.join(pieces)}</g>
{''.join(legend)}
<line x1="40" y1="261" x2="1120" y2="261" stroke="#284535" stroke-width="1.2"/>
<text x="40" y="279" class="mono" font-size="10" fill="#719481">GITHUB LINGUIST / PUBLIC OWNED REPOS · EXCLUDES FORKS</text>
<text x="1120" y="279" text-anchor="end" class="mono" font-size="10" fill="#719481">{escape(synced)}</text>
</svg>'''


def main():
    total, checked = collect(os.getenv("GITHUB_TOKEN", ""))
    timestamp = datetime.now(timezone.utc).strftime("%d %b %Y UTC")
    svg = render(total, checked, timestamp)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT.with_suffix(".svg.tmp")
    pending.write_text(svg, encoding="utf-8")
    pending.replace(OUTPUT)
    print(f"Generated verified language file-size chart from {checked} public repos")


if __name__ == "__main__":
    main()
