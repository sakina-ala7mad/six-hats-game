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
            "input_bg": "#0a3157",
        }
    return {
        "bg": "#f4f6f8",
        "bg_card": PALETTE["white"],
        "text": PALETTE["navy"],
        "text_muted": "#3d4a5c",
        "border": PALETTE["mauve"],
        "accent": PALETTE["blue"],
        "accent2": PALETTE["coral"],
        "input_bg": "#ffffff",
    }


def inject_css(dark: bool) -> str:
    v = theme_vars(dark)
    return f"""
<style>
/* ---- base app background/text ---- */
.stApp {{
    background-color: {v['bg']};
    color: {v['text']};
}}

/* ---- force readable text everywhere EXCEPT our own colored
   pill/badge/hat-button elements, which set their own explicit
   contrast color and must not be overridden ---- */
.stApp *:not(.hc-pill):not(.hc-pill *):not(.hc-badge):not(.hc-badge *)
  :not(.hc-team-code):not([class*="hatbtn"]):not([class*="hatbtn"] *)
  :not(div.stButton):not(div.stButton *)
  :not([data-testid="stFormSubmitButton"]):not([data-testid="stFormSubmitButton"] *) {{
    color: {v['text']} !important;
}}

/* ---- headings / markdown text ---- */
h1, h2, h3, h4, h5, h6,
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] span,
[data-testid="stMarkdownContainer"] strong {{
    color: {v['text']} !important;
}}

/* ---- widget labels (e.g. "Your name", "Team code") ---- */
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label,
.stApp label {{
    color: {v['text']} !important;
}}

/* ---- captions / muted helper text ---- */
[data-testid="stCaptionContainer"] {{
    color: {v['text_muted']} !important;
}}

/* ---- text inputs / text areas ---- */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {{
    color: {v['text']} !important;
    background-color: {v['input_bg']} !important;
    border: 1px solid {v['border']} !important;
}}
[data-testid="stTextInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder {{
    color: {v['text_muted']} !important;
    opacity: 0.8;
}}

/* ---- radio button options ---- */
[data-testid="stRadio"] label p,
[data-testid="stRadio"] div[role="radiogroup"] label {{
    color: {v['text']} !important;
}}

/* ---- tabs ---- */
[data-testid="stTabs"] button p {{
    color: {v['text']} !important;
}}

/* ---- select dropdowns (menu options render in a page-level portal,
   so these rules are intentionally NOT scoped under .stApp) ---- */
[data-baseweb="popover"] li,
[data-baseweb="menu"] li,
[data-baseweb="select"] * {{
    color: {PALETTE['navy']} !important;
}}

/* ---- sidebar ---- */
[data-testid="stSidebar"] {{
    background-color: {v['bg_card']};
    border-right: 1px solid {v['border']};
}}

/* ---- cards / pills / badges (kept independent of forced text color) ---- */
.hc-card {{
    background-color: {v['bg_card']};
    border: 1px solid {v['border']};
    border-radius: 14px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
}}
.hc-card, .hc-card * {{
    color: {v['text']};
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

/* ---- buttons (default accent styling) ---- */
div.stButton > button,
div[data-testid="stFormSubmitButton"] button {{
    background-color: {v['accent']};
    color: white !important;
    border: none;
    border-radius: 10px;
    padding: 0.5rem 1.2rem;
    font-weight: 600;
}}
div.stButton > button *,
div[data-testid="stFormSubmitButton"] button * {{
    color: white !important;
}}
div.stButton > button:hover,
div[data-testid="stFormSubmitButton"] button:hover {{
    background-color: {v['accent2']};
    color: white !important;
}}

hr {{
    border-color: {v['border']};
}}
</style>
"""


def hat_button_css(hat_name: str, color: str, text_on: str, key: str, selected: bool) -> str:
    """CSS for one colored hat-picker button, targeted via Streamlit's
    key-based `.st-key-<key>` container class (Streamlit >= 1.36)."""
    border = "4px solid #ffffff" if selected else "2px solid transparent"
    return f"""
<style>
.st-key-{key} button {{
    background-color: {color} !important;
    color: {text_on} !important;
    border: {border} !important;
    box-shadow: {"0 0 0 2px " + PALETTE["navy"] if selected else "none"};
    width: 100%;
}}
.st-key-{key} button * {{
    color: {text_on} !important;
}}
.st-key-{key} button:hover {{
    filter: brightness(0.95);
}}
</style>
"""
