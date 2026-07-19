"""
styles.py — theme CSS injection for the Six Hats Game.

Brand palette:
  #02223c  deep navy      (dark bg / primary text on light)
  #6c7a89  slate gray     (secondary text / borders)
  #ffffff  white
  #ff3366  coral red      (accent / Red hat)
  #802547  wine
  #977c8e  dusty mauve
  #92ded7  pale aqua
  #2ec4b6  teal green     (Green hat)
  #56b9f5  sky blue
  #20a4f3  bright blue    (Blue hat / primary accent)
"""

PALETTE = {
    "navy": "#02223c",
    "slate": "#6c7a89",
    "white": "#ffffff",
    "coral": "#ff3366",
    "wine": "#802547",
    "mauve": "#977c8e",
    "aqua": "#92ded7",
    "teal": "#2ec4b6",
    "sky": "#56b9f5",
    "blue": "#20a4f3",
}


def theme_vars(dark: bool) -> dict:
    if dark:
        return {
            "bg": PALETTE["navy"],
            "bg_card": "#0a3157",
            "text": PALETTE["white"],
            "text_muted": PALETTE["aqua"],
            "border": PALETTE["slate"],
            "accent": PALETTE["blue"],
            "accent2": PALETTE["coral"],
        }
    return {
        "bg": "#f4f6f8",
        "bg_card": PALETTE["white"],
        "text": PALETTE["navy"],
        "text_muted": PALETTE["slate"],
        "border": PALETTE["mauve"],
        "accent": PALETTE["blue"],
        "accent2": PALETTE["coral"],
    }


def inject_css(dark: bool) -> str:
    v = theme_vars(dark)
    return f"""
<style>
.stApp {{
    background-color: {v['bg']};
    color: {v['text']};
}}
h1, h2, h3, h4, p, span, label, .stMarkdown {{
    color: {v['text']} !important;
}}
[data-testid="stSidebar"] {{
    background-color: {v['bg_card']};
    border-right: 1px solid {v['border']};
}}
.hc-card {{
    background-color: {v['bg_card']};
    border: 1px solid {v['border']};
    border-radius: 14px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
}}
.hc-badge {{
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 999px;
    font-weight: 700;
    font-size: 0.85rem;
    letter-spacing: 0.02em;
}}
.hc-pill {{
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.35rem 0.9rem;
    border-radius: 999px;
    font-weight: 600;
    font-size: 0.9rem;
    margin: 0.15rem;
}}
.hc-muted {{
    color: {v['text_muted']} !important;
    font-size: 0.9rem;
}}
.hc-team-code {{
    font-family: monospace;
    font-size: 1.4rem;
    letter-spacing: 0.25rem;
    background-color: {v['bg']};
    color: {v['accent']} !important;
    border: 2px dashed {v['accent']};
    border-radius: 10px;
    padding: 0.5rem 1rem;
    display: inline-block;
}}
div.stButton > button {{
    background-color: {v['accent']};
    color: white;
    border: none;
    border-radius: 10px;
    padding: 0.5rem 1.2rem;
    font-weight: 600;
}}
div.stButton > button:hover {{
    background-color: {v['accent2']};
    color: white;
}}
hr {{
    border-color: {v['border']};
}}
</style>
"""
