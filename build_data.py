"""Build site/data.json — the precomputed dataset for the static GitHub Pages site.

Scans every FBS team's 247 Crystal Ball, computes confidence tiers + momentum
+ stars/ratings (reusing scout.scan_team), and writes a single data.json that
the static frontend reads. Diffs against the previous data.json so the NEW-badge
feature survives across scheduled refreshes.

Stdlib-only (scout.py + teams.py are urllib-based, no pip needed).
"""
import json
import os
import datetime as dt

import teams
import scout

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(HERE, "docs", "data.json")

# Default watchlist for the static "shared targets" feature (powers + Miami).
DEFAULT_WATCHLIST = ["miami", "alabama", "georgia", "texas", "ohio-state", "florida-state"]

YEARS = (2027, 2028)


def load_previous():
    if not os.path.exists(DATA_PATH):
        return {}
    try:
        with open(DATA_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def prev_pick_map(prev):
    """slug -> {recruit_name: picks} from previous run."""
    out = {}
    for slug, b in (prev.get("boards") or {}).items():
        out[slug] = {r["name"]: r["picks"] for r in b.get("recruits", [])}
    return out


def main():
    os.makedirs(os.path.join(HERE, "site"), exist_ok=True)
    prev = load_previous()
    prev_picks = prev_pick_map(prev)

    boards = {}
    for name, slug in teams.FBS_TEAMS:
        try:
            _, recs = scout.scan_team(slug, years=YEARS, timeout=20)
        except Exception:
            continue
        if not recs:
            continue
        recruits = []
        new_count = 0
        pp = prev_picks.get(slug, {})
        for rname, r in sorted(recs.items(), key=lambda kv: (kv[1]["pct"], kv[1]["picks"]), reverse=True):
            is_new = (rname not in pp) or (r["picks"] > pp.get(rname, 0))
            if is_new:
                new_count += 1
            recruits.append({
                "name": rname,
                "pct": r["pct"],
                "picks": r["picks"],
                "miami": r["miami"],
                "tier": r["tier"],
                "trend_symbol": r["trend_symbol"],
                "stars": r["stars"],
                "rating": r["rating"],
                "years": r["years"],
                "new": is_new,
            })
        strength = round(sum(r["pct"] * r["picks"] for r in recs.values()) /
                         max(1, sum(r["picks"] for r in recs.values())), 1)
        boards[slug] = {
            "name": name,
            "strength": strength,
            "count": len(recs),
            "new_count": new_count,
            "recruits": recruits,
        }

    data = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "years": list(YEARS),
        "teams": teams.all_teams(),
        "boards": boards,
        "watchlist": DEFAULT_WATCHLIST,
    }
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"Wrote {DATA_PATH}: {len(boards)} team boards, "
          f"{sum(b['count'] for b in boards.values())} total recruits.")


if __name__ == "__main__":
    main()
