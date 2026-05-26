# VITS Attendance Intelligence
### MPOnline Ltd. · Skills Development Vertical

Streamlit-based attendance management system for VITS Bhopal internship and certificate programs.

## Features
- Upload Teams attendance CSV → auto-validates, parses, flags issues
- 75% threshold eligibility tracking across 2,228 students / 13 batches
- Dashboard, student directory, at-risk report
- Export to multi-sheet Excel (Log · Summary · At-Risk · Batch · Session Pivot)
- Claude AI Insights for pattern detection and action recommendations

## Setup

### 1. Clone & install locally (optional)
```bash
git clone https://github.com/YOUR_USERNAME/vits-attendance.git
cd vits-attendance
pip install -r requirements.txt
streamlit run app.py
```

### 2. Deploy on Streamlit Community Cloud
See `DEPLOYMENT_GUIDE.md` for step-by-step instructions.

## Adding AI Insights API Key
In Streamlit Community Cloud → App Settings → Secrets:
```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

## Data
- `data/master_students.csv` — all enrolled students (2,228 rows)
- `data/batch_info.csv` — batch metadata (13 batches)
- `data/logo.png` — MPOnline logo

## Attendance Threshold
**75%** of scheduled session duration = Present  
Set per-session in the sidebar.

---
*MPOnline Ltd. · Joint venture between Govt. of Madhya Pradesh and TCS*
