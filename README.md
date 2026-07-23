# 🏈 CFB Prediction Tracker

A free, public web app that tracks **247Sports Crystal Ball** predictions for every FBS football team — confidence tiers, momentum, star ratings, a 2-team board-comparison with strength gauges, and a trending carousel.

Built as a **static site on GitHub Pages** — no server, no cost. A GitHub Action scrapes 247 on a schedule (every 3 hours) and commits the precomputed `site/data.json`; the page reads that JSON and renders entirely in the browser.

## What it shows
- **Scan a team** — pick any FBS team → leaderboard with Miami/team lean %, confidence tier (Locked/Strong/Soft/Toss-up/Fading/Lost), momentum arrow, stars + composite, paginated.
- **Watchlist shared targets** — recruits genuinely predicted to 2+ of the default powers.
- **Rival board comparison** — pick Team A vs B → side-by-side boards, bounded strength gauges (warning/critical thresholds), shared-target detection.
- **Trending carousel** — top recruits from the last team you viewed.

## Architecture
- `scout.py` — 247 Crystal Ball scraper (stdlib `urllib` only; 247 rejects `requests` with 406).
- `teams.py` — FBS team directory (slug → name).
- `build_data.py` — scans all teams, writes `site/data.json` (run by the Action).
- `site/index.html` — the static UI (reads `data.json`, no backend).
- `.github/workflows/refresh.yml` — scheduled scraper → commits `data.json`.

## Local dev
```bash
python build_data.py        # regenerate docs/data.json
# then open docs/index.html (or serve the folder)
python -m http.server -d docs 8000
```

## Notes / honest scope
- 247's per-team Crystal Ball lists only recruits predicted *to that team*, so "shared/contested" recruits are rare (247 exposes no national feed). That's truthful, not a bug.
- **CanesInsight** is Miami-only and is intentionally **not** in this multi-team build. ESPN/On3 recruiting APIs are login-walled / nonexistent and are not scraped.
- Data refreshes on the schedule, not in real time — "Scan" reads the latest `data.json`.

Data source: 247Sports.com (public pages). This project is not affiliated with 247Sports.
