import streamlit as st
import pandas as pd
import re
import base64
import io
import os
import json
from datetime import date, datetime
import anthropic

# ── PAGE CONFIG — must be first Streamlit call ────────────────────────────────
st.set_page_config(
    page_title="VITS Attendance · MPOnline",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
THRESHOLD_PCT = 0.75
BOT_KEYWORDS  = ["otter.ai", "fireflies", "notetaker"]
STAFF_DOMAINS = ["mponline.gov.in"]
DATA_DIR      = os.path.join(os.path.dirname(__file__), "data")
LOGO_PATH     = os.path.join(DATA_DIR, "logo.png")
MASTER_PATH   = os.path.join(DATA_DIR, "master_students.csv")
BATCH_PATH    = os.path.join(DATA_DIR, "batch_info.csv")
LOG_COLS      = ['Date','Batch','Session','App_No','Raw_Name','Clean_Name',
                 'Email','Dur_Min','Dur_Raw','Status','Matched']
PROG_SHORT    = {
    "Certification in Advanced Software Engineering & AI foundation": "SE + AI Foundation",
    "Advanced Software Engineering & Development Internship":         "Adv. Software Eng.",
    "AI/ML Internship Program":                                       "AI / ML",
    "Digital Marketing Internship Program":                           "Digital Marketing",
}

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Core layout */
#MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 0.8rem !important; padding-bottom: 1rem !important; }

/* Force sidebar always visible, collapse arrow styled */
section[data-testid="stSidebar"] {
    background: #0D1B2A !important;
    min-width: 300px !important;
}
section[data-testid="stSidebar"] > div:first-child { padding-top: 1rem; }

/* Sidebar text — white labels, readable */
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown h3,
section[data-testid="stSidebar"] .stCaption { color: rgba(255,255,255,0.75) !important; }

/* Sidebar inputs — white bg, black text, always readable */
section[data-testid="stSidebar"] input {
    background-color: #FFFFFF !important;
    color: #111111 !important;
    -webkit-text-fill-color: #111111 !important;
    border-radius: 6px !important;
    border: 1px solid rgba(255,255,255,0.3) !important;
}
/* Sidebar selectbox */
section[data-testid="stSidebar"] .stSelectbox > div > div {
    background-color: #1E3A5F !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    border-radius: 6px !important;
    color: white !important;
}
section[data-testid="stSidebar"] .stSelectbox > div > div > div { color: white !important; }
section[data-testid="stSidebar"] .stSelectbox svg { fill: white !important; }

/* Sidebar info box */
.sb-info {
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 8px;
    padding: 12px 14px;
    font-size: 0.8rem;
    line-height: 1.9;
    color: rgba(255,255,255,0.85);
    margin: 8px 0;
}
.sb-info strong { color: #FF6B35; }

/* Threshold pill */
.threshold-pill {
    background: rgba(255,107,53,0.18);
    border: 1px solid rgba(255,107,53,0.4);
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 0.78rem;
    color: #FFB399;
    line-height: 1.8;
    margin-top: 8px;
}
.threshold-pill strong { color: #FF6B35; }

/* Topbar */
.topbar {
    background: linear-gradient(90deg, #0D1B2A 0%, #1B3A6B 60%, #2E5FA3 100%);
    border-radius: 12px;
    padding: 16px 28px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 18px;
    box-shadow: 0 4px 20px rgba(27,58,107,0.22);
    overflow: visible;
}
.topbar-right { text-align: right; line-height: 1.5; }
.topbar-title { font-size: 0.95rem; font-weight: 700; color: white; }
.topbar-sub { font-size: 0.72rem; color: rgba(255,255,255,0.55); }
.topbar-pill {
    display: inline-block;
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.7rem;
    color: rgba(255,255,255,0.8);
    margin-left: 6px;
}
.topbar-pill.live::before {
    content: '●';
    color: #4ADE80;
    margin-right: 4px;
    font-size: 0.55rem;
}

/* Persistence banner */
.persist-banner {
    background: #E8F5EE;
    border: 1px solid #86EFAC;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 0.8rem;
    color: #1A7A4A;
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 14px;
}
.persist-banner.warn {
    background: #FFF3DC;
    border-color: #FCD34D;
    color: #92400E;
}

/* KPI cards */
.kpi-card {
    background: white;
    border-radius: 10px;
    padding: 18px 16px;
    border: 1px solid #D0D5E8;
    border-left: 4px solid #2E5FA3;
    box-shadow: 0 2px 10px rgba(27,58,107,0.07);
    text-align: center;
    height: 100%;
}
.kpi-card.green { border-left-color: #1A7A4A; }
.kpi-card.amber { border-left-color: #E8920A; }
.kpi-card.red   { border-left-color: #C0392B; }
.kpi-val { font-size: 2rem; font-weight: 800; color: #1B3A6B; line-height: 1; margin: 5px 0 2px; font-family: 'Courier New', monospace; }
.kpi-lbl { font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; color: #6B7280; }
.kpi-sub { font-size: 0.7rem; color: #9CA3AF; }

/* Section heading */
.sec-title {
    font-size: 0.72rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.09em; color: #6B7280; margin: 0 0 14px;
    padding-left: 10px; border-left: 3px solid #FF6B35;
}

/* Badges */
.badge { display: inline-block; padding: 3px 9px; border-radius: 20px; font-size: 0.7rem; font-weight: 700; white-space: nowrap; }
.badge-present  { background: #E8F5EE; color: #1A7A4A; }
.badge-late     { background: #FFF3DC; color: #E8920A; }
.badge-absent   { background: #FDEDEC; color: #C0392B; }
.badge-eligible { background: #E8F5EE; color: #1A7A4A; }
.badge-atrisk   { background: #FFF3DC; color: #E8920A; }
.badge-danger   { background: #FDEDEC; color: #C0392B; }
.badge-nodata   { background: #F3F4F6; color: #9CA3AF; }

/* Progress bar */
.prog-row { display: flex; align-items: center; gap: 8px; }
.prog-bar { flex: 1; height: 7px; background: #E5E7EB; border-radius: 4px; overflow: hidden; min-width: 60px; }
.prog-fill { height: 100%; border-radius: 4px; }
.prog-val { font-size: 0.75rem; font-weight: 700; min-width: 40px; text-align: right; font-family: monospace; }

/* Alerts */
.alert { padding: 11px 16px; border-radius: 8px; font-size: 0.83rem; margin-bottom: 10px; line-height: 1.5; }
.alert-success { background: #E8F5EE; color: #166534; border: 1px solid #86EFAC; }
.alert-warning { background: #FFF3DC; color: #92400E; border: 1px solid #FCD34D; }
.alert-error   { background: #FDEDEC; color: #991B1B; border: 1px solid #FCA5A5; }
.alert-info    { background: #EFF6FF; color: #1E40AF; border: 1px solid #93C5FD; }

/* Upload hint */
.upload-hint {
    background: #EFF6FF; border: 1.5px dashed #93C5FD;
    border-radius: 10px; padding: 14px 18px;
    font-size: 0.83rem; color: #1E40AF; margin-bottom: 14px; line-height: 1.75;
}
.upload-hint strong { color: #1B3A6B; }

/* Tables */
.styled-table { width: 100%; border-collapse: collapse; font-size: 0.81rem; }
.styled-table th {
    background: #1B3A6B; color: white; padding: 9px 12px;
    text-align: left; font-size: 0.72rem;
    text-transform: uppercase; letter-spacing: 0.04em; white-space: nowrap;
}
.styled-table td { padding: 8px 12px; border-bottom: 1px solid #E5E7EB; vertical-align: middle; }
.styled-table tr:last-child td { border-bottom: none; }
.styled-table tr:hover td { background: #F9FAFB; }
.tbl-wrap { overflow-x: auto; border-radius: 10px; border: 1px solid #E5E7EB; box-shadow: 0 2px 10px rgba(27,58,107,0.06); }

/* Step bar */
.steps { display: flex; border-radius: 8px; overflow: hidden; margin-bottom: 20px; }
.step { flex: 1; padding: 10px 6px; text-align: center; font-size: 0.74rem; font-weight: 600; background: #E5E7EB; color: #6B7280; }
.step.done   { background: #1A7A4A; color: white; }
.step.active { background: #1B3A6B; color: white; }

/* AI panel */
.ai-wrap { background: linear-gradient(135deg, #0D1B2A 0%, #1B3A6B 100%); border-radius: 12px; padding: 20px; }
.ai-label { font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(255,255,255,0.4); margin-bottom: 4px; }
.ai-title { font-size: 1rem; font-weight: 700; color: white; margin-bottom: 3px; }
.ai-sub   { font-size: 0.8rem; color: rgba(255,255,255,0.55); margin-bottom: 14px; }

/* Empty state */
.empty-state { text-align: center; padding: 48px 24px; color: #9CA3AF; }
.empty-icon  { font-size: 2.8rem; margin-bottom: 10px; }
.empty-state h3 { color: #374151; font-size: 1rem; margin-bottom: 6px; }
</style>
""", unsafe_allow_html=True)


# ── LOAD MASTER DATA ─────────────────────────────────────────────────────────
@st.cache_data
def load_master():
    df = pd.read_csv(MASTER_PATH, dtype=str).fillna('')
    df.columns = ['App_No','Name','Email','Prog_Code','Prog_Name','Batch','Timing','SME']
    return df

@st.cache_data
def load_batches():
    df = pd.read_csv(BATCH_PATH, dtype=str)
    df['Enrolled'] = pd.to_numeric(df['Enrolled'], errors='coerce').fillna(0).astype(int)
    return df

@st.cache_data
def get_logo_b64():
    with open(LOGO_PATH, "rb") as f:
        return base64.b64encode(f.read()).decode()


# ── GOOGLE SHEETS PERSISTENCE ─────────────────────────────────────────────────
def get_gsheet_client():
    """Return authorised gspread client using service_account.json file in data/."""
    try:
        import gspread
        import json
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        # Primary: read service_account.json from data/ folder
        sa_path = os.path.join(DATA_DIR, "service_account.json")
        if os.path.exists(sa_path):
            with open(sa_path, "r") as f:
                creds_dict = json.load(f)
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            client = gspread.authorize(creds)
            st.session_state.pop("gsheet_error", None)
            return client

        # Fallback: TOML secrets
        creds_dict = dict(st.secrets["gcp_service_account"])
        pk = str(creds_dict.get("private_key", ""))
        pk = pk.replace("\\n", "\n")
        creds_dict["private_key"] = pk
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        st.session_state.pop("gsheet_error", None)
        return client

    except Exception as e:
        st.session_state["gsheet_error"] = f"{type(e).__name__}: {str(e)[:300]}"
        return None

def get_sheet(client, sheet_name="Attendance Log"):
    """Return the worksheet, creating it if needed."""
    sheet_id = st.secrets.get("GSHEET_ID", "").strip()
    if not sheet_id:
        st.session_state["gsheet_error"] = "GSHEET_ID is empty"
        return None
    sh = None
    # Try open_by_key first
    try:
        sh = client.open_by_key(sheet_id)
    except Exception as e1:
        # Fallback: open_by_url
        try:
            url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
            sh = client.open_by_url(url)
        except Exception as e2:
            st.session_state["gsheet_error"] = (
                f"Cannot open Sheet (404 = check Drive API is enabled AND Sheet is shared "
                f"with the bot email). key_err={e1} | url_err={e2}"
            )
            return None
    # Get or create the worksheet tab
    try:
        return sh.worksheet(sheet_name)
    except Exception:
        try:
            ws = sh.add_worksheet(title=sheet_name, rows=5000, cols=len(LOG_COLS))
            ws.append_row(LOG_COLS)
            return ws
        except Exception as e:
            st.session_state["gsheet_error"] = f"Worksheet create failed: {e}"
            return None

def load_log_from_sheet():
    """Load attendance log from Google Sheet → DataFrame."""
    client = get_gsheet_client()
    if not client:
        return None
    ws = get_sheet(client)
    if not ws:
        return None
    try:
        data = ws.get_all_records()
        if not data:
            return pd.DataFrame(columns=LOG_COLS)
        return pd.DataFrame(data)
    except Exception as e:
        st.session_state["gsheet_error"] = str(e)
        return None

def save_rows_to_sheet(rows_df):
    """Append new rows to Google Sheet."""
    client = get_gsheet_client()
    if not client:
        return False
    ws = get_sheet(client)
    if not ws:
        return False
    try:
        for _, row in rows_df.iterrows():
            ws.append_row([str(row.get(c, '')) for c in LOG_COLS])
        return True
    except Exception as e:
        st.error(f"Google Sheets save error: {e}")
        return False

def has_sheets_configured():
    """Check if Google Sheets is configured via JSON file or TOML secrets."""
    try:
        # Check for JSON file in data/
        sa_path = os.path.join(DATA_DIR, "service_account.json")
        has_json_file = os.path.exists(sa_path)

        # Check TOML secrets
        sheet_id = st.secrets.get("GSHEET_ID", "")
        has_sa   = "gcp_service_account" in st.secrets
        valid_id = bool(sheet_id) and not sheet_id.startswith("http") and len(sheet_id) > 10

        return (has_json_file or has_sa) and valid_id
    except Exception:
        return False


# ── SESSION STATE — LOG ───────────────────────────────────────────────────────
def init_log():
    """Load from Google Sheets if configured, else use session memory."""
    sheets_ok = has_sheets_configured()

    # First load this session — pull from Sheets if configured
    if "att_log" not in st.session_state:
        if sheets_ok:
            with st.spinner("Loading attendance data from Google Sheets..."):
                df = load_log_from_sheet()
            st.session_state["att_log"]       = df if df is not None else pd.DataFrame(columns=LOG_COLS)
            st.session_state["using_sheets"]  = df is not None
        else:
            st.session_state["att_log"]       = pd.DataFrame(columns=LOG_COLS)
            st.session_state["using_sheets"]  = False
    else:
        # Already loaded this session — just update sheets flag
        st.session_state["using_sheets"] = sheets_ok and st.session_state.get("using_sheets", False)

def get_log():
    return st.session_state.get("att_log", pd.DataFrame(columns=LOG_COLS))

def append_log(rows_df):
    existing = get_log()
    st.session_state["att_log"] = pd.concat([existing, rows_df], ignore_index=True)
    if st.session_state.get("using_sheets"):
        return save_rows_to_sheet(rows_df)
    return True


# ── PARSERS & HELPERS ─────────────────────────────────────────────────────────
def parse_duration_minutes(s):
    if not s or not isinstance(s, str): return 0.0
    h  = int(m.group(1)) if (m := re.search(r'(\d+)h', s)) else 0
    mn = int(m.group(1)) if (m := re.search(r'(\d+)m', s)) else 0
    sc = int(m.group(1)) if (m := re.search(r'(\d+)s', s)) else 0
    return round(h * 60 + mn + sc / 60, 1)

def clean_name(raw):
    return re.sub(r'\s*\([^)]*\)\s*', ' ', str(raw)).strip()

def is_excluded(name, email):
    n, e = name.lower(), (email or '').lower()
    return any(k in n for k in BOT_KEYWORDS) or any(d in e for d in STAFF_DOMAINS)

def match_student(raw_name, master_df):
    cleaned = clean_name(raw_name).lower().strip()
    mask = master_df['Name'].str.lower().str.strip() == cleaned
    if mask.any():
        return master_df.loc[mask.idxmax(), 'App_No']
    for _, row in master_df.iterrows():
        ml = row['Name'].lower().strip()
        if ml in cleaned or cleaned in ml:
            return row['App_No']
    return None

def parse_teams_csv(text):
    lines = text.splitlines()
    in_p, rows = False, []
    for line in lines:
        if line.startswith('2. Participants'): in_p = True; continue
        if in_p and line.startswith('3. In-Meeting'): break
        if not in_p or line.startswith('Name,'): continue
        if not line.strip().replace(',', ''): continue
        cols, cur, in_q = [], '', False
        for ch in line:
            if ch == '"': in_q = not in_q
            elif ch == ',' and not in_q: cols.append(cur.strip()); cur = ''
            else: cur += ch
        cols.append(cur.strip())
        if len(cols) >= 4: rows.append(cols)
    return rows

def status_label(dur_min, threshold_min):
    if dur_min >= threshold_min: return "✅ Present"
    elif dur_min >= 1:           return "⚠ Late"
    else:                        return "❌ Absent"

def attendance_status(pct):
    if pct is None:       return "No Data"
    if pct >= THRESHOLD_PCT: return "✅ Eligible"
    if pct >= 0.50:       return "⚠ At Risk"
    return "❌ Will Not Qualify"

def pct_bar_html(pct_float, color=None):
    if pct_float is None:
        return '<span style="color:#9CA3AF;font-size:0.78rem">No data yet</span>'
    p = round(pct_float * 100, 1)
    if color is None:
        color = "#1A7A4A" if p >= 75 else ("#E8920A" if p >= 50 else "#C0392B")
    return (f'<div class="prog-row">'
            f'<div class="prog-bar"><div class="prog-fill" style="width:{p}%;background:{color}"></div></div>'
            f'<span class="prog-val" style="color:{color}">{p:.1f}%</span></div>')

def badge_html(text):
    cls = {"✅ Present":"badge-present","⚠ Late":"badge-late","❌ Absent":"badge-absent",
           "✅ Eligible":"badge-eligible","⚠ At Risk":"badge-atrisk",
           "❌ Will Not Qualify":"badge-danger","No Data":"badge-nodata"}.get(text,"badge-nodata")
    return f'<span class="badge {cls}">{text}</span>'

@st.cache_data(show_spinner=False)
def compute_summary(master_hash, log_hash):
    """Cached summary — recomputes only when data changes."""
    master_df = load_master()
    log_df    = get_log()
    rows = []
    for _, stu in master_df.iterrows():
        app_no, batch = stu['App_No'], stu['Batch']
        sub           = log_df[(log_df['App_No']==app_no) & (log_df['Batch']==batch)] if not log_df.empty else pd.DataFrame()
        sess_held     = log_df[log_df['Batch']==batch]['Session'].nunique() if not log_df.empty else 0
        present       = (sub['Status']=='✅ Present').sum() if not sub.empty else 0
        late          = (sub['Status']=='⚠ Late').sum()    if not sub.empty else 0
        absent        = (sub['Status']=='❌ Absent').sum()  if not sub.empty else 0
        pct           = (present / sess_held) if sess_held > 0 else None
        rows.append({'App_No':app_no,'Name':stu['Name'],'Email':stu['Email'],
                     'Batch':batch,'Program':stu['Prog_Name'],'SME':stu['SME'],
                     'Sessions_Held':sess_held,'Present':present,'Late':late,'Absent':absent,
                     'Attend_Pct':pct,'Status':attendance_status(pct)})
    return pd.DataFrame(rows)

def get_summary():
    log_df = get_log()
    log_hash = str(len(log_df)) + str(log_df['Status'].value_counts().to_dict() if not log_df.empty else '')
    return compute_summary("v1", log_hash)


# ── EXCEL EXPORT ──────────────────────────────────────────────────────────────
def export_excel(log_df, summary_df):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
        wb = writer.book
        hdr  = wb.add_format({'bold':True,'bg_color':'#1B3A6B','font_color':'white','font_size':9,'border':1})
        grn  = wb.add_format({'bg_color':'#E8F5EE','font_color':'#1A7A4A','bold':True,'border':1,'font_size':9})
        amb  = wb.add_format({'bg_color':'#FFF3DC','font_color':'#92400E','bold':True,'border':1,'font_size':9})
        red  = wb.add_format({'bg_color':'#FDEDEC','font_color':'#991B1B','bold':True,'border':1,'font_size':9})
        pct  = wb.add_format({'num_format':'0.0%','border':1,'align':'center','font_size':9})
        cel  = wb.add_format({'border':1,'font_size':9})
        alt  = wb.add_format({'border':1,'font_size':9,'bg_color':'#F9FAFB'})

        def hdr_row(ws, hdrs, widths):
            for c,(h,w) in enumerate(zip(hdrs,widths)):
                ws.write(0,c,h,hdr); ws.set_column(c,c,w)

        def row_fmt(i): return alt if i%2==0 else cel

        def status_fmt(v):
            if '✅ Present' in str(v) or '✅ Eligible' in str(v): return grn
            if '⚠' in str(v): return amb
            if '❌' in str(v): return red
            return cel

        def write_pct(ws, r, c, v):
            if v is not None and str(v) not in ('','None'):
                try: ws.write_number(r, c, float(v), pct)
                except: ws.write_blank(r, c, None, pct)
            else:
                ws.write_blank(r, c, None, pct)

        # Sheet 1 — Attendance Log
        ws1 = wb.add_worksheet('Attendance Log')
        writer.sheets['Attendance Log'] = ws1
        cols1 = ['Date','Batch','Session','App_No','Clean_Name','Email','Dur_Min','Dur_Raw','Status']
        hdrs1 = ['Date','Batch','Session','App No.','Name','Email','Duration (min)','Duration (raw)','Status']
        hdr_row(ws1, hdrs1, [12,10,9,16,28,30,14,14,16])
        if not log_df.empty:
            for r, row in log_df[cols1].reset_index(drop=True).iterrows():
                f = row_fmt(r)
                for c,v in enumerate(row):
                    if cols1[c]=='Status': ws1.write(r+1,c,str(v),status_fmt(v))
                    else: ws1.write(r+1,c,str(v) if v else '',f)

        # Sheet 2 — Student Summary
        ws2 = wb.add_worksheet('Student Summary')
        writer.sheets['Student Summary'] = ws2
        cols2 = ['App_No','Name','Email','Batch','Program','SME','Sessions_Held','Present','Late','Absent','Attend_Pct','Status']
        hdrs2 = ['App No.','Name','Email','Batch','Program','SME','Sessions','Present','Late','Absent','Attend %','Status']
        hdr_row(ws2, hdrs2, [16,28,30,10,40,22,10,9,9,9,12,22])
        if not summary_df.empty:
            for r, row in summary_df[cols2].reset_index(drop=True).iterrows():
                f = row_fmt(r)
                for c,col in enumerate(cols2):
                    v = row[col]
                    if col=='Attend_Pct': write_pct(ws2,r+1,c,v)
                    elif col=='Status': ws2.write(r+1,c,str(v),status_fmt(v))
                    else: ws2.write(r+1,c,str(v) if v else '',f)

        # Sheet 3 — At-Risk
        ws3 = wb.add_worksheet('At-Risk Report')
        writer.sheets['At-Risk Report'] = ws3
        risk = summary_df[summary_df['Status'].isin(['⚠ At Risk','❌ Will Not Qualify'])]
        cols3 = ['App_No','Name','Email','Batch','Program','SME','Attend_Pct','Status']
        hdrs3 = ['App No.','Name','Email','Batch','Program','SME','Attend %','Status']
        hdr_row(ws3, hdrs3, [16,28,30,10,40,22,12,22])
        for r, row in risk[cols3].reset_index(drop=True).iterrows():
            f = row_fmt(r)
            for c,col in enumerate(cols3):
                v = row[col]
                if col=='Attend_Pct': write_pct(ws3,r+1,c,v)
                elif col=='Status': ws3.write(r+1,c,str(v),status_fmt(v))
                else: ws3.write(r+1,c,str(v) if v else '',f)

        # Sheet 4 — Batch Summary
        ws4 = wb.add_worksheet('Batch Summary')
        writer.sheets['Batch Summary'] = ws4
        batches = load_batches()
        log_sess = log_df.groupby('Batch')['Session'].nunique().to_dict() if not log_df.empty else {}
        hdrs4 = ['Batch','Program','SME','Timing','Enrolled','Sessions Run','Eligible','At Risk','Won\'t Qualify','Eligible %']
        hdr_row(ws4, hdrs4, [10,40,22,16,10,13,10,10,14,13])
        for r, brow in batches.reset_index(drop=True).iterrows():
            b     = brow['Batch']
            b_sum = summary_df[summary_df['Batch']==b] if not summary_df.empty else pd.DataFrame()
            sess  = log_sess.get(b, 0)
            elig  = (b_sum['Status']=='✅ Eligible').sum() if not b_sum.empty else 0
            risk  = (b_sum['Status']=='⚠ At Risk').sum()  if not b_sum.empty else 0
            fail  = (b_sum['Status']=='❌ Will Not Qualify').sum() if not b_sum.empty else 0
            ep    = elig/int(brow['Enrolled']) if int(brow['Enrolled'])>0 and sess>0 else None
            f     = row_fmt(r)
            for c,v in enumerate([b,brow['Program'],brow['SME'],brow['Timing'],int(brow['Enrolled']),sess,elig,risk,fail]):
                ws4.write(r+1,c,v,f)
            write_pct(ws4,r+1,9,ep)

        # Sheet 5 — Session Pivot
        if not log_df.empty:
            ws5 = wb.add_worksheet('Session Pivot')
            writer.sheets['Session Pivot'] = ws5
            hdr_row(ws5, ['Date','Batch','Session','Total','Present','Late','Absent','Rate'],
                    [12,10,9,10,10,10,10,12])
            piv = log_df.groupby(['Date','Batch','Session']).agg(
                Total=('Status','count'),
                Present=('Status', lambda x:(x=='✅ Present').sum()),
                Late=('Status',    lambda x:(x=='⚠ Late').sum()),
                Absent=('Status',  lambda x:(x=='❌ Absent').sum()),
            ).reset_index()
            piv['Rate'] = piv['Present']/piv['Total']
            for r, row in piv.reset_index(drop=True).iterrows():
                f = row_fmt(r)
                for c,v in enumerate([str(row['Date']),row['Batch'],row['Session'],
                                       row['Total'],row['Present'],row['Late'],row['Absent']]):
                    ws5.write(r+1,c,v,f)
                write_pct(ws5,r+1,7,row['Rate'])

    return buf.getvalue()


# ── TOPBAR ────────────────────────────────────────────────────────────────────
def render_topbar():
    log_df = get_log()
    sess   = log_df['Session'].nunique() if not log_df.empty else 0
    recs   = len(log_df)
    using  = st.session_state.get("using_sheets", False)
    mode_color = "#4ADE80" if using else "#FBBF24"
    mode_text  = "Google Sheets connected" if using else "Session memory"
    logo   = get_logo_b64()

    st.markdown(f"""
    <div style="background:linear-gradient(90deg,#0D1B2A 0%,#1B3A6B 60%,#2E5FA3 100%);
                border-radius:12px;padding:14px 24px;margin-bottom:18px;
                box-shadow:0 4px 20px rgba(27,58,107,0.22);
                display:flex;align-items:center;justify-content:space-between;gap:20px;">
        <div style="background:white;border-radius:8px;padding:10px 18px;display:inline-flex;align-items:center;">
            <img src="data:image/png;base64,{logo}" style="height:52px;width:auto;display:block;" alt="MPOnline">
        </div>
        <div style="text-align:right;flex:1;">
            <div style="font-size:1rem;font-weight:700;color:white;line-height:1.2;">VITS Attendance Intelligence</div>
            <div style="font-size:0.72rem;color:rgba(255,255,255,0.6);margin-top:5px;">
                Skills Development Vertical &nbsp;·&nbsp;
                <span style="background:rgba(255,255,255,0.14);border-radius:20px;padding:3px 11px;color:rgba(255,255,255,0.9);">
                    {sess} sessions · {recs:,} records
                </span>
                <span style="background:rgba(255,255,255,0.10);border-radius:20px;padding:3px 11px;margin-left:5px;color:{mode_color};font-weight:600;">
                    ● {mode_text}
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
def render_sidebar(batches_df):
    with st.sidebar:
        st.markdown("### ⚙️ Session Setup")
        st.markdown("---")

        batch_list = batches_df['Batch'].tolist()
        sel_idx = st.selectbox(
            "Batch",
            range(len(batch_list)),
            format_func=lambda i: f"{batch_list[i]}  —  {PROG_SHORT.get(batches_df.iloc[i]['Program'], batches_df.iloc[i]['Program'][:28])}",
            key="sb_batch"
        )
        sel_batch = batch_list[sel_idx]
        brow = batches_df[batches_df['Batch']==sel_batch].iloc[0]

        st.markdown(f"""
        <div class="sb-info">
        <strong>Program:</strong> {PROG_SHORT.get(brow['Program'], brow['Program'])}<br>
        <strong>SME:</strong> {brow['SME']}<br>
        <strong>Timing:</strong> {brow['Timing']}<br>
        <strong>Enrolled:</strong> {brow['Enrolled']} students
        </div>
        """, unsafe_allow_html=True)

        session_no   = st.number_input("Session Number", min_value=1, max_value=300, value=1, key="sb_sess")
        session_date = st.date_input("Session Date", value=date.today(), key="sb_date")
        sched_dur    = st.number_input("Scheduled Duration (min)", min_value=30, max_value=360, value=120, step=15, key="sb_dur")
        threshold_min = round(sched_dur * THRESHOLD_PCT)

        st.markdown(f"""
        <div class="threshold-pill">
        <strong>Threshold: {threshold_min} min</strong> = {int(THRESHOLD_PCT*100)}% of {sched_dur} min<br>
        ≥{threshold_min} min → Present &nbsp;|&nbsp; 1–{threshold_min-1} min → Late
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # Persistence status
        if st.session_state.get("using_sheets"):
            st.markdown("**💾 Storage:** Google Sheets")
            st.caption("Data persists across sessions ✓")
        else:
            st.markdown("**⚠ Storage:** Session memory only")
            st.caption("Data resets on page refresh. Set up Google Sheets to persist data.")

        st.markdown("---")
        log_df = get_log()
        st.markdown(f"""
        <div style="font-size:0.79rem;line-height:2;color:rgba(255,255,255,0.7)">
        📋 Records: <strong style="color:white">{len(log_df):,}</strong><br>
        📅 Sessions: <strong style="color:white">{log_df['Session'].nunique() if not log_df.empty else 0}</strong><br>
        🎯 Threshold: <strong style="color:#FF6B35">{int(THRESHOLD_PCT*100)}%</strong>
        </div>
        """, unsafe_allow_html=True)

        # ── DEBUG: show secrets status ──
        with st.expander("🔧 Connection Debug — CLICK HERE", expanded=True):
            try:
                sa_path = os.path.join(DATA_DIR, "service_account.json")
                st.write("**service_account.json exists:**", os.path.exists(sa_path))
                all_keys = list(st.secrets.keys())
                st.write("**Secret keys found:**", all_keys)
                
                sheet_id = st.secrets.get("GSHEET_ID", "NOT FOUND")
                st.write("**GSHEET_ID:**", sheet_id[:30] + "..." if len(str(sheet_id)) > 30 else sheet_id)
                st.write("**Starts with http?**", str(sheet_id).startswith("http"))
                st.write("**Length:**", len(str(sheet_id)))
                
                has_gcp = "gcp_service_account" in st.secrets
                st.write("**gcp_service_account present:**", has_gcp)
                
                configured = has_sheets_configured()
                st.write("**has_sheets_configured():**", configured)
                st.write("**using_sheets flag:**", st.session_state.get("using_sheets", "not set"))
                
                if configured:
                    st.success("✅ Config detected")
                else:
                    st.error("❌ Config incomplete — GSHEET_ID must be the ID only (not a URL)")

                # Show last connection error if any
                err = st.session_state.get("gsheet_error")
                if err:
                    st.error(f"**Last error:** {err[:300]}")

                if st.button("🔄 Test connection to Sheets"):
                    st.session_state.pop("gsheet_error", None)
                    if "att_log" in st.session_state:
                        del st.session_state["att_log"]
                    if "using_sheets" in st.session_state:
                        del st.session_state["using_sheets"]
                    st.rerun()
            except Exception as e:
                st.error(f"Debug error: {e}")

        return sel_batch, int(session_no), session_date, int(sched_dur), threshold_min


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — IMPORT & PROCESS
# ══════════════════════════════════════════════════════════════════════════════
def tab_import(master_df, sel_batch, session_no, session_date, sched_dur, threshold_min):
    # Persistence banner
    if st.session_state.get("using_sheets"):
        st.markdown('<div class="persist-banner">💾 Google Sheets connected — all committed data is saved permanently and shared across the team.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="persist-banner warn">⚠ Running on session memory — data will reset on page refresh. Contact your admin to connect Google Sheets.</div>', unsafe_allow_html=True)

    st.markdown('<p class="sec-title">Import & Process Teams Attendance CSV</p>', unsafe_allow_html=True)

    step = st.session_state.get('import_step', 1)
    st.markdown(f"""
    <div class="steps">
        <div class="step {'done' if step>1 else 'active'}">1 · Upload CSV</div>
        <div class="step {'done' if step>2 else 'active' if step==2 else ''}">2 · Validate</div>
        <div class="step {'done' if step>3 else 'active' if step==3 else ''}">3 · Review</div>
        <div class="step {'active' if step==4 else 'done' if step>4 else ''}">4 · Done</div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("📖 How to get the attendance CSV from Teams", expanded=(step==1)):
        st.markdown("""
**After class ends:**
1. Open **Microsoft Teams** → click **Calendar** in the left panel
2. Find today's meeting → click it
3. Click the **Recap** tab → find **Attendance** → click **⬇ Download**
4. A `.csv` file downloads to your computer
5. Upload it below

> ⚠ **Wait ~5 minutes after class** before downloading — Teams needs time to generate the full report.
        """)

    st.markdown(f"""
    <div class="upload-hint">
    <strong>Processing:</strong> &nbsp;
    Batch <strong>{sel_batch}</strong> &nbsp;·&nbsp;
    Session <strong>{session_no}</strong> &nbsp;·&nbsp;
    Date <strong>{session_date.strftime('%d %b %Y')}</strong> &nbsp;·&nbsp;
    Threshold <strong>{threshold_min} min</strong> ({int(THRESHOLD_PCT*100)}% of {sched_dur} min)
    <br><span style="font-size:0.76rem;color:#3B82F6">← Change batch/session/date in the left sidebar</span>
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Upload Teams CSV",
        type=['csv','txt'],
        key="csv_upload",
        label_visibility="collapsed"
    )

    if not uploaded:
        st.session_state['import_step'] = 1
        st.session_state.pop('pending_df', None)
        return

    st.session_state['import_step'] = 2
    text     = uploaded.read().decode('utf-8-sig', errors='replace')
    raw_rows = parse_teams_csv(text)

    if not raw_rows:
        st.markdown('<div class="alert alert-error">❌ No participants found. Make sure you uploaded a Teams attendance CSV and it contains a "2. Participants" section.</div>', unsafe_allow_html=True)
        return

    # Process
    processed, bot_count, unmatched = [], 0, 0
    batch_master = master_df[master_df['Batch']==sel_batch]

    for cols in raw_rows:
        raw_name = cols[0] if len(cols)>0 else ''
        email    = cols[4] if len(cols)>4 else ''
        dur_raw  = cols[3] if len(cols)>3 else ''
        if is_excluded(raw_name, email): bot_count += 1; continue
        dur_min  = parse_duration_minutes(dur_raw)
        cleaned  = clean_name(raw_name)
        app_no   = match_student(raw_name, batch_master) or match_student(raw_name, master_df)
        if not app_no: unmatched += 1
        processed.append({
            'Date':str(session_date),'Batch':sel_batch,'Session':session_no,
            'App_No':app_no or '','Raw_Name':raw_name,'Clean_Name':cleaned,
            'Email':email,'Dur_Min':dur_min,'Dur_Raw':dur_raw,
            'Status':status_label(dur_min, threshold_min),'Matched':bool(app_no),
        })

    pending_df = pd.DataFrame(processed)
    present_n  = (pending_df['Status']=='✅ Present').sum()
    late_n     = (pending_df['Status']=='⚠ Late').sum()
    absent_n   = (pending_df['Status']=='❌ Absent').sum()

    st.markdown("---")
    st.markdown('<p class="sec-title">Validation Results</p>', unsafe_allow_html=True)

    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(f'<div class="kpi-card green"><div class="kpi-lbl">Present</div><div class="kpi-val">{present_n}</div><div class="kpi-sub">≥{threshold_min} min</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="kpi-card amber"><div class="kpi-lbl">Late</div><div class="kpi-val">{late_n}</div><div class="kpi-sub">< {threshold_min} min</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="kpi-card red"><div class="kpi-lbl">Absent</div><div class="kpi-val">{absent_n}</div><div class="kpi-sub">Not in report</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="kpi-card"><div class="kpi-lbl">Total</div><div class="kpi-val">{len(pending_df)}</div><div class="kpi-sub">{bot_count} bots excluded</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    if bot_count:
        st.markdown(f'<div class="alert alert-info">ℹ {bot_count} bot/staff entry(ies) excluded (Otter.ai, Fireflies, mponline.gov.in).</div>', unsafe_allow_html=True)
    if unmatched:
        st.markdown(f'<div class="alert alert-warning">⚠ {unmatched} name(s) not matched to Master Data. Edit the "Clean Name" column below to fix, then commit.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="alert alert-success">✅ All {len(pending_df)} students matched successfully.</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<p class="sec-title">Preview — Edit Names to Fix Mismatches</p>', unsafe_allow_html=True)

    edit_df = pending_df[['Clean_Name','Raw_Name','Dur_Min','Dur_Raw','Status','Matched','App_No']].copy()
    edit_df.columns = ['Clean Name ✏','Raw Name (Teams)','Duration (min)','Duration (raw)','Status','Matched?','App No.']
    edited = st.data_editor(
        edit_df,
        use_container_width=True,
        hide_index=True,
        disabled=['Raw Name (Teams)','Duration (min)','Duration (raw)','Status','Matched?','App No.'],
        column_config={
            'Matched?':       st.column_config.CheckboxColumn(width='small'),
            'Duration (min)': st.column_config.NumberColumn(format='%.1f min', width='small'),
            'Status':         st.column_config.TextColumn(width='medium'),
        },
        key="edit_table"
    )

    # Re-match after name edits
    pending_df['Clean_Name'] = edited['Clean Name ✏'].values
    for i, row in pending_df.iterrows():
        if not row['Matched']:
            new_app = match_student(row['Clean_Name'], batch_master) or match_student(row['Clean_Name'], master_df)
            if new_app:
                pending_df.at[i,'App_No']  = new_app
                pending_df.at[i,'Matched'] = True

    st.session_state['pending_df'] = pending_df
    st.session_state['import_step'] = 3

    st.markdown("---")
    col_commit, col_dl, _ = st.columns([2,2,4])

    with col_commit:
        if st.button("✅ Commit to Attendance Log", type="primary", use_container_width=True):
            log_df = get_log()
            # Duplicate check
            if not log_df.empty:
                dup = log_df[(log_df['Batch']==sel_batch) &
                             (log_df['Session'].astype(str)==str(session_no)) &
                             (log_df['Date']==str(session_date))]
                if not dup.empty:
                    st.warning(f"⚠ Session {session_no} for {sel_batch} on {session_date} already exists. Delete it from the log first to re-commit.")
                    return

            commit_cols = ['Date','Batch','Session','App_No','Raw_Name','Clean_Name','Email','Dur_Min','Dur_Raw','Status','Matched']
            rows_to_commit = pending_df[commit_cols].copy()
            saved = append_log(rows_to_commit)

            st.session_state['import_step'] = 4
            st.session_state.pop('pending_df', None)
            st.session_state['log_loaded'] = True  # keep loaded flag

            if saved:
                st.success(f"✅ {len(rows_to_commit)} records committed — {sel_batch} Session {session_no} on {session_date}")
                st.balloons()
            else:
                st.warning("Records saved to session memory but Google Sheets sync failed. Check your Sheets configuration.")

    with col_dl:
        if st.session_state.get('pending_df') is not None:
            csv_b = pending_df.to_csv(index=False).encode()
            st.download_button("⬇ Download Processed CSV", data=csv_b,
                               file_name=f"Processed_{sel_batch}_S{session_no}.csv",
                               mime="text/csv", use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
def tab_dashboard(batches_df):
    log_df     = get_log()
    summary_df = get_summary()
    total_sess = log_df['Session'].nunique() if not log_df.empty else 0
    eligible   = (summary_df['Status']=='✅ Eligible').sum()
    atrisk     = (summary_df['Status']=='⚠ At Risk').sum()
    fail       = (summary_df['Status']=='❌ Will Not Qualify').sum()

    st.markdown('<p class="sec-title">Overall Attendance Health</p>', unsafe_allow_html=True)
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    cards = [
        (c1,"Enrollments","2,228","13 batches",""),
        (c2,"Unique Students","1,523","705 multi-enrolled",""),
        (c3,"Sessions Logged",str(total_sess),"All batches",""),
        (c4,"Eligible ≥75%", str(eligible) if eligible else "—","Certificate track","green"),
        (c5,"At Risk",        str(atrisk)   if atrisk  else "—","50–74%","amber"),
        (c6,"Won't Qualify",  str(fail)     if fail    else "—","Below 50%","red"),
    ]
    for col,lbl,val,sub,cls in cards:
        with col:
            st.markdown(f'<div class="kpi-card {cls}"><div class="kpi-lbl">{lbl}</div><div class="kpi-val">{val}</div><div class="kpi-sub">{sub}</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    st.markdown('<p class="sec-title">Batch Performance</p>', unsafe_allow_html=True)

    rows_html = ""
    for _, brow in batches_df.iterrows():
        b        = brow['Batch']
        enrolled = int(brow['Enrolled'])
        b_sess   = log_df[log_df['Batch']==b]['Session'].nunique() if not log_df.empty else 0
        b_sum    = summary_df[summary_df['Batch']==b]
        elig     = (b_sum['Status']=='✅ Eligible').sum()
        risk     = ((b_sum['Status']=='⚠ At Risk')|(b_sum['Status']=='❌ Will Not Qualify')).sum()
        b_pct    = elig/enrolled if enrolled>0 and b_sess>0 else None
        color    = "#1A7A4A" if b_pct and b_pct>=0.75 else ("#E8920A" if b_pct and b_pct>=0.50 else "#C0392B")
        bar      = pct_bar_html(b_pct, color)
        rows_html += f"""<tr>
            <td><strong>{b}</strong></td>
            <td style="font-size:0.79rem">{PROG_SHORT.get(brow['Program'],brow['Program'][:35])}</td>
            <td style="font-size:0.79rem">{brow['SME']}</td>
            <td style="text-align:center;font-family:monospace">{enrolled}</td>
            <td style="text-align:center;font-family:monospace">{b_sess or '—'}</td>
            <td style="text-align:center;color:#1A7A4A;font-weight:700">{elig or '—'}</td>
            <td style="text-align:center;color:#E8920A;font-weight:700">{risk or '—'}</td>
            <td style="min-width:160px">{bar}</td>
        </tr>"""

    st.markdown(f"""
    <div class="tbl-wrap">
    <table class="styled-table" style="min-width:750px">
      <thead><tr>
        <th>Batch</th><th>Program</th><th>SME</th>
        <th style="text-align:center">Enrolled</th><th style="text-align:center">Sessions</th>
        <th style="text-align:center">✅ Eligible</th><th style="text-align:center">⚠ At Risk</th>
        <th>Attendance %</th>
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table></div>
    """, unsafe_allow_html=True)

    # Export
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    if not log_df.empty:
        if st.button("📥 Generate Excel Report", type="primary"):
            with st.spinner("Building report..."):
                try:
                    xl = export_excel(log_df, summary_df)
                    st.download_button(
                        "⬇ Download Excel",
                        data=xl,
                        file_name=f"VITS_Attendance_{date.today().isoformat()}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                except Exception as e:
                    st.error(f"Export error: {e}")
    else:
        st.markdown('<div class="empty-state"><div class="empty-icon">📊</div><h3>No data yet</h3><p>Import and commit a session to see the dashboard populate.</p></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — STUDENTS
# ══════════════════════════════════════════════════════════════════════════════
def tab_students(batches_df):
    summary_df = get_summary()
    log_df     = get_log()

    c1,c2,c3 = st.columns([3,2,2])
    with c1: q  = st.text_input("🔍 Search name / ID / email", placeholder="Start typing...", label_visibility="collapsed", key="stu_q")
    with c2: bf = st.selectbox("Batch",  ["All Batches"] + batches_df['Batch'].tolist(), label_visibility="collapsed", key="stu_bf")
    with c3: sf = st.selectbox("Status", ["All Status","✅ Eligible","⚠ At Risk","❌ Will Not Qualify","No Data"], label_visibility="collapsed", key="stu_sf")

    df = summary_df.copy()
    if q:           df = df[df['Name'].str.lower().str.contains(q.lower()) | df['App_No'].str.lower().str.contains(q.lower()) | df['Email'].str.lower().str.contains(q.lower())]
    if bf!="All Batches": df = df[df['Batch']==bf]
    if sf!="All Status":  df = df[df['Status']==sf]

    st.caption(f"Showing {len(df):,} of {len(summary_df):,} enrollment records")

    if df.empty:
        st.markdown('<div class="empty-state"><div class="empty-icon">🔍</div><h3>No results</h3><p>Try different search or filter criteria.</p></div>', unsafe_allow_html=True)
        return

    rows_html = ""
    for _, row in df.head(300).iterrows():
        bar = pct_bar_html(row['Attend_Pct'])
        rows_html += f"""<tr>
            <td style="font-family:monospace;font-size:0.75rem">{row['App_No']}</td>
            <td style="font-weight:600">{row['Name']}</td>
            <td style="font-family:monospace;font-size:0.8rem">{row['Batch']}</td>
            <td style="text-align:center;font-family:monospace">{row['Sessions_Held'] or '—'}</td>
            <td style="text-align:center;color:#1A7A4A;font-weight:700">{row['Present'] or '—'}</td>
            <td style="text-align:center;color:#C0392B;font-weight:700">{row['Absent'] or '—'}</td>
            <td style="min-width:130px">{bar}</td>
            <td>{badge_html(row['Status'])}</td>
        </tr>"""

    st.markdown(f"""
    <div class="tbl-wrap">
    <table class="styled-table" style="min-width:700px">
      <thead><tr>
        <th>App No.</th><th>Name</th><th>Batch</th>
        <th style="text-align:center">Sessions</th><th style="text-align:center">Present</th>
        <th style="text-align:center">Absent</th><th>Attendance %</th><th>Status</th>
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table></div>
    """, unsafe_allow_html=True)
    if len(df)>300: st.caption(f"Showing first 300 of {len(df)} results. Use filters to narrow down.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — ATTENDANCE LOG
# ══════════════════════════════════════════════════════════════════════════════
def tab_log(batches_df):
    log_df = get_log()
    if log_df.empty:
        st.markdown('<div class="empty-state"><div class="empty-icon">📋</div><h3>No records yet</h3><p>Import and commit a session to start the log.</p></div>', unsafe_allow_html=True)
        return

    c1,c2,c3,c4 = st.columns([3,2,2,2])
    with c1: q  = st.text_input("🔍",placeholder="Search name or batch...",label_visibility="collapsed",key="log_q")
    with c2: bf = st.selectbox("Batch",["All Batches"]+batches_df['Batch'].tolist(),label_visibility="collapsed",key="log_bf")
    with c3: sf = st.selectbox("Status",["All","✅ Present","⚠ Late","❌ Absent"],label_visibility="collapsed",key="log_sf")
    with c4: st.markdown(f"<div style='padding-top:8px;font-size:0.82rem;color:#6B7280'>{len(log_df):,} total records</div>", unsafe_allow_html=True)

    filtered = log_df.copy()
    try: filtered = filtered.sort_values(['Date','Batch','Session'],ascending=[False,True,True])
    except: pass
    if q:           filtered = filtered[filtered['Clean_Name'].str.lower().str.contains(q.lower(),na=False) | filtered['Batch'].str.lower().str.contains(q.lower(),na=False)]
    if bf!="All Batches": filtered = filtered[filtered['Batch']==bf]
    if sf!="All":   filtered = filtered[filtered['Status']==sf]

    display = filtered.head(500)
    rows_html = ""
    for _, row in display.iterrows():
        rows_html += f"""<tr>
            <td style="font-family:monospace;font-size:0.75rem">{row['Date']}</td>
            <td style="font-family:monospace;font-weight:700">{row['Batch']}</td>
            <td style="text-align:center;font-family:monospace">{row['Session']}</td>
            <td style="font-weight:500">{row['Clean_Name']}</td>
            <td style="text-align:center;font-family:monospace">{float(row['Dur_Min']):.0f} min</td>
            <td>{badge_html(row['Status'])}</td>
            <td style="font-size:0.74rem;color:#9CA3AF">{row.get('Email','') or '—'}</td>
        </tr>"""

    st.markdown(f"""
    <div class="tbl-wrap">
    <table class="styled-table" style="min-width:680px">
      <thead><tr>
        <th>Date</th><th>Batch</th><th style="text-align:center">Session</th>
        <th>Name</th><th style="text-align:center">Duration</th><th>Status</th><th>Email</th>
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table></div>
    """, unsafe_allow_html=True)

    if len(filtered)>500: st.caption(f"Showing 500 of {len(filtered)} filtered records.")

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    col1, col2 = st.columns([2,6])
    with col1:
        csv_b = log_df.to_csv(index=False).encode()
        st.download_button("⬇ Download Full Log", data=csv_b,
                           file_name=f"AttendanceLog_{date.today().isoformat()}.csv", mime="text/csv")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — AT-RISK
# ══════════════════════════════════════════════════════════════════════════════
def tab_atrisk(batches_df):
    log_df     = get_log()
    summary_df = get_summary()
    risk_df    = summary_df[summary_df['Status'].isin(['⚠ At Risk','❌ Will Not Qualify'])].copy()

    if log_df.empty:
        st.markdown('<div class="alert alert-info">ℹ Import and commit attendance sessions first. At-Risk report will auto-populate.</div>', unsafe_allow_html=True)
        return

    if risk_df.empty:
        st.markdown('<div class="alert alert-success">🎉 No at-risk students — all students with data are on track for their certificate.</div>', unsafe_allow_html=True)
        return

    st.markdown(f'<div class="alert alert-warning">⚠ <strong>{len(risk_df)} students</strong> are below 75% attendance and at risk of losing their certificate. Share with each SME and college SPOC every Friday.</div>', unsafe_allow_html=True)

    c1,c2,c3 = st.columns([2,2,4])
    with c1: bf = st.selectbox("Batch",["All Batches"]+batches_df['Batch'].tolist(),label_visibility="collapsed",key="risk_bf")
    with c2: sf = st.selectbox("Status",["All Risk","⚠ At Risk","❌ Will Not Qualify"],label_visibility="collapsed",key="risk_sf")
    with c3:
        csv_b = risk_df.to_csv(index=False).encode()
        st.download_button("⬇ Export At-Risk CSV", data=csv_b,
                           file_name=f"AtRisk_{date.today().isoformat()}.csv", mime="text/csv", type="primary")

    if bf!="All Batches": risk_df = risk_df[risk_df['Batch']==bf]
    if sf=="⚠ At Risk":   risk_df = risk_df[risk_df['Status']=='⚠ At Risk']
    elif sf=="❌ Will Not Qualify": risk_df = risk_df[risk_df['Status']=='❌ Will Not Qualify']
    risk_df = risk_df.sort_values('Attend_Pct', ascending=True)

    rows_html = ""
    for _, row in risk_df.iterrows():
        bar = pct_bar_html(row['Attend_Pct'])
        rows_html += f"""<tr>
            <td style="font-family:monospace;font-size:0.75rem">{row['App_No']}</td>
            <td style="font-weight:600">{row['Name']}</td>
            <td style="font-size:0.74rem;color:#9CA3AF">{row['Email'] or '—'}</td>
            <td style="font-family:monospace;font-weight:700">{row['Batch']}</td>
            <td style="font-size:0.78rem">{PROG_SHORT.get(row['Program'],row['Program'][:28])}</td>
            <td style="font-size:0.78rem">{row['SME']}</td>
            <td style="text-align:center;font-family:monospace">{row['Sessions_Held']}</td>
            <td style="text-align:center;font-family:monospace">{row['Present']}</td>
            <td style="min-width:130px">{bar}</td>
            <td>{badge_html(row['Status'])}</td>
        </tr>"""

    st.markdown(f"""
    <div class="tbl-wrap">
    <table class="styled-table" style="min-width:900px">
      <thead><tr>
        <th>App No.</th><th>Name</th><th>Email</th><th>Batch</th><th>Program</th><th>SME</th>
        <th style="text-align:center">Sessions</th><th style="text-align:center">Present</th>
        <th>Attendance %</th><th>Status</th>
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table></div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — AI INSIGHTS
# ══════════════════════════════════════════════════════════════════════════════
def tab_ai():
    log_df     = get_log()
    summary_df = get_summary()
    batches    = load_batches()

    total_sess = log_df['Session'].nunique() if not log_df.empty else 0
    eligible   = (summary_df['Status']=='✅ Eligible').sum()
    atrisk     = (summary_df['Status']=='⚠ At Risk').sum()
    fail       = (summary_df['Status']=='❌ Will Not Qualify').sum()
    nodata     = (summary_df['Status']=='No Data').sum()

    batch_lines = []
    for _, brow in batches.iterrows():
        b     = brow['Batch']
        b_log = log_df[log_df['Batch']==b] if not log_df.empty else pd.DataFrame()
        b_s   = b_log['Session'].nunique() if not b_log.empty else 0
        b_sum = summary_df[summary_df['Batch']==b]
        be    = (b_sum['Status']=='✅ Eligible').sum()
        br    = ((b_sum['Status']=='⚠ At Risk')|(b_sum['Status']=='❌ Will Not Qualify')).sum()
        batch_lines.append(f"{b} ({PROG_SHORT.get(brow['Program'],brow['Program'][:25])}, {brow['SME']}): {brow['Enrolled']} enrolled, {b_s} sessions, {be} eligible, {br} at-risk")

    context = f"""You are an attendance analytics assistant for MPOnline Ltd. (Govt. of MP + TCS JV), helping Palash Jaiswal manage internship/certificate attendance at VITS Bhopal.

DATA:
- Enrollments: 2,228 across 13 batches (1,523 unique, 705 multi-enrolled)
- Sessions logged: {total_sess} | Records: {len(log_df)}
- Eligible (≥75%): {eligible} | At Risk (50-74%): {atrisk} | Won't Qualify (<50%): {fail} | No data: {nodata}

BATCHES:
{chr(10).join(batch_lines)}

Programs: SE+AI Foundation, Advanced Software Engineering, AI/ML, Digital Marketing.
Certificate = ≥75% attendance. No refund policy. Be direct, specific, actionable."""

    st.markdown("""
    <div class="ai-wrap">
        <div class="ai-label">Powered by Claude · Anthropic</div>
        <div class="ai-title">🤖 Attendance Intelligence Assistant</div>
        <div class="ai-sub">Ask questions, get summaries, identify at-risk patterns, plan next steps.</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    quick = {
        "📊 Summary":        "Give me a concise attendance health summary across all 13 batches.",
        "🔍 Worst Batches":  "Which batches have the worst attendance rates and what are likely causes?",
        "🚨 At-Risk":        "How many students risk losing their certificate? Which batches need urgent attention?",
        "💡 This Week":      "What are the 3 most important actions I should take this week?",
        "📩 SPOC Message":   "Draft a WhatsApp message to a college SPOC about students who are at risk of losing their certificate.",
    }
    cols = st.columns(5)
    clicked_q = None
    for col, (label, question) in zip(cols, quick.items()):
        with col:
            if st.button(label, use_container_width=True, key=f"ai_quick_{label}"):
                clicked_q = question

    user_q = st.text_input("Or type your own question...", key="ai_input",
                           placeholder="e.g. Which students in B3(A) have below 50%?",
                           label_visibility="collapsed")
    send   = st.button("Send →", type="primary", key="ai_send")
    question = clicked_q or (user_q if send and user_q else None)

    if question:
        try:
            api_key = st.secrets.get("ANTHROPIC_API_KEY","")
        except Exception:
            api_key = ""

        if not api_key:
            st.markdown('<div class="alert alert-warning">⚠ No Anthropic API key configured. Add ANTHROPIC_API_KEY to Streamlit Secrets to enable AI Insights.</div>', unsafe_allow_html=True)
            return

        with st.spinner("Analysing..."):
            try:
                client = anthropic.Anthropic(api_key=api_key)
                msg    = client.messages.create(
                    model="claude-sonnet-4-20250514", max_tokens=1000,
                    system=context,
                    messages=[{"role":"user","content":question}]
                )
                answer = msg.content[0].text
                st.markdown(f"""
                <div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:10px;
                            padding:18px;margin-top:14px;line-height:1.8;
                            font-size:0.87rem;white-space:pre-wrap">{answer}</div>
                """, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"API error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    master_df  = load_master()
    batches_df = load_batches()
    init_log()

    render_topbar()

    sel_batch, session_no, session_date, sched_dur, threshold_min = render_sidebar(batches_df)

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📥  Import & Process",
        "📊  Dashboard",
        "👤  Students",
        "📋  Attendance Log",
        "🚨  At-Risk",
        "🤖  AI Insights",
    ])

    with tab1: tab_import(master_df, sel_batch, session_no, session_date, sched_dur, threshold_min)
    with tab2: tab_dashboard(batches_df)
    with tab3: tab_students(batches_df)
    with tab4: tab_log(batches_df)
    with tab5: tab_atrisk(batches_df)
    with tab6: tab_ai()


if __name__ == "__main__":
    main()
