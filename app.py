import time
import random
import streamlit as st

import db
from content import HATS, HAT_ORDER, PUZZLE_SCENARIOS, SCENARIO_PROMPTS
from styles import inject_css, PALETTE

st.set_page_config(page_title="Six Hats Game", page_icon="🎩", layout="centered")

db.init_db()

# ---------------------------------------------------------------------------
# SESSION STATE INIT
# ---------------------------------------------------------------------------
defaults = {
    "player_id": None,
    "dark_mode": True,
    "screen": "login",
    "intro_seen": False,
    "mode": None,       # 'individual' | 'team'
    "submode": None,    # 'puzzle' | 'scenario'
    "puzzle_scn": None,
    "puzzle_start": None,
    "scenario_prompt": None,
    "scenario_hat": None,
    "scenario_start": None,
    "last_result": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# try to restore login from URL query params (?pid=...)
qp = st.query_params
if st.session_state.player_id is None and "pid" in qp:
    p = db.get_player(qp["pid"])
    if p:
        st.session_state.player_id = p["player_id"]
        st.session_state.screen = "menu" if st.session_state.intro_seen else "intro"

st.markdown(inject_css(st.session_state.dark_mode), unsafe_allow_html=True)


def hat_pill(hat_name, size="normal"):
    h = HATS[hat_name]
    pad = "0.35rem 0.9rem" if size == "normal" else "0.2rem 0.6rem"
    return (
        f'<span class="hc-pill" style="background-color:{h["color"]};'
        f'color:{h["text_on"]};padding:{pad};">🎩 {hat_name} — {h["tagline"]}</span>'
    )


def current_player():
    if st.session_state.player_id:
        return db.get_player(st.session_state.player_id)
    return None


# ---------------------------------------------------------------------------
# SIDEBAR (shown once logged in)
# ---------------------------------------------------------------------------
def render_sidebar():
    p = current_player()
    with st.sidebar:
        st.markdown("### 🎩 Six Hats Game")
        if p:
            team = db.get_team_by_id(p["team_id"]) if p["team_id"] else None
            st.markdown(f"**{p['name']}**")
            st.markdown(f"Level **{p['level']}** · {p['exp']} XP")
            if team:
                st.markdown(f"Team: **{team['team_name']}**  \nCode: `{team['team_id']}`")
            else:
                st.markdown("_Playing individually_")
            st.progress(min(1.0, (p["exp"] % 100) / 100))
            st.divider()
            if st.button("🏠 Main Menu", use_container_width=True):
                st.session_state.screen = "menu"
                st.rerun()
            if st.button("🏆 Dashboard", use_container_width=True):
                st.session_state.screen = "dashboard"
                st.rerun()
            if st.button("🚪 Log out", use_container_width=True):
                st.query_params.clear()
                for k in defaults:
                    st.session_state[k] = defaults[k]
                st.rerun()
        st.divider()
        st.session_state.dark_mode = st.toggle("🌙 Dark theme", value=st.session_state.dark_mode)


# ---------------------------------------------------------------------------
# LOGIN / TEAM CREATE-JOIN
# ---------------------------------------------------------------------------
def render_login():
    st.markdown("## 🎩 Six Hats Game")
    st.markdown(
        '<p class="hc-muted">A quick team-thinking game based on Edward de Bono\'s '
        "Six Thinking Hats — sharpen how your team reasons, feels, and communicates.</p>",
        unsafe_allow_html=True,
    )
    st.markdown('<div class="hc-card">', unsafe_allow_html=True)
    name = st.text_input("Your name", key="login_name")

    team_choice = st.radio(
        "Team setup",
        ["Play individually", "Create a new team", "Join an existing team"],
        horizontal=False,
    )

    team_id = None
    new_team_name = None
    join_code = None

    if team_choice == "Create a new team":
        new_team_name = st.text_input("New team name")
    elif team_choice == "Join an existing team":
        join_code = st.text_input("Team code (given to you by your teammate)").strip().upper()

    if st.button("Enter the game", type="primary"):
        if not name or not name.strip():
            st.error("Please enter your name.")
        elif team_choice == "Create a new team" and not new_team_name:
            st.error("Please enter a team name.")
        elif team_choice == "Join an existing team" and not join_code:
            st.error("Please enter a team code.")
        else:
            team_id = None
            if team_choice == "Create a new team":
                existing = db.get_team_by_name(new_team_name.strip())
                if existing:
                    st.error("That team name is already taken. Try another, or join it with its code.")
                    st.stop()
                team_id = db.create_team(new_team_name.strip())
                st.success(f"Team '{new_team_name}' created! Share this code with teammates:")
                st.markdown(f'<div class="hc-team-code">{team_id}</div>', unsafe_allow_html=True)
            elif team_choice == "Join an existing team":
                t = db.get_team_by_id(join_code)
                if not t:
                    st.error("No team found with that code. Double-check with your teammate.")
                    st.stop()
                team_id = t["team_id"]

            existing_player = db.find_player_by_name(name.strip(), team_id)
            if existing_player:
                player_id = existing_player["player_id"]
                db.touch_player(player_id)
            else:
                player_id = db.create_player(name.strip(), team_id)

            st.session_state.player_id = player_id
            st.query_params["pid"] = player_id
            st.session_state.screen = "intro" if not st.session_state.intro_seen else "menu"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown(
        '<p class="hc-muted">Already played before on this team? Enter the exact same name '
        "and team code to pick up your saved progress.</p>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# ONE-TIME INTRO / EXPLAINER
# ---------------------------------------------------------------------------
def render_intro():
    st.markdown("## 👋 Welcome! Here's how Six Thinking Hats works")
    st.markdown(
        '<p class="hc-muted">Six Thinking Hats is a technique where each "hat" represents a '
        "different way of thinking. Teams switch hats together to explore a problem from every "
        "angle — instead of arguing from six angles at once.</p>",
        unsafe_allow_html=True,
    )
    for hat in HAT_ORDER:
        h = HATS[hat]
        st.markdown(
            f'<div class="hc-card">{hat_pill(hat)}<p style="margin-top:0.6rem;">{h["desc"]}</p></div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        '<p class="hc-muted">In this game you\'ll practice recognizing and using each hat through '
        "two modes: a fast <b>Puzzle Mode</b> and a deeper <b>Scenario Mode</b>.</p>",
        unsafe_allow_html=True,
    )
    if st.button("Got it, let's play →", type="primary"):
        st.session_state.intro_seen = True
        st.session_state.screen = "menu"
        st.rerun()


# ---------------------------------------------------------------------------
# MAIN MENU
# ---------------------------------------------------------------------------
def render_menu():
    p = current_player()
    st.markdown(f"## Welcome back, {p['name']} 👋")
    st.markdown('<div class="hc-card">', unsafe_allow_html=True)
    st.markdown("#### 1. Choose your play mode")
    mode_options = ["Individual"] + (["Team"] if p["team_id"] else [])
    if not p["team_id"]:
        st.markdown(
            '<p class="hc-muted">You joined without a team, so team mode is unavailable this '
            "session. Log out and join/create a team to unlock it.</p>",
            unsafe_allow_html=True,
        )
    mode = st.radio("Mode", mode_options, horizontal=True, label_visibility="collapsed")
    st.markdown("#### 2. Choose a game")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            '<div class="hc-card"><b>🧩 Puzzle Mode</b><p class="hc-muted">Match sentences to '
            "the right hat. Light, fast, great for warm-ups.</p></div>",
            unsafe_allow_html=True,
        )
        if st.button("Play Puzzle Mode", use_container_width=True):
            st.session_state.mode = mode.lower()
            st.session_state.submode = "puzzle"
            st.session_state.screen = "puzzle_tutorial"
            st.rerun()
    with c2:
        st.markdown(
            '<div class="hc-card"><b>🎭 Scenario Mode</b><p class="hc-muted">Get a real scenario '
            "and a random hat. Write the best response for that hat.</p></div>",
            unsafe_allow_html=True,
        )
        if st.button("Play Scenario Mode", use_container_width=True):
            st.session_state.mode = mode.lower()
            st.session_state.submode = "scenario"
            st.session_state.screen = "scenario_tutorial"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# PUZZLE MODE
# ---------------------------------------------------------------------------
def render_puzzle_tutorial():
    st.markdown("## 🧩 Puzzle Mode — how it works")
    st.markdown(
        '<div class="hc-card">'
        "<ol>"
        "<li>You'll see a short business scenario and 6 sentences.</li>"
        "<li>Assign each sentence to the hat color it best represents.</li>"
        "<li>Submit before time adds up — the faster and more accurate you are, the more XP you earn.</li>"
        "</ol></div>",
        unsafe_allow_html=True,
    )
    if st.button("Start Puzzle →", type="primary"):
        st.session_state.puzzle_scn = random.choice(PUZZLE_SCENARIOS)
        st.session_state.puzzle_start = time.time()
        st.session_state.screen = "puzzle_game"
        st.rerun()
    if st.button("← Back to menu"):
        st.session_state.screen = "menu"
        st.rerun()


def render_puzzle_game():
    scn = st.session_state.puzzle_scn
    st.markdown(f"## 🧩 {scn['title']}")
    st.markdown('<p class="hc-muted">Match each sentence to the hat it represents.</p>', unsafe_allow_html=True)

    items = list(scn["sentences"].items())
    random.Random(scn["title"]).shuffle(items)  # stable shuffle per scenario

    answers = {}
    with st.form("puzzle_form"):
        for i, (correct_hat, sentence) in enumerate(items):
            st.markdown(f'<div class="hc-card">“{sentence}”</div>', unsafe_allow_html=True)
            choice = st.selectbox(
                f"Which hat fits sentence {i + 1}?",
                HAT_ORDER,
                key=f"puzzle_choice_{i}",
                index=None,
                placeholder="Choose a hat...",
            )
            answers[i] = (correct_hat, choice)
        submitted = st.form_submit_button("Submit answers", type="primary")

    if submitted:
        if any(choice is None for _, choice in answers.values()):
            st.error("Please answer all 6 before submitting.")
            return
        elapsed = time.time() - st.session_state.puzzle_start
        correct = sum(1 for correct_hat, choice in answers.values() if choice == correct_hat)
        accuracy_pct = correct / len(answers)

        base_xp = correct * 10
        speed_bonus = 0
        if elapsed < 30:
            speed_bonus = 20
        elif elapsed < 60:
            speed_bonus = 10
        elif elapsed < 90:
            speed_bonus = 5
        total_xp = base_xp + speed_bonus if accuracy_pct >= 0.5 else max(0, base_xp)

        db.add_exp(
            st.session_state.player_id, total_xp,
            st.session_state.mode, "puzzle", correct,
        )
        st.session_state.last_result = {
            "correct": correct, "total": len(answers), "elapsed": elapsed,
            "xp": total_xp, "speed_bonus": speed_bonus,
        }
        st.session_state.screen = "puzzle_result"
        st.rerun()


def render_puzzle_result():
    r = st.session_state.last_result
    st.markdown("## ✅ Round complete!")
    st.markdown(
        f'<div class="hc-card">'
        f"<h3>{r['correct']} / {r['total']} correct</h3>"
        f"<p>Time: {r['elapsed']:.1f}s · Speed bonus: +{r['speed_bonus']} XP</p>"
        f"<h2 style='color:{PALETTE['blue']};'>+{r['xp']} XP</h2>"
        f"</div>",
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Play again", use_container_width=True):
            st.session_state.puzzle_scn = random.choice(PUZZLE_SCENARIOS)
            st.session_state.puzzle_start = time.time()
            st.session_state.screen = "puzzle_game"
            st.rerun()
    with c2:
        if st.button("Back to menu", use_container_width=True):
            st.session_state.screen = "menu"
            st.rerun()


# ---------------------------------------------------------------------------
# SCENARIO MODE
# ---------------------------------------------------------------------------
def score_response(text, hat, keywords):
    if not text or not text.strip():
        return 0, "No response given."
    text_l = text.lower()
    kw_hits = sum(1 for kw in keywords.get(hat, []) if kw in text_l)
    length_score = min(40, len(text.split()) * 2)  # up to 40 pts for effort/depth
    relevance_score = min(50, kw_hits * 15)          # up to 50 pts for hat-fit
    base = length_score + relevance_score
    base = min(90, base) + (10 if kw_hits >= 2 else 0)  # small bonus for strong fit
    base = min(100, base)
    if base >= 70:
        note = f"Strong {hat} Hat thinking — clearly matched the mindset."
    elif base >= 40:
        note = f"Decent attempt, but could lean harder into {hat} Hat thinking."
    else:
        note = f"This reads more like a different hat than {hat}. Review the hat's focus."
    return base, note


def render_scenario_tutorial():
    st.markdown("## 🎭 Scenario Mode — how it works")
    st.markdown(
        '<div class="hc-card">'
        "<ol>"
        "<li>You'll see one real-world scenario.</li>"
        "<li>You'll be randomly assigned a hat.</li>"
        "<li>Write the best possible response <i>from that hat's point of view</i>.</li>"
        "<li>You're scored on how well your answer fits the hat, plus speed.</li>"
        "</ol>"
        '<p class="hc-muted">Team mode: everyone on the team sees the same scenario and '
        "contributes their own hat response — all XP is added to the team's total.</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    if st.button("Start Scenario →", type="primary"):
        prompt = random.choice(SCENARIO_PROMPTS)
        st.session_state.scenario_prompt = prompt
        st.session_state.scenario_hat = random.choice(HAT_ORDER)
        st.session_state.scenario_start = time.time()
        st.session_state.screen = "scenario_game"
        st.rerun()
    if st.button("← Back to menu"):
        st.session_state.screen = "menu"
        st.rerun()


def render_scenario_game():
    prompt = st.session_state.scenario_prompt
    hat = st.session_state.scenario_hat
    st.markdown(f"## 🎭 Scenario")
    st.markdown(f'<div class="hc-card"><p>{prompt["title"]}</p></div>', unsafe_allow_html=True)
    st.markdown(f"Your hat: {hat_pill(hat)}", unsafe_allow_html=True)
    st.markdown(f'<p class="hc-muted">{HATS[hat]["desc"]}</p>', unsafe_allow_html=True)

    with st.form("scenario_form"):
        response = st.text_area("Your response, written from this hat's perspective:", height=150)
        submitted = st.form_submit_button("Submit response", type="primary")

    if submitted:
        elapsed = time.time() - st.session_state.scenario_start
        score, note = score_response(response, hat, prompt["keywords"])
        speed_bonus = 15 if elapsed < 45 else (8 if elapsed < 90 else 0)
        xp = int(score * 0.4) + speed_bonus  # up to ~55 xp per round

        db.add_exp(
            st.session_state.player_id, xp,
            st.session_state.mode, "scenario", score,
        )
        st.session_state.last_result = {
            "score": score, "note": note, "elapsed": elapsed,
            "xp": xp, "speed_bonus": speed_bonus, "hat": hat,
        }
        st.session_state.screen = "scenario_result"
        st.rerun()


def render_scenario_result():
    r = st.session_state.last_result
    st.markdown("## ✅ Response scored!")
    st.markdown(
        f'<div class="hc-card">'
        f"{hat_pill(r['hat'])}"
        f"<h3 style='margin-top:0.6rem;'>Creativity/fit score: {r['score']}/100</h3>"
        f"<p>{r['note']}</p>"
        f"<p>Time: {r['elapsed']:.1f}s · Speed bonus: +{r['speed_bonus']} XP</p>"
        f"<h2 style='color:{PALETTE['blue']};'>+{r['xp']} XP</h2>"
        f"</div>",
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Play again", use_container_width=True):
            prompt = random.choice(SCENARIO_PROMPTS)
            st.session_state.scenario_prompt = prompt
            st.session_state.scenario_hat = random.choice(HAT_ORDER)
            st.session_state.scenario_start = time.time()
            st.session_state.screen = "scenario_game"
            st.rerun()
    with c2:
        if st.button("Back to menu", use_container_width=True):
            st.session_state.screen = "menu"
            st.rerun()


# ---------------------------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------------------------
def render_dashboard():
    st.markdown("## 🏆 Leaderboards")
    tab1, tab2 = st.tabs(["Teams", "Individuals"])
    with tab1:
        teams = db.leaderboard_teams()
        if not teams:
            st.markdown('<p class="hc-muted">No teams yet.</p>', unsafe_allow_html=True)
        for i, t in enumerate(teams, start=1):
            st.markdown(
                f'<div class="hc-card">#{i} <b>{t["team_name"]}</b> '
                f'<span class="hc-muted">({t["team_id"]})</span>'
                f'<h3 style="color:{PALETTE["blue"]};margin:0;">{t["total_exp"]} XP</h3></div>',
                unsafe_allow_html=True,
            )
    with tab2:
        players = db.leaderboard_players()
        if not players:
            st.markdown('<p class="hc-muted">No players yet.</p>', unsafe_allow_html=True)
        for i, p in enumerate(players, start=1):
            team_str = f' · {p["team_name"]}' if p["team_name"] else " · individual"
            st.markdown(
                f'<div class="hc-card">#{i} <b>{p["name"]}</b> '
                f'<span class="hc-muted">Lvl {p["level"]}{team_str}</span>'
                f'<h3 style="color:{PALETTE["blue"]};margin:0;">{p["exp"]} XP</h3></div>',
                unsafe_allow_html=True,
            )
    if st.button("← Back to menu"):
        st.session_state.screen = "menu"
        st.rerun()


# ---------------------------------------------------------------------------
# ROUTER
# ---------------------------------------------------------------------------
if st.session_state.player_id is None:
    render_login()
else:
    render_sidebar()
    screen = st.session_state.screen
    if screen == "intro":
        render_intro()
    elif screen == "menu":
        render_menu()
    elif screen == "puzzle_tutorial":
        render_puzzle_tutorial()
    elif screen == "puzzle_game":
        render_puzzle_game()
    elif screen == "puzzle_result":
        render_puzzle_result()
    elif screen == "scenario_tutorial":
        render_scenario_tutorial()
    elif screen == "scenario_game":
        render_scenario_game()
    elif screen == "scenario_result":
        render_scenario_result()
    elif screen == "dashboard":
        render_dashboard()
    else:
        render_menu()
