import streamlit as st
import pandas as pd
import numpy as np
import io
import re
import base64
import json
import os
from datetime import date, datetime
import anthropic

# ── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="VITS Attendance · MPOnline",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",  # always open
)

# ── CONSTANTS ────────────────────────────────────────────────────────────────
THRESHOLD_PCT     = 0.75          # 75% eligibility
BOT_KEYWORDS      = ["otter.ai", "fireflies", "notetaker"]
STAFF_DOMAINS     = ["mponline.gov.in"]
DATA_DIR          = os.path.join(os.path.dirname(__file__), "data")
LOGO_PATH         = os.path.join(DATA_DIR, "logo.png")
MASTER_PATH       = os.path.join(DATA_DIR, "master_students.csv")
BATCH_PATH        = os.path.join(DATA_DIR, "batch_info.csv")
LOG_KEY           = "att_log"       # session_state key for attendance log DataFrame
PROG_SHORT        = {
    "Certification in Advanced Software Engineering & AI foundation": "SE + AI Foundation",
    "Advanced Software Engineering & Development Internship":         "Adv. Software Eng.",
    "AI/ML Internship Program":                                       "AI / ML",
    "Digital Marketing Internship Program":                          "Digital Marketing",
}

# ── GLOBAL CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Hide default Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1rem !important; }

/* ── Custom topbar ── */
.topbar {
    background: linear-gradient(90deg, #1B3A6B 0%, #2E5FA3 100%);
    border-radius: 12px;
    padding: 14px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;
    box-shadow: 0 4px 18px rgba(27,58,107,0.18);
}
.topbar-right {
    font-size: 0.78rem;
    color: rgba(255,255,255,0.65);
    text-align: right;
    line-height: 1.5;
}

/* ── KPI cards ── */
.kpi-card {
    background: white;
    border-radius: 10px;
    padding: 18px 20px;
    border: 1px solid #D0D5E8;
    border-left: 4px solid #2E5FA3;
    box-shadow: 0 2px 10px rgba(27,58,107,0.08);
    text-align: center;
}
.kpi-card.green { border-left-color: #1A7A4A; }
.kpi-card.amber { border-left-color: #E8920A; }
.kpi-card.red   { border-left-color: #C0392B; }
.kpi-card.blue  { border-left-color: #2E5FA3; }
.kpi-val  { font-size: 2.2rem; font-weight: 800; color: #1B3A6B; line-height: 1; margin: 4px 0; font-family: monospace; }
.kpi-lbl  { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; color: #6B7280; }
.kpi-sub  { font-size: 0.72rem; color: #9CA3AF; margin-top: 3px; }

/* ── Section title ── */
.sec-title {
    font-size: 0.78rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.08em; color: #6B7280; margin: 0 0 12px 0;
    padding-left: 10px; border-left: 3px solid #FF6B35;
}

/* ── Status badges ── */
.badge {
    display: inline-block; padding: 3px 10px; border-radius: 20px;
    font-size: 0.72rem; font-weight: 700;
}
.badge-present  { background: #E8F5EE; color: #1A7A4A; }
.badge-late     { background: #FFF3DC; color: #E8920A; }
.badge-absent   { background: #FDEDEC; color: #C0392B; }
.badge-eligible { background: #E8F5EE; color: #1A7A4A; }
.badge-atrisk   { background: #FFF3DC; color: #E8920A; }
.badge-danger   { background: #FDEDEC; color: #C0392B; }
.badge-nodata   { background: #F3F4F6; color: #9CA3AF; }

/* ── Upload hint ── */
.upload-hint {
    background: #EFF6FF; border: 1px dashed #93C5FD;
    border-radius: 10px; padding: 16px 18px;
    font-size: 0.84rem; color: #1E40AF; margin-bottom: 14px;
    line-height: 1.7;
}
.upload-hint strong { color: #1B3A6B; }

/* ── Alert boxes ── */
.alert { padding: 12px 16px; border-radius: 8px; font-size: 0.84rem; margin-bottom: 10px; }
.alert-success { background: #E8F5EE; color: #1A7A4A; border: 1px solid #86EFAC; }
.alert-warning { background: #FFF3DC; color: #92400E; border: 1px solid #FCD34D; }
.alert-error   { background: #FDEDEC; color: #991B1B; border: 1px solid #FCA5A5; }
.alert-info    { background: #EFF6FF; color: #1E40AF; border: 1px solid #93C5FD; }

/* ── Table styling ── */
.styled-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
.styled-table th {
    background: #1B3A6B; color: white; padding: 9px 12px;
    text-align: left; font-weight: 600; font-size: 0.74rem;
    text-transform: uppercase; letter-spacing: 0.04em;
}
.styled-table td { padding: 8px 12px; border-bottom: 1px solid #E5E7EB; }
.styled-table tr:hover td { background: #F9FAFB; }
.styled-table tr:last-child td { border-bottom: none; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] { background: #0D1B2A !important; }
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] h4,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] div { color: rgba(255,255,255,0.85) !important; }
section[data-testid="stSidebar"] input[type="number"],
section[data-testid="stSidebar"] input[type="text"],
section[data-testid="stSidebar"] input[type="date"],
section[data-testid="stSidebar"] input {
    color: #111111 !important;
    -webkit-text-fill-color: #111111 !important;
    background: #FFFFFF !important;
    border-radius: 6px !important;
}
section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {
    background: rgba(255,255,255,0.12) !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
}
section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] span { color: #FFFFFF !important; }
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stNumberInput label,
section[data-testid="stSidebar"] .stDateInput label { color: rgba(255,255,255,0.55) !important; font-size:0.75rem !important; }

/* ── Progress bars ── */
.prog-row { display: flex; align-items: center; gap: 10px; }
.prog-bar { flex: 1; height: 7px; background: #E5E7EB; border-radius: 4px; overflow: hidden; }
.prog-fill { height: 100%; border-radius: 4px; transition: width 0.5s ease; }
.prog-val  { font-size: 0.78rem; font-weight: 700; min-width: 42px; text-align: right; font-family: monospace; }

/* ── AI panel ── */
.ai-wrap {
    background: linear-gradient(135deg, #0D1B2A 0%, #1B3A6B 100%);
    border-radius: 12px; padding: 22px; color: white;
}
.ai-label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(255,255,255,0.45); margin-bottom: 4px; }
.ai-title { font-size: 1.05rem; font-weight: 700; margin-bottom: 4px; }
.ai-sub   { font-size: 0.82rem; color: rgba(255,255,255,0.6); margin-bottom: 16px; }
.ai-out   {
    background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.12);
    border-radius: 8px; padding: 16px; font-size: 0.84rem;
    color: rgba(255,255,255,0.9); line-height: 1.75; white-space: pre-wrap;
    min-height: 80px; max-height: 400px; overflow-y: auto;
}

/* ── Step indicators ── */
.steps { display: flex; gap: 0; margin-bottom: 20px; border-radius: 8px; overflow: hidden; }
.step { flex: 1; padding: 10px 8px; text-align: center; font-size: 0.76rem; font-weight: 600; background: #E5E7EB; color: #6B7280; }
.step.done   { background: #1A7A4A; color: white; }
.step.active { background: #1B3A6B; color: white; }
</style>
""", unsafe_allow_html=True)


# ── HELPERS ──────────────────────────────────────────────────────────────────
@st.cache_data
def load_master():
    df = pd.read_csv(MASTER_PATH, dtype=str)
    df.columns = ['App_No','Name','Email','Prog_Code','Prog_Name','Batch','Timing','SME']
    df = df.fillna('')
    return df

@st.cache_data
def load_batches():
    df = pd.read_csv(BATCH_PATH, dtype=str)
    df['Enrolled'] = pd.to_numeric(df['Enrolled'], errors='coerce').fillna(0).astype(int)
    return df

def get_logo_b64():
    with open(LOGO_PATH, "rb") as f:
        return base64.b64encode(f.read()).decode()

def parse_duration_minutes(s):
    """Parse '1h 54m 46s' → total minutes (float)."""
    if not s or not isinstance(s, str):
        return 0.0
    h = int(m.group(1)) if (m := re.search(r'(\d+)h', s)) else 0
    mn = int(m.group(1)) if (m := re.search(r'(\d+)m', s)) else 0
    sc = int(m.group(1)) if (m := re.search(r'(\d+)s', s)) else 0
    return round(h * 60 + mn + sc / 60, 1)

def clean_name(raw):
    """Remove (External), (Unverified), roll numbers from Teams name."""
    return re.sub(r'\s*\([^)]*\)\s*', ' ', str(raw)).strip()

def is_excluded(name, email):
    n, e = name.lower(), email.lower()
    return any(k in n for k in BOT_KEYWORDS) or any(d in e for d in STAFF_DOMAINS)

def match_student(raw_name, master_df):
    """Return App_No if name matches master, else None."""
    cleaned = clean_name(raw_name).lower().strip()
    # Exact match on cleaned name
    mask = master_df['Name'].str.lower().str.strip() == cleaned
    if mask.any():
        return master_df.loc[mask.idxmax(), 'App_No']
    # Partial match — name contains or is contained
    for _, row in master_df.iterrows():
        master_lower = row['Name'].lower().strip()
        if master_lower in cleaned or cleaned in master_lower:
            return row['App_No']
    return None

def parse_teams_csv(text):
    """Parse Teams attendance CSV → list of dicts (Section 2 participants only)."""
    lines = text.splitlines()
    in_participants = False
    rows = []
    for line in lines:
        if line.startswith('2. Participants'):
            in_participants = True
            continue
        if in_participants and line.startswith('3. In-Meeting'):
            break
        if not in_participants:
            continue
        if line.startswith('Name,'):
            continue
        if not line.strip().replace(',', ''):
            continue
        # Parse CSV line (handle quoted commas)
        cols, cur, in_q = [], '', False
        for ch in line:
            if ch == '"':
                in_q = not in_q
            elif ch == ',' and not in_q:
                cols.append(cur.strip())
                cur = ''
            else:
                cur += ch
        cols.append(cur.strip())
        if len(cols) >= 4:
            rows.append(cols)
    return rows

def status_label(dur_min, threshold_min):
    if dur_min >= threshold_min:
        return "✅ Present"
    elif dur_min >= 1:
        return "⚠ Late"
    else:
        return "❌ Absent"

def attendance_status(pct):
    if pct is None:
        return "No Data"
    if pct >= THRESHOLD_PCT:
        return "✅ Eligible"
    elif pct >= 0.50:
        return "⚠ At Risk"
    else:
        return "❌ Will Not Qualify"

def pct_bar_html(pct_float, color=None):
    if pct_float is None:
        return '<span style="color:#9CA3AF;font-size:0.78rem">No data</span>'
    p = round(pct_float * 100, 1)
    if color is None:
        color = "#1A7A4A" if p >= 75 else ("#E8920A" if p >= 50 else "#C0392B")
    return f'''<div class="prog-row">
        <div class="prog-bar"><div class="prog-fill" style="width:{p}%;background:{color}"></div></div>
        <span class="prog-val" style="color:{color}">{p:.1f}%</span>
    </div>'''

def badge_html(text):
    cls_map = {
        "✅ Present":         "badge-present",
        "⚠ Late":            "badge-late",
        "❌ Absent":          "badge-absent",
        "✅ Eligible":        "badge-eligible",
        "⚠ At Risk":         "badge-atrisk",
        "❌ Will Not Qualify":"badge-danger",
        "No Data":            "badge-nodata",
    }
    cls = cls_map.get(text, "badge-nodata")
    return f'<span class="badge {cls}">{text}</span>'

def init_log():
    if LOG_KEY not in st.session_state:
        st.session_state[LOG_KEY] = pd.DataFrame(columns=[
            'Date','Batch','Session','App_No','Raw_Name','Clean_Name',
            'Email','Dur_Min','Dur_Raw','Status','Matched'
        ])

def get_log():
    return st.session_state[LOG_KEY]

def append_log(rows_df):
    existing = get_log()
    st.session_state[LOG_KEY] = pd.concat([existing, rows_df], ignore_index=True)

def compute_summary(master_df, log_df):
    """Per (App_No, Batch) attendance summary."""
    rows = []
    for _, stu in master_df.iterrows():
        app_no = stu['App_No']
        batch  = stu['Batch']
        sub = log_df[(log_df['App_No'] == app_no) & (log_df['Batch'] == batch)]
        sessions_held = log_df[log_df['Batch'] == batch]['Session'].nunique()
        present = (sub['Status'] == '✅ Present').sum()
        late    = (sub['Status'] == '⚠ Late').sum()
        absent  = (sub['Status'] == '❌ Absent').sum()
        attend_pct = (present / sessions_held) if sessions_held > 0 else None
        rows.append({
            'App_No': app_no, 'Name': stu['Name'], 'Email': stu['Email'],
            'Batch': batch, 'Program': stu['Prog_Name'], 'SME': stu['SME'],
            'Sessions_Held': sessions_held, 'Present': present,
            'Late': late, 'Absent': absent,
            'Attend_Pct': attend_pct,
            'Status': attendance_status(attend_pct)
        })
    return pd.DataFrame(rows)

def export_excel(master_df, log_df, summary_df):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
        wb = writer.book

        # Formats
        hdr_fmt = wb.add_format({'bold':True,'bg_color':'#1B3A6B','font_color':'white',
                                  'font_size':10,'border':1,'align':'center'})
        green_fmt = wb.add_format({'bg_color':'#E8F5EE','font_color':'#1A7A4A','bold':True,'border':1})
        amber_fmt = wb.add_format({'bg_color':'#FFF3DC','font_color':'#92400E','bold':True,'border':1})
        red_fmt   = wb.add_format({'bg_color':'#FDEDEC','font_color':'#991B1B','bold':True,'border':1})
        pct_fmt   = wb.add_format({'num_format':'0.0%','border':1,'align':'center'})
        cell_fmt  = wb.add_format({'border':1,'font_size':9})
        mono_fmt  = wb.add_format({'border':1,'font_size':9,'font_name':'Courier New'})
        alt_fmt   = wb.add_format({'border':1,'font_size':9,'bg_color':'#F9FAFB'})

        def write_header(ws, headers, widths):
            for c, (h, w) in enumerate(zip(headers, widths)):
                ws.write(0, c, h, hdr_fmt)
                ws.set_column(c, c, w)

        # ── Sheet 1: Attendance Log ──────────────────────────────────────
        ws1 = writer.sheets.get('Attendance Log') or wb.add_worksheet('Attendance Log')
        writer.sheets['Attendance Log'] = ws1
        log_cols = ['Date','Batch','Session','App_No','Clean_Name','Email','Dur_Min','Dur_Raw','Status']
        log_hdrs = ['Date','Batch','Session','App No.','Student Name','Email','Duration (min)','Duration (raw)','Status']
        log_widths = [12,10,9,16,28,32,14,14,16]
        write_header(ws1, log_hdrs, log_widths)
        if not log_df.empty:
            for r, row in log_df[log_cols].iterrows():
                fmt = alt_fmt if r % 2 == 0 else cell_fmt
                for c, v in enumerate(row):
                    if log_cols[c] == 'Status':
                        sf = green_fmt if '✅ Present' in str(v) else (amber_fmt if '⚠' in str(v) else red_fmt)
                        ws1.write(r+1, c, v, sf)
                    else:
                        ws1.write(r+1, c, v, mono_fmt if c in [0,1,2,3] else fmt)

        # ── Sheet 2: Student Summary ─────────────────────────────────────
        ws2 = wb.add_worksheet('Student Summary')
        writer.sheets['Student Summary'] = ws2
        sum_hdrs  = ['App No.','Name','Email','Batch','Program','SME','Sessions Held','Present','Late','Absent','Attend %','Status']
        sum_cols  = ['App_No','Name','Email','Batch','Program','SME','Sessions_Held','Present','Late','Absent','Attend_Pct','Status']
        sum_widths= [16,28,32,10,40,22,14,9,9,9,12,22]
        write_header(ws2, sum_hdrs, sum_widths)
        if not summary_df.empty:
            for r, row in summary_df[sum_cols].iterrows():
                fmt = alt_fmt if r % 2 == 0 else cell_fmt
                for c, col in enumerate(sum_cols):
                    v = row[col]
                    if col == 'Attend_Pct':
                        ws2.write_number(r+1, c, float(v), pct_fmt) if v is not None else ws2.write_blank(r+1, c, None, pct_fmt)
                    elif col == 'Status':
                        sf = green_fmt if '✅ Eligible' in str(v) else (amber_fmt if '⚠' in str(v) else (red_fmt if '❌' in str(v) else cell_fmt))
                        ws2.write(r+1, c, v, sf)
                    else:
                        ws2.write(r+1, c, str(v) if v else '', mono_fmt if c in [0,3] else fmt)

        # ── Sheet 3: At-Risk ─────────────────────────────────────────────
        ws3 = wb.add_worksheet('At-Risk Report')
        writer.sheets['At-Risk Report'] = ws3
        risk_df = summary_df[summary_df['Status'].isin(['⚠ At Risk','❌ Will Not Qualify'])]
        risk_hdrs  = ['App No.','Name','Email','Batch','Program','SME','Attend %','Status']
        risk_cols  = ['App_No','Name','Email','Batch','Program','SME','Attend_Pct','Status']
        risk_widths= [16,28,32,10,40,22,12,22]
        write_header(ws3, risk_hdrs, risk_widths)
        for r, row in risk_df[risk_cols].reset_index(drop=True).iterrows():
            fmt = alt_fmt if r % 2 == 0 else cell_fmt
            for c, col in enumerate(risk_cols):
                v = row[col]
                if col == 'Attend_Pct':
                    ws3.write_number(r+1, c, float(v), pct_fmt) if v is not None else ws3.write_blank(r+1, c, None, pct_fmt)
                elif col == 'Status':
                    sf = amber_fmt if '⚠' in str(v) else red_fmt
                    ws3.write(r+1, c, v, sf)
                else:
                    ws3.write(r+1, c, str(v) if v else '', mono_fmt if c in [0,3] else fmt)

        # ── Sheet 4: Batch Summary ───────────────────────────────────────
        ws4 = wb.add_worksheet('Batch Summary')
        writer.sheets['Batch Summary'] = ws4
        b_hdrs  = ['Batch','Program','SME','Timing','Enrolled','Sessions Run','Eligible','At Risk','Will Not Qualify','Eligible %']
        b_widths= [10,40,22,16,10,13,10,10,18,14]
        write_header(ws4, b_hdrs, b_widths)
        batches_df = load_batches()
        log_grp = log_df.groupby('Batch')['Session'].nunique().reset_index() if not log_df.empty else pd.DataFrame(columns=['Batch','Session'])
        for r, brow in batches_df.iterrows():
            b = brow['Batch']
            b_sum = summary_df[summary_df['Batch'] == b] if not summary_df.empty else pd.DataFrame()
            sess_run = log_grp.loc[log_grp['Batch']==b,'Session'].values[0] if len(log_grp) and b in log_grp['Batch'].values else 0
            elig  = (b_sum['Status'] == '✅ Eligible').sum() if len(b_sum) else 0
            risk  = (b_sum['Status'] == '⚠ At Risk').sum()  if len(b_sum) else 0
            fail  = (b_sum['Status'] == '❌ Will Not Qualify').sum() if len(b_sum) else 0
            ep    = elig / int(brow['Enrolled']) if int(brow['Enrolled']) > 0 and sess_run > 0 else None
            vals  = [b, brow['Program'], brow['SME'], brow['Timing'], int(brow['Enrolled']), sess_run, elig, risk, fail, ep]
            fmt   = alt_fmt if r % 2 == 0 else cell_fmt
            for c, v in enumerate(vals):
                if c == 9:
                    ws4.write_number(r+1, c, float(v), pct_fmt) if v is not None else ws4.write_blank(r+1, c, None, pct_fmt)
                else:
                    ws4.write(r+1, c, v, fmt)

        # ── Sheet 5: Session-wise pivot ──────────────────────────────────
        if not log_df.empty:
            ws5 = wb.add_worksheet('Session Pivot')
            writer.sheets['Session Pivot'] = ws5
            pivot_hdrs = ['Date','Batch','Session','Total Students','Present','Late','Absent','Attendance Rate']
            write_header(ws5, pivot_hdrs, [12,10,9,14,10,10,10,14])
            pivot = log_df.groupby(['Date','Batch','Session']).agg(
                Total=('Status','count'),
                Present=('Status', lambda x: (x=='✅ Present').sum()),
                Late=('Status', lambda x: (x=='⚠ Late').sum()),
                Absent=('Status', lambda x: (x=='❌ Absent').sum()),
            ).reset_index()
            pivot['Rate'] = pivot['Present'] / pivot['Total']
            for r, row in pivot.iterrows():
                fmt = alt_fmt if r % 2 == 0 else cell_fmt
                ws5.write(r+1, 0, str(row['Date']), fmt)
                ws5.write(r+1, 1, row['Batch'], fmt)
                ws5.write(r+1, 2, row['Session'], fmt)
                ws5.write(r+1, 3, row['Total'], fmt)
                ws5.write(r+1, 4, row['Present'], fmt)
                ws5.write(r+1, 5, row['Late'], fmt)
                ws5.write(r+1, 6, row['Absent'], fmt)
                ws5.write_number(r+1, 7, float(row['Rate']), pct_fmt) if row['Rate'] is not None else ws5.write_blank(r+1, 7, None, pct_fmt)

    return buf.getvalue()


# ── TOPBAR ───────────────────────────────────────────────────────────────────
def render_topbar():
    logo_b64 = get_logo_b64()
    log_df = get_log()
    total_sessions = log_df['Session'].nunique() if not log_df.empty else 0
    total_records  = len(log_df)
    st.markdown(f"""
    <div class="topbar">
        <img src="data:image/png;base64,{logo_b64}" style="height:46px;object-fit:contain;" alt="MPOnline Logo">
        <div class="topbar-right">
            <strong style="color:white;font-size:0.9rem">VITS Attendance Intelligence</strong><br>
            Skills Development Vertical &nbsp;·&nbsp; {total_sessions} sessions logged &nbsp;·&nbsp; {total_records:,} records
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── SIDEBAR ──────────────────────────────────────────────────────────────────
def render_sidebar(master_df, batches_df):
    with st.sidebar:
        st.markdown("### ⚙️ Session Configuration")
        st.caption("← Click arrow at screen edge to hide/show this panel")
        st.markdown("---")

        batch_options = batches_df['Batch'].tolist()
        batch_labels  = [f"{b}" for b in batch_options]
        selected_batch_idx = st.selectbox(
            "Batch", range(len(batch_options)),
            format_func=lambda i: f"{batch_options[i]} — {PROG_SHORT.get(batches_df.iloc[i]['Program'], batches_df.iloc[i]['Program'][:30])}",
            key="sidebar_batch"
        )
        selected_batch = batch_options[selected_batch_idx]
        batch_row = batches_df[batches_df['Batch'] == selected_batch].iloc[0]

        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.07);border-radius:8px;padding:12px 14px;margin:8px 0;font-size:0.8rem;line-height:1.8;">
        <strong>Program:</strong> {PROG_SHORT.get(batch_row['Program'], batch_row['Program'])}<br>
        <strong>SME:</strong> {batch_row['SME']}<br>
        <strong>Timing:</strong> {batch_row['Timing']}<br>
        <strong>Enrolled:</strong> {batch_row['Enrolled']} students
        </div>
        """, unsafe_allow_html=True)

        session_no   = st.number_input("Session Number", min_value=1, max_value=300, value=1, key="sidebar_session")
        session_date = st.date_input("Session Date", value=date.today(), key="sidebar_date")
        sched_dur    = st.number_input("Scheduled Duration (min)", min_value=30, max_value=360, value=120, step=15, key="sidebar_dur")
        threshold_min = round(sched_dur * THRESHOLD_PCT)

        st.markdown(f"""
        <div style="background:rgba(255,107,53,0.15);border:1px solid rgba(255,107,53,0.3);border-radius:8px;padding:10px 12px;margin-top:8px;font-size:0.78rem;line-height:1.8;">
        <strong style="color:#FF6B35">Threshold:</strong> {threshold_min} min = {int(THRESHOLD_PCT*100)}% of {sched_dur} min<br>
        <span style="color:rgba(255,255,255,0.5)">≥{threshold_min}m → Present &nbsp;|&nbsp; 1–{threshold_min-1}m → Late</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📊 Quick Stats")
        log_df = get_log()
        total_rec = len(log_df)
        total_sess = log_df['Session'].nunique() if not log_df.empty else 0
        st.markdown(f"""
        <div style="font-size:0.82rem;line-height:2;">
        Records logged: <strong>{total_rec:,}</strong><br>
        Sessions committed: <strong>{total_sess}</strong><br>
        Threshold: <strong>{int(THRESHOLD_PCT*100)}%</strong>
        </div>
        """, unsafe_allow_html=True)

        return selected_batch, int(session_no), session_date, int(sched_dur), threshold_min


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — IMPORT & PROCESS
# ══════════════════════════════════════════════════════════════════════════════
def tab_import(master_df, selected_batch, session_no, session_date, sched_dur, threshold_min):
    st.markdown('<p class="sec-title">Import & Process Teams Attendance CSV</p>', unsafe_allow_html=True)

    # Step indicator
    step = st.session_state.get('import_step', 1)
    st.markdown(f"""
    <div class="steps">
        <div class="step {'done' if step>1 else 'active' if step==1 else ''}">1 · Upload CSV</div>
        <div class="step {'done' if step>2 else 'active' if step==2 else ''}">2 · Validate</div>
        <div class="step {'done' if step>3 else 'active' if step==3 else ''}">3 · Review</div>
        <div class="step {'active' if step==4 else 'done' if step>4 else ''}">4 · Commit</div>
    </div>
    """, unsafe_allow_html=True)

    # Instructions
    with st.expander("📖 How to get the CSV from Teams", expanded=(step == 1)):
        st.markdown("""
**After your class ends — follow these exact steps:**

1. Open **Microsoft Teams** → click **Calendar** in the left panel
2. Find the meeting → click it to open details
3. Click the **Recap** tab at the top
4. Look for **Attendance** → click the **⬇ Download** button
5. Save the `.csv` file to your computer
6. **Rename it:** `BATCHCODE_DDMMYYYY.csv` → e.g. `B3A_25052026.csv`
7. Upload it below ↓

> ⚠ **Wait ~5 minutes after the class before downloading** — Teams takes time to generate the full report.
        """)

    # Upload
    st.markdown('<p class="sec-title">Upload Teams CSV</p>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="upload-hint">
    <strong>Session being processed:</strong> &nbsp;
    Batch <strong>{selected_batch}</strong> &nbsp;·&nbsp;
    Session <strong>{session_no}</strong> &nbsp;·&nbsp;
    Date <strong>{session_date.strftime('%d %b %Y')}</strong> &nbsp;·&nbsp;
    Threshold <strong>{threshold_min} min</strong> ({int(THRESHOLD_PCT*100)}% of {sched_dur} min)<br>
    <span style="font-size:0.78rem">Change these in the sidebar ←</span>
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Drop the Teams attendance CSV here",
        type=['csv', 'txt'],
        key="csv_upload",
        label_visibility="collapsed"
    )

    if not uploaded:
        st.session_state['import_step'] = 1
        st.session_state.pop('pending_df', None)
        return

    st.session_state['import_step'] = 2

    # Parse
    text = uploaded.read().decode('utf-8-sig', errors='replace')
    raw_rows = parse_teams_csv(text)

    if not raw_rows:
        st.markdown('<div class="alert alert-error">❌ No participants found in Section 2 of this CSV. Make sure you uploaded a Teams attendance report, not another file.</div>', unsafe_allow_html=True)
        return

    # Process rows
    processed = []
    bot_count, unmatched = 0, 0
    for cols in raw_rows:
        raw_name = cols[0] if len(cols) > 0 else ''
        email    = cols[4] if len(cols) > 4 else ''
        dur_raw  = cols[3] if len(cols) > 3 else ''

        if is_excluded(raw_name, email):
            bot_count += 1
            continue

        dur_min  = parse_duration_minutes(dur_raw)
        cleaned  = clean_name(raw_name)
        app_no   = match_student(raw_name, master_df[master_df['Batch'] == selected_batch])
        if not app_no:
            app_no = match_student(raw_name, master_df)  # try all batches
        status   = status_label(dur_min, threshold_min)

        if not app_no:
            unmatched += 1

        processed.append({
            'Date':       str(session_date),
            'Batch':      selected_batch,
            'Session':    session_no,
            'App_No':     app_no or '',
            'Raw_Name':   raw_name,
            'Clean_Name': cleaned,
            'Email':      email,
            'Dur_Min':    dur_min,
            'Dur_Raw':    dur_raw,
            'Status':     status,
            'Matched':    bool(app_no),
        })

    pending_df = pd.DataFrame(processed)

    # Validation summary
    st.markdown("---")
    st.markdown('<p class="sec-title">Validation Report</p>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    present_n = (pending_df['Status'] == '✅ Present').sum()
    late_n    = (pending_df['Status'] == '⚠ Late').sum()
    absent_n  = (pending_df['Status'] == '❌ Absent').sum()

    with c1:
        st.markdown(f'<div class="kpi-card green"><div class="kpi-lbl">Present</div><div class="kpi-val">{present_n}</div><div class="kpi-sub">≥{threshold_min} min</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="kpi-card amber"><div class="kpi-lbl">Late</div><div class="kpi-val">{late_n}</div><div class="kpi-sub">< {threshold_min} min</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="kpi-card red"><div class="kpi-lbl">Absent</div><div class="kpi-val">{absent_n}</div><div class="kpi-sub">Not in report</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="kpi-card blue"><div class="kpi-lbl">Total</div><div class="kpi-val">{len(pending_df)}</div><div class="kpi-sub">{bot_count} bots excluded</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    if bot_count:
        st.markdown(f'<div class="alert alert-info">ℹ {bot_count} bot/staff entry(ies) automatically excluded (Otter.ai, Fireflies, mponline.gov.in).</div>', unsafe_allow_html=True)
    if unmatched:
        st.markdown(f'<div class="alert alert-warning">⚠ {unmatched} student name(s) could not be matched to Master Data. Check the "Matched?" column below — edit the Clean Name and re-run if needed.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="alert alert-success">✅ All {len(pending_df)} students matched to Master Data. Ready to commit.</div>', unsafe_allow_html=True)

    # Editable preview
    st.markdown("---")
    st.markdown('<p class="sec-title">Preview & Edit Before Committing</p>', unsafe_allow_html=True)
    st.caption("You can edit the 'Clean Name' column to fix any mismatches, then click Commit.")

    edit_df = pending_df[['Clean_Name','Raw_Name','Dur_Min','Dur_Raw','Status','Matched','App_No']].copy()
    edit_df.columns = ['Clean Name (edit to fix)','Raw Name (from Teams)','Duration (min)','Duration (raw)','Status','Matched?','App No.']

    edited = st.data_editor(
        edit_df,
        use_container_width=True,
        hide_index=True,
        disabled=['Raw Name (from Teams)','Duration (min)','Duration (raw)','Status','Matched?','App No.'],
        column_config={
            'Status': st.column_config.TextColumn('Status', width='medium'),
            'Matched?': st.column_config.CheckboxColumn('Matched?', width='small'),
            'Duration (min)': st.column_config.NumberColumn('Duration (min)', format='%.1f min', width='small'),
        },
        key="edit_table"
    )

    # Re-match after edits
    pending_df['Clean_Name'] = edited['Clean Name (edit to fix)'].values
    for i, row in pending_df.iterrows():
        if not row['Matched']:
            new_app = match_student(row['Clean_Name'], master_df[master_df['Batch'] == selected_batch])
            if new_app:
                pending_df.at[i, 'App_No']  = new_app
                pending_df.at[i, 'Matched'] = True

    st.session_state['pending_df'] = pending_df
    st.session_state['import_step'] = 3

    # Commit button
    st.markdown("---")
    col_commit, col_dl, _ = st.columns([2, 2, 4])
    with col_commit:
        if st.button("✅ Commit to Attendance Log", type="primary", use_container_width=True):
            log_df = get_log()
            # Check for existing session
            if not log_df.empty:
                dup = log_df[(log_df['Batch'] == selected_batch) &
                             (log_df['Session'] == session_no) &
                             (log_df['Date'] == str(session_date))]
                if not dup.empty:
                    st.warning(f"Session {session_no} for {selected_batch} on {session_date} already exists. Remove it from the log first if you want to re-commit.")
                    return
            commit_cols = ['Date','Batch','Session','App_No','Raw_Name','Clean_Name','Email','Dur_Min','Dur_Raw','Status','Matched']
            append_log(pending_df[commit_cols])
            st.session_state['import_step'] = 4
            st.session_state.pop('pending_df', None)
            st.success(f"✅ {len(pending_df)} records committed for {selected_batch} Session {session_no} on {session_date}.")
            st.balloons()

    with col_dl:
        if st.session_state.get('pending_df') is not None:
            csv_bytes = pending_df.to_csv(index=False).encode()
            st.download_button(
                "⬇ Download Processed CSV",
                data=csv_bytes,
                file_name=f"Processed_{selected_batch}_S{session_no}.csv",
                mime="text/csv",
                use_container_width=True
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
def tab_dashboard(master_df, batches_df):
    st.markdown('<p class="sec-title">Overall Attendance Health</p>', unsafe_allow_html=True)

    log_df = get_log()
    summary_df = compute_summary(master_df, log_df)
    total_sessions = log_df['Session'].nunique() if not log_df.empty else 0

    eligible = (summary_df['Status'] == '✅ Eligible').sum()
    atrisk   = (summary_df['Status'] == '⚠ At Risk').sum()
    fail     = (summary_df['Status'] == '❌ Will Not Qualify').sum()
    nodata   = (summary_df['Status'] == 'No Data').sum()

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    for col, label, val, sub, cls in [
        (c1, "Enrollments",       "2,228",       "13 batches",         "blue"),
        (c2, "Unique Students",   "1,523",       "705 multi-enrolled", "blue"),
        (c3, "Sessions Logged",   str(total_sessions), "All batches",  ""),
        (c4, "Eligible ≥75%",     str(eligible) if eligible else "—", "Certificate track", "green"),
        (c5, "At Risk",           str(atrisk)   if atrisk else "—",   "50–74%",            "amber"),
        (c6, "Will Not Qualify",  str(fail)     if fail else "—",     "Below 50%",         "red"),
    ]:
        with col:
            st.markdown(f'<div class="kpi-card {cls}"><div class="kpi-lbl">{label}</div><div class="kpi-val">{val}</div><div class="kpi-sub">{sub}</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # Batch performance table
    st.markdown('<p class="sec-title">Batch Performance</p>', unsafe_allow_html=True)

    rows_html = ""
    for _, brow in batches_df.iterrows():
        b = brow['Batch']
        enrolled = int(brow['Enrolled'])
        b_log    = log_df[log_df['Batch'] == b] if not log_df.empty else pd.DataFrame()
        b_sess   = b_log['Session'].nunique() if not b_log.empty else 0
        b_sum    = summary_df[summary_df['Batch'] == b]
        elig     = (b_sum['Status'] == '✅ Eligible').sum()
        risk     = (b_sum['Status'] == '⚠ At Risk').sum() + (b_sum['Status'] == '❌ Will Not Qualify').sum()
        b_pct    = elig / enrolled if enrolled > 0 and b_sess > 0 else None
        color    = "#1A7A4A" if b_pct and b_pct >= 0.75 else ("#E8920A" if b_pct and b_pct >= 0.50 else "#C0392B")
        bar      = pct_bar_html(b_pct, color)

        rows_html += f"""<tr>
            <td><strong>{b}</strong></td>
            <td style="font-size:0.78rem">{PROG_SHORT.get(brow['Program'], brow['Program'][:35])}</td>
            <td style="font-size:0.78rem">{brow['SME']}</td>
            <td style="text-align:center;font-family:monospace">{enrolled}</td>
            <td style="text-align:center;font-family:monospace">{b_sess or '—'}</td>
            <td style="text-align:center;color:#1A7A4A;font-weight:700">{elig or '—'}</td>
            <td style="text-align:center;color:#E8920A;font-weight:700">{risk or '—'}</td>
            <td style="min-width:160px">{bar}</td>
        </tr>"""

    st.markdown(f"""
    <div class="tbl-wrap" style="overflow-x:auto;border-radius:10px;border:1px solid #E5E7EB;box-shadow:0 2px 10px rgba(27,58,107,0.07)">
    <table class="styled-table" style="min-width:800px">
      <thead><tr>
        <th>Batch</th><th>Program</th><th>SME</th>
        <th style="text-align:center">Enrolled</th><th style="text-align:center">Sessions</th>
        <th style="text-align:center">✅ Eligible</th><th style="text-align:center">⚠ At Risk</th>
        <th>Attendance %</th>
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table></div>
    """, unsafe_allow_html=True)

    # Export button — generate only when clicked
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    if not log_df.empty:
        if st.button("⬇ Generate & Export Full Excel Report", type="primary"):
            try:
                xl = export_excel(master_df, log_df, summary_df)
                st.download_button(
                    "⬇ Click here to download",
                    data=xl,
                    file_name=f"VITS_Attendance_{date.today().isoformat()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            except Exception as e:
                st.error(f"Export error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — STUDENTS
# ══════════════════════════════════════════════════════════════════════════════
def tab_students(master_df, batches_df):
    st.markdown('<p class="sec-title">Student Attendance Directory</p>', unsafe_allow_html=True)

    log_df     = get_log()
    summary_df = compute_summary(master_df, log_df)

    col_search, col_batch, col_status = st.columns([3, 2, 2])
    with col_search:
        q = st.text_input("🔍 Search name / ID / email", placeholder="Type to search...", label_visibility="collapsed")
    with col_batch:
        b_filter = st.selectbox("Batch", ["All"] + batches_df['Batch'].tolist(), label_visibility="collapsed")
    with col_status:
        s_filter = st.selectbox("Status", ["All Status", "✅ Eligible", "⚠ At Risk", "❌ Will Not Qualify", "No Data"], label_visibility="collapsed")

    display_df = summary_df.copy()
    if q:
        mask = (display_df['Name'].str.lower().str.contains(q.lower()) |
                display_df['App_No'].str.lower().str.contains(q.lower()) |
                display_df['Email'].str.lower().str.contains(q.lower()))
        display_df = display_df[mask]
    if b_filter != "All":
        display_df = display_df[display_df['Batch'] == b_filter]
    if s_filter != "All Status":
        display_df = display_df[display_df['Status'] == s_filter]

    st.caption(f"Showing {len(display_df):,} of {len(summary_df):,} enrollment records")

    rows_html = ""
    for _, row in display_df.head(250).iterrows():
        bar = pct_bar_html(row['Attend_Pct'])
        rows_html += f"""<tr>
            <td class="mono" style="font-family:monospace;font-size:0.76rem">{row['App_No']}</td>
            <td style="font-weight:600">{row['Name']}</td>
            <td style="font-family:monospace;font-size:0.8rem">{row['Batch']}</td>
            <td style="text-align:center;font-family:monospace">{row['Sessions_Held'] or '—'}</td>
            <td style="text-align:center;color:#1A7A4A;font-weight:700">{row['Present'] or '—'}</td>
            <td style="text-align:center;color:#C0392B;font-weight:700">{row['Absent'] or '—'}</td>
            <td style="min-width:140px">{bar}</td>
            <td>{badge_html(row['Status'])}</td>
        </tr>"""

    st.markdown(f"""
    <div style="overflow-x:auto;border-radius:10px;border:1px solid #E5E7EB;box-shadow:0 2px 10px rgba(27,58,107,0.07)">
    <table class="styled-table" style="min-width:750px">
      <thead><tr>
        <th>App No.</th><th>Name</th><th>Batch</th><th style="text-align:center">Sessions</th>
        <th style="text-align:center">Present</th><th style="text-align:center">Absent</th>
        <th>Attendance %</th><th>Status</th>
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table></div>
    """, unsafe_allow_html=True)

    if len(display_df) > 250:
        st.caption(f"Showing first 250 of {len(display_df)} results. Use filters to narrow down.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — ATTENDANCE LOG
# ══════════════════════════════════════════════════════════════════════════════
def tab_log(batches_df):
    st.markdown('<p class="sec-title">Full Attendance Log</p>', unsafe_allow_html=True)

    log_df = get_log()
    if log_df.empty:
        st.markdown("""
        <div style="text-align:center;padding:48px;color:#9CA3AF">
            <div style="font-size:2.5rem;margin-bottom:12px">📋</div>
            <strong style="color:#374151">No records yet</strong><br>
            Import and commit a session to start building the log.
        </div>
        """, unsafe_allow_html=True)
        return

    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
    with c1:
        q = st.text_input("🔍", placeholder="Search name or batch...", label_visibility="collapsed")
    with c2:
        bf = st.selectbox("Batch", ["All"] + batches_df['Batch'].tolist(), key="log_bf", label_visibility="collapsed")
    with c3:
        sf = st.selectbox("Status", ["All", "✅ Present", "⚠ Late", "❌ Absent"], key="log_sf", label_visibility="collapsed")
    with c4:
        st.markdown(f"<div style='padding-top:8px;font-size:0.82rem;color:#6B7280'>{len(log_df):,} total records</div>", unsafe_allow_html=True)

    filtered = log_df.copy().sort_values(['Date','Batch','Session'], ascending=[False,True,True])
    if q:
        filtered = filtered[filtered['Clean_Name'].str.lower().str.contains(q.lower()) |
                            filtered['Batch'].str.lower().str.contains(q.lower())]
    if bf != "All":
        filtered = filtered[filtered['Batch'] == bf]
    if sf != "All":
        filtered = filtered[filtered['Status'] == sf]

    display = filtered.head(500)
    rows_html = ""
    for _, row in display.iterrows():
        rows_html += f"""<tr>
            <td style="font-family:monospace;font-size:0.76rem">{row['Date']}</td>
            <td style="font-family:monospace;font-weight:700">{row['Batch']}</td>
            <td style="text-align:center;font-family:monospace">{row['Session']}</td>
            <td style="font-weight:500">{row['Clean_Name']}</td>
            <td style="text-align:center;font-family:monospace">{row['Dur_Min']:.0f} min</td>
            <td>{badge_html(row['Status'])}</td>
            <td style="font-size:0.75rem;color:#9CA3AF">{row['Email'] or '—'}</td>
        </tr>"""

    st.markdown(f"""
    <div style="overflow-x:auto;border-radius:10px;border:1px solid #E5E7EB;box-shadow:0 2px 10px rgba(27,58,107,0.07)">
    <table class="styled-table" style="min-width:700px">
      <thead><tr>
        <th>Date</th><th>Batch</th><th style="text-align:center">Session</th>
        <th>Name</th><th style="text-align:center">Duration</th><th>Status</th><th>Email</th>
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table></div>
    """, unsafe_allow_html=True)

    if len(filtered) > 500:
        st.caption(f"Showing 500 of {len(filtered)} filtered records.")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    csv_bytes = log_df.to_csv(index=False).encode()
    st.download_button("⬇ Download Full Log CSV", data=csv_bytes,
                       file_name=f"AttendanceLog_{date.today().isoformat()}.csv", mime="text/csv")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — AT-RISK
# ══════════════════════════════════════════════════════════════════════════════
def tab_atrisk(master_df, batches_df):
    st.markdown("""
    <div class="alert alert-warning">⚠ Students below 75% attendance are at risk of losing their certificate. Review weekly and share with each SME and SPOC.</div>
    """, unsafe_allow_html=True)

    log_df     = get_log()
    summary_df = compute_summary(master_df, log_df)
    risk_df    = summary_df[summary_df['Status'].isin(['⚠ At Risk','❌ Will Not Qualify'])].copy()

    if risk_df.empty:
        if log_df.empty:
            st.markdown('<div class="alert alert-info">ℹ No attendance data committed yet. Import sessions first.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="alert alert-success">🎉 No at-risk students. All enrolled students with data are on track.</div>', unsafe_allow_html=True)
        return

    c1, c2, c3 = st.columns([2, 2, 4])
    with c1:
        bf = st.selectbox("Filter by Batch", ["All"] + batches_df['Batch'].tolist(), key="risk_bf", label_visibility="collapsed")
    with c2:
        sf = st.selectbox("Filter by Status", ["All Risk", "⚠ At Risk", "❌ Will Not Qualify"], key="risk_sf", label_visibility="collapsed")
    with c3:
        st.markdown(f"<div style='padding-top:8px;font-size:0.82rem;color:#C0392B;font-weight:700'>{len(risk_df)} students at risk</div>", unsafe_allow_html=True)

    if bf != "All":
        risk_df = risk_df[risk_df['Batch'] == bf]
    if sf == "⚠ At Risk":
        risk_df = risk_df[risk_df['Status'] == '⚠ At Risk']
    elif sf == "❌ Will Not Qualify":
        risk_df = risk_df[risk_df['Status'] == '❌ Will Not Qualify']

    risk_df = risk_df.sort_values('Attend_Pct', ascending=True)

    rows_html = ""
    for _, row in risk_df.iterrows():
        bar = pct_bar_html(row['Attend_Pct'])
        rows_html += f"""<tr>
            <td style="font-family:monospace;font-size:0.76rem">{row['App_No']}</td>
            <td style="font-weight:600">{row['Name']}</td>
            <td style="font-size:0.76rem;color:#9CA3AF">{row['Email'] or '—'}</td>
            <td style="font-family:monospace;font-weight:700">{row['Batch']}</td>
            <td style="font-size:0.78rem">{PROG_SHORT.get(row['Program'], row['Program'][:28])}</td>
            <td style="font-size:0.78rem">{row['SME']}</td>
            <td style="text-align:center;font-family:monospace">{row['Sessions_Held']}</td>
            <td style="text-align:center;font-family:monospace">{row['Present']}</td>
            <td style="min-width:130px">{bar}</td>
            <td>{badge_html(row['Status'])}</td>
        </tr>"""

    st.markdown(f"""
    <div style="overflow-x:auto;border-radius:10px;border:1px solid #FCA5A5;box-shadow:0 2px 10px rgba(192,57,43,0.08)">
    <table class="styled-table" style="min-width:900px">
      <thead><tr>
        <th>App No.</th><th>Name</th><th>Email</th><th>Batch</th><th>Program</th><th>SME</th>
        <th style="text-align:center">Sessions</th><th style="text-align:center">Present</th>
        <th>Attendance %</th><th>Status</th>
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table></div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # Export at-risk
    csv_bytes = risk_df.to_csv(index=False).encode()
    st.download_button(
        "⬇ Export At-Risk Report",
        data=csv_bytes,
        file_name=f"AtRisk_{date.today().isoformat()}.csv",
        mime="text/csv",
        type="primary"
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — AI INSIGHTS
# ══════════════════════════════════════════════════════════════════════════════
def tab_ai(master_df):
    st.markdown("""
    <div class="ai-wrap">
        <div class="ai-label">Powered by Claude · Anthropic</div>
        <div class="ai-title">Attendance Intelligence Assistant</div>
        <div class="ai-sub">Ask questions, get summaries, identify patterns, and plan follow-up actions.</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    log_df     = get_log()
    summary_df = compute_summary(master_df, log_df)

    # Context for Claude
    total_sessions = log_df['Session'].nunique() if not log_df.empty else 0
    eligible = (summary_df['Status'] == '✅ Eligible').sum()
    atrisk   = (summary_df['Status'] == '⚠ At Risk').sum()
    fail     = (summary_df['Status'] == '❌ Will Not Qualify').sum()
    nodata   = (summary_df['Status'] == 'No Data').sum()

    batch_lines = []
    for _, brow in load_batches().iterrows():
        b = brow['Batch']
        b_log = log_df[log_df['Batch'] == b] if not log_df.empty else pd.DataFrame()
        b_sess = b_log['Session'].nunique() if not b_log.empty else 0
        b_sum  = summary_df[summary_df['Batch'] == b]
        be = (b_sum['Status'] == '✅ Eligible').sum()
        br = ((b_sum['Status'] == '⚠ At Risk') | (b_sum['Status'] == '❌ Will Not Qualify')).sum()
        batch_lines.append(f"{b} ({PROG_SHORT.get(brow['Program'], brow['Program'][:30])}, SME: {brow['SME']}): "
                           f"{brow['Enrolled']} enrolled, {b_sess} sessions, {be} eligible, {br} at-risk/fail")

    context = f"""You are an attendance analytics assistant for MPOnline Ltd., a Govt. of Madhya Pradesh and TCS joint venture.
You are helping Palash Jaiswal, Associate Consultant in the Skills Development vertical, manage internship/certificate program attendance at VITS Bhopal.

CURRENT DATA:
- Total enrollments: 2,228 across 13 batches (1,523 unique students, 705 multi-enrolled)
- Sessions logged: {total_sessions}
- Attendance records: {len(log_df)}
- Eligible (≥75%): {eligible}
- At Risk (50–74%): {atrisk}
- Will Not Qualify (<50%): {fail}
- No data yet: {nodata}

BATCH SUMMARIES:
{chr(10).join(batch_lines)}

Programs: SE+AI Foundation, Advanced Software Engineering, AI/ML Internship, Digital Marketing Internship.
Certificate requires ≥75% attendance. No refund policy.

Be direct, specific, and actionable. Use bullet points where helpful. Reference specific batch codes and numbers."""

    # Quick-ask buttons
    st.markdown('<p class="sec-title">Quick Questions</p>', unsafe_allow_html=True)
    q_cols = st.columns(5)
    quick_questions = {
        "📊 Summary":         "Give me a concise attendance health summary across all 13 batches.",
        "🔍 Worst batches":   "Which batches have the worst attendance and what are likely causes?",
        "🚨 At-Risk":         "How many students risk losing their certificate and which batches need urgent attention?",
        "💡 Actions":         "What are the 3 most important actions I should take this week based on attendance data?",
        "📧 SPOC Message":    "Draft a short WhatsApp message to a college SPOC about students who are at risk of losing their certificate.",
    }

    clicked_q = None
    for col, (label, question) in zip(q_cols, quick_questions.items()):
        with col:
            if st.button(label, use_container_width=True):
                clicked_q = question

    # Chat input
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    user_input = st.text_input("Ask anything about the attendance data...", key="ai_input", label_visibility="collapsed",
                                placeholder="e.g. Which students in B3(A) have below 50% attendance?")
    send_btn = st.button("Send →", type="primary")

    question = clicked_q or (user_input if send_btn else None)

    if question:
        api_key = os.environ.get("ANTHROPIC_API_KEY") or st.secrets.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            st.markdown('<div class="alert alert-warning">⚠ No Anthropic API key found. Add ANTHROPIC_API_KEY to your Streamlit secrets to enable AI Insights.</div>', unsafe_allow_html=True)
            return

        with st.spinner("Analysing attendance data..."):
            try:
                client = anthropic.Anthropic(api_key=api_key)
                msg = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1000,
                    system=context,
                    messages=[{"role": "user", "content": question}]
                )
                answer = msg.content[0].text
                st.markdown(f"""
                <div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:10px;padding:18px;margin-top:14px;line-height:1.75;font-size:0.88rem;white-space:pre-wrap">{answer}</div>
                """, unsafe_allow_html=True)
            except Exception as e:
                st.markdown(f'<div class="alert alert-error">❌ API error: {str(e)}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    init_log()
    master_df  = load_master()
    batches_df = load_batches()

    render_topbar()

    selected_batch, session_no, session_date, sched_dur, threshold_min = render_sidebar(master_df, batches_df)

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📥  Import & Process",
        "📊  Dashboard",
        "👤  Students",
        "📋  Attendance Log",
        "🚨  At-Risk",
        "🤖  AI Insights",
    ])

    with tab1:
        tab_import(master_df, selected_batch, session_no, session_date, sched_dur, threshold_min)
    with tab2:
        tab_dashboard(master_df, batches_df)
    with tab3:
        tab_students(master_df, batches_df)
    with tab4:
        tab_log(batches_df)
    with tab5:
        tab_atrisk(master_df, batches_df)
    with tab6:
        tab_ai(master_df)


if __name__ == "__main__":
    main()
