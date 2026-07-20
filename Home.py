"""
Home.py
========
Landing page. This is the entry point you run with:
    streamlit run Home.py

It has NO calculation logic of its own — it's just a friendly front door
that points to the two independent sections, which live in pages/ and
each have their own engine file.
"""

import streamlit as st
from ui_theme import apply_theme, hero, card_start, card_end

st.set_page_config(
    page_title="Staff Arabia HR Tools",
    page_icon="✨",
    layout="centered",
)
apply_theme()

hero(
    "✨ Staff Arabia HR Tools",
    "One place for your attendance workflows. Pick a tool from the sidebar, or click a card below.",
)

col1, col2 = st.columns(2)

with col1:
    card_start()
    st.markdown("### 🗓️ Timesheet Generator")
    st.write(
        "Upload attendance, employee, and vacation sheets — get back one "
        "fully formatted Excel timesheet, per employee, per day, with "
        "hours, overtime, and delays calculated automatically."
    )
    st.page_link("pages/1_Timesheet_Generator.py", label="Open Timesheet Generator →", icon="🗓️")
    card_end()

with col2:
    card_start()
    st.markdown("### ✅ Daily Check-Up")
    st.write(
        "Upload today's punch sheet, leave sheet, and employee list — "
        "instantly see who's missing a punch in, a punch out, or didn't "
        "show up at all, and whether they're on approved leave."
    )
    st.page_link("pages/2_Daily_Checkup.py", label="Open Daily Check-Up →", icon="✅")
    card_end()

st.divider()
st.caption(
    "Each tool above is fully self-contained — its files, its calculations, "
    "and its data never mix with the other tool."
)
