"""SQLite state store — hosting-ready.

The DB path comes from env DATABASE_PATH (default ./state/predictions.db).
On a host you'd point DATABASE_PATH at a mounted volume (or swap this module
for Postgres — the API surface (seen_keys, mark_seen, watchlist_*) stays
the same, so app.py never changes).

State tracked:
  - seen 247 predictions per team (so we can badge NEW ones)
  - a watchlist of team slugs (default: miami)
"""

import os
import sqlite3
import json
import datetime as dt

DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "state", "predictions.db"))


def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.execute("PRAGMA journal_mode=WAL;")
    return c


def init():
    c = _conn()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS seen (
            team_slug TEXT,
            key TEXT,
            PRIMARY KEY (team_slug, key)
        );
        CREATE TABLE IF NOT EXISTS watchlist (
            team_slug TEXT PRIMARY KEY,
            team_name TEXT
        );
    """)
    # seed default watchlist
    c.execute("INSERT OR IGNORE INTO watchlist(team_slug, team_name) VALUES ('miami','Miami')")
    c.commit()
    c.close()


def seen_keys(team_slug):
    c = _conn()
    rows = c.execute("SELECT key FROM seen WHERE team_slug=?", (team_slug,)).fetchall()
    c.close()
    return set(r[0] for r in rows)


def mark_seen(team_slug, keys):
    c = _conn()
    c.executemany("INSERT OR IGNORE INTO seen(team_slug, key) VALUES (?,?)",
                   [(team_slug, k) for k in keys])
    c.commit()
    c.close()


def watchlist():
    c = _conn()
    rows = c.execute("SELECT team_slug, team_name FROM watchlist ORDER BY team_name").fetchall()
    c.close()
    return [{"slug": s, "name": n} for s, n in rows]


def watch_add(slug, name):
    c = _conn()
    c.execute("INSERT OR IGNORE INTO watchlist(team_slug, team_name) VALUES (?,?)", (slug, name))
    c.commit()
    c.close()


def watch_remove(slug):
    c = _conn()
    c.execute("DELETE FROM watchlist WHERE team_slug=?", (slug,))
    c.execute("DELETE FROM seen WHERE team_slug=?", (slug,))
    c.commit()
    c.close()


def key_for(r):
    return f"{r['name']}|{r['analyst']}|{r['date']}|{r['school']}"
