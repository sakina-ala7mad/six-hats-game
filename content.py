"""
content.py — Six Thinking Hats definitions and game content.
"""

# Color mapping.
# Note: the supplied brand palette does not contain a true yellow, which is
# the traditional color for the "Optimism" hat. To keep all six hats
# instantly distinguishable (important for a fast-paced game), we introduce
# one small, deliberate exception — a warm gold (#f2c14e) for the Yellow hat
# only. Every other hat uses a color from the exact palette provided.
HATS = {
    "White": {
        "color": "#ffffff",
        "text_on": "#02223c",
        "tagline": "Facts & Information",
        "desc": "Neutral, objective. What data do we actually have? What's missing?",
    },
    "Red": {
        "color": "#ff3366",
        "text_on": "#ffffff",
        "tagline": "Feelings & Intuition",
        "desc": "Emotions, hunches, gut reactions — no justification needed.",
    },
    "Black": {
        "color": "#02223c",
        "text_on": "#ffffff",
        "tagline": "Caution & Critical Judgement",
        "desc": "Risks, weaknesses, why something might not work.",
    },
    "Yellow": {
        "color": "#f2c14e",
        "text_on": "#02223c",
        "tagline": "Optimism & Benefits",
        "desc": "Value, feasibility, best-case outcomes.",
    },
    "Green": {
        "color": "#2ec4b6",
        "text_on": "#02223c",
        "tagline": "Creativity & New Ideas",
        "desc": "Alternatives, provocations, what else could we try?",
    },
    "Blue": {
        "color": "#20a4f3",
        "text_on": "#ffffff",
        "tagline": "Process & Big Picture",
        "desc": "Managing the thinking itself — agenda, focus, next steps.",
    },
}

HAT_ORDER = ["White", "Red", "Black", "Yellow", "Green", "Blue"]

# ---------------------------------------------------------------------------
# PUZZLE MODE: for each scenario, 6 sentences that must be matched to hats.
# ---------------------------------------------------------------------------
PUZZLE_SCENARIOS = [
    {
        "title": "Launching a new product line",
        "sentences": {
            "White": "Our market research shows 42% of surveyed customers want this feature.",
            "Red": "Honestly, this launch date makes me nervous.",
            "Black": "If the supplier misses the deadline, we lose the holiday window entirely.",
            "Yellow": "This could open up a completely new customer segment for us.",
            "Green": "What if we bundled it with a subscription instead of selling it standalone?",
            "Blue": "Let's set a checkpoint next Friday to review where we stand.",
        },
    },
    {
        "title": "A project is behind schedule",
        "sentences": {
            "White": "We are currently 12 days behind the original plan.",
            "Red": "I feel like the team is losing morale over this delay.",
            "Black": "Rushing the QA phase now could cause a much bigger failure later.",
            "Yellow": "The delay gives us extra time to fix the bug we flagged last month.",
            "Green": "What if we split the release into two smaller phases?",
            "Blue": "Let's list our options first, then decide as a group.",
        },
    },
    {
        "title": "Choosing a new office layout",
        "sentences": {
            "White": "The current layout fits 40 desks; the new one fits 55.",
            "Red": "People seem excited about having more natural light.",
            "Black": "Open layouts can increase noise complaints, based on last year's survey.",
            "Yellow": "More collaborative space could boost cross-team communication.",
            "Green": "What if we created rotating 'quiet zones' instead of fixed ones?",
            "Blue": "Let's agree on our top 3 priorities before comparing options.",
        },
    },
    {
        "title": "A customer complaint just came in",
        "sentences": {
            "White": "The customer's order was delayed by 5 days according to the tracking log.",
            "Red": "This complaint really stings because we pride ourselves on speed.",
            "Black": "If we don't respond within 24 hours, we risk a public review.",
            "Yellow": "Handling this well could turn the customer into a loyal advocate.",
            "Green": "What if we offered a small credit plus a personal follow-up call?",
            "Blue": "Let's assign an owner for this issue right now.",
        },
    },
    {
        "title": "Deciding on a new hiring process",
        "sentences": {
            "White": "Our average time-to-hire is currently 34 days.",
            "Red": "Candidates have told us the process feels impersonal.",
            "Black": "Adding more interview rounds could increase drop-off rates.",
            "Yellow": "A faster process could help us win top candidates over competitors.",
            "Green": "What if we replaced one interview round with a paid trial project?",
            "Blue": "Let's define what 'success' looks like for this process before changing it.",
        },
    },
]

# ---------------------------------------------------------------------------
# SCENARIO MODE: open-ended prompts. Each hat has expected keyword themes
# used for a lightweight heuristic score (0-100) on the written response.
# ---------------------------------------------------------------------------
SCENARIO_PROMPTS = [
    {
        "title": "Your team's biggest client just asked for a 30% discount or they'll leave.",
        "keywords": {
            "White": ["data", "contract", "revenue", "history", "number", "fact", "percent", "usage"],
            "Red": ["feel", "worried", "frustrat", "excit", "uneasy", "gut", "sense"],
            "Black": ["risk", "lose", "precedent", "margin", "problem", "danger", "cost"],
            "Yellow": ["opportunity", "benefit", "loyal", "retain", "grow", "long-term", "positive"],
            "Green": ["what if", "alternative", "instead", "idea", "creative", "bundle", "tier"],
            "Blue": ["plan", "step", "next", "agenda", "process", "decide", "meeting"],
        },
    },
    {
        "title": "A new competitor just launched a cheaper version of your main product.",
        "keywords": {
            "White": ["price", "feature", "market", "data", "compare", "spec", "fact"],
            "Red": ["worried", "threat", "excite", "nervous", "feel", "gut"],
            "Black": ["risk", "lose customers", "danger", "weak", "undercut", "problem"],
            "Yellow": ["opportunity", "differentiate", "premium", "quality", "benefit", "strength"],
            "Green": ["what if", "new feature", "reposition", "idea", "innovate", "bundle"],
            "Blue": ["plan", "strategy", "step", "timeline", "review", "decide"],
        },
    },
    {
        "title": "Two team members strongly disagree on the direction of a project.",
        "keywords": {
            "White": ["fact", "data", "evidence", "requirement", "spec", "timeline"],
            "Red": ["feel", "tension", "frustrat", "uncomfortable", "emotion"],
            "Black": ["risk", "conflict", "delay", "problem", "weakness"],
            "Yellow": ["benefit", "strength", "opportunity", "align", "positive"],
            "Green": ["what if", "compromise", "alternative", "combine", "idea", "new approach"],
            "Blue": ["mediate", "meeting", "process", "agenda", "facilitate", "decide"],
        },
    },
    {
        "title": "Leadership wants your team to cut costs by 20% this quarter.",
        "keywords": {
            "White": ["budget", "number", "cost", "data", "expense", "current spend"],
            "Red": ["worried", "stress", "morale", "feel", "anxious"],
            "Black": ["risk", "quality", "layoff", "cut too", "danger", "impact"],
            "Yellow": ["efficient", "opportunity", "streamline", "benefit", "leaner"],
            "Green": ["what if", "automate", "renegotiate", "alternative", "idea"],
            "Blue": ["plan", "priorit", "timeline", "review", "step", "process"],
        },
    },
    {
        "title": "A key employee just resigned unexpectedly, mid-project.",
        "keywords": {
            "White": ["status", "handover", "documentation", "fact", "current", "task list"],
            "Red": ["worried", "shock", "feel", "loss", "concern"],
            "Black": ["risk", "delay", "knowledge gap", "danger", "deadline"],
            "Yellow": ["opportunity", "cross-train", "growth", "benefit", "fresh"],
            "Green": ["what if", "redistribute", "hire", "idea", "alternative", "interim"],
            "Blue": ["plan", "handover plan", "step", "priorit", "timeline", "process"],
        },
    },
]
