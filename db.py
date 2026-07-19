"""
db.py — persistence layer for the Six Hats Game.

Uses a local SQLite file (sixhats.db) so scores survive page refreshes and
new browser sessions as long as the app process is alive. See README.md
for notes on making this survive redeploys on Streamlit Community Cloud.
"""

import sqlite3
import uuid
import string
import random
import datetime
from contextlib import contextmanager

DB_PATH = "sixhats.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                team_id TEXT PRIMARY KEY,
                team_name TEXT UNIQUE NOT NULL,
                total_exp INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS players (
                player_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                team_id TEXT,
                exp INTEGER NOT NULL DEFAULT 0,
                level INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                FOREIGN KEY (team_id) REFERENCES teams(team_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                team_id TEXT,
                mode TEXT NOT NULL,        -- 'individual' or 'team'
                submode TEXT NOT NULL,     -- 'puzzle' or 'scenario'
                score INTEGER NOT NULL,
                exp_gained INTEGER NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)


def _new_code(length=6):
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


def create_team(team_name):
    team_id = _new_code(6)
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT * FROM teams WHERE team_id = ?", (team_id,)
        ).fetchone()
        while existing:
            team_id = _new_code(6)
            existing = conn.execute(
                "SELECT * FROM teams WHERE team_id = ?", (team_id,)
            ).fetchone()
        conn.execute(
            "INSERT INTO teams (team_id, team_name, total_exp, created_at) VALUES (?, ?, 0, ?)",
            (team_id, team_name, datetime.datetime.utcnow().isoformat()),
        )
    return team_id


def get_team_by_id(team_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM teams WHERE team_id = ?", (team_id,)).fetchone()
        return dict(row) if row else None


def get_team_by_name(team_name):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM teams WHERE lower(team_name) = lower(?)", (team_name,)
        ).fetchone()
        return dict(row) if row else None


def create_player(name, team_id=None):
    player_id = str(uuid.uuid4())[:8]
    now = datetime.datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO players (player_id, name, team_id, exp, level, created_at, last_seen) "
            "VALUES (?, ?, ?, 0, 1, ?, ?)",
            (player_id, name, team_id, now, now),
        )
    return player_id


def get_player(player_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM players WHERE player_id = ?", (player_id,)).fetchone()
        return dict(row) if row else None


def find_player_by_name(name, team_id=None):
    with get_conn() as conn:
        if team_id:
            row = conn.execute(
                "SELECT * FROM players WHERE lower(name) = lower(?) AND team_id = ?",
                (name, team_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM players WHERE lower(name) = lower(?) AND team_id IS NULL",
                (name,),
            ).fetchone()
        return dict(row) if row else None


def touch_player(player_id):
    with get_conn() as conn:
        conn.execute(
            "UPDATE players SET last_seen = ? WHERE player_id = ?",
            (datetime.datetime.utcnow().isoformat(), player_id),
        )


def level_from_exp(exp):
    return max(1, exp // 100 + 1)


def add_exp(player_id, delta, mode, submode, score):
    """Apply exp change to a player (and their team, if in team mode)."""
    with get_conn() as conn:
        player = conn.execute("SELECT * FROM players WHERE player_id = ?", (player_id,)).fetchone()
        if not player:
            return
        new_exp = max(0, player["exp"] + delta)
        new_level = level_from_exp(new_exp)
        conn.execute(
            "UPDATE players SET exp = ?, level = ?, last_seen = ? WHERE player_id = ?",
            (new_exp, new_level, datetime.datetime.utcnow().isoformat(), player_id),
        )
        if mode == "team" and player["team_id"]:
            conn.execute(
                "UPDATE teams SET total_exp = MAX(0, total_exp + ?) WHERE team_id = ?",
                (delta, player["team_id"]),
            )
        conn.execute(
            "INSERT INTO sessions (player_id, team_id, mode, submode, score, exp_gained, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                player_id,
                player["team_id"],
                mode,
                submode,
                score,
                delta,
                datetime.datetime.utcnow().isoformat(),
            ),
        )


def leaderboard_teams(limit=20):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT team_id, team_name, total_exp FROM teams ORDER BY total_exp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def leaderboard_players(limit=20):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT p.player_id, p.name, p.exp, p.level, t.team_name "
            "FROM players p LEFT JOIN teams t ON p.team_id = t.team_id "
            "ORDER BY p.exp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def team_members(team_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM players WHERE team_id = ? ORDER BY exp DESC", (team_id,)
        ).fetchall()
        return [dict(r) for r in rows]
