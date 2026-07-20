"""
engines/daily_checkup_engine.py
==================================
Calculation logic for the DAILY CHECK-UP section only.

This file is completely independent from engines/timesheet_engine.py —
it does its own file detection and its own calculations, on purpose, so
this section can never break (or be broken by) the Timesheet Generator.

What it does
------------
Given a Punch In/Out sheet, a Leave/Vacation sheet, and an Employee List
sheet, for a chosen date it classifies every employee into one of:

    - Complete             punched in AND out
    - Missing Punch Out    punched in, never punched out
    - Missing Punch In     punched out, but was never punched in
    - No Punch At All      no punch record at all that day

...and for every one of those, whether they have a leave/mission/WFH
record covering that day (and what kind).
"""

import datetime
import pandas as pd


class CheckupError(Exception):
    """Raised for any user-facing problem (missing columns, bad files, etc.)."""
    pass


# ── Step 1: figure out which uploaded file is which ──────────────────────────
def classify_files(file_dict):
    """
    file_dict: {filename: file-like object}. Returns (punch_file, leave_file,
    emp_file) as the same file-like objects, seeked back to position 0.
    """
    punch_file = leave_file = emp_file = None
    problems = []

    for fname, fobj in file_dict.items():
        try:
            fobj.seek(0)
            df_peek = pd.read_excel(fobj, nrows=3)
            df_peek.columns = df_peek.columns.str.strip()
            cols = [c.lower() for c in df_peek.columns]
            if "i/o" in cols:
                punch_file = fobj
            elif "vacation" in cols and "from" in cols:
                leave_file = fobj
            elif "title" in cols and "employees name" in cols:
                emp_file = fobj
        except Exception as e:
            problems.append(f"Could not read '{fname}': {e}")
        finally:
            fobj.seek(0)

    missing = []
    if not punch_file:
        missing.append("Punch In/Out sheet — needs a column named 'I/O'")
    if not leave_file:
        missing.append("Leave/Vacation sheet — needs columns 'Vacation' + 'From'")
    if not emp_file:
        missing.append("Employee List sheet — needs columns 'Employees Name' + 'Title'")

    if missing:
        msg = "Could not identify all 3 required files:\n- " + "\n- ".join(missing)
        if problems:
            msg += "\n\nAlso had trouble reading some files:\n- " + "\n- ".join(problems)
        raise CheckupError(msg)

    return punch_file, leave_file, emp_file


# ── Step 2: normalize a Code value into a consistent string key ──────────────
def norm_code(x):
    if pd.isna(x):
        return None
    s = str(x).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s if s else None


def _find_code_column(df):
    """Employee list files may label the ID column 'Code' (English) or
    'كود البصمة' (Arabic, 'fingerprint code'). Support both."""
    for candidate in ["Code", "كود البصمة"]:
        if candidate in df.columns:
            return candidate
    return None


# ── Step 3: load & clean the 3 dataframes ─────────────────────────────────────
def load_dataframes(punch_file, leave_file, emp_file):
    df_punch = pd.read_excel(punch_file)
    df_leave = pd.read_excel(leave_file)
    df_emp = pd.read_excel(emp_file)

    df_punch.columns = df_punch.columns.str.strip()
    df_leave.columns = df_leave.columns.str.strip()
    df_emp.columns = df_emp.columns.str.strip()

    # Punch file
    if "Code" not in df_punch.columns:
        raise CheckupError("The Punch In/Out sheet has no 'Code' column.")
    df_punch["Date"] = pd.to_datetime(df_punch["Date"], errors="coerce").dt.date
    df_punch["Time"] = pd.to_datetime(df_punch["Time"], errors="coerce").dt.time
    df_punch["CodeKey"] = df_punch["Code"].map(norm_code)
    df_punch = df_punch.dropna(subset=["Date", "CodeKey"])
    if df_punch.empty:
        raise CheckupError(
            "The Punch In/Out sheet has no valid rows after cleaning. "
            "Check the 'Date' and 'Code' columns."
        )

    # Leave file
    leave_code_col = _find_code_column(df_leave) or "Code"
    if leave_code_col not in df_leave.columns:
        raise CheckupError("The Leave/Vacation sheet has no employee code column.")
    df_leave["From"] = pd.to_datetime(df_leave["From"], errors="coerce")
    df_leave["To"] = pd.to_datetime(df_leave["To"], errors="coerce")
    df_leave["CodeKey"] = df_leave[leave_code_col].map(norm_code)

    # Employee list — Code column may be 'Code' or the Arabic 'كود البصمة'
    emp_code_col = _find_code_column(df_emp)
    if not emp_code_col:
        raise CheckupError(
            "The Employee List sheet needs an employee code column named "
            "'Code' or 'كود البصمة'."
        )
    df_emp["CodeKey"] = df_emp[emp_code_col].map(norm_code)
    df_emp["Employees Name"] = df_emp["Employees Name"].astype(str).str.strip()
    df_emp_master = df_emp[
        df_emp["CodeKey"].notna()
        & df_emp["Employees Name"].notna()
        & (df_emp["Employees Name"] != "")
        & (df_emp["Employees Name"].str.lower() != "nan")
    ].drop_duplicates(subset=["CodeKey"], keep="first").reset_index(drop=True)

    if df_emp_master.empty:
        raise CheckupError(
            "The Employee List sheet has no valid rows after cleaning. "
            "Check the code and 'Employees Name' columns."
        )

    emp_by_code = df_emp_master.set_index("CodeKey").to_dict("index")

    return df_punch, df_leave, emp_by_code


# ── Step 4: per-employee-per-day helpers ──────────────────────────────────────
def _fmt_time(t):
    return t.strftime("%H:%M") if t else ""


def _get_leave_for_date(df_leave, code_key, target_date):
    """Returns (has_leave, leave_type, leave_status) for one employee/date.
    If several leave records cover the date, they're joined with ' + '."""
    rows = df_leave[df_leave["CodeKey"] == code_key]
    matches = []
    for _, row in rows.iterrows():
        f, t = row["From"], row["To"]
        if pd.isna(f) or pd.isna(t):
            continue
        if f.date() <= target_date <= t.date():
            matches.append(row)
    if not matches:
        return False, "", ""
    types = " + ".join(sorted({str(m.get("Vacation", "")).strip() for m in matches}))
    statuses = " + ".join(sorted({str(m.get("Status", "")).strip() for m in matches if pd.notna(m.get("Status"))}))
    return True, types, statuses


# ── Step 5: build the report ──────────────────────────────────────────────────
def build_daily_report(file_dict):
    """
    file_dict: {filename: file-like object}, exactly 3 files.

    Returns (report_df, available_dates, stats)
      report_df columns: Date, Code, Name, Title, Department, Time In,
                          Time Out, Status, Has Leave, Leave Type, Leave Status
      available_dates: sorted list of every date found in the punch sheet
      stats: {"num_employees": int, "num_dates": int}
    """
    if len(file_dict) != 3:
        raise CheckupError(f"Expected exactly 3 files, got {len(file_dict)}.")

    punch_file, leave_file, emp_file = classify_files(file_dict)
    df_punch, df_leave, emp_by_code = load_dataframes(punch_file, leave_file, emp_file)

    available_dates = sorted(df_punch["Date"].dropna().unique().tolist())
    if not available_dates:
        raise CheckupError("No valid dates found in the Punch In/Out sheet.")

    roster = sorted(emp_by_code.items(), key=lambda kv: str(kv[1].get("Employees Name", "")))

    rows = []
    for date in available_dates:
        day_punches = df_punch[df_punch["Date"] == date]
        for code_key, info in roster:
            name = str(info.get("Employees Name", "")).strip()
            title = str(info.get("Title", "")).strip() or "—"
            dept = str(info.get("Department", "")).strip() or "—"
            code_display = str(info.get(_find_code_column_from_keys(info), code_key)).strip()

            person_day = day_punches[day_punches["CodeKey"] == code_key]
            ins = person_day[person_day["I/O"] == "Punch In"]["Time"].dropna().tolist()
            outs = person_day[person_day["I/O"] == "Punch Out"]["Time"].dropna().tolist()
            t_in = min(ins) if ins else None
            t_out = max(outs) if outs else None

            has_in, has_out = bool(t_in), bool(t_out)
            if has_in and has_out:
                status = "✅ Complete"
            elif has_in and not has_out:
                status = "⚠️ Missing Punch Out"
            elif has_out and not has_in:
                status = "⚠️ Missing Punch In"
            else:
                status = "🚫 No Punch At All"

            has_leave, leave_type, leave_status = _get_leave_for_date(df_leave, code_key, date)

            rows.append(
                {
                    "Date": date,
                    "Code": code_display,
                    "Name": name,
                    "Title": title,
                    "Department": dept,
                    "Time In": _fmt_time(t_in),
                    "Time Out": _fmt_time(t_out),
                    "Status": status,
                    "Has Leave": "Yes" if has_leave else "No",
                    "Leave Type": leave_type,
                    "Leave Status": leave_status,
                }
            )

    report_df = pd.DataFrame(rows)
    stats = {"num_employees": len(roster), "num_dates": len(available_dates)}
    return report_df, available_dates, stats


def _find_code_column_from_keys(info_dict):
    """Same idea as _find_code_column but for a plain dict of one employee's
    row (already extracted from emp_by_code)."""
    for candidate in ["Code", "كود البصمة"]:
        if candidate in info_dict:
            return candidate
    return "Code"
