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
    """Render the compact, verified activity dashboard using its SVG template."""
    values = {}
    for key in ("last_year", "lifetime", "current_streak", "longest_streak"):
        number = stats[key]
        if type(number) is not int or number < 0:
            raise ValueError(f"Invalid numeric metric: {key}")
        values[key] = f"{number:,}"

    substitutions = {
        "{{LAST_YEAR}}": values["last_year"],
        "{{LIFETIME}}": values["lifetime"],
        "{{CURRENT}}": values["current_streak"],
        "{{LONGEST}}": values["longest_streak"],
        "{{SYNCED}}": escape(str(stats["as_of"])),
    }
    template_path = OUTPUT.parent / "templates" / "activity-compact.svg"
    result = template_path.read_text(encoding="utf-8")
    for marker, replacement in substitutions.items():
        if marker not in result:
            raise RuntimeError(f"Missing activity template marker: {marker}")
        result = result.replace(marker, replacement)
    return result


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
