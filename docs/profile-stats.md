# Self-hosted GitHub contribution dashboard

The profile displays `assets/engineering-dashboard.svg`. The data is fetched using the authenticated GitHub GraphQL **viewer contribution calendar**, not a third-party stats widget. Private repository names, commit details, and tokens are never printed into the image. A secret with access to the account's private contribution counts is required.

## One-time setup

1. Create a **classic** Personal Access Token under https://github.com/settings/tokens with `read:user` only. Set an expiration and rotate it before expiry. Do **not** grant broad `repo` access.
2. In this repository, open **Settings → Secrets and variables → Actions → New repository secret**. Name it exactly `PROFILE_STATS_TOKEN` and paste the token value. Never put it in a file, a commit, or chat.
3. Open **Actions → Verify and render profile contributions → Run workflow** on `main`. The job verifies the token belongs to `imsayon`, loads the calendar in three-month windows, checks day totals, generates the SVG and commits it to `assets/engineering-dashboard.svg`.
4. Compare the displayed `Last 365 days` count with your native GitHub profile graph. Small differences can occur near a rolling-date boundary or because GitHub's public-profile visibility settings differ; do not present mismatched counts as identical.

The job runs daily at 05:19 UTC. If the token is missing, it preserves the existing SVG and logs a warning. If an API request fails or returns incomplete data, the generator exits without overwriting the last successfully generated SVG. The README never embeds the token or private repository names.

`Last 365 days` is the official `contributionCalendar.totalContributions` queried over a rolling 365-day period. `All time` is the sum of quarterly GitHub contribution calendar totals since the account creation year. Streaks use non-zero daily counts across those quarterly calendars. A missing today does not end an ongoing streak if yesterday was active.

Tests: `python -m unittest discover -s scripts -p 'test_profile_stats.py' -v`

**Privacy:** Because the result is a README image, its aggregate numbers will be visible to profile visitors after the repository is published. The image deliberately does not reveal which private repositories contributed to them.
