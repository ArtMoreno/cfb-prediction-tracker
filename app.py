"""CFB Prediction Tracker — Flask web app (hosting-ready).

Run locally:   python app.py   ->  http://localhost:5000
Hosted:        gunicorn app:app  (PORT + DATABASE_PATH from env)

Endpoints:
  GET  /               team picker + watchlist + recent feed
  GET  /api/teams      JSON list of all FBS teams
  POST /api/scan       {slug, years?} -> live scan, badges NEW vs stored state
  GET  /api/watchlist  list
  POST /api/watch       {slug, name} add
  DEL  /api/watch/<slug> remove
  POST /api/scan-watch scan every team in the watchlist, aggregate NEW picks
"""

import os
import json
import datetime as dt

from flask import Flask, request, jsonify, render_template

import teams
import scout
import store

store.init()
app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html", teams=teams.all_teams())


@app.route("/api/teams")
def api_teams():
    return jsonify(teams.all_teams())


@app.route("/api/scan", methods=["POST"])
def api_scan():
    data = request.get_json(force=True, silent=True) or {}
    slug = data.get("slug")
    if not slug:
        return jsonify({"error": "slug required"}), 400
    years = tuple(int(y) for y in data.get("years", [2027, 2028, 2029]))
    try:
        preds, recs = scout.scan_team(slug, years=years)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    seen = store.seen_keys(slug)
    new = []
    for r in preds:
        k = store.key_for(r)
        if k not in seen:
            new.append(k)
    # mark all as seen now (caller already got the NEW set)
    if new:
        store.mark_seen(slug, new)

    ranked = sorted(recs.items(), key=lambda kv: (kv[1]["pct"], kv[1]["miami"]), reverse=True)
    return jsonify({
        "slug": slug,
        "team_name": teams.team_by_slug(slug),
        "count": len(preds),
        "new_count": len(new),
        "predictions": preds,
        "recruits": [
            {"name": n, "pct": v["pct"], "miami": v["miami"],
             "picks": v["picks"], "years": v["years"],
             "tier": v["tier"], "tier_color": v["tier_color"],
             "trend": v["trend"], "trend_symbol": v["trend_symbol"],
             "stars": v["stars"], "rating": v["rating"],
             "latest_school": v["latest"]["school"] if v["latest"] else None}
            for n, v in ranked
        ],
        "scanned_at": dt.datetime.now().isoformat(timespec="seconds"),
    })


@app.route("/api/watchlist")
def api_watchlist():
    return jsonify(store.watchlist())


@app.route("/api/watch", methods=["POST"])
def api_watch_add():
    data = request.get_json(force=True, silent=True) or {}
    slug, name = data.get("slug"), data.get("name")
    if not slug or not name:
        return jsonify({"error": "slug and name required"}), 400
    store.watch_add(slug, name)
    return jsonify(store.watchlist())


@app.route("/api/watch/<slug>", methods=["DELETE"])
def api_watch_del(slug):
    store.watch_remove(slug)
    return jsonify(store.watchlist())


@app.route("/api/scan-watch", methods=["POST"])
def api_scan_watch():
    data = request.get_json(force=True, silent=True) or {}
    years = tuple(int(y) for y in data.get("years", [2027, 2028, 2029]))
    results = []
    for w in store.watchlist():
        slug = w["slug"]
        try:
            preds, _ = scout.scan_team(slug, years=years, timeout=20)
        except Exception:
            continue
        seen = store.seen_keys(slug)
        fresh = [r for r in preds if store.key_for(r) not in seen]
        if fresh:
            store.mark_seen(slug, [store.key_for(r) for r in fresh])
        results.append({
            "slug": slug, "team_name": w["name"],
            "new": [{"name": r["name"], "school": r["school"],
                      "analyst": r["analyst"], "date": r["date"]} for r in fresh],
            "total": len(preds),
        })
    total_new = sum(len(r["new"]) for r in results)
    return jsonify({"results": results, "total_new": total_new,
                    "scanned_at": dt.datetime.now().isoformat(timespec="seconds")})


@app.route("/api/contested", methods=["POST"])
def api_contested():
    """Contested targets across the whole watchlist (auto cross-reference)."""
    data = request.get_json(force=True, silent=True) or {}
    years = tuple(int(y) for y in data.get("years", [2027, 2028, 2029]))
    slugs = [w["slug"] for w in store.watchlist()]
    if not slugs:
        return jsonify({"shared": [], "boards": {}, "teams": 0})
    try:
        res = scout.compare_boards(slugs, years=years)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    names = {w["slug"]: w["name"] for w in store.watchlist()}
    for slug, b in res["boards"].items():
        b["name"] = names.get(slug, teams.team_by_slug(slug))
    for c in res["shared"]:
        c["leader_name"] = names.get(c["leader"], c["leader"])
        for t in c["teams"]:
            t["team_name"] = names.get(t["slug"], t["slug"])
    return jsonify({"shared": res["shared"], "boards": res["boards"],
                    "teams": len(slugs),
                    "scanned_at": dt.datetime.now().isoformat(timespec="seconds")})


@app.route("/api/rivals", methods=["POST"])
def api_rivals():
    """Explicit A-vs-B (or A-vs-B-vs-C) head-to-head board comparison."""
    data = request.get_json(force=True, silent=True) or {}
    slugs = data.get("slugs") or []
    if len(slugs) < 2:
        return jsonify({"error": "provide at least 2 slugs"}), 400
    years = tuple(int(y) for y in data.get("years", [2027, 2028, 2029]))
    try:
        res = scout.compare_boards(slugs, years=years)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    names = {w["slug"]: w["name"] for w in store.watchlist()}
    for slug, b in res["boards"].items():
        b["name"] = names.get(slug, teams.team_by_slug(slug))
    for c in res["shared"]:
        c["leader_name"] = names.get(c["leader"], c["leader"])
        for t in c["teams"]:
            t["team_name"] = names.get(t["slug"], t["slug"])
    return jsonify({"shared": res["shared"], "boards": res["boards"],
                    "scanned_at": dt.datetime.now().isoformat(timespec="seconds")})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
