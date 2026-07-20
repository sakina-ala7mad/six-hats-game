"""
pages/2_Daily_Checkup.py
===========================
UI for the Daily Check-Up section ONLY.
Uses engines/daily_checkup_engine.py exclusively — does not import or
touch anything from the Timesheet Generator section.
"""

import io
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import streamlit as st
from ui_theme import apply_theme, hero, card_start, card_end
from engines.daily_checkup_engine import build_daily_report, CheckupError

st.set_page_config(page_title="Daily Check-Up", page_icon="✅", layout="wide")
apply_theme()

hero(
    "✅ Daily Check-Up",
    "See instantly who's missing a punch in, a punch out, or didn't attend at all — and whether they're on leave.",
    pill="SECTION 2",
)

with st.expander("What are the 3 files?", expanded=False):
    st.markdown(
        """
- **Punch In/Out sheet** — needs a column called **`I/O`**
- **Leave / Vacation sheet** — needs columns **`Vacation`** and **`From`**
- **Employee List sheet** — needs columns **`Employees Name`** and **`Title`**,
  plus an employee code column named **`Code`** or **`كود البصمة`**
        """
    )

card_start()
uploaded_files = st.file_uploader(
    "Upload all 3 Excel files here (select all 3 at once)",
    type=["xlsx", "xls"],
    accept_multiple_files=True,
    key="checkup_uploader",
)

if "checkup_report" not in st.session_state:
    st.session_state.checkup_report = None

if uploaded_files:
    if len(uploaded_files) != 3:
        st.warning(f"Please upload exactly 3 files. You've uploaded {len(uploaded_files)}.")
    else:
        st.success(f"3 files ready: {', '.join(f.name for f in uploaded_files)}")

        if st.button("🔍 Run Daily Check-Up", type="primary", use_container_width=True):
            file_dict = {f.name: io.BytesIO(f.getvalue()) for f in uploaded_files}
            try:
                with st.spinner("Reading files and matching records..."):
                    report_df, available_dates, stats = build_daily_report(file_dict)
                st.session_state.checkup_report = (report_df, available_dates, stats)
            except CheckupError as e:
                st.error(f"⚠️ {e}")
                st.session_state.checkup_report = None
            except Exception as e:
                st.error(f"❌ Something unexpected went wrong: {e}")
                st.session_state.checkup_report = None
else:
    st.info("Waiting for you to upload the 3 files above.")
card_end()

# ── Dashboard ──────────────────────────────────────────────────────────────────
if st.session_state.checkup_report:
    report_df, available_dates, stats = st.session_state.checkup_report

    st.subheader("📊 Dashboard")

    # Filters
    fcol1, fcol2, fcol3, fcol4 = st.columns([1.1, 1.3, 1.3, 1.6])

    with fcol1:
        date_options = ["All dates"] + [d.strftime("%d %b %Y") for d in available_dates]
        date_choice = st.selectbox("Date", date_options)

    with fcol2:
        status_options = sorted(report_df["Status"].unique().tolist())
        default_statuses = [s for s in status_options if "Complete" not in s]
        status_filter = st.multiselect("Status", status_options, default=default_statuses)

    with fcol3:
        dept_options = sorted(report_df["Department"].unique().tolist())
        dept_filter = st.multiselect("Department", dept_options, default=[])

    with fcol4:
        search = st.text_input("Search by name", placeholder="Type a name...")

    filtered = report_df.copy()
    if date_choice != "All dates":
        target = pd.to_datetime(date_choice, format="%d %b %Y").date()
        filtered = filtered[filtered["Date"] == target]
    if status_filter:
        filtered = filtered[filtered["Status"].isin(status_filter)]
    if dept_filter:
        filtered = filtered[filtered["Department"].isin(dept_filter)]
    if search:
        filtered = filtered[filtered["Name"].str.contains(search, case=False, na=False)]

    # Summary metrics (based on current filter's date scope, all statuses)
    scope_df = report_df.copy()
    if date_choice != "All dates":
        target = pd.to_datetime(date_choice, format="%d %b %Y").date()
        scope_df = scope_df[scope_df["Date"] == target]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("✅ Complete", int((scope_df["Status"] == "✅ Complete").sum()))
    m2.metric("⚠️ Missing Punch Out", int((scope_df["Status"] == "⚠️ Missing Punch Out").sum()))
    m3.metric("⚠️ Missing Punch In", int((scope_df["Status"] == "⚠️ Missing Punch In").sum()))
    m4.metric("🚫 No Punch At All", int((scope_df["Status"] == "🚫 No Punch At All").sum()))

    st.divider()

    display_df = filtered.copy()
    display_df["Date"] = display_df["Date"].apply(lambda d: d.strftime("%d %b %Y"))
    display_df = display_df.sort_values(["Date", "Status", "Name"])

    st.dataframe(
        display_df[
            ["Date", "Code", "Name", "Title", "Department", "Time In", "Time Out",
             "Status", "Has Leave", "Leave Type", "Leave Status"]
        ],
        use_container_width=True,
        hide_index=True,
        height=460,
    )

    st.caption(f"Showing {len(display_df)} of {len(report_df)} total records.")

    # Download filtered view as Excel
    out_buffer = io.BytesIO()
    display_df.to_excel(out_buffer, index=False, sheet_name="Daily Checkup")
    out_buffer.seek(0)
    st.download_button(
        label="⬇️ Download this view (.xlsx)",
        data=out_buffer,
        file_name="Daily_Checkup_Report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
