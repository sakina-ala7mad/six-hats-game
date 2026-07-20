"""
pages/1_Timesheet_Generator.py
=================================
UI for the Timesheet Generator section ONLY.
Uses engines/timesheet_engine.py exclusively — does not import or touch
anything from the Daily Check-Up section.
"""

import io
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from ui_theme import apply_theme, hero, card_start, card_end
from engines.timesheet_engine import generate_timesheet, TimesheetError, DEFAULT_WEEKEND_DAYS

st.set_page_config(page_title="Timesheet Generator", page_icon="🗓️", layout="centered")
apply_theme()

hero(
    "🗓️ Timesheet Generator",
    "Turn attendance, employee, and vacation sheets into one formatted Excel timesheet.",
    pill="SECTION 1",
)

with st.expander("What are the 3 files?", expanded=False):
    st.markdown(
        """
- **Attendance / System file** — needs a column called **`I/O`**
- **Employees Data file** — needs columns **`Employees Name`** and **`Title`**
- **Vacation Transaction file** — needs columns **`Vacation`** and **`From`**
        """
    )

with st.sidebar:
    st.header("⚙️ Timesheet Settings")
    st.caption("Defaults are fine for normal use.")
    workday_hrs = st.number_input(
        "Standard workday length (hours)", min_value=1.0, max_value=24.0, value=8.0, step=0.5
    )
    work_start = st.text_input("Official work start time (24h, e.g. 10:00)", value="10:00")

    st.caption("Weekend days:")
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    default_selected = [day_names[i] for i in sorted(DEFAULT_WEEKEND_DAYS)]
    selected_weekend_days = st.multiselect(
        "Days treated as weekend", day_names, default=default_selected, key="ts_weekend"
    )
    weekend_days = {day_names.index(d) for d in selected_weekend_days}

card_start()
uploaded_files = st.file_uploader(
    "Upload all 3 Excel files here (select all 3 at once)",
    type=["xlsx", "xls"],
    accept_multiple_files=True,
    key="ts_uploader",
)

if uploaded_files:
    if len(uploaded_files) != 3:
        st.warning(f"Please upload exactly 3 files. You've uploaded {len(uploaded_files)}.")
    else:
        st.success(f"3 files ready: {', '.join(f.name for f in uploaded_files)}")

        if st.button("🚀 Generate Timesheet", type="primary", use_container_width=True):
            file_dict = {f.name: io.BytesIO(f.getvalue()) for f in uploaded_files}
            progress_bar = st.progress(0, text="Starting...")

            def update_progress(current, total):
                progress_bar.progress(current / total, text=f"Processing employee {current}/{total}...")

            try:
                with st.spinner("Reading and validating files..."):
                    wb, output_filename, stats = generate_timesheet(
                        file_dict,
                        workday_hrs=workday_hrs,
                        work_start=work_start,
                        weekend_days=weekend_days,
                        progress_callback=update_progress,
                    )

                progress_bar.progress(1.0, text="Done!")
                st.success(
                    f"✅ Timesheet generated: **{stats['num_employees']} employees** "
                    f"× **{stats['num_days']} days** ({stats['month_str']})"
                )

                buffer = io.BytesIO()
                wb.save(buffer)
                buffer.seek(0)

                st.download_button(
                    label="⬇️ Download Timesheet (.xlsx)",
                    data=buffer,
                    file_name=output_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            except TimesheetError as e:
                st.error(f"⚠️ {e}")
            except Exception as e:
                st.error(f"❌ Something unexpected went wrong: {e}")
else:
    st.info("Waiting for you to upload the 3 files above.")
card_end()
