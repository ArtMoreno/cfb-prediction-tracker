"""247Sports Crystal Ball scout — parameterized by team slug + years.

Pure scraping/parsing: no file or DB I/O. The Flask app owns persistence
(state store) so this module stays hosting-agnostic and testable.

Verified 2026-07-23: 247 serves plain HTML (no JS wall) when given a full
browser header set WITH Accept-Encoding: identity. The requests library is
rejected (HTTP 406), so we use stdlib urllib.
"""

import re
import html
import urllib.request
import datetime as dt
from collections import defaultdict

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,*/*;q=0.8"),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",  # 247 rejects gzip from Python with HTTP 406
}


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


_CRYSTAL_RE = re.compile(
    r'<li class="name">\s*<a[^>]*>([^<]+)<span>([^<]*)</span>.*?</a>.*?'
    r'<li class="predicted-by">.*?alt="([^"]+)".*?<span>([^<]+)</span>.*?</li>.*?'
    r'<li class="prediction">\s*<div>\s*<img alt="([^"]+)".*?'
    r'<span class="prediction-date">([^<]+)</span>',
    re.S,
)


def parse_crystal(html_text):
    rows = []
    for name, yr, analyst, title, school, date in _CRYSTAL_RE.findall(html_text):
        name = html.unescape(name).strip()
        school = html.unescape(school).strip()
        date = date.strip()
        rows.append({
            "name": name,
            "year": yr.strip("() "),
            "analyst": analyst,
            "school": school,
            "date": date,
            "dt": _parse_date(date),
        })
    return rows


def _parse_date(s):
    for fmt in ("%m/%d/%y %I:%M%p", "%m/%d/%Y %I:%M%p", "%m/%d/%y %H:%M", "%m/%d/%Y %H:%M"):
        try:
            return dt.datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    return None


def parse_ratings(txt):
    """Extract per-recruit stars + composite from the CB page markup.

    Each recruit is an <li class="name"> block containing the player link,
    position, and a <span class="ranking"> with icon-starsolid (yellow=filled,
    lightgrey=empty) followed by the composite score in <b>. Returns
    {normalized_name: {"stars": int, "rating": float|None}}.
    """
    out = {}
    for block in re.split(r'(?=<li class="name">)', txt):
        if 'class="name"' not in block[:40]:
            continue
        nm = re.search(r'/player/[^"]+">([^<]+)<', block)
        if not nm:
            continue
        name = re.sub(r"\s+", " ", nm.group(1)).strip()
        sy = len(re.findall(r'icon-starsolid yellow', block))
        sg = len(re.findall(r'icon-starsolid lightgrey', block))
        stars = sy + sg
        rt = re.search(r'class="ranking">.*?<b>([\d.]+)</b>', block, re.S)
        rating = float(rt.group(1)) if rt else None
        out[_norm(name)] = {"stars": stars, "rating": rating}
    return out


def scan_team(slug, years=(2027, 2028, 2029), timeout=25, momentum_days=90):
    """Return (predictions, recruits) for one team across the given years.

    predictions: list of row dicts (see parse_crystal).
    recruits: name -> {picks, miami, pct, latest, years(set), picks_detail,
                        tier, tier_color, trend, trend_symbol, stars, rating}.
    On any fetch failure for a year, that year is skipped (graceful).
    """
    predictions = []
    ratings_by_year = {}
    for yr in years:
        url = (f"https://247sports.com/college/{slug}/"
                f"Season/{yr}-Football/currenttargetpredictions/")
        try:
            txt = fetch(url, timeout=timeout)
        except Exception:
            continue
        rows = parse_crystal(txt)
        ratings_by_year[str(yr)] = parse_ratings(txt)
        for r in rows:
            r["class"] = yr
            r["team_slug"] = slug
            predictions.append(r)

    recruits = defaultdict(lambda: {"picks": 0, "miami": 0, "latest": None,
                                    "years": set(), "picks_detail": [],
                                    "stars": 0, "rating": None})
    for r in predictions:
        rec = recruits[r["name"]]
        rec["picks"] += 1
        rec["years"].add(r["year"])
        is_miami = _norm(r["school"]) == _norm(slug)
        if is_miami:
            rec["miami"] += 1
        rec["picks_detail"].append((r["dt"], is_miami))
        # carry stars/rating from this year's page (first one wins)
        yr_ratings = ratings_by_year.get(str(r["year"]), {})
        rinfo = yr_ratings.get(_norm(r["name"]))
        if rinfo:
            if not rec["stars"]:
                rec["stars"] = rinfo["stars"]
            if rec["rating"] is None:
                rec["rating"] = rinfo["rating"]
        if rec["latest"] is None or (r["dt"] and (rec["latest"]["dt"] is None or r["dt"] > rec["latest"]["dt"])):
            rec["latest"] = r

    now = dt.datetime.now()
    cutoff = now - dt.timedelta(days=momentum_days)
    out = {}
    for name, rec in recruits.items():
        pct = round(100.0 * rec["miami"] / rec["picks"], 1) if rec["picks"] else 0.0
        rec["pct"] = pct
        rec["years"] = sorted(rec["years"])
        # --- confidence tier ---
        rec["tier"], rec["tier_color"] = _tier(pct, rec["picks"], rec["miami"])
        # --- momentum: recent window vs older ---
        recent = [m for (d, m) in rec["picks_detail"] if d and d >= cutoff]
        older = [m for (d, m) in rec["picks_detail"] if d and d < cutoff]
        rec_recent = sum(1 for m in recent if m)
        rec_older = sum(1 for m in older if m)
        rec_n, old_n = len(recent), len(older)
        rec_pct = (100.0 * rec_recent / rec_n) if rec_n else None
        old_pct = (100.0 * rec_older / old_n) if old_n else None
        rec["trend"], rec["trend_symbol"] = _trend(rec_pct, old_pct, rec_n, old_n)
        out[name] = rec
    return predictions, out


def _tier(pct, picks, miami):
    """Confidence tier from Miami share + volume."""
    if picks >= 5 and pct >= 80:
        return "Locked", "#16a34a"
    if picks >= 4 and pct >= 60:
        return "Strong", "#1ec35a"
    if pct > 50:
        return "Soft", "#f59e0b"
    if pct == 50 or (picks > 0 and 0 < pct < 50):
        # split board if exactly 50, else Miami losing but contested
        return ("Toss-up", "#eab308") if pct == 50 else ("Fading", "#ef4444")
    if pct == 0:
        return "Lost", "#ef4444"
    return "Soft", "#f59e0b"


def _trend(rec_pct, old_pct, rec_n, old_n):
    """Momentum arrow. Needs enough recent signal to be meaningful."""
    if rec_n == 0:
        return "steady", "▬"
    if old_n == 0:
        # all picks recent -> trend reflects current lean direction
        return ("up" if rec_pct and rec_pct >= 60 else "steady"), ("▲" if rec_pct and rec_pct >= 60 else "▬")
    if rec_pct is None or old_pct is None:
        return "steady", "▬"
    diff = rec_pct - old_pct
    if diff >= 20:
        return "up", "▲"
    if diff <= -20:
        return "down", "▼"
    return "steady", "▬"


def _norm(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())


def compare_boards(slugs, years=(2027, 2028, 2029), timeout=20):
    """Side-by-side board comparison for 2+ teams (rival head-to-head).

    For each team we already have the full prediction board (recruit, lean %,
    picks, tier, trend). We return:
      - per-team ranked recruit lists (top by lean then picks)
      - a board-strength score = sum(lean_pct * picks) normalized to 0-100
        across the compared teams (who's "winning the cycle" on paper)
      - shared recruits: those genuinely predicted to 2+ of the teams
        (analysts picked the same kid for both) -- 247 never shows this.

    Star/composite ratings are NOT reliably inline on 247's CB pages, so we
    deliberately omit them rather than fake them.
    """
    per_team = {}
    for slug in slugs:
        try:
            _, recs = scan_team(slug, years=years, timeout=timeout)
        except Exception:
            continue
        per_team[slug] = recs

    boards = {}
    for slug, recs in per_team.items():
        ranked = sorted(recs.values(),
                        key=lambda r: (r["pct"], r["picks"]), reverse=True)
        strength = sum(r["pct"] * r["picks"] for r in recs.values())
        n = sum(r["picks"] for r in recs.values()) or 1
        boards[slug] = {
            "slug": slug,
            "recruits": [
                {"name": n0, "pct": r["pct"], "picks": r["picks"],
                 "tier": r["tier"], "trend": r["trend_symbol"],
                 "years": r["years"], "stars": r["stars"], "rating": r["rating"]}
                for n0, r in ((k, v) for k, v in
                              sorted(recs.items(), key=lambda kv: (kv[1]["pct"], kv[1]["picks"]), reverse=True))
            ],
            "count": len(recs),
            "strength": round(strength / n, 1),  # avg weighted lean
        }

    # shared recruits (genuine overlaps)
    by_recruit = defaultdict(dict)
    for slug, recs in per_team.items():
        for name, rec in recs.items():
            by_recruit[_norm(name)][slug] = {
                "slug": slug, "name": name, "pct": rec["pct"],
                "picks": rec["picks"], "tier": rec["tier"],
            }
    shared = []
    for norm, tmap in by_recruit.items():
        if len(tmap) < 2:
            continue
        teams = sorted(tmap.values(), key=lambda t: t["pct"], reverse=True)
        shared.append({
            "name": teams[0]["name"],
            "teams": teams,
            "leader": teams[0]["slug"],
            "team_count": len(teams),
        })
    shared.sort(key=lambda c: c["team_count"], reverse=True)
    return {"boards": boards, "shared": shared}
