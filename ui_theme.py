"""
ui_theme.py
============
Pure presentation only — CSS and small layout helpers shared by every
page so the app *looks* like one product. There is zero business logic
in this file; nothing here reads Excel files or touches employee data.
Each section's actual functionality lives entirely in its own page +
engine file and does not depend on this one.
"""

import streamlit as st

_CSS = """
<style>
/* Overall glossy gradient background */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(180deg, #f7f9fc 0%, #eef2f9 100%);
}

/* Cards */
.sa-card {
    background: linear-gradient(145deg, #ffffff, #f4f7fc);
    border: 1px solid #e3e8f2;
    border-radius: 16px;
    padding: 1.4rem 1.6rem;
    box-shadow: 0 4px 18px rgba(31, 45, 90, 0.06);
    margin-bottom: 1rem;
}

/* Glossy header banner */
.sa-hero {
    background: linear-gradient(120deg, #1f3c88 0%, #2d5bd7 55%, #4f8ef7 100%);
    border-radius: 20px;
    padding: 2.2rem 2rem;
    color: white;
    box-shadow: 0 10px 30px rgba(45, 91, 215, 0.25);
    margin-bottom: 1.6rem;
}
.sa-hero h1 {
    color: white;
    margin: 0 0 .3rem 0;
    font-size: 2rem;
}
.sa-hero p {
    color: #dce6fb;
    margin: 0;
    font-size: 1.02rem;
}

/* Section badge/pill */
.sa-pill {
    display: inline-block;
    background: #eaf0fe;
    color: #2d5bd7;
    border-radius: 999px;
    padding: 0.25rem 0.85rem;
    font-size: 0.8rem;
    font-weight: 600;
    margin-bottom: 0.6rem;
}

/* Buttons */
.stButton > button, .stDownloadButton > button {
    border-radius: 10px;
    font-weight: 600;
    padding: 0.6rem 1.2rem;
    border: none;
    background: linear-gradient(120deg, #2d5bd7, #4f8ef7);
    color: white;
    box-shadow: 0 4px 14px rgba(45, 91, 215, 0.25);
}
.stButton > button:hover, .stDownloadButton > button:hover {
    filter: brightness(1.07);
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #101a3a 0%, #1c2b5c 100%);
}
[data-testid="stSidebar"] * {
    color: #eef2ff !important;
}
</style>
"""


def apply_theme():
    st.markdown(_CSS, unsafe_allow_html=True)


def hero(title, subtitle, pill=None):
    pill_html = f'<span class="sa-pill">{pill}</span><br/>' if pill else ""
    st.markdown(
        f"""
        <div class="sa-hero">
            {pill_html}
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def card_start():
    st.markdown('<div class="sa-card">', unsafe_allow_html=True)


def card_end():
    st.markdown("</div>", unsafe_allow_html=True)
