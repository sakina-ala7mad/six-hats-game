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

FIRST_SUBMIT_BONUS = 15


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


def _now():
    return datetime.datetime.utcnow().isoformat()


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
        # A "round" is one team scenario-mode game. It is created by a host
        # (the player who started it) and stays 'active' until every player
        # who joined it has submitted their own response.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rounds (
                round_id TEXT PRIMARY KEY,
                team_id TEXT NOT NULL,
                host_player_id TEXT NOT NULL,
                scenario_idx INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'lobby',  -- lobby | active | completed
                created_at TEXT NOT NULL,
                started_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS round_participants (
                round_id TEXT NOT NULL,
                player_id TEXT NOT NULL,
                hat TEXT NOT NULL,
                joined_at TEXT NOT NULL,
                response TEXT,
                score INTEGER,
                note TEXT,
                xp INTEGER,
                submitted INTEGER NOT NULL DEFAULT 0,
                submit_time TEXT,
                got_bonus INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (round_id, player_id)
            )
        """)


def _new_code(length=6):
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


def create_team(team_name):
    team_id = _new_code(6)
    with get_conn() as conn:
        existing = conn.execute("SELECT 1 FROM teams WHERE team_id = ?", (team_id,)).fetchone()
        while existing:
            team_id = _new_code(6)
            existing = conn.execute("SELECT 1 FROM teams WHERE team_id = ?", (team_id,)).fetchone()
        conn.execute(
            "INSERT INTO teams (team_id, team_name, total_exp, created_at) VALUES (?, ?, 0, ?)",
            (team_id, team_name, _now()),
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
    now = _now()
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
        conn.execute("UPDATE players SET last_seen = ? WHERE player_id = ?", (_now(), player_id))


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
            (new_exp, new_level, _now(), player_id),
        )
        if mode == "team" and player["team_id"]:
            conn.execute(
                "UPDATE teams SET total_exp = MAX(0, total_exp + ?) WHERE team_id = ?",
                (delta, player["team_id"]),
            )
        conn.execute(
            "INSERT INTO sessions (player_id, team_id, mode, submode, score, exp_gained, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (player_id, player["team_id"], mode, submode, score, delta, _now()),
        )


def leaderboard_teams(limit=20):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT team_id, team_name, total_exp FROM teams ORDER BY total_exp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def leaderboard_individual_players(limit=20):
    """Players who are not on any team, ranked by their own XP."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT player_id, name, exp, level FROM players "
            "WHERE team_id IS NULL ORDER BY exp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def leaderboard_team_members(limit=50):
    """Players who belong to a team, ranked by their own XP, with team name."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT p.player_id, p.name, p.exp, p.level, t.team_name "
            "FROM players p JOIN teams t ON p.team_id = t.team_id "
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


# ---------------------------------------------------------------------------
# TEAM SCENARIO ROUNDS (host starts a round, teammates join, everyone must
# submit before results are revealed; the first submitter gets a personal
# speed bonus that does NOT count toward the team total).
# ---------------------------------------------------------------------------
def create_round(team_id, host_player_id, scenario_idx):
    """Create a new round in the 'lobby' phase. Teammates can join while it's
    in lobby; the host then explicitly starts it (see start_round)."""
    round_id = str(uuid.uuid4())[:8]
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO rounds (round_id, team_id, host_player_id, scenario_idx, status, created_at) "
            "VALUES (?, ?, ?, ?, 'lobby', ?)",
            (round_id, team_id, host_player_id, scenario_idx, _now()),
        )
    return round_id


def get_current_round(team_id):
    """The team's in-progress round, whether still in the lobby or already
    active. Returns None once it's completed (or if none exists)."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM rounds WHERE team_id = ? AND status IN ('lobby', 'active') "
            "ORDER BY created_at DESC LIMIT 1",
            (team_id,),
        ).fetchone()
        return dict(row) if row else None


def get_round(round_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM rounds WHERE round_id = ?", (round_id,)).fetchone()
        return dict(row) if row else None


def start_round(round_id):
    """Host action: close the lobby and begin the answering phase for
    everyone who has joined so far. Timing is measured from this moment,
    server-side, so it's fair across everyone's browser."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE rounds SET status = 'active', started_at = ? WHERE round_id = ? AND status = 'lobby'",
            (_now(), round_id),
        )


def join_round(round_id, player_id, hat):
    """Join a round while it's still in the lobby. Returns the participant
    row, or None if the round has already started (too late to join)."""
    round_row = get_round(round_id)
    if not round_row:
        return None
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT * FROM round_participants WHERE round_id = ? AND player_id = ?",
            (round_id, player_id),
        ).fetchone()
        if existing:
            return dict(existing)
        if round_row["status"] != "lobby":
            return None
        conn.execute(
            "INSERT INTO round_participants (round_id, player_id, hat, joined_at, submitted) "
            "VALUES (?, ?, ?, ?, 0)",
            (round_id, player_id, hat, _now()),
        )
        row = conn.execute(
            "SELECT * FROM round_participants WHERE round_id = ? AND player_id = ?",
            (round_id, player_id),
        ).fetchone()
        return dict(row)


def get_participant(round_id, player_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM round_participants WHERE round_id = ? AND player_id = ?",
            (round_id, player_id),
        ).fetchone()
        return dict(row) if row else None


def round_participants_list(round_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT rp.*, p.name AS player_name FROM round_participants rp "
            "JOIN players p ON rp.player_id = p.player_id "
            "WHERE rp.round_id = ? ORDER BY rp.joined_at ASC",
            (round_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def submit_round_answer(round_id, player_id, response, score, note, xp):
    """Record one player's answer and add their XP to both them and their team."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE round_participants SET response = ?, score = ?, note = ?, xp = ?, "
            "submitted = 1, submit_time = ? WHERE round_id = ? AND player_id = ?",
            (response, score, note, xp, _now(), round_id, player_id),
        )
    add_exp(player_id, xp, "team", "scenario", score)


def all_submitted(round_id):
    with get_conn() as conn:
        total = conn.execute(
            "SELECT COUNT(*) c FROM round_participants WHERE round_id = ?", (round_id,)
        ).fetchone()["c"]
        submitted = conn.execute(
            "SELECT COUNT(*) c FROM round_participants WHERE round_id = ? AND submitted = 1",
            (round_id,),
        ).fetchone()["c"]
        return total > 0 and total == submitted


def finalize_round_if_ready(round_id):
    """If everyone has submitted and the round isn't finalized yet: give the
    first submitter their personal speed bonus (NOT added to the team total)
    and mark the round completed. Safe to call repeatedly."""
    round_row = get_round(round_id)
    if not round_row or round_row["status"] == "completed":
        return False
    if not all_submitted(round_id):
        return False
    participants = round_participants_list(round_id)
    first = min(participants, key=lambda p: p["submit_time"])
    with get_conn() as conn:
        conn.execute(
            "UPDATE round_participants SET got_bonus = 1 WHERE round_id = ? AND player_id = ?",
            (round_id, first["player_id"]),
        )
        conn.execute("UPDATE rounds SET status = 'completed' WHERE round_id = ?", (round_id,))
    add_exp(first["player_id"], FIRST_SUBMIT_BONUS, "individual", "scenario", 0)
    return True
