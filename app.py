import time
import random
import streamlit as st

import db
from content import HATS, HAT_ORDER, PUZZLE_SCENARIOS, SCENARIO_PROMPTS
from styles import inject_css, hat_button_css, PALETTE

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
    "mode": None,        # 'individual' | 'team'
    "submode": None,     # 'puzzle' | 'scenario'
    # puzzle
    "puzzle_scn": None,
    "puzzle_order": None,
    "puzzle_start": None,
    "puzzle_answers": {},
    # scenario - individual
    "scenario_prompt": None,
    "scenario_hat": None,
    "scenario_start": None,
    # scenario - team round
    "round_id": None,
    "round_start": None,
    "last_result": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# restore login from URL query params (?pid=...)
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
        f'color:{h["text_on"]};padding:{pad};">{h["emoji"]} {hat_name} — {h["tagline"]}</span>'
    )


def current_player():
    if st.session_state.player_id:
        return db.get_player(st.session_state.player_id)
    return None


def hat_picker(prefix, selected_hat=None, disabled=False):
    """Render a row of 6 colored hat buttons. Returns the newly clicked hat
    (or None if no button was clicked this run)."""
    clicked = None
    cols = st.columns(6)
    for i, hat in enumerate(HAT_ORDER):
        h = HATS[hat]
        key = f"hatbtn_{prefix}_{hat}"
        is_selected = selected_hat == hat
        st.markdown(hat_button_css(hat, h["color"], h["text_on"], key, is_selected), unsafe_allow_html=True)
        with cols[i]:
            label = f"{'✅ ' if is_selected else ''}{h['emoji']} {hat}"
            if st.button(label, key=key, disabled=disabled, use_container_width=True):
                clicked = hat
    return clicked


def feedback_note(hat, score, keywords):
    """Human-readable correction / feedback for a scenario-mode response."""
    if score >= 70:
        return f"Strong {hat} Hat thinking — this clearly matched the mindset."
    sample = ", ".join(keywords.get(hat, [])[:3])
    if score >= 40:
        return (
            f"Decent attempt, but it could lean harder into {hat} Hat thinking "
            f"({HATS[hat]['tagline']}). Try touching on ideas like: {sample}."
        )
    return (
        f"This reads more like a different hat than {hat} "
        f"({HATS[hat]['tagline']}). A stronger {hat} Hat answer would focus on things "
        f"like: {sample}."
    )


def score_response(text, hat, keywords):
    if not text or not text.strip():
        return 0, "No response given."
    text_l = text.lower()
    kw_hits = sum(1 for kw in keywords.get(hat, []) if kw in text_l)
    length_score = min(40, len(text.split()) * 2)
    relevance_score = min(50, kw_hits * 15)
    base = length_score + relevance_score
    base = min(90, base) + (10 if kw_hits >= 2 else 0)
    base = min(100, base)
    return base, feedback_note(hat, base, keywords)


# ---------------------------------------------------------------------------
# SIDEBAR
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
# LOGIN
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
# ONE-TIME INTRO
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
        "<li>Tap the colored hat button you think each sentence belongs to.</li>"
        "<li>Submit before time adds up — the faster and more accurate you are, the more XP you earn.</li>"
        "<li>After you submit, you'll see exactly which ones were right and wrong, with the correct hat shown.</li>"
        "</ol></div>",
        unsafe_allow_html=True,
    )
    if st.button("Start Puzzle →", type="primary"):
        scn = random.choice(PUZZLE_SCENARIOS)
        items = list(scn["sentences"].items())
        random.shuffle(items)
        st.session_state.puzzle_scn = scn
        st.session_state.puzzle_order = items
        st.session_state.puzzle_answers = {}
        st.session_state.puzzle_start = time.time()
        st.session_state.screen = "puzzle_game"
        st.rerun()
    if st.button("← Back to menu"):
        st.session_state.screen = "menu"
        st.rerun()


def render_puzzle_game():
    scn = st.session_state.puzzle_scn
    items = st.session_state.puzzle_order
    st.markdown(f"## 🧩 {scn['title']}")
    st.markdown('<p class="hc-muted">Tap the hat each sentence represents.</p>', unsafe_allow_html=True)

    for i, (correct_hat, sentence) in enumerate(items):
        st.markdown(f'<div class="hc-card">“{sentence}”</div>', unsafe_allow_html=True)
        current = st.session_state.puzzle_answers.get(i)
        clicked = hat_picker(f"p{i}", selected_hat=current)
        if clicked:
            st.session_state.puzzle_answers[i] = clicked
            st.rerun()

    st.divider()
    answered = len(st.session_state.puzzle_answers)
    st.markdown(f'<p class="hc-muted">{answered} / {len(items)} answered</p>', unsafe_allow_html=True)
    if st.button("Submit answers", type="primary"):
        if answered < len(items):
            st.error("Please answer all 6 before submitting.")
        else:
            elapsed = time.time() - st.session_state.puzzle_start
            results = []
            correct_count = 0
            for i, (correct_hat, sentence) in enumerate(items):
                chosen = st.session_state.puzzle_answers[i]
                is_correct = chosen == correct_hat
                correct_count += int(is_correct)
                results.append({
                    "sentence": sentence, "correct_hat": correct_hat,
                    "chosen": chosen, "is_correct": is_correct,
                })

            accuracy_pct = correct_count / len(items)
            base_xp = correct_count * 10
            speed_bonus = 20 if elapsed < 30 else (10 if elapsed < 60 else (5 if elapsed < 90 else 0))
            total_xp = base_xp + speed_bonus if accuracy_pct >= 0.5 else max(0, base_xp)

            db.add_exp(st.session_state.player_id, total_xp, st.session_state.mode, "puzzle", correct_count)
            st.session_state.last_result = {
                "results": results, "correct": correct_count, "total": len(items),
                "elapsed": elapsed, "xp": total_xp, "speed_bonus": speed_bonus,
            }
            st.session_state.screen = "puzzle_result"
            st.rerun()

    if st.button("← Give up and return to menu"):
        st.session_state.screen = "menu"
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

    st.markdown("#### Answer review")
    for item in r["results"]:
        icon = "✅" if item["is_correct"] else "❌"
        border_color = PALETTE["teal"] if item["is_correct"] else PALETTE["coral"]
        extra = ""
        if not item["is_correct"]:
            extra = (
                f'<p style="margin-top:0.4rem;">Your answer: {hat_pill(item["chosen"], "small")}'
                f'<br>Correct answer: {hat_pill(item["correct_hat"], "small")}</p>'
            )
        else:
            extra = f'<p style="margin-top:0.4rem;">{hat_pill(item["correct_hat"], "small")}</p>'
        st.markdown(
            f'<div class="hc-card" style="border-left:5px solid {border_color};">'
            f'{icon} “{item["sentence"]}”{extra}</div>',
            unsafe_allow_html=True,
        )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Play again", use_container_width=True):
            scn = random.choice(PUZZLE_SCENARIOS)
            items = list(scn["sentences"].items())
            random.shuffle(items)
            st.session_state.puzzle_scn = scn
            st.session_state.puzzle_order = items
            st.session_state.puzzle_answers = {}
            st.session_state.puzzle_start = time.time()
            st.session_state.screen = "puzzle_game"
            st.rerun()
    with c2:
        if st.button("Back to menu", use_container_width=True):
            st.session_state.screen = "menu"
            st.rerun()


# ---------------------------------------------------------------------------
# SCENARIO MODE — INDIVIDUAL
# ---------------------------------------------------------------------------
def render_scenario_tutorial():
    st.markdown("## 🎭 Scenario Mode — how it works")
    if st.session_state.mode == "team":
        st.markdown(
            '<div class="hc-card">'
            "<ol>"
            "<li>One teammate starts the round and becomes the <b>host</b> — the team doesn't need "
            "to be full, the host can start anytime.</li>"
            "<li>Everyone else joins that round from this screen.</li>"
            "<li>Each of you gets your own random hat and writes your own response.</li>"
            "<li>Results are revealed only once <b>every</b> teammate who joined has submitted.</li>"
            "<li>Whoever submits first earns a personal speed bonus — that bonus is theirs alone, "
            "it doesn't add to the team's total.</li>"
            "</ol></div>",
            unsafe_allow_html=True,
        )
        if st.button("Continue →", type="primary"):
            st.session_state.screen = "scenario_lobby"
            st.rerun()
    else:
        st.markdown(
            '<div class="hc-card">'
            "<ol>"
            "<li>You'll see one real-world scenario.</li>"
            "<li>You'll be randomly assigned a hat.</li>"
            "<li>Write the best possible response <i>from that hat's point of view</i>.</li>"
            "<li>You're scored on how well your answer fits the hat, plus speed.</li>"
            "</ol></div>",
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
    st.markdown("## 🎭 Scenario")
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
        xp = int(score * 0.4) + speed_bonus

        db.add_exp(st.session_state.player_id, xp, st.session_state.mode, "scenario", score)
        st.session_state.last_result = {
            "score": score, "note": note, "elapsed": elapsed, "xp": xp,
            "speed_bonus": speed_bonus, "hat": hat, "response": response,
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
        f'<p style="margin-top:0.4rem;"><i>“{r["response"]}”</i></p>'
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
# SCENARIO MODE — TEAM (host + lobby + rounds)
# ---------------------------------------------------------------------------
def render_scenario_lobby():
    p = current_player()
    team = db.get_team_by_id(p["team_id"])
    current_round = db.get_current_round(team["team_id"])

    if current_round is None:
        st.markdown("## 🎭 Team Scenario — Lobby")
        st.markdown(
            f'<div class="hc-card">No round is running for <b>{team["team_name"]}</b> right now.'
            "<p class=\"hc-muted\">Start one now — you don't need the whole team present. "
            "You'll wait in a lobby while teammates join, then start the round whenever "
            "you're ready.</p></div>",
            unsafe_allow_html=True,
        )
        if st.button("🚀 Start round (become host)", type="primary"):
            scenario_idx = random.randrange(len(SCENARIO_PROMPTS))
            round_id = db.create_round(team["team_id"], p["player_id"], scenario_idx)
            hat = random.choice(HAT_ORDER)
            db.join_round(round_id, p["player_id"], hat)
            st.session_state.round_id = round_id
            st.session_state.screen = "scenario_room_lobby"
            st.rerun()
        if st.button("← Back to menu"):
            st.session_state.screen = "menu"
            st.rerun()
        return

    participant = db.get_participant(current_round["round_id"], p["player_id"])
    host = db.get_player(current_round["host_player_id"])

    if current_round["status"] == "lobby":
        if participant is None:
            st.markdown("## 🎭 Team Scenario — Lobby")
            st.markdown(
                f'<div class="hc-card">A round is gathering, hosted by <b>{host["name"]}</b>.'
                "<p class=\"hc-muted\">Join now while it's still in the lobby — once the host "
                "starts it, joining closes.</p></div>",
                unsafe_allow_html=True,
            )
            if st.button("🙋 Join lobby", type="primary"):
                hat = random.choice(HAT_ORDER)
                db.join_round(current_round["round_id"], p["player_id"], hat)
                st.session_state.round_id = current_round["round_id"]
                st.session_state.screen = "scenario_room_lobby"
                st.rerun()
            if st.button("← Back to menu"):
                st.session_state.screen = "menu"
                st.rerun()
            return
        st.session_state.round_id = current_round["round_id"]
        st.session_state.screen = "scenario_room_lobby"
        st.rerun()
        return

    # status == 'active'
    if participant is None:
        st.markdown("## 🎭 Team Scenario")
        st.markdown(
            f'<div class="hc-card">This round already started without you, hosted by '
            f'<b>{host["name"]}</b>.<p class="hc-muted">You\'ll be able to join the next one.</p></div>',
            unsafe_allow_html=True,
        )
        if st.button("← Back to menu"):
            st.session_state.screen = "menu"
            st.rerun()
        return

    st.session_state.round_id = current_round["round_id"]
    st.session_state.screen = "scenario_waiting" if participant["submitted"] else "scenario_game_team"
    st.rerun()


def render_scenario_room_lobby():
    """Waiting room shown before the host starts the round."""
    round_row = db.get_round(st.session_state.round_id)
    p = current_player()
    is_host = round_row["host_player_id"] == p["player_id"]
    host = db.get_player(round_row["host_player_id"])
    participants = db.round_participants_list(round_row["round_id"])

    st.markdown("## 🕓 Waiting Room")
    st.markdown(
        f'<p class="hc-muted">Hosted by {host["name"]} · Round code <code>{round_row["round_id"]}</code></p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="hc-card"><b>{len(participants)} joined so far</b><br>'
        + "<br>".join(f"🙋 {pt['player_name']}" for pt in participants)
        + "</div>",
        unsafe_allow_html=True,
    )

    if is_host:
        st.markdown(
            '<p class="hc-muted">You\'re the host. Start whenever you\'re ready — the whole '
            "team doesn't need to be here.</p>",
            unsafe_allow_html=True,
        )
        if st.button("▶️ Start the round now", type="primary"):
            db.start_round(round_row["round_id"])
            st.session_state.screen = "scenario_lobby"
            st.rerun()
    else:
        st.markdown('<p class="hc-muted">Waiting for the host to start the round...</p>', unsafe_allow_html=True)
        if st.button("🔄 Refresh"):
            st.rerun()

    if st.button("← Back to menu"):
        st.session_state.screen = "menu"
        st.rerun()


def render_scenario_game_team():
    round_row = db.get_round(st.session_state.round_id)
    prompt = SCENARIO_PROMPTS[round_row["scenario_idx"]]
    participant = db.get_participant(round_row["round_id"], st.session_state.player_id)
    hat = participant["hat"]
    host = db.get_player(round_row["host_player_id"])

    st.markdown("## 🎭 Team Scenario")
    st.markdown(
        f'<p class="hc-muted">Hosted by {host["name"]} · Round code <code>{round_row["round_id"]}</code></p>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="hc-card"><p>{prompt["title"]}</p></div>', unsafe_allow_html=True)
    st.markdown(f"Your hat: {hat_pill(hat)}", unsafe_allow_html=True)
    st.markdown(f'<p class="hc-muted">{HATS[hat]["desc"]}</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hc-muted">Tip: the first teammate to submit earns a personal speed bonus '
        "— it's yours alone and won't be shared with the team total.</p>",
        unsafe_allow_html=True,
    )

    with st.form("scenario_team_form"):
        response = st.text_area("Your response, written from this hat's perspective:", height=150)
        submitted = st.form_submit_button("Submit response", type="primary")

    if submitted:
        score, note = score_response(response, hat, prompt["keywords"])
        xp = int(score * 0.4)
        db.submit_round_answer(round_row["round_id"], st.session_state.player_id, response, score, note, xp)
        db.finalize_round_if_ready(round_row["round_id"])
        st.session_state.screen = "scenario_waiting"
        st.rerun()


def render_scenario_waiting():
    round_row = db.get_round(st.session_state.round_id)
    if round_row["status"] == "completed" or db.all_submitted(round_row["round_id"]):
        db.finalize_round_if_ready(round_row["round_id"])
        st.session_state.screen = "scenario_team_result"
        st.rerun()
        return

    participants = db.round_participants_list(round_row["round_id"])
    st.markdown("## ⏳ Waiting for your teammates")
    st.markdown(
        '<p class="hc-muted">Results unlock once every teammate who joined this round has '
        "submitted their answer.</p>",
        unsafe_allow_html=True,
    )
    for pt in participants:
        status = "✅ Submitted" if pt["submitted"] else "⌛ Still answering"
        st.markdown(
            f'<div class="hc-card">{hat_pill(pt["hat"], "small")} <b>{pt["player_name"]}</b> — {status}</div>',
            unsafe_allow_html=True,
        )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Refresh status", use_container_width=True, type="primary"):
            st.rerun()
    with c2:
        if st.button("← Back to menu", use_container_width=True):
            st.session_state.screen = "menu"
            st.rerun()


def render_scenario_team_result():
    round_row = db.get_round(st.session_state.round_id)
    prompt = SCENARIO_PROMPTS[round_row["scenario_idx"]]
    participants = db.round_participants_list(round_row["round_id"])

    st.markdown("## ✅ Team round complete!")
    st.markdown(f'<div class="hc-card"><p>{prompt["title"]}</p></div>', unsafe_allow_html=True)

    for pt in participants:
        bonus_badge = (
            f'<span class="hc-badge" style="background-color:{PALETTE["blue"]};color:white;">'
            f"🏅 First to submit +{db.FIRST_SUBMIT_BONUS} XP</span> "
            if pt["got_bonus"] else ""
        )
        st.markdown(
            f'<div class="hc-card">'
            f'{hat_pill(pt["hat"], "small")} <b>{pt["player_name"]}</b> {bonus_badge}'
            f'<p style="margin-top:0.5rem;"><i>“{pt["response"] or "(no response)"}”</i></p>'
            f'<p>Score: <b>{pt["score"]}/100</b> · +{pt["xp"]} XP to team</p>'
            f'<p class="hc-muted">{pt["note"]}</p>'
            f"</div>",
            unsafe_allow_html=True,
        )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Start a new round", use_container_width=True):
            st.session_state.screen = "scenario_lobby"
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
    tab1, tab2, tab3 = st.tabs(["🏢 Teams", "🧍 Individual players", "👥 Team members"])

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
        st.markdown(
            '<p class="hc-muted">Players who are not on any team, ranked by their own XP.</p>',
            unsafe_allow_html=True,
        )
        solo = db.leaderboard_individual_players()
        if not solo:
            st.markdown('<p class="hc-muted">No individual players yet.</p>', unsafe_allow_html=True)
        for i, pl in enumerate(solo, start=1):
            st.markdown(
                f'<div class="hc-card">#{i} <b>{pl["name"]}</b> '
                f'<span class="hc-muted">Lvl {pl["level"]}</span>'
                f'<h3 style="color:{PALETTE["blue"]};margin:0;">{pl["exp"]} XP</h3></div>',
                unsafe_allow_html=True,
            )

    with tab3:
        st.markdown(
            '<p class="hc-muted">Players who belong to a team, ranked by their own personal XP.</p>',
            unsafe_allow_html=True,
        )
        members = db.leaderboard_team_members()
        if not members:
            st.markdown('<p class="hc-muted">No team members yet.</p>', unsafe_allow_html=True)
        for i, pl in enumerate(members, start=1):
            st.markdown(
                f'<div class="hc-card">#{i} <b>{pl["name"]}</b> '
                f'<span class="hc-muted">Lvl {pl["level"]} · {pl["team_name"]}</span>'
                f'<h3 style="color:{PALETTE["blue"]};margin:0;">{pl["exp"]} XP</h3></div>',
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
    elif screen == "scenario_lobby":
        render_scenario_lobby()
    elif screen == "scenario_room_lobby":
        render_scenario_room_lobby()
    elif screen == "scenario_game_team":
        render_scenario_game_team()
    elif screen == "scenario_waiting":
        render_scenario_waiting()
    elif screen == "scenario_team_result":
        render_scenario_team_result()
    elif screen == "dashboard":
        render_dashboard()
    else:
        render_menu()
