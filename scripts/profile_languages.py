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
    """Create eight proportional horizontal bars using actual GitHub Linguist bytes."""
    if type(repo_count) is not int or repo_count < 1:
        raise ValueError("Invalid repository count")
    items = sorted(totals.items(), key=lambda pair: (-pair[1], pair[0]))
    if not items or any(type(size) is not int or size < 0 for _, size in items):
        raise ValueError("Invalid language data")
    total = sum(size for _, size in items)
    if total <= 0:
        raise ValueError("Empty language sizes")

    leaders = items[:7]
    remainder = sum(size for _, size in items[7:])
    if remainder:
        leaders.append(("Other", remainder))

    rows = []
    for index, (name, size) in enumerate(leaders):
        pct = 100.0 * size / total
        track_width = 305.0
        colored_width = track_width * size / total
        y = 91 + index * 30
        color = COLORS.get(
            name,
            OTHER if name == "Other" else
            ["#80c3a0", "#c2b487", "#bf9aa6", "#849db7"][index % 4],
        )
        rows.append(
            f'<g><title>{escape(name)}: {pct:.1f}%</title>'
            f'<text x="25" y="{y + 5}" class="name">{escape(name)}</text>'
            f'<rect x="143" y="{y - 6}" width="{track_width:.1f}" height="12" rx="6" fill="#353B39"/>'
            f'<rect x="143" y="{y - 6}" width="{colored_width:.2f}" height="12" '
            f'rx="{min(6.0, colored_width / 2):.2f}" fill="{color}"/>'
            f'<text x="535" y="{y + 5}" text-anchor="end" class="pct">{pct:.1f}%</text></g>'
        )

    template_path = OUTPUT.parent / "templates" / "languages-compact.svg"
    result = template_path.read_text(encoding="utf-8")
    substitutions = {
        "{{REPO_COUNT}}": str(repo_count),
        "{{ROWS}}": "\n".join(rows),
        "{{SYNCED}}": escape(synced),
    }
    for marker, replacement in substitutions.items():
        if marker not in result:
            raise RuntimeError(f"Missing language template marker: {marker}")
        result = result.replace(marker, replacement)
    return result


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
