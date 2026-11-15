#!/usr/bin/env python3
"""Render self-hosted profile stats from GitHub's authenticated contribution calendar.

Requires PROFILE_STATS_TOKEN (a token for imsayon with read:user). Never logs it.
Publishes an SVG only after every GraphQL request and consistency check succeeds.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime, time, timedelta, timezone
from html import escape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

LOGIN = "imsayon"
API = "https://api.github.com/graphql"
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "engineering-dashboard.svg"
UTC = timezone.utc

IDENTITY = """query { viewer { login createdAt } }"""
CALENDAR = """query($from: DateTime!, $to: DateTime!) {
  viewer {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}"""
TOTAL_ONLY = """query($from: DateTime!, $to: DateTime!) {
  viewer {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar { totalContributions }
    }
  }
}"""


def iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def graphql(token: str, query: str, variables: dict | None = None) -> dict:
    data = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
    request = Request(
        API,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "imsayon-self-hosted-profile-stats",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError) as exc:
        code = getattr(exc, "code", "network")
        raise RuntimeError(f"GitHub GraphQL request failed (HTTP {code})") from exc
    if payload.get("errors"):
        messages = "; ".join(item.get("message", "GraphQL error") for item in payload["errors"])
        raise RuntimeError(f"GitHub GraphQL reported errors: {messages}")
    viewer = payload.get("data", {}).get("viewer")
    if not isinstance(viewer, dict):
        raise RuntimeError("GitHub GraphQL returned no authenticated viewer")
    return viewer


def calendar(viewer: dict) -> dict:
    value = viewer.get("contributionsCollection", {}).get("contributionCalendar")
    if not isinstance(value, dict) or type(value.get("totalContributions")) is not int:
        raise RuntimeError("GitHub returned a missing or malformed contribution calendar")
    if value["totalContributions"] < 0:
        raise RuntimeError("GitHub returned negative contributions")
    return value


def quarter_windows(start_year: int, today: date):
    if start_year < 2008 or start_year > today.year:
        raise ValueError("Invalid account creation year")
    year, month = start_year, 1
    while (year, month) <= (today.year, today.month):
        first = date(year, month, 1)
        next_year = year + (1 if month == 10 else 0)
        next_month = 1 if month == 10 else month + 3
        last = min(date(next_year, next_month, 1) - timedelta(days=1), today)
        if first <= last:
            yield first, last
        year, month = next_year, next_month


def parse_days(value: dict, first: date, last: date) -> dict[date, int]:
    weeks = value.get("weeks")
    if not isinstance(weeks, list):
        raise RuntimeError("GitHub returned no contribution weeks")
    result: dict[date, int] = {}
    for week in weeks:
        for entry in week.get("contributionDays", []):
            day = date.fromisoformat(entry["date"])
            count = entry["contributionCount"]
            if type(count) is not int or count < 0:
                raise RuntimeError("Invalid GitHub contribution day count")
            if first <= day <= last:
                if day in result and result[day] != count:
                    raise RuntimeError("Conflicting counts for the same calendar date")
                result[day] = count
    expected = (last - first).days + 1
    if len(result) != expected:
        raise RuntimeError(f"Incomplete contribution calendar {first}–{last}: {len(result)}/{expected} days")
    return result


def streaks(counts: dict[date, int], today: date) -> tuple[int, int]:
    cursor = today if counts.get(today, 0) > 0 else today - timedelta(days=1)
    current = 0
    while counts.get(cursor, 0) > 0:
        current += 1
        cursor -= timedelta(days=1)
    longest = run = 0
    for day in sorted(counts):
        if counts[day] > 0:
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    return current, longest


def collect(token: str, now: datetime) -> dict:
    viewer = graphql(token, IDENTITY)
    if viewer.get("login", "").lower() != LOGIN:
        raise RuntimeError(f"Token belongs to {viewer.get('login', 'unknown')}, expected {LOGIN}")
    first_year = datetime.fromisoformat(viewer["createdAt"].replace("Z", "+00:00")).year
    today = now.date()
    total = 0
    daily: dict[date, int] = {}
    for first, last in quarter_windows(first_year, today):
        start_at = datetime.combine(first, time.min, UTC)
        end_at = min(datetime.combine(last, time.max, UTC), now)
        value = calendar(graphql(token, CALENDAR, {"from": iso(start_at), "to": iso(end_at)}))
        days = parse_days(value, first, last)
        if sum(days.values()) != value["totalContributions"]:
            raise RuntimeError(f"GitHub calendar total mismatch for {first}–{last}")
        if daily.keys() & days.keys():
            raise RuntimeError("Quarter windows overlap")
        daily.update(days)
        total += value["totalContributions"]
    rolling_start = now - timedelta(days=365)
    rolling = calendar(graphql(token, TOTAL_ONLY, {"from": iso(rolling_start), "to": iso(now)}))
    current, longest = streaks(daily, today)
    return {
        "last_year": rolling["totalContributions"],
        "lifetime": total,
        "current_streak": current,
        "longest_streak": longest,
        "as_of": now.strftime("%d %b %Y · UTC"),
    }


def render(stats: dict) -> str:
    def value(key: str) -> str:
        item = stats[key]
        if type(item) is not int or item < 0:
            raise ValueError(f"Invalid numeric metric: {key}")
        return f"{item:,}"

    values = [value(key) for key in ("last_year", "lifetime", "current_streak", "longest_streak")]
    labels = ["LAST 365 DAYS", "ALL TIME", "CURRENT STREAK", "LONGEST STREAK"]
    units = ["contributions", "contributions", "days", "days"]
    lines = []
    for i, (number, label, unit) in enumerate(zip(values, labels, units)):
        x = 40 + i * 274
        lines.append(f'''<g transform="translate({x},112)">
          <text x="0" y="0" class="label">{label}</text>
          <text x="0" y="73" class="number">{number}</text>
          <text x="0" y="105" class="unit">{unit}</text>
        </g>''')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1160 270" role="img" aria-labelledby="title desc">
<title id="title">Sayon GitHub engineering activity</title>
<desc id="desc">Verified GitHub contribution calendar counts: {values[0]} in the past 365 days, {values[1]} all time, current streak {values[2]} days, longest streak {values[3]} days.</desc>
<defs>
 <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#13221c"/><stop offset="1" stop-color="#0b1310"/></linearGradient>
 <style>.mono{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}} .label{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:13px;font-weight:600;letter-spacing:2px;fill:#91bd9e}} .number{{font-family:system-ui,Segoe UI,Arial,sans-serif;font-size:53px;font-weight:700;fill:#daf1df;font-variant-numeric:tabular-nums}} .unit{{font-family:system-ui,Segoe UI,Arial,sans-serif;font-size:17px;fill:#9fb4a6}} .dot{{animation:pulse 2.6s ease-in-out infinite}} @keyframes pulse{{50%{{opacity:.4}}}} @media(prefers-reduced-motion:reduce){{.dot{{animation:none}}}}</style>
</defs>
<rect width="1160" height="270" rx="16" fill="url(#bg)"/>
<rect x="1" y="1" width="1158" height="268" rx="15" fill="none" stroke="#345843" stroke-width="1.5"/>
<path d="M40 63H1120" stroke="#284535" stroke-width="1.3"/>
<text x="40" y="37" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="14" font-weight="600" letter-spacing="1.8" fill="#b6dfc5">GITHUB / ENGINEERING ACTIVITY</text>
<circle class="dot" cx="927" cy="32" r="4.5" fill="#8fdbad"/>
<text x="942" y="37" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="11" fill="#8cba9b">API VERIFIED</text>
{''.join(lines)}
<path d="M308 93V231 M582 93V231 M856 93V231" stroke="#2c4939" stroke-width="1.5"/>
<path d="M40 240H1120" stroke="#284535" stroke-width="1.2"/>
<text x="41" y="257" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="10.5" fill="#719481">SOURCE: GITHUB CONTRIBUTION CALENDAR</text>
<text x="1118" y="257" text-anchor="end" font-family="ui-monospace,Menlo,Consolas,monospace" font-size="10.5" fill="#719481">SYNCED {escape(str(stats['as_of']))}</text>
</svg>'''


def main() -> None:
    token = os.environ.get("PROFILE_STATS_TOKEN", "").strip()
    if not token:
        raise SystemExit("Missing PROFILE_STATS_TOKEN; configure the GitHub Actions secret and rerun")
    now = datetime.now(UTC)
    result = collect(token, now)
    svg = render(result)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pending = OUTPUT.with_suffix(".svg.tmp")
    pending.write_text(svg, encoding="utf-8")
    pending.replace(OUTPUT)
    print("Verified GitHub contribution calendar and wrote self-hosted engineering dashboard")


if __name__ == "__main__":
    main()
