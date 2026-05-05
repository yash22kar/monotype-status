"""
Research Team Productivity Dashboard
Streamlit + Supabase
"""
import streamlit as st
import pandas as pd
from datetime import date, datetime, time
import re
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from supabase import create_client, Client

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Research Team Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Global CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Tabs: full width, evenly spaced ───────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: rgba(255,255,255,0.04);
    border-radius: 10px;
    padding: 4px;
    margin-bottom: 1.2rem;
}
.stTabs [data-baseweb="tab"] {
    flex: 1;
    justify-content: center;
    font-weight: 600;
    font-size: 1rem;
    border-radius: 8px;
    height: 46px;
    color: rgba(255,255,255,0.55);
    transition: all 0.2s ease;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg,#4f8ef7,#764ba2) !important;
    color: white !important;
}
.stTabs [data-baseweb="tab-highlight"] { display: none; }
.stTabs [data-baseweb="tab-border"]    { display: none; }

/* ── Metric cards ───────────────────────────────────────────────────── */
.metric-card {
    border-radius: 14px;
    padding: 20px 18px 16px;
    text-align: center;
    box-shadow: 0 4px 16px rgba(0,0,0,0.3);
    margin-bottom: 6px;
}
.metric-card .val {
    font-size: 2.6rem;
    font-weight: 800;
    color: #fff;
    line-height: 1;
    margin: 8px 0 6px;
}
.metric-card .lbl {
    font-size: 0.82rem;
    color: rgba(255,255,255,0.82);
    font-weight: 500;
    letter-spacing: 0.03em;
}
.metric-card .ico { font-size: 1.5rem; }

/* ── Researcher table rows ──────────────────────────────────────────── */
.r-table-header {
    display: flex;
    padding: 9px 16px;
    background: rgba(255,255,255,0.07);
    border-radius: 8px 8px 0 0;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: rgba(255,255,255,0.45);
    margin-bottom: 1px;
}
.r-row {
    display: flex;
    align-items: center;
    padding: 10px 16px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    background: rgba(255,255,255,0.02);
    transition: background 0.15s;
}
.r-row:hover { background: rgba(255,255,255,0.05); }
.r-row.expanded { background: rgba(79,142,247,0.08); border-left: 3px solid #4f8ef7; }
.r-name { flex: 2.8; font-weight: 600; }
.r-num  { flex: 0.7; text-align: center; font-size: 0.95rem; }
.r-done { color: #2ecc71; font-weight: 700; }
.r-pend { color: #e67e22; font-weight: 700; }
.r-detail {
    background: rgba(79,142,247,0.05);
    border-left: 3px solid rgba(79,142,247,0.5);
    padding: 16px 20px 20px 24px;
    margin-bottom: 2px;
}

/* ── Sidebar cleanup ────────────────────────────────────────────────── */
section[data-testid="stSidebar"] > div {
    display: flex;
    flex-direction: column;
    height: 100%;
}
.sidebar-spacer { flex: 1; }
</style>
""", unsafe_allow_html=True)

# ─── Constants ────────────────────────────────────────────────────────────────
CREDENTIALS = {
    "yash.baviskar@centralogic.net":        {"password": "Krishna@123",   "role": "admin"},
    "research.insights@centralogic.com":    {"password": "Research#2026", "role": "read_only"},
}

def is_read_only() -> bool:
    return st.session_state.get("user_role") == "read_only"

RESEARCHERS = [
    "Ashwini Jadhav", "Bhushan Joshi", "Aditya Jadhav", "Sahil Mete",
    "Omkar Yemul", "Sakshi Gund", "Sakshi Patil", "Sakshi Karale",
    "Sakshi Khadakkar", "Shubham Pawar", "Shubham Jagdhane",
    "Manohar Chavan", "Vallabh Tupe", "Kajal Gupta",
]

QA_REVIEWERS = [
    "Ashwini Jadhav", "Bhushan Joshi", "Aditya Jadhav", "Sahil Mete",
    "Omkar Yemul", "Sakshi Gund", "Sakshi Patil", "Sakshi Karale",
    "Sakshi Khadakkar", "Shubham Pawar", "Shubham Jagdhane",
    "Manohar Chavan", "Vallabh Tupe", "Kajal Gupta",
    "Manasi Kolhe", "Swamini Jadhav", "Rahul Modhave",
    "Niketan Gadade", "Ajinkya Mhetre",
]

FUD_REVIEWERS = [
    "Ashwini Jadhav", "Bhushan Joshi", "Aditya Jadhav", "Sahil Mete",
    "Omkar Yemul", "Sakshi Gund", "Sakshi Patil", "Sakshi Karale",
    "Sakshi Khadakkar", "Shubham Pawar", "Shubham Jagdhane",
    "Manohar Chavan", "Vallabh Tupe", "Kajal Gupta",
]

ASSET_COUNT_FIELDS = [
    "subsidiary_count",
    "website_count",
    "app",
    "digital_ads",
    "epubs",
    "software",
    "dam",
    "webserver",
]
ASSET_DATE_FIELDS = ["start_date", "end_date"]
ASSET_TIME_FIELDS = ["start_time", "end_time"]

# ─── Supabase Client ──────────────────────────────────────────────────────────
@st.cache_resource
def get_sb() -> Client:
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception:
        st.error(
            "⚠️ Supabase credentials not configured. "
            "Add `SUPABASE_URL` and `SUPABASE_KEY` to `.streamlit/secrets.toml`."
        )
        st.stop()

# ─── Cached Fetchers ──────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def _raw_companies():
    return get_sb().table("companies").select("*").order("company_name").execute().data or []

@st.cache_data(ttl=30)
def _raw_metrics():
    return get_sb().table("daily_metrics").select("*").execute().data or []

def get_companies() -> pd.DataFrame:
    data = _raw_companies()
    if not data:
        return pd.DataFrame(columns=[
            "id", "company_name", "assigned_to", "status",
            "subsidiary_count", "website_count", "date_completed",
            "app", "digital_ads", "epubs", "software", "dam", "webserver",
            "start_date", "end_date",
            "start_time", "end_time",
            "qa_status", "fud_status", "qa_done_date", "fud_done_date",
            "wayback_status", "created_at"
        ])
    df = pd.DataFrame(data)
    for col in ASSET_COUNT_FIELDS:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    for col in ASSET_DATE_FIELDS:
        if col not in df.columns:
            df[col] = None
    for col in ASSET_TIME_FIELDS:
        if col not in df.columns:
            df[col] = None
    for col in ["qa_status", "fud_status"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("")
    for col in ["qa_done_date", "fud_done_date"]:
        if col not in df.columns:
            df[col] = None
    if "wayback_status" not in df.columns:
        df["wayback_status"] = "completed"
    df["wayback_status"] = df["wayback_status"].fillna("completed")
    return df

def get_metrics() -> pd.DataFrame:
    data = _raw_metrics()
    if not data:
        return pd.DataFrame(columns=["id", "date", "researcher", "fud_completed", "qa_done"])
    df = pd.DataFrame(data)
    for col in ["fud_completed", "qa_done"]:
        df[col] = pd.to_numeric(df.get(col, 0), errors="coerce").fillna(0).astype(int)
    return df

def bust_cache():
    _raw_companies.clear()
    _raw_metrics.clear()

def _api_error_message(err: Exception) -> str:
    # postgrest.exceptions.APIError often stores a dict as args[0]
    try:
        if getattr(err, "args", None) and err.args:
            if isinstance(err.args[0], dict):
                return err.args[0].get("message") or str(err.args[0])
            return str(err.args[0])
    except Exception:
        pass
    return str(err)

def _pgrst_missing_column(err: Exception):
    msg = _api_error_message(err)
    m = re.search(r"Could not find the '([^']+)' column of '([^']+)'", msg)
    if not m:
        return None
    return m.group(1)

def _warn_missing_columns_once(table: str, cols: list):
    if not cols:
        return
    key = f"_warned_missing_cols_{table}"
    warned = set(st.session_state.get(key, []))
    new_cols = [c for c in cols if c not in warned]
    if not new_cols:
        return
    warned.update(new_cols)
    st.session_state[key] = sorted(warned)
    st.warning(
        f"Database schema is missing columns on `{table}`: {', '.join(new_cols)}. "
        "Run the SQL migration (see `schema.sql`) and then reload the Supabase API schema cache.",
        icon="⚠️",
    )

def _safe_update_row(table: str, match_col: str, match_val, changes: dict, context: str = "record") -> bool:
    """Update a row, retrying by dropping unknown columns (PGRST204) so the UI doesn't crash."""
    if not changes:
        return False

    pending = dict(changes)
    dropped = []
    for _ in range(20):
        try:
            get_sb().table(table).update(pending).eq(match_col, match_val).execute()
            if dropped:
                _warn_missing_columns_once(table, dropped)
            return True
        except Exception as err:
            missing = _pgrst_missing_column(err)
            if missing and missing in pending:
                dropped.append(missing)
                pending.pop(missing, None)
                if not pending:
                    _warn_missing_columns_once(table, dropped)
                    st.error(f"Could not update {context} because required columns are missing in Supabase.")
                    return False
                continue

            st.error(f"Failed to update {context}.")
            st.caption(_api_error_message(err))
            return False

# ─── DB Write Operations ──────────────────────────────────────────────────────
def complete_companies(updates: list, date_str: str):
    """Mark as LEM/AM complete.
    updates = [{"id": int, "subsidiary_count": int, "qa_status": bool, "fud_status": bool}]"""
    for u in updates:
        payload = {
            "status": "completed",
            "subsidiary_count": u["subsidiary_count"],
            "website_count": u.get("website_count", 0),
            "app": u.get("app", 0),
            "digital_ads": u.get("digital_ads", 0),
            "epubs": u.get("epubs", 0),
            "software": u.get("software", 0),
            "dam": u.get("dam", 0),
            "webserver": u.get("webserver", 0),
            "start_date": _date_to_db(u.get("start_date")),
            "end_date": _date_to_db(u.get("end_date")),
            "start_time": _time_to_db(u.get("start_time")),
            "end_time": _time_to_db(u.get("end_time")),
            "date_completed": date_str,
        }
        if "qa_status" in u:
            payload["qa_status"] = u.get("qa_status") or None
            payload["qa_done_date"] = date_str if (u.get("qa_status") or None) else None
        if "fud_status" in u:
            payload["fud_status"] = u.get("fud_status") or None
            payload["fud_done_date"] = date_str if (u.get("fud_status") or None) else None
        _safe_update_row("companies", "id", u["id"], payload, context=f"company ID {u['id']}")
    bust_cache()

def save_asset_mapping(entries: list):
    """Save Asset Mapping counts/times without changing QA/FUD reviewer fields."""
    for e in entries:
        _safe_update_row("companies", "id", e["id"], {
            "subsidiary_count": e.get("subsidiary_count", 0),
            "website_count":    e.get("website_count", 0),
            "app":              e.get("app", 0),
            "digital_ads":      e.get("digital_ads", 0),
            "epubs":            e.get("epubs", 0),
            "software":         e.get("software", 0),
            "dam":              e.get("dam", 0),
            "webserver":        e.get("webserver", 0),
            "start_date":       _date_to_db(e.get("start_date")),
            "end_date":         _date_to_db(e.get("end_date")),
            "start_time":       _time_to_db(e.get("start_time")),
            "end_time":         _time_to_db(e.get("end_time")),
        }, context=f"company ID {e['id']}")
    bust_cache()

def update_company_asset_fields(company_id: int, changes: dict):
    """Update only the provided Asset Mapping fields for one company."""
    if not changes:
        return False
    ok = _safe_update_row("companies", "id", company_id, changes, context=f"company ID {company_id}")
    if ok:
        bust_cache()
        return True
    return None

def save_qa_fud(entries: list, today_str: str):
    """Save counts + QA/FUD reviewer names and auto-manage done dates."""
    for e in entries:
        qa  = e.get("qa_status")  or None
        fud = e.get("fud_status") or None
        existing_qa_date  = e.get("qa_done_date")  or None
        existing_fud_date = e.get("fud_done_date") or None
        _safe_update_row("companies", "id", e["id"], {
            "subsidiary_count": e.get("subsidiary_count", 0),
            "website_count":    e.get("website_count", 0),
            "app":              e.get("app", 0),
            "digital_ads":      e.get("digital_ads", 0),
            "epubs":            e.get("epubs", 0),
            "software":         e.get("software", 0),
            "dam":              e.get("dam", 0),
            "webserver":        e.get("webserver", 0),
            "start_date":       _date_to_db(e.get("start_date")),
            "end_date":         _date_to_db(e.get("end_date")),
            "start_time":       _time_to_db(e.get("start_time")),
            "end_time":         _time_to_db(e.get("end_time")),
            "qa_status":        qa,
            "fud_status":       fud,
            "qa_done_date":     (existing_qa_date  or today_str) if qa  else None,
            "fud_done_date":    (existing_fud_date or today_str) if fud else None,
        }, context=f"company ID {e['id']}")
    bust_cache()

def revert_companies(ids: list):
    for cid in ids:
        _safe_update_row("companies", "id", cid, {
            "status": "pending",
            "subsidiary_count": 0,
            "website_count": 0,
            "app": 0,
            "digital_ads": 0,
            "epubs": 0,
            "software": 0,
            "dam": 0,
            "webserver": 0,
            "start_date": None,
            "end_date": None,
            "start_time": None,
            "end_time": None,
            "date_completed": None,
            "qa_status": None,
            "fud_status": None,
            "qa_done_date": None,
            "fud_done_date": None,
        }, context=f"company ID {cid}")
    bust_cache()

def upsert_metrics(date_str: str, researcher: str, fud: int, qa: int):
    get_sb().table("daily_metrics").upsert(
        {"date": date_str, "researcher": researcher, "fud_completed": fud, "qa_done": qa},
        on_conflict="date,researcher",
    ).execute()
    bust_cache()

def assign_companies(ids: list, researcher: str):
    get_sb().table("companies").update({"assigned_to": researcher}).in_("id", ids).execute()
    bust_cache()

def insert_companies(rows: list):
    get_sb().table("companies").insert(rows).execute()
    bust_cache()

def delete_companies(ids: list):
    get_sb().table("companies").delete().in_("id", ids).execute()
    bust_cache()

# ─── Helpers ──────────────────────────────────────────────────────────────────
def _now_ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _date_to_db(value):
    parsed = _parse_date_value(value)
    return parsed.isoformat() if parsed else None

def _parse_date_value(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()

def _time_to_db(value):
    parsed = _parse_time_value(value)
    return parsed.strftime("%H:%M:%S") if parsed else None

def _parse_time_value(value):
    if value is None or value == "":
        return None
    if isinstance(value, time):
        return value.replace(second=0, microsecond=0)
    if isinstance(value, datetime):
        return value.time().replace(second=0, microsecond=0)

    text = str(value).strip()
    if not text or text.lower() == "nat":
        return None

    normalized = text.replace("T", " ")
    if " " in normalized:
        normalized = normalized.split(" ")[-1]
    if "." in normalized:
        normalized = normalized.split(".")[0]

    for candidate, fmt in ((normalized, "%H:%M:%S"), (normalized[:5], "%H:%M")):
        try:
            return datetime.strptime(candidate, fmt).time().replace(second=0, microsecond=0)
        except ValueError:
            continue

    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime().time().replace(second=0, microsecond=0)

def _fmt_time(value):
    parsed = _parse_time_value(value)
    return parsed.strftime("%H:%M") if parsed else "—"

def _fmt_date(value):
    parsed = _parse_date_value(value)
    return parsed.strftime("%Y/%m/%d") if parsed else "—"

def _safe_col(df: pd.DataFrame, col: str) -> pd.Series:
    """Return a column filled with '' for NaN so string comparisons work safely."""
    return df[col].fillna("") if col in df.columns else pd.Series("", index=df.index)

# ─── UI Helpers ──────────────────────────────────────────────────────────────
def colored_metric(label: str, value, gradient: str, icon: str) -> str:
    return f"""
    <div class="metric-card" style="background:{gradient};">
        <div class="ico">{icon}</div>
        <div class="val">{value}</div>
        <div class="lbl">{label}</div>
    </div>"""

# ─── Login ────────────────────────────────────────────────────────────────────
def login_page():
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("## 📊 Research Team Dashboard")
        st.markdown("##### Sign in to continue")
        st.divider()
        with st.form("login_form"):
            email = st.text_input("Email Address")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In", width='stretch', type="primary"):
                user = CREDENTIALS.get(email)
                if user and password == user["password"]:
                    st.session_state.update(logged_in=True, user_email=email, user_role=user["role"], last_saved=None)
                    st.rerun()
                else:
                    st.error("Invalid email or password.")

# ─── Sidebar ──────────────────────────────────────────────────────────────────
def render_sidebar(cdf: pd.DataFrame):
    with st.sidebar:
        # ── TOP: Identity ──────────────────────────────────────────────
        st.markdown("## 📊 Research Dashboard")
        st.divider()
        st.markdown(
            f"<p style='margin:0;font-size:0.78rem;color:rgba(255,255,255,0.5);'>LOGGED IN AS</p>"
            f"<p style='margin:4px 0 2px;font-weight:700;font-size:0.95rem;'>"
            f"📧 {st.session_state.user_email}</p>",
            unsafe_allow_html=True,
        )
        if st.session_state.get("last_saved"):
            st.caption(f"🕐 Last saved: {st.session_state.last_saved}")

        st.divider()

        # ── MIDDLE: Admin actions ──────────────────────────────────────
        if not is_read_only():
            st.markdown(
                "<p style='font-size:0.75rem;font-weight:700;text-transform:uppercase;"
                "letter-spacing:0.07em;color:rgba(255,255,255,0.4);margin-bottom:6px;'>Admin Actions</p>",
                unsafe_allow_html=True,
            )

            with st.expander("📥 Import Companies (CSV)"):
                st.caption("CSV must have `company_name`. Optional: `assigned_to`.")
                uploaded = st.file_uploader("Upload CSV", type="csv", key="csv_up")
                if uploaded:
                    try:
                        df_up = pd.read_csv(uploaded)
                        if "company_name" not in df_up.columns:
                            st.error("`company_name` column is required.")
                        else:
                            st.dataframe(df_up.head(5), width='stretch')
                            st.caption(f"{len(df_up)} rows found")
                            if st.button("⬆️ Import All", type="primary", key="btn_import"):
                                rows = []
                                for _, row in df_up.iterrows():
                                    r = {"company_name": str(row["company_name"]).strip()}
                                    if "assigned_to" in df_up.columns and pd.notna(row.get("assigned_to")):
                                        val = str(row["assigned_to"]).strip()
                                        if val in RESEARCHERS:
                                            r["assigned_to"] = val
                                    rows.append(r)
                                insert_companies(rows)
                                st.success(f"Imported {len(rows)} companies!")
                                st.rerun()
                    except Exception as e:
                        st.error(str(e))

            with st.expander("➕ Add Company"):
                with st.form("add_company_form"):
                    cname = st.text_input("Company Name")
                    cassign = st.selectbox("Assign To", ["— Unassigned —"] + RESEARCHERS)
                    if st.form_submit_button("Add", type="primary"):
                        if cname.strip():
                            r = {"company_name": cname.strip()}
                            if cassign != "— Unassigned —":
                                r["assigned_to"] = cassign
                            insert_companies([r])
                            st.success(f"Added: {cname.strip()}")
                            st.rerun()
                        else:
                            st.error("Company name is required.")

            with st.expander("👤 Assign Unassigned"):
                unassigned = cdf[_safe_col(cdf, "assigned_to") == ""]
                st.caption(f"{len(unassigned)} unassigned companies")
                if not unassigned.empty:
                    target_r = st.selectbox("Researcher", RESEARCHERS, key="sb_r")
                    picked = st.multiselect("Companies", unassigned["company_name"].tolist(), key="sb_c")
                    if st.button("Assign →", type="primary", key="btn_assign"):
                        if picked:
                            ids = unassigned[unassigned["company_name"].isin(picked)]["id"].tolist()
                            assign_companies(ids, target_r)
                            st.success(f"Assigned {len(ids)} to {target_r}.")
                            st.rerun()
                        else:
                            st.warning("Select at least one company.")
                else:
                    st.success("All companies are assigned!")

        # ── BOTTOM: Logout (pushed to bottom via spacer) ───────────────
        st.markdown("<div class='sidebar-spacer'></div>", unsafe_allow_html=True)
        st.divider()
        if st.button("🚪 Logout", width='stretch'):
            st.session_state.update(logged_in=False, user_email=None)
            st.rerun()

# ─── Tab 1: Daily Entry ───────────────────────────────────────────────────────
def tab_daily(cdf: pd.DataFrame, mdf: pd.DataFrame):
    # ── Header row: title left, date picker right ──
    h1, h2 = st.columns([7, 2])
    with h1:
        st.markdown("## 📅 Daily Progress Entry")
    with h2:
        sel_date = st.date_input("Select date", value=date.today(), label_visibility="collapsed")
        st.markdown(
            f"<p style='text-align:right;color:rgba(255,255,255,0.45);font-size:0.82rem;margin:0'>"
            f"{sel_date.strftime('%A, %B %d %Y')}</p>",
            unsafe_allow_html=True,
        )
    date_str = sel_date.strftime("%Y-%m-%d")

    # ── Colored metric cards ──
    done_today = cdf[_safe_col(cdf, "date_completed") == date_str]
    n_lem  = len(done_today)
    n_sub  = int(done_today["subsidiary_count"].sum()) if not done_today.empty else 0
    n_qa   = int(done_today["qa_status"].astype(bool).sum())  if not done_today.empty else 0
    n_fud  = int(done_today["fud_status"].astype(bool).sum()) if not done_today.empty else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(colored_metric("Asset Mapping Done Today",   n_lem,  "linear-gradient(135deg,#1a6b3c,#27ae60)", "✅"), unsafe_allow_html=True)
    m2.markdown(colored_metric("Subsidiaries Today",   n_sub,  "linear-gradient(135deg,#1a4a7a,#2980b9)", "📦"), unsafe_allow_html=True)
    m3.markdown(colored_metric("QA Done Today",        n_qa,   "linear-gradient(135deg,#5a1a7a,#8e44ad)", "🔍"), unsafe_allow_html=True)
    m4.markdown(colored_metric("Salesforce Ready Today",       n_fud,  "linear-gradient(135deg,#7a3a0a,#d35400)", "📋"), unsafe_allow_html=True)

    st.divider()

    # ── Summary table: all researchers at a glance ──
    st.markdown("### Researcher Progress")
    summary_rows = []
    for r in RESEARCHERS:
        r_df   = cdf[_safe_col(cdf, "assigned_to") == r]
        r_comp = r_df[r_df["status"] == "completed"]
        r_done_today = r_comp[_safe_col(r_comp, "date_completed") == date_str]
        summary_rows.append({
            "Researcher":   r,
            "Assigned":     len(r_df),
            "Done":         len(r_comp),
            "Pending":      len(r_df) - len(r_comp),
            "QA ✅ Today":  int(r_done_today["qa_status"].astype(bool).sum())  if not r_done_today.empty else 0,
            "FUD ✅ Today": int(r_done_today["fud_status"].astype(bool).sum()) if not r_done_today.empty else 0,
        })
    st.dataframe(
        pd.DataFrame(summary_rows),
        width='stretch',
        hide_index=True,
        column_config={
            "Researcher":   st.column_config.TextColumn(width="large"),
            "Assigned":     st.column_config.NumberColumn(width="small"),
            "Done":         st.column_config.NumberColumn(width="small"),
            "Pending":      st.column_config.NumberColumn(width="small"),
            "QA ✅ Today":  st.column_config.NumberColumn(width="small"),
            "FUD ✅ Today": st.column_config.NumberColumn(width="small"),
        },
    )

    st.divider()

    # ── Per-researcher expandable rows ──
    st.markdown("### Update Progress")
    if is_read_only():
        st.caption("View-only access — data entry is disabled for this account.")
    else:
        st.caption("Click ▼ on any row to expand and update that researcher's companies.")

    if "exp_r" not in st.session_state:
        st.session_state.exp_r = set()

    # Column ratios (must match the HTML header below)
    COL = [3, 0.7, 0.7, 0.75, 0.6, 0.6, 0.85]

    # Table header using matching Streamlit columns
    hdr = st.columns(COL)
    for col, label in zip(hdr, ["Researcher", "Assigned", "Done", "Pending", "QA", "FUD", ""]):
        col.markdown(
            f"<p style='font-size:0.72rem;font-weight:700;text-transform:uppercase;"
            f"letter-spacing:0.08em;color:rgba(255,255,255,0.45);margin:0;"
            f"text-align:center'>{label}</p>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<hr style='margin:4px 0 2px;border-color:rgba(255,255,255,0.12)'>",
        unsafe_allow_html=True,
    )

    for researcher in RESEARCHERS:
        r_df       = cdf[_safe_col(cdf, "assigned_to") == researcher]
        r_pending  = r_df[r_df["status"] == "pending"].sort_values("company_name")
        r_completed = r_df[r_df["status"] == "completed"]
        r_done_today = r_completed[_safe_col(r_completed, "date_completed") == date_str]

        n_assigned = len(r_df)
        n_done     = len(r_completed)
        n_pending  = len(r_pending)
        qa_today   = int(r_done_today["qa_status"].astype(bool).sum())  if not r_done_today.empty else 0
        fud_today  = int(r_done_today["fud_status"].astype(bool).sum()) if not r_done_today.empty else 0
        is_exp     = researcher in st.session_state.exp_r

        # ── Stats row (columns-aligned) ──
        row_cols = st.columns(COL)
        row_cols[0].markdown(f"**{researcher}**")
        row_cols[1].markdown(f"<p style='text-align:center;margin:6px 0'>{n_assigned}</p>", unsafe_allow_html=True)
        row_cols[2].markdown(f"<p style='text-align:center;margin:6px 0;color:#2ecc71;font-weight:700'>{n_done}</p>", unsafe_allow_html=True)
        row_cols[3].markdown(f"<p style='text-align:center;margin:6px 0;color:#e67e22;font-weight:700'>{n_pending}</p>", unsafe_allow_html=True)
        row_cols[4].markdown(f"<p style='text-align:center;margin:6px 0'>{qa_today}</p>",  unsafe_allow_html=True)
        row_cols[5].markdown(f"<p style='text-align:center;margin:6px 0'>{fud_today}</p>", unsafe_allow_html=True)

        if not is_read_only():
            if row_cols[6].button(
                "▲ Close" if is_exp else "▼ Open",
                key=f"tog_{researcher}",
                width='stretch',
            ):
                if is_exp:
                    st.session_state.exp_r.discard(researcher)
                else:
                    st.session_state.exp_r.add(researcher)
                st.rerun()

        st.markdown(
            "<hr style='margin:2px 0;border-color:rgba(255,255,255,0.06)'>",
            unsafe_allow_html=True,
        )

        # ── Expanded detail panel ──
        if is_exp and not is_read_only():
            with st.container():
                # Pending companies checklist
                if r_pending.empty:
                    st.success("✅ All assigned companies are completed!")
                else:
                    st.markdown(
                        f"<div style='border-left:3px solid #f59e0b;padding-left:12px;"
                        f"margin-bottom:8px;font-size:0.95rem;font-weight:700;color:#f59e0b;"
                        f"letter-spacing:0.02em'>"
                        f"⏳ Pending Companies ({n_pending})</div>",
                        unsafe_allow_html=True,
                    )
                    with st.form(f"pend_{researcher}_{date_str}"):
                        field_widths = [3.2, 0.9, 0.9, 0.8, 1.0, 0.9, 1.0, 0.9, 1.0, 1.3, 1.2, 1.3, 1.2]
                        hc0, hc1, hc2, hc3, hc4, hc5, hc6, hc7, hc8, hc9, hc10, hc11, hc12 = st.columns(field_widths)
                        hc0.markdown("**Asset Mapping ↗ Company Name**")
                        hc1.markdown("**Subsidiaries**")
                        hc2.markdown("**Websites**")
                        hc3.markdown("**App**")
                        hc4.markdown("**Digital Ads**")
                        hc5.markdown("**Epubs**")
                        hc6.markdown("**Software**")
                        hc7.markdown("**DAM**")
                        hc8.markdown("**Webserver**")
                        hc9.markdown("**Start Date**")
                        hc10.markdown("**Start Time**")
                        hc11.markdown("**End Date**")
                        hc12.markdown("**End Time**")
                        st.markdown("<hr style='margin:4px 0 8px 0'>", unsafe_allow_html=True)

                        all_entries = []
                        to_complete = []

                        for _, row in r_pending.iterrows():
                            cc0, cc1, cc2, cc3, cc4, cc5, cc6, cc7, cc8, cc9, cc10, cc11, cc12 = st.columns(field_widths)
                            lem_am = cc0.checkbox(
                                str(row["company_name"]), value=False,
                                key=f"lem_{row['id']}_{date_str}",
                            )
                            sub = cc1.number_input(
                                "sub", min_value=0, value=int(row["subsidiary_count"]),
                                key=f"sub_{row['id']}_{date_str}", label_visibility="collapsed",
                            )
                            web = cc2.number_input(
                                "web", min_value=0, value=int(row.get("website_count", 0)),
                                key=f"web_{row['id']}_{date_str}", label_visibility="collapsed",
                            )
                            app_count = cc3.number_input(
                                "app", min_value=0, value=int(row.get("app", 0)),
                                key=f"app_{row['id']}_{date_str}", label_visibility="collapsed",
                            )
                            digital_ads = cc4.number_input(
                                "digital_ads", min_value=0, value=int(row.get("digital_ads", 0)),
                                key=f"digital_ads_{row['id']}_{date_str}", label_visibility="collapsed",
                            )
                            epubs = cc5.number_input(
                                "epubs", min_value=0, value=int(row.get("epubs", 0)),
                                key=f"epubs_{row['id']}_{date_str}", label_visibility="collapsed",
                            )
                            software = cc6.number_input(
                                "software", min_value=0, value=int(row.get("software", 0)),
                                key=f"software_{row['id']}_{date_str}", label_visibility="collapsed",
                            )
                            dam = cc7.number_input(
                                "dam", min_value=0, value=int(row.get("dam", 0)),
                                key=f"dam_{row['id']}_{date_str}", label_visibility="collapsed",
                            )
                            webserver = cc8.number_input(
                                "webserver", min_value=0, value=int(row.get("webserver", 0)),
                                key=f"webserver_{row['id']}_{date_str}", label_visibility="collapsed",
                            )
                            start_date = cc9.date_input(
                                "start_date",
                                value=_parse_date_value(row.get("start_date")) or sel_date,
                                key=f"start_date_{row['id']}_{date_str}",
                                label_visibility="collapsed",
                            )
                            start_time = cc10.time_input(
                                "start_time", value=_parse_time_value(row.get("start_time")),
                                key=f"start_time_{row['id']}_{date_str}", label_visibility="collapsed",
                                step=60,
                            )
                            end_date = cc11.date_input(
                                "end_date",
                                value=_parse_date_value(row.get("end_date")) or sel_date,
                                key=f"end_date_{row['id']}_{date_str}",
                                label_visibility="collapsed",
                            )
                            end_time = cc12.time_input(
                                "end_time", value=_parse_time_value(row.get("end_time")),
                                key=f"end_time_{row['id']}_{date_str}", label_visibility="collapsed",
                                step=60,
                            )
                            entry = {
                                "id": int(row["id"]),
                                "subsidiary_count": sub,
                                "website_count": web,
                                "app": app_count,
                                "digital_ads": digital_ads,
                                "epubs": epubs,
                                "software": software,
                                "dam": dam,
                                "webserver": webserver,
                                "start_date": start_date,
                                "start_time": start_time,
                                "end_date": end_date,
                                "end_time": end_time,
                            }
                            all_entries.append(entry)
                            if lem_am:
                                to_complete.append(entry)

                        st.markdown("")
                        bc1, bc2 = st.columns(2)
                        save_qf  = bc1.form_submit_button("💾 Save Asset Mapping Progress", width='stretch')
                        mark_lem = bc2.form_submit_button("✅ Mark Asset Mapping Complete", type="primary", width='stretch')

                        if mark_lem:
                            if to_complete:
                                complete_ids = {e["id"] for e in to_complete}
                                non_complete = [e for e in all_entries if e["id"] not in complete_ids]
                                if non_complete:
                                    save_asset_mapping(non_complete)
                                complete_companies(to_complete, date_str)
                                st.session_state.last_saved = _now_ts()
                                st.session_state.op_count += 1
                                st.success(f"Marked {len(to_complete)} companies as Asset Mapping complete!")
                                st.rerun()
                            else:
                                st.warning("Check at least one Asset Mapping checkbox to mark complete.")
                        if save_qf:
                            save_asset_mapping(all_entries)
                            st.session_state.last_saved = _now_ts()
                            st.session_state.op_count += 1
                            st.success("Asset Mapping progress saved!")
                            st.rerun()

                # Completed today with unmark
                if not r_done_today.empty:
                    st.divider()
                    st.markdown(f"**✅ Completed Today ({len(r_done_today)})** — check to unmark:")
                    with st.form(f"unmark_{researcher}_{date_str}"):
                        field_widths = [3.2, 0.9, 0.9, 0.8, 1.0, 0.9, 1.0, 0.9, 1.0, 1.3, 1.2, 1.3, 1.2]
                        hc0, hc1, hc2, hc3, hc4, hc5, hc6, hc7, hc8, hc9, hc10, hc11, hc12 = st.columns(field_widths)
                        hc0.markdown("**Unmark ↗ Company Name**")
                        hc1.markdown("**Subsidiaries**")
                        hc2.markdown("**Websites**")
                        hc3.markdown("**App**")
                        hc4.markdown("**Digital Ads**")
                        hc5.markdown("**Epubs**")
                        hc6.markdown("**Software**")
                        hc7.markdown("**DAM**")
                        hc8.markdown("**Webserver**")
                        hc9.markdown("**Start Date**")
                        hc10.markdown("**Start Time**")
                        hc11.markdown("**End Date**")
                        hc12.markdown("**End Time**")
                        st.markdown("<hr style='margin:4px 0 8px 0'>", unsafe_allow_html=True)
                        to_unmark = []
                        for _, row in r_done_today.sort_values("company_name").iterrows():
                            uc0, uc1, uc2, uc3, uc4, uc5, uc6, uc7, uc8, uc9, uc10, uc11, uc12 = st.columns(field_widths)
                            chk = uc0.checkbox(
                                str(row["company_name"]), value=False,
                                key=f"unk_{row['id']}_{date_str}",
                            )
                            uc1.markdown(f"`{int(row['subsidiary_count'])}`")
                            uc2.markdown(f"`{int(row.get('website_count', 0))}`")
                            uc3.markdown(f"`{int(row.get('app', 0))}`")
                            uc4.markdown(f"`{int(row.get('digital_ads', 0))}`")
                            uc5.markdown(f"`{int(row.get('epubs', 0))}`")
                            uc6.markdown(f"`{int(row.get('software', 0))}`")
                            uc7.markdown(f"`{int(row.get('dam', 0))}`")
                            uc8.markdown(f"`{int(row.get('webserver', 0))}`")
                            uc9.markdown(f"`{_fmt_date(row.get('start_date'))}`")
                            uc10.markdown(f"`{_fmt_time(row.get('start_time'))}`")
                            uc11.markdown(f"`{_fmt_date(row.get('end_date'))}`")
                            uc12.markdown(f"`{_fmt_time(row.get('end_time'))}`")
                            if chk:
                                to_unmark.append(int(row["id"]))
                        st.markdown("")
                        unmark_btn = st.form_submit_button("↩️ Unmark Selected (revert to Pending)", width='stretch')
                        if unmark_btn:
                            if to_unmark:
                                revert_companies(to_unmark)
                                st.session_state.last_saved = _now_ts()
                                st.session_state.op_count += 1
                                st.success(f"Reverted {len(to_unmark)} companies to pending.")
                                st.rerun()
                            else:
                                st.warning("Select at least one company to unmark.")


# ─── Tab 2: Companies ─────────────────────────────────────────────────────────
def tab_companies(cdf: pd.DataFrame):
    st.markdown("## 🏢 Company Overview")

    total = len(cdf)
    done = int((cdf["status"] == "completed").sum()) if not cdf.empty else 0
    pending = total - done

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📋 Total Companies", total)
    m2.metric("✅ Completed", done)
    m3.metric("⏳ Pending", pending)
    m4.metric("📈 Progress", f"{done / total * 100:.1f}%" if total else "0%")

    st.divider()

    # ── Per-researcher summary ──
    st.markdown("### Researcher Assignment Summary")
    rows = []
    for r in RESEARCHERS:
        r_df = cdf[_safe_col(cdf, "assigned_to") == r]
        n_total = len(r_df)
        n_done = int((r_df["status"] == "completed").sum()) if not r_df.empty else 0
        n_sub = int(r_df["subsidiary_count"].sum()) if not r_df.empty else 0
        rows.append({
            "Researcher": r,
            "Assigned": n_total,
            "Completed": n_done,
            "Pending": n_total - n_done,
            "Subsidiaries": n_sub,
            "Progress": f"{n_done / n_total * 100:.0f}%" if n_total else "—",
        })
    st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)

    st.divider()

    # ── Filters ──
    st.markdown("### All Companies")
    fc1, fc2, fc3 = st.columns([3, 3, 4])
    f_researcher = fc1.selectbox("Researcher", ["All"] + RESEARCHERS, key="co_r")
    f_status = fc2.selectbox("Status", ["All", "Pending", "Completed"], key="co_s")
    f_search = fc3.text_input("Search", placeholder="Type company name…", key="co_search")

    view = cdf.copy()
    if f_researcher != "All":
        view = view[_safe_col(view, "assigned_to") == f_researcher]
    if f_status == "Pending":
        view = view[view["status"] == "pending"]
    elif f_status == "Completed":
        view = view[view["status"] == "completed"]
    if f_search:
        view = view[view["company_name"].str.contains(f_search, case=False, na=False)]

    st.caption(f"Showing {len(view)} of {total} companies")

    if view.empty:
        st.info("No companies match the current filters.")
        return

    # ── Editable table with Select checkbox + editable Assigned To ──
    ASSIGNEE_OPTIONS = ["— Unassigned —"] + RESEARCHERS

    display = view[
        ["id", "company_name", "assigned_to", "status", "subsidiary_count", "website_count",
         "qa_status", "fud_status", "date_completed", "qa_done_date", "fud_done_date"]
    ].copy()
    display.columns = [
        "ID", "Company Name", "Assigned To", "Status", "Subsidiaries", "Websites",
        "QA Reviewer", "FUD Reviewer", "LEM Date", "QA Date", "FUD Date"
    ]
    display["Assigned To"] = display["Assigned To"].apply(
        lambda x: x if (x and x in RESEARCHERS) else "— Unassigned —"
    )
    display["Status"] = display["Status"].map({"completed": "✅ Completed", "pending": "⏳ Pending"})
    display["QA Reviewer"]  = display["QA Reviewer"].apply(
        lambda x: x if (x and x in QA_REVIEWERS)  else "— None —"
    )
    display["FUD Reviewer"] = display["FUD Reviewer"].apply(
        lambda x: x if (x and x in FUD_REVIEWERS) else "— None —"
    )
    # Normalise date columns to proper date objects for DateColumn
    for _dc in ["LEM Date", "QA Date", "FUD Date"]:
        display[_dc] = pd.to_datetime(display[_dc], errors="coerce").dt.date

    # Snapshot originals to detect changes
    original_assignees     = display.set_index("ID")["Assigned To"].to_dict()
    original_qa_reviewers  = display.set_index("ID")["QA Reviewer"].to_dict()
    original_fud_reviewers = display.set_index("ID")["FUD Reviewer"].to_dict()
    original_qa_dates      = display.set_index("ID")["QA Date"].to_dict()
    original_fud_dates     = display.set_index("ID")["FUD Date"].to_dict()
    original_subsidiaries  = display.set_index("ID")["Subsidiaries"].to_dict()
    original_websites      = display.set_index("ID")["Websites"].to_dict()
    # Keep full row data for save logic
    id_to_row = view.set_index("id")
    sel_all_key = f"sel_all_{f_researcher}_{f_status}_{f_search}"
    if sel_all_key not in st.session_state:
        st.session_state[sel_all_key] = False

    _sa_col, _ = st.columns([1, 9])
    with _sa_col:
        if st.button(
            "☑ Deselect All" if st.session_state[sel_all_key] else "☑ Select All",
            key=f"btn_selall_{sel_all_key}",
            width='stretch',
        ):
            st.session_state[sel_all_key] = not st.session_state[sel_all_key]
            st.rerun()

    display.insert(0, "Select", st.session_state[sel_all_key])

    # Key resets on filter change and after each operation
    editor_key = f"co_ed_{f_researcher}_{f_status}_{f_search}_{st.session_state.get('op_count', 0)}"

    edited = st.data_editor(
        display,
        column_config={
            "Select": st.column_config.CheckboxColumn("☑", default=False, width="small"),
            "ID": st.column_config.NumberColumn(width="small"),
            "Company Name": st.column_config.TextColumn(width="large"),
            "Assigned To": st.column_config.SelectboxColumn(
                "Assigned To", options=ASSIGNEE_OPTIONS, width="medium", required=True,
            ),
            "Status": st.column_config.TextColumn(width="medium"),
            "Subsidiaries": st.column_config.NumberColumn(width="small"),
            "Websites": st.column_config.NumberColumn(width="small"),
            "QA Reviewer": st.column_config.SelectboxColumn(
                "QA Reviewer", options=["— None —"] + QA_REVIEWERS, width="medium",
            ),
            "FUD Reviewer": st.column_config.SelectboxColumn(
                "FUD Reviewer", options=["— None —"] + FUD_REVIEWERS, width="medium",
            ),
            "LEM Date": st.column_config.DateColumn("LEM Date", width="small"),
            "QA Date":  st.column_config.DateColumn("QA Date",  width="small"),
            "FUD Date": st.column_config.DateColumn("FUD Date", width="small"),
        },
        disabled=["ID", "Company Name", "Status", "LEM Date"],
        hide_index=True,
        width='stretch',
        key=editor_key,
    )

    # ── Detect changes and offer save buttons ──
    today_str = date.today().strftime("%Y-%m-%d")

    changed_assign = edited[
        edited.apply(lambda r: r["Assigned To"] != original_assignees.get(r["ID"], "— Unassigned —"), axis=1)
    ]
    changed_qa_fud = edited[
        edited.apply(
            lambda r: (
                r["QA Reviewer"]  != original_qa_reviewers.get(r["ID"],  "— None —") or
                r["FUD Reviewer"] != original_fud_reviewers.get(r["ID"], "— None —")
            ), axis=1
        )
    ]

    if not changed_assign.empty:
        st.info(f"**{len(changed_assign)} assignee change(s) pending** — click Save to apply.")
        if st.button("💾 Save Assignee Changes", type="primary", key="btn_save_assign"):
            sb = get_sb()
            for _, row in changed_assign.iterrows():
                new_val = row["Assigned To"]
                sb.table("companies").update({
                    "assigned_to": None if new_val == "— Unassigned —" else new_val
                }).eq("id", int(row["ID"])).execute()
            bust_cache()
            st.session_state.op_count += 1
            st.success(f"Saved assignee changes for {len(changed_assign)} company/companies.")
            st.rerun()

    if not changed_qa_fud.empty:
        st.info(f"**{len(changed_qa_fud)} QA/FUD change(s) pending** — click Save to apply.")
        if st.button("💾 Save QA / FUD Changes", type="primary", key="btn_save_qa_fud"):
            entries = []
            for _, row in changed_qa_fud.iterrows():
                rid = int(row["ID"])
                orig = id_to_row.loc[rid] if rid in id_to_row.index else {}
                qa_val  = row["QA Reviewer"];  qa_val  = "" if qa_val  == "— None —" else qa_val
                fud_val = row["FUD Reviewer"]; fud_val = "" if fud_val == "— None —" else fud_val
                entries.append({
                    "id":            rid,
                    "subsidiary_count": int(orig.get("subsidiary_count", 0)) if hasattr(orig, "get") else 0,
                    "website_count":    int(orig.get("website_count",    0)) if hasattr(orig, "get") else 0,
                    "qa_status":     qa_val,
                    "fud_status":    fud_val,
                    "qa_done_date":  orig.get("qa_done_date")  if hasattr(orig, "get") else None,
                    "fud_done_date": orig.get("fud_done_date") if hasattr(orig, "get") else None,
                })
            save_qa_fud(entries, today_str)
            st.session_state.op_count += 1
            st.success(f"Saved QA/FUD reviewers for {len(entries)} company/companies.")
            st.rerun()

    changed_counts = edited[
        edited.apply(
            lambda r: (
                int(r["Subsidiaries"]) != int(original_subsidiaries.get(r["ID"], 0)) or
                int(r["Websites"])     != int(original_websites.get(r["ID"], 0))
            ), axis=1
        )
    ]
    if not changed_counts.empty:
        st.info(f"**{len(changed_counts)} count change(s) pending** — click Save to apply.")
        if st.button("💾 Save Count Changes", type="primary", key="btn_save_counts"):
            sb = get_sb()
            for _, row in changed_counts.iterrows():
                sb.table("companies").update({
                    "subsidiary_count": int(row["Subsidiaries"]),
                    "website_count":    int(row["Websites"]),
                }).eq("id", int(row["ID"])).execute()
            bust_cache()
            st.session_state.op_count += 1
            st.success(f"Saved counts for {len(changed_counts)} company/companies.")
            st.rerun()

    def _nd(v):
        """Normalise date: treat None and NaT as identical."""
        if v is None:
            return None
        try:
            return None if pd.isna(v) else v
        except (TypeError, ValueError):
            return v

    changed_dates = edited[
        edited.apply(
            lambda r: (
                _nd(r["QA Date"])  != _nd(original_qa_dates.get(r["ID"]))  or
                _nd(r["FUD Date"]) != _nd(original_fud_dates.get(r["ID"]))
            ), axis=1
        )
    ]
    if not changed_dates.empty:
        st.info(f"**{len(changed_dates)} date change(s) pending** — click Save to apply.")
        if st.button("💾 Save Date Changes", type="primary", key="btn_save_dates"):
            sb = get_sb()
            for _, row in changed_dates.iterrows():
                sb.table("companies").update({
                    "qa_done_date":  str(_nd(row["QA Date"]))  if _nd(row["QA Date"])  else None,
                    "fud_done_date": str(_nd(row["FUD Date"])) if _nd(row["FUD Date"]) else None,
                }).eq("id", int(row["ID"])).execute()
            bust_cache()
            st.session_state.op_count += 1
            st.success(f"Saved dates for {len(changed_dates)} company/companies.")
            st.rerun()

    selected = edited[edited["Select"] == True]
    n_sel = len(selected)

    st.markdown("---")
    if n_sel == 1:
        selected_id = int(selected.iloc[0]["ID"])
        selected_row = id_to_row.loc[selected_id] if selected_id in id_to_row.index else None

        if selected_row is not None:
            st.markdown("### Selected Company Asset Mapping")
            st.caption(f"Editing: {selected_row.get('company_name', '')} (ID: {selected_id})")

            with st.form(f"company_asset_edit_top_{selected_id}_{st.session_state.get('op_count', 0)}"):
                ec1, ec2, ec3, ec4, ec5 = st.columns(5)
                subsidiaries_val = ec1.number_input("Subsidiaries", min_value=0, value=int(selected_row.get("subsidiary_count", 0)), key=f"cmp_top_sub_{selected_id}")
                websites_val = ec2.number_input("Websites", min_value=0, value=int(selected_row.get("website_count", 0)), key=f"cmp_top_web_{selected_id}")
                digital_ads_val = ec3.number_input("Digital Ads", min_value=0, value=int(selected_row.get("digital_ads", 0)), key=f"cmp_top_digital_ads_{selected_id}")
                epubs_val = ec4.number_input("Epubs", min_value=0, value=int(selected_row.get("epubs", 0)), key=f"cmp_top_epubs_{selected_id}")
                software_val = ec5.number_input("Software", min_value=0, value=int(selected_row.get("software", 0)), key=f"cmp_top_software_{selected_id}")

                ec6, ec7, ec8, ec9 = st.columns(4)
                dam_val = ec6.number_input("DAM", min_value=0, value=int(selected_row.get("dam", 0)), key=f"cmp_top_dam_{selected_id}")
                webserver_val = ec7.number_input("Webserver", min_value=0, value=int(selected_row.get("webserver", 0)), key=f"cmp_top_webserver_{selected_id}")
                start_time_val = ec8.time_input("Start Time", value=_parse_time_value(selected_row.get("start_time")), key=f"cmp_top_start_time_{selected_id}", step=60)
                end_time_val = ec9.time_input("End Time", value=_parse_time_value(selected_row.get("end_time")), key=f"cmp_top_end_time_{selected_id}", step=60)

                save_asset_changes_top = st.form_submit_button("💾 Save Asset Mapping Changes", type="primary", width='stretch')

            if save_asset_changes_top:
                proposed_values = {
                    "subsidiary_count": int(subsidiaries_val),
                    "website_count": int(websites_val),
                    "digital_ads": int(digital_ads_val),
                    "epubs": int(epubs_val),
                    "software": int(software_val),
                    "dam": int(dam_val),
                    "webserver": int(webserver_val),
                    "start_time": _time_to_db(start_time_val),
                    "end_time": _time_to_db(end_time_val),
                }
                original_values = {
                    "subsidiary_count": int(selected_row.get("subsidiary_count", 0)),
                    "website_count": int(selected_row.get("website_count", 0)),
                    "digital_ads": int(selected_row.get("digital_ads", 0)),
                    "epubs": int(selected_row.get("epubs", 0)),
                    "software": int(selected_row.get("software", 0)),
                    "dam": int(selected_row.get("dam", 0)),
                    "webserver": int(selected_row.get("webserver", 0)),
                    "start_time": _time_to_db(selected_row.get("start_time")),
                    "end_time": _time_to_db(selected_row.get("end_time")),
                }
                changed_payload = {key: value for key, value in proposed_values.items() if value != original_values.get(key)}

                res = update_company_asset_fields(selected_id, changed_payload)
                if res is True:
                    st.session_state.op_count += 1
                    st.success("Asset Mapping fields updated for the selected company.")
                    st.rerun()
                elif res is False:
                    st.info("No Asset Mapping changes detected for the selected company.")
    elif n_sel > 1:
        st.info("Select exactly one company to edit all Asset Mapping fields.")
    else:
        st.caption("Select exactly one company above to open the full Asset Mapping editor.")

    # ── Action toolbar ──
    st.markdown("---")
    if n_sel == 0:
        st.caption("☝️ Check rows above to select companies, then use the actions below.")
        action_disabled = True
    else:
        st.markdown(f"**{n_sel} company/companies selected** — choose an action:")
        action_disabled = False

    ac1, ac2, ac3 = st.columns([2, 2, 6])

    # Delete
    with ac1:
        if st.button(
            f"🗑️ Delete ({n_sel})" if n_sel else "🗑️ Delete",
            disabled=action_disabled,
            key="btn_delete",
            width='stretch',
        ):
            ids = selected["ID"].tolist()
            delete_companies(ids)
            st.session_state.op_count += 1
            st.session_state[sel_all_key] = False
            st.success(f"Deleted {n_sel} company/companies.")
            st.rerun()

    # Revert to Pending
    sel_completed = selected[selected["Status"] == "✅ Completed"]
    with ac2:
        if st.button(
            f"↩️ Revert ({len(sel_completed)})" if sel_completed is not None and len(sel_completed) else "↩️ Revert",
            disabled=(action_disabled or len(sel_completed) == 0),
            key="btn_revert",
            width='stretch',
            help="Revert selected completed companies back to pending",
        ):
            ids = sel_completed["ID"].tolist()
            revert_companies(ids)
            st.session_state.op_count += 1
            st.session_state[sel_all_key] = False
            st.success(f"Reverted {len(ids)} companies to pending.")
            st.rerun()

    # Edit subsidiary count for selected
    with ac3:
        if not action_disabled:
            with st.popover("✏️ Edit Subsidiary Count", width='stretch'):
                new_sub = st.number_input("New Subsidiary Count", min_value=0, value=0, key="new_sub_val")
                if st.button("Save", type="primary", key="btn_save_sub"):
                    sb = get_sb()
                    for cid in selected["ID"].tolist():
                        sb.table("companies").update({"subsidiary_count": new_sub}).eq("id", cid).execute()
                    bust_cache()
                    st.session_state.op_count += 1
                    st.success(f"Updated subsidiary count to {new_sub} for {n_sel} company/companies.")
                    st.rerun()

    st.markdown("")
    if n_sel == 1:
        selected_id = int(selected.iloc[0]["ID"])
        selected_row = id_to_row.loc[selected_id] if selected_id in id_to_row.index else None

        if selected_row is not None:
            st.markdown("### Edit Asset Mapping")
            st.caption("Update the selected company’s Asset Mapping fields. QA and Salesforce reviewer fields are intentionally excluded here.")

            with st.form(f"company_asset_edit_{selected_id}_{st.session_state.get('op_count', 0)}"):
                ec1, ec2, ec3, ec4, ec5 = st.columns(5)
                subsidiaries_val = ec1.number_input(
                    "Subsidiaries",
                    min_value=0,
                    value=int(selected_row.get("subsidiary_count", 0)),
                    key=f"cmp_sub_{selected_id}",
                )
                websites_val = ec2.number_input(
                    "Websites",
                    min_value=0,
                    value=int(selected_row.get("website_count", 0)),
                    key=f"cmp_web_{selected_id}",
                )
                digital_ads_val = ec3.number_input(
                    "Digital Ads",
                    min_value=0,
                    value=int(selected_row.get("digital_ads", 0)),
                    key=f"cmp_digital_ads_{selected_id}",
                )
                epubs_val = ec4.number_input(
                    "Epubs",
                    min_value=0,
                    value=int(selected_row.get("epubs", 0)),
                    key=f"cmp_epubs_{selected_id}",
                )
                software_val = ec5.number_input(
                    "Software",
                    min_value=0,
                    value=int(selected_row.get("software", 0)),
                    key=f"cmp_software_{selected_id}",
                )

                ec6, ec7, ec8, ec9 = st.columns(4)
                dam_val = ec6.number_input(
                    "DAM",
                    min_value=0,
                    value=int(selected_row.get("dam", 0)),
                    key=f"cmp_dam_{selected_id}",
                )
                webserver_val = ec7.number_input(
                    "Webserver",
                    min_value=0,
                    value=int(selected_row.get("webserver", 0)),
                    key=f"cmp_webserver_{selected_id}",
                )
                start_time_val = ec8.time_input(
                    "Start Time",
                    value=_parse_time_value(selected_row.get("start_time")),
                    key=f"cmp_start_time_{selected_id}",
                    step=60,
                )
                end_time_val = ec9.time_input(
                    "End Time",
                    value=_parse_time_value(selected_row.get("end_time")),
                    key=f"cmp_end_time_{selected_id}",
                    step=60,
                )

                save_asset_changes = st.form_submit_button(
                    "💾 Save Asset Mapping Changes",
                    type="primary",
                    width='stretch',
                )

            if save_asset_changes:
                proposed_values = {
                    "subsidiary_count": int(subsidiaries_val),
                    "website_count": int(websites_val),
                    "digital_ads": int(digital_ads_val),
                    "epubs": int(epubs_val),
                    "software": int(software_val),
                    "dam": int(dam_val),
                    "webserver": int(webserver_val),
                    "start_time": _time_to_db(start_time_val),
                    "end_time": _time_to_db(end_time_val),
                }
                original_values = {
                    "subsidiary_count": int(selected_row.get("subsidiary_count", 0)),
                    "website_count": int(selected_row.get("website_count", 0)),
                    "digital_ads": int(selected_row.get("digital_ads", 0)),
                    "epubs": int(selected_row.get("epubs", 0)),
                    "software": int(selected_row.get("software", 0)),
                    "dam": int(selected_row.get("dam", 0)),
                    "webserver": int(selected_row.get("webserver", 0)),
                    "start_time": _time_to_db(selected_row.get("start_time")),
                    "end_time": _time_to_db(selected_row.get("end_time")),
                }
                changed_payload = {
                    key: value for key, value in proposed_values.items()
                    if value != original_values.get(key)
                }

                res = update_company_asset_fields(selected_id, changed_payload)
                if res is True:
                    st.session_state.op_count += 1
                    st.success("Asset Mapping fields updated for the selected company.")
                    st.rerun()
                elif res is False:
                    st.info("No Asset Mapping changes detected for the selected company.")
    elif n_sel > 1:
        st.info("Select exactly one company to edit all Asset Mapping fields.")

# ─── Tab 3: Analytics ─────────────────────────────────────────────────────────
def tab_companies(cdf: pd.DataFrame):
    st.markdown("## 🏢 Company Overview")

    total = len(cdf)
    done = int((cdf["status"] == "completed").sum()) if not cdf.empty else 0
    pending = total - done

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📋 Total Companies", total)
    m2.metric("✅ Completed", done)
    m3.metric("⏳ Pending", pending)
    m4.metric("📈 Progress", f"{done / total * 100:.1f}%" if total else "0%")

    st.divider()
    st.markdown("### Researcher Assignment Summary")
    rows = []
    for r in RESEARCHERS:
        r_df = cdf[_safe_col(cdf, "assigned_to") == r]
        n_total = len(r_df)
        n_done = int((r_df["status"] == "completed").sum()) if not r_df.empty else 0
        n_sub = int(r_df["subsidiary_count"].sum()) if not r_df.empty else 0
        rows.append({
            "Researcher": r,
            "Assigned": n_total,
            "Completed": n_done,
            "Pending": n_total - n_done,
            "Subsidiaries": n_sub,
            "Progress": f"{n_done / n_total * 100:.0f}%" if n_total else "—",
        })
    st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)

    st.divider()
    st.markdown("### All Companies")
    fc1, fc2, fc3 = st.columns([3, 3, 4])
    f_researcher = fc1.selectbox("Researcher", ["All"] + RESEARCHERS, key="co_r_clean")
    f_status = fc2.selectbox("Status", ["All", "Pending", "Completed"], key="co_s_clean")
    f_search = fc3.text_input("Search", placeholder="Type company name...", key="co_search_clean")

    view = cdf.copy()
    if f_researcher != "All":
        view = view[_safe_col(view, "assigned_to") == f_researcher]
    if f_status == "Pending":
        view = view[view["status"] == "pending"]
    elif f_status == "Completed":
        view = view[view["status"] == "completed"]
    if f_search:
        view = view[view["company_name"].str.contains(f_search, case=False, na=False)]

    st.caption(f"Showing {len(view)} of {total} companies")
    if view.empty:
        st.info("No companies match the current filters.")
        return

    assignee_options = ["— Unassigned —"] + RESEARCHERS
    display = view[["id", "company_name", "assigned_to", "status", "subsidiary_count", "website_count", "qa_status", "fud_status", "wayback_status", "date_completed", "qa_done_date", "fud_done_date"]].copy()
    display.columns = ["ID", "Company Name", "Assigned To", "Status", "Subsidiary", "Websites", "QA Reviewer", "FUD Reviewer", "Wayback Status", "LEM Date", "QA Date", "FUD Date"]
    display["Assigned To"] = display["Assigned To"].apply(lambda x: x if (x and x in RESEARCHERS) else "— Unassigned —")
    display["Status"] = display["Status"].map({"completed": "✅ Completed", "pending": "⏳ Pending"})
    display["LEM Date"] = pd.to_datetime(display["LEM Date"], errors="coerce").dt.date
    display["QA Reviewer"] = display["QA Reviewer"].apply(lambda x: x if (x and x in QA_REVIEWERS) else "—")
    display["FUD Reviewer"] = display["FUD Reviewer"].apply(lambda x: x if (x and x in FUD_REVIEWERS) else "—")
    display["Wayback Status"] = display["Wayback Status"].apply(lambda x: x if x in ("in-progress", "completed") else "completed")
    display["QA Date"] = pd.to_datetime(display["QA Date"], errors="coerce").dt.date
    display["FUD Date"] = pd.to_datetime(display["FUD Date"], errors="coerce").dt.date

    original_assignees = display.set_index("ID")["Assigned To"].to_dict()
    original_qa_reviewers = display.set_index("ID")["QA Reviewer"].to_dict()
    original_fud_reviewers = display.set_index("ID")["FUD Reviewer"].to_dict()
    original_wayback_statuses = display.set_index("ID")["Wayback Status"].to_dict()
    original_lem_dates = display.set_index("ID")["LEM Date"].to_dict()
    original_qa_dates = display.set_index("ID")["QA Date"].to_dict()
    original_fud_dates = display.set_index("ID")["FUD Date"].to_dict()
    id_to_row = view.set_index("id")
    sel_all_key = f"sel_all_clean_{f_researcher}_{f_status}_{f_search}"
    if sel_all_key not in st.session_state:
        st.session_state[sel_all_key] = False

    _sa_col, _ = st.columns([1, 9])
    with _sa_col:
        if st.button("☑ Deselect All" if st.session_state[sel_all_key] else "☑ Select All", key=f"btn_selall_{sel_all_key}", width='stretch'):
            st.session_state[sel_all_key] = not st.session_state[sel_all_key]
            st.rerun()

    display.insert(0, "Select", st.session_state[sel_all_key])
    editor_key = f"co_ed_clean_{f_researcher}_{f_status}_{f_search}_{st.session_state.get('op_count', 0)}"
    _ro = is_read_only()
    edited = st.data_editor(
        display,
        column_config={
            "Select": st.column_config.CheckboxColumn("☑", default=False, width="small"),
            "ID": st.column_config.NumberColumn(width="small"),
            "Company Name": st.column_config.TextColumn(width="large"),
            "Assigned To": st.column_config.SelectboxColumn("Assigned To", options=assignee_options, width="medium", required=True),
            "Status": st.column_config.TextColumn(width="medium"),
            "Subsidiary": st.column_config.NumberColumn(width="small"),
            "Websites": st.column_config.NumberColumn(width="small"),
            "QA Reviewer": st.column_config.SelectboxColumn("QA Reviewer", options=["—"] + QA_REVIEWERS, width="medium", required=False),
            "FUD Reviewer": st.column_config.SelectboxColumn("FUD Reviewer", options=["—"] + FUD_REVIEWERS, width="medium", required=False),
            "Wayback Status": st.column_config.SelectboxColumn("Wayback Status", options=["completed", "in-progress"], width="medium", required=True),
            "LEM Date": st.column_config.DateColumn("LEM Date", width="small", format="YYYY-MM-DD"),
            "QA Date": st.column_config.DateColumn("QA Date", width="small", format="YYYY-MM-DD"),
            "FUD Date": st.column_config.DateColumn("FUD Date", width="small", format="YYYY-MM-DD"),
        },
        disabled=True if _ro else ["ID", "Company Name", "Status"],
        hide_index=True,
        width='stretch',
        key=editor_key,
    )

    changed_assign = edited[edited.apply(lambda r: r["Assigned To"] != original_assignees.get(r["ID"], "— Unassigned —"), axis=1)]
    if not _ro and not changed_assign.empty:
        st.info(f"**{len(changed_assign)} assignee change(s) pending** — click Save to apply.")
        if st.button("ð Save Assignee Changes", type="primary", key="btn_save_assign_clean"):
            sb = get_sb()
            for _, row in changed_assign.iterrows():
                new_val = row["Assigned To"]
                sb.table("companies").update({"assigned_to": None if new_val == "— Unassigned —" else new_val}).eq("id", int(row["ID"])).execute()
            bust_cache()
            st.session_state.op_count += 1
            st.success(f"Saved assignee changes for {len(changed_assign)} company/companies.")
            st.rerun()

    # Check for changes in QA Reviewer, FUD Reviewer, and date fields
    def has_field_change(row, field_name, original_dict):
        original_val = original_dict.get(row["ID"], None)
        new_val = row[field_name]
        # Handle NaT/None comparison for dates
        if pd.isna(original_val) and pd.isna(new_val):
            return False
        return str(original_val) != str(new_val)

    changed_qa_reviewers = edited[edited.apply(lambda r: has_field_change(r, "QA Reviewer", original_qa_reviewers), axis=1)]
    changed_fud_reviewers = edited[edited.apply(lambda r: has_field_change(r, "FUD Reviewer", original_fud_reviewers), axis=1)]
    changed_wayback = edited[edited.apply(lambda r: has_field_change(r, "Wayback Status", original_wayback_statuses), axis=1)]
    changed_lem_dates = edited[edited.apply(lambda r: has_field_change(r, "LEM Date", original_lem_dates), axis=1)]
    changed_qa_dates = edited[edited.apply(lambda r: has_field_change(r, "QA Date", original_qa_dates), axis=1)]
    changed_fud_dates = edited[edited.apply(lambda r: has_field_change(r, "FUD Date", original_fud_dates), axis=1)]

    # Combine all changes
    all_field_changes = pd.concat([
        changed_qa_reviewers.assign(change_type="QA Reviewer"),
        changed_fud_reviewers.assign(change_type="FUD Reviewer"),
        changed_wayback.assign(change_type="Wayback Status"),
        changed_lem_dates.assign(change_type="LEM Date"),
        changed_qa_dates.assign(change_type="QA Date"),
        changed_fud_dates.assign(change_type="FUD Date")
    ]).drop_duplicates(subset=["ID"])

    if not _ro and not all_field_changes.empty:
        st.info(f"**{len(all_field_changes)} field change(s) pending** — click Save to apply reviewer and date updates.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("ð Save Field Changes", type="primary", key="btn_save_field_changes"):
                sb = get_sb()
                success_count = 0
                for _, row in all_field_changes.iterrows():
                    update_data = {}
                    company_id = int(row["ID"])
                    
                    # QA Reviewer
                    if has_field_change(row, "QA Reviewer", original_qa_reviewers):
                        new_qa = row["QA Reviewer"]
                        update_data["qa_status"] = None if new_qa == "—" else new_qa
                    
                    # FUD Reviewer
                    if has_field_change(row, "FUD Reviewer", original_fud_reviewers):
                        new_fud = row["FUD Reviewer"]
                        update_data["fud_status"] = None if new_fud == "—" else new_fud

                    # Wayback Status
                    if has_field_change(row, "Wayback Status", original_wayback_statuses):
                        update_data["wayback_status"] = row["Wayback Status"]

                    # LEM Date
                    if has_field_change(row, "LEM Date", original_lem_dates):
                        new_lem_date = row["LEM Date"]
                        update_data["date_completed"] = None if pd.isna(new_lem_date) else str(new_lem_date)
                    
                    # QA Date
                    if has_field_change(row, "QA Date", original_qa_dates):
                        new_qa_date = row["QA Date"]
                        update_data["qa_done_date"] = None if pd.isna(new_qa_date) else str(new_qa_date)
                    
                    # FUD Date
                    if has_field_change(row, "FUD Date", original_fud_dates):
                        new_fud_date = row["FUD Date"]
                        update_data["fud_done_date"] = None if pd.isna(new_fud_date) else str(new_fud_date)
                    
                    if update_data:
                        sb.table("companies").update(update_data).eq("id", company_id).execute()
                        success_count += 1
                
                if success_count > 0:
                    bust_cache()
                    st.session_state.op_count += 1
                    st.success(f"Successfully saved field changes for {success_count} company/companies.")
                    st.rerun()
                else:
                    st.warning("No changes were saved.")
        
        with col2:
            if st.button("â Reset Changes", key="btn_reset_field_changes"):
                st.rerun()

    selected = edited[edited["Select"] == True]
    n_sel = len(selected)

    st.markdown("---")
    if not _ro and n_sel == 1:
        selected_id = int(selected.iloc[0]["ID"])
        selected_row = id_to_row.loc[selected_id] if selected_id in id_to_row.index else None
        if selected_row is not None:
            st.markdown("### Selected Company Asset Mapping")
            st.caption(f"Editing: {selected_row.get('company_name', '')} (ID: {selected_id})")

            with st.form(f"company_asset_edit_clean_{selected_id}_{st.session_state.get('op_count', 0)}"):
                ec1, ec2, ec3, ec4 = st.columns(4)
                subsidiaries_val = ec1.number_input("Subsidiaries", min_value=0, value=int(selected_row.get("subsidiary_count", 0)), key=f"cmp_clean_sub_{selected_id}")
                websites_val = ec2.number_input("Websites", min_value=0, value=int(selected_row.get("website_count", 0)), key=f"cmp_clean_web_{selected_id}")
                app_val = ec3.number_input("App", min_value=0, value=int(selected_row.get("app", 0)), key=f"cmp_clean_app_{selected_id}")
                digital_ads_val = ec4.number_input("Digital Ads", min_value=0, value=int(selected_row.get("digital_ads", 0)), key=f"cmp_clean_digital_ads_{selected_id}")

                ec5, ec6, ec7, ec8, ec9 = st.columns(5)
                epubs_val = ec5.number_input("Epubs", min_value=0, value=int(selected_row.get("epubs", 0)), key=f"cmp_clean_epubs_{selected_id}")
                software_val = ec6.number_input("Software", min_value=0, value=int(selected_row.get("software", 0)), key=f"cmp_clean_software_{selected_id}")
                dam_val = ec7.number_input("DAM", min_value=0, value=int(selected_row.get("dam", 0)), key=f"cmp_clean_dam_{selected_id}")
                webserver_val = ec8.number_input("Webserver", min_value=0, value=int(selected_row.get("webserver", 0)), key=f"cmp_clean_webserver_{selected_id}")
                start_time_val = ec9.time_input("Start Time", value=_parse_time_value(selected_row.get("start_time")), key=f"cmp_clean_start_time_{selected_id}", step=60)

                ec10, ec11, ec12, ec13 = st.columns(4)
                end_time_val = ec10.time_input("End Time", value=_parse_time_value(selected_row.get("end_time")), key=f"cmp_clean_end_time_{selected_id}", step=60)
                start_date_val = ec11.date_input("Start Date", value=_parse_date_value(selected_row.get("start_date")), key=f"cmp_clean_start_date_{selected_id}")
                end_date_val = ec12.date_input("End Date", value=_parse_date_value(selected_row.get("end_date")), key=f"cmp_clean_end_date_{selected_id}")
                save_asset_changes = ec13.form_submit_button("💾 Save Asset Mapping Changes", type="primary", width='stretch')

            if save_asset_changes:
                proposed_values = {
                    "subsidiary_count": int(subsidiaries_val),
                    "website_count": int(websites_val),
                    "app": int(app_val),
                    "digital_ads": int(digital_ads_val),
                    "epubs": int(epubs_val),
                    "software": int(software_val),
                    "dam": int(dam_val),
                    "webserver": int(webserver_val),
                    "start_date": _date_to_db(start_date_val),
                    "end_date": _date_to_db(end_date_val),
                    "start_time": _time_to_db(start_time_val),
                    "end_time": _time_to_db(end_time_val),
                }
                original_values = {
                    "subsidiary_count": int(selected_row.get("subsidiary_count", 0)),
                    "website_count": int(selected_row.get("website_count", 0)),
                    "app": int(selected_row.get("app", 0)),
                    "digital_ads": int(selected_row.get("digital_ads", 0)),
                    "epubs": int(selected_row.get("epubs", 0)),
                    "software": int(selected_row.get("software", 0)),
                    "dam": int(selected_row.get("dam", 0)),
                    "webserver": int(selected_row.get("webserver", 0)),
                    "start_date": _date_to_db(selected_row.get("start_date")),
                    "end_date": _date_to_db(selected_row.get("end_date")),
                    "start_time": _time_to_db(selected_row.get("start_time")),
                    "end_time": _time_to_db(selected_row.get("end_time")),
                }
                changed_payload = {k: v for k, v in proposed_values.items() if v != original_values.get(k)}
                res = update_company_asset_fields(selected_id, changed_payload)
                if res is True:
                    st.session_state.op_count += 1
                    st.success("Asset Mapping fields updated for the selected company.")
                    st.rerun()
                elif res is False:
                    st.info("No Asset Mapping changes detected for the selected company.")
    elif n_sel > 1:
        st.info("Select exactly one company to view and edit Asset Mapping details.")
    else:
        st.caption("Select exactly one company above to open the Asset Mapping editor.")

    if not _ro:
      st.markdown("---")
      if n_sel == 0:
        st.caption("☝️ Check rows above to select companies, then use the actions below.")
        action_disabled = True
      else:
        st.markdown(f"**{n_sel} company/companies selected** — choose an action:")
        action_disabled = False

      ac1, ac2, ac3 = st.columns([2, 2, 6])
      with ac1:
        if st.button(f"🗑️ Delete ({n_sel})" if n_sel else "🗑️ Delete", disabled=action_disabled, key="btn_delete_clean", width='stretch'):
            ids = selected["ID"].tolist()
            delete_companies(ids)
            st.session_state.op_count += 1
            st.session_state[sel_all_key] = False
            st.success(f"Deleted {n_sel} company/companies.")
            st.rerun()

      sel_completed = selected[selected["Status"] == "✅ Completed"]
      with ac2:
        if st.button(
            f"↩️ Revert ({len(sel_completed)})" if len(sel_completed) else "↩️ Revert",
            disabled=(action_disabled or len(sel_completed) == 0),
            key="btn_revert_clean",
            width='stretch',
            help="Revert selected completed companies back to pending",
        ):
            ids = sel_completed["ID"].tolist()
            revert_companies(ids)
            st.session_state.op_count += 1
            st.session_state[sel_all_key] = False
            st.success(f"Reverted {len(ids)} companies to pending.")
            st.rerun()

      with ac3:
        if not action_disabled:
            with st.popover("✏️ Edit Subsidiary Count", width='stretch'):
                new_sub = st.number_input("New Subsidiary Count", min_value=0, value=0, key="new_sub_val_clean")
                if st.button("Save", type="primary", key="btn_save_sub_clean"):
                    sb = get_sb()
                    for cid in selected["ID"].tolist():
                        sb.table("companies").update({"subsidiary_count": new_sub}).eq("id", cid).execute()
                    bust_cache()
                    st.session_state.op_count += 1
                    st.success(f"Updated subsidiary count to {new_sub} for {n_sel} company/companies.")
                    st.rerun()

def tab_analytics(cdf: pd.DataFrame, mdf: pd.DataFrame):
    st.markdown("## 📊 Analytics")

    dc1, dc2 = st.columns(2)
    start_d = dc1.date_input(
        "Start Date",
        value=date(date.today().year, date.today().month, 1),
        key="ana_start",
    )
    end_d = dc2.date_input("End Date", value=date.today(), key="ana_end")

    if start_d > end_d:
        st.error("Start date must be before end date.")
        return

    start_str = start_d.strftime("%Y-%m-%d")
    end_str = end_d.strftime("%Y-%m-%d")

    done_range = cdf[
        (cdf["status"] == "completed")
        & (_safe_col(cdf, "date_completed") >= start_str)
        & (_safe_col(cdf, "date_completed") <= end_str)
    ]

    metric_totals = {
        "asset_mapping_total": len(done_range),
        "subsidiaries_total": int(done_range["subsidiary_count"].sum()) if not done_range.empty else 0,
        "websites_total": int(done_range["website_count"].sum()) if not done_range.empty else 0,
        "app_total": int(done_range["app"].sum()) if not done_range.empty else 0,
        "qa_total": int(done_range["qa_status"].astype(bool).sum()) if not done_range.empty else 0,
        "salesforce_ready_total": int(done_range["fud_status"].astype(bool).sum()) if not done_range.empty else 0,
        "wayback_stuck_total": int((done_range["wayback_status"] == "in-progress").sum()) if not done_range.empty else 0,
        "digital_ads_total": int(done_range["digital_ads"].sum()) if not done_range.empty else 0,
        "epubs_total": int(done_range["epubs"].sum()) if not done_range.empty else 0,
        "software_total": int(done_range["software"].sum()) if not done_range.empty else 0,
        "dam_total": int(done_range["dam"].sum()) if not done_range.empty else 0,
        "webserver_total": int(done_range["webserver"].sum()) if not done_range.empty else 0,
    }

    
    # Helper function to create simple metric display
    def create_simple_metric(icon, title, value, gradient="linear-gradient(135deg,#1e293b,#334155)"):
        return f"""
        <div style="text-align: center; padding: 20px; background: {gradient};
                    border-radius: 12px; margin: 4px; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
            <div style="font-size: 24px; margin-bottom: 8px;">{icon}</div>
            <div style="font-size: 13px; color: rgba(255,255,255,0.75); margin-bottom: 8px; font-weight: 600; letter-spacing: 0.5px; text-transform: uppercase;">{title}</div>
            <div style="font-size: 34px; font-weight: bold; color: #ffffff; line-height: 1;">{value:,}</div>
        </div>
        """

    # Main metrics - always visible
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.markdown(create_simple_metric("✅", "Asset Mapping Completed", metric_totals["asset_mapping_total"], "linear-gradient(135deg,#1a6b3c,#27ae60)"), unsafe_allow_html=True)
    with col2:
        st.markdown(create_simple_metric("🏢", "Subsidiaries", metric_totals["subsidiaries_total"], "linear-gradient(135deg,#1a4a7a,#2980b9)"), unsafe_allow_html=True)
    with col3:
        st.markdown(create_simple_metric("🌐", "Websites", metric_totals["websites_total"], "linear-gradient(135deg,#0e7490,#06b6d4)"), unsafe_allow_html=True)
    with col4:
        st.markdown(create_simple_metric("🔍", "QA Done", metric_totals["qa_total"], "linear-gradient(135deg,#5a1a7a,#8e44ad)"), unsafe_allow_html=True)
    with col5:
        st.markdown(create_simple_metric("📋", "Salesforce Ready", metric_totals["salesforce_ready_total"], "linear-gradient(135deg,#7a3a0a,#d35400)"), unsafe_allow_html=True)
    with col6:
        st.markdown(create_simple_metric("⏳", "Wayback Stuck", metric_totals["wayback_stuck_total"], "linear-gradient(135deg,#1a3a5a,#0f4c75)"), unsafe_allow_html=True)

    # Toggle button for extended assets
    st.markdown("")
    toggle_col1, toggle_col2, toggle_col3 = st.columns([1, 2, 1])
    with toggle_col2:
        if st.button(
            " Show More Assets" if not st.session_state.show_all_assets else " Show Less Assets",
            width='stretch',
            type="secondary",
            key="toggle_assets"
        ):
            st.session_state.show_all_assets = not st.session_state.show_all_assets
            st.rerun()

    # Extended assets - only visible when toggle is on
    if st.session_state.show_all_assets:
        # Responsive grid for extended assets (6 columns to include App)
        ext_col1, ext_col2, ext_col3, ext_col4, ext_col5, ext_col6 = st.columns([1, 1, 1, 1, 1, 1])
        with ext_col1:
            st.markdown(create_simple_metric("📢", "Digital Ads", metric_totals["digital_ads_total"], "linear-gradient(135deg,#7a1a3a,#c0392b)"), unsafe_allow_html=True)
        with ext_col2:
            st.markdown(create_simple_metric("📚", "Epubs", metric_totals["epubs_total"], "linear-gradient(135deg,#2d1a7a,#5b2be8)"), unsafe_allow_html=True)
        with ext_col3:
            st.markdown(create_simple_metric("💾", "Software", metric_totals["software_total"], "linear-gradient(135deg,#7a6a0a,#d4ac0d)"), unsafe_allow_html=True)
        with ext_col4:
            st.markdown(create_simple_metric("🗄️", "DAM", metric_totals["dam_total"], "linear-gradient(135deg,#1a5a4a,#1abc9c)"), unsafe_allow_html=True)
        with ext_col5:
            st.markdown(create_simple_metric("🖥️", "Webserver", metric_totals["webserver_total"], "linear-gradient(135deg,#0a4a7a,#0ea5e9)"), unsafe_allow_html=True)
        with ext_col6:
            st.markdown(create_simple_metric("📱", "App", metric_totals["app_total"], "linear-gradient(135deg,#7a1a5a,#e91e8c)"), unsafe_allow_html=True)

    st.divider()

    # Researcher summary table
    st.markdown("### Researcher Summary")
    rows = []
    for r in RESEARCHERS:
        r_done = done_range[_safe_col(done_range, "assigned_to") == r]
        rows.append({
            "Researcher": r,
            "Asset Mapping": len(r_done),
            "Subsidiaries": int(r_done["subsidiary_count"].sum()) if not r_done.empty else 0,
            "Websites": int(r_done["website_count"].sum()) if not r_done.empty else 0,
            "App": int(r_done["app"].sum()) if not r_done.empty else 0,
            "Digital Ads": int(r_done["digital_ads"].sum()) if not r_done.empty else 0,
            "Epubs": int(r_done["epubs"].sum()) if not r_done.empty else 0,
            "Software": int(r_done["software"].sum()) if not r_done.empty else 0,
            "DAM": int(r_done["dam"].sum()) if not r_done.empty else 0,
            "Webserver": int(r_done["webserver"].sum()) if not r_done.empty else 0,
            "QA Done": int(r_done["qa_status"].astype(bool).sum()) if not r_done.empty else 0,
            "Salesforce Ready": int(r_done["fud_status"].astype(bool).sum()) if not r_done.empty else 0,
            "Wayback Stuck": int((r_done["wayback_status"] == "in-progress").sum()) if not r_done.empty else 0,
        })
    summary = pd.DataFrame(rows)
    totals = {
        "Researcher": "TOTAL",
        "Asset Mapping": summary["Asset Mapping"].sum(),
        "Subsidiaries": summary["Subsidiaries"].sum(),
        "Websites": summary["Websites"].sum(),
        "App": summary["App"].sum(),
        "Digital Ads": summary["Digital Ads"].sum(),
        "Epubs": summary["Epubs"].sum(),
        "Software": summary["Software"].sum(),
        "DAM": summary["DAM"].sum(),
        "Webserver": summary["Webserver"].sum(),
        "QA Done": summary["QA Done"].sum(),
        "Salesforce Ready": summary["Salesforce Ready"].sum(),
        "Wayback Stuck": summary["Wayback Stuck"].sum(),
    }
    st.dataframe(
        pd.concat([summary, pd.DataFrame([totals])], ignore_index=True),
        width='stretch',
        hide_index=True,
    )

    if done_range.empty:
        st.info("No completed companies in the selected date range.")
        return

    st.divider()

    # ── Bar chart: Companies per researcher ──
    st.markdown("### Companies Completed by Researcher")
    chart_data = summary[summary["Asset Mapping"] > 0]
    fig_bar = px.bar(
        chart_data,
        x="Researcher",
        y="Asset Mapping",
        color="Asset Mapping",
        color_continuous_scale="Blues",
        text="Asset Mapping",
        title=f"{start_d.strftime('%b %d')} – {end_d.strftime('%b %d, %Y')}",
    )
    fig_bar.update_traces(textposition="outside")
    fig_bar.update_layout(
        xaxis_tickangle=-35,
        coloraxis_showscale=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(b=120),
    )
    st.plotly_chart(fig_bar, width='stretch')

    # ── Line chart: Daily trend ──
    st.divider()
    st.markdown("### Daily Completion Trend")
    daily = (
        done_range.groupby("date_completed")
        .agg(Companies=("id", "count"), Subsidiaries=("subsidiary_count", "sum"))
        .reset_index()
    )
    daily["date_completed"] = pd.to_datetime(daily["date_completed"])
    daily = daily.sort_values("date_completed")

    fig_line = make_subplots(specs=[[{"secondary_y": True}]])
    fig_line.add_trace(
        go.Scatter(
            x=daily["date_completed"],
            y=daily["Companies"],
            name="Companies",
            mode="lines+markers",
            line=dict(color="#1f77b4"),
            marker=dict(size=6),
        ),
        secondary_y=False,
    )
    fig_line.add_trace(
        go.Scatter(
            x=daily["date_completed"],
            y=daily["Subsidiaries"],
            name="Subsidiaries",
            mode="lines+markers",
            line=dict(color="#17becf"),
            marker=dict(size=6),
        ),
        secondary_y=True,
    )
    fig_line.update_layout(
        title="Daily Companies & Subsidiaries Completed",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(title="Date"),
    )
    fig_line.update_yaxes(title_text="Companies", secondary_y=False)
    fig_line.update_yaxes(title_text="Subsidiaries", secondary_y=True)
    st.plotly_chart(fig_line, width='stretch')

    # ── Pie chart: Overall completion ──
    st.divider()
    st.markdown("### Overall Completion Status (All Time)")
    total_all = len(cdf)
    total_done = int((cdf["status"] == "completed").sum()) if not cdf.empty else 0
    total_pend = total_all - total_done

    if total_all > 0:
        fig_pie = px.pie(
            pd.DataFrame({"Status": ["Completed", "Pending"], "Count": [total_done, total_pend]}),
            values="Count",
            names="Status",
            color="Status",
            color_discrete_map={"Completed": "#2ecc71", "Pending": "#e67e22"},
            title=f"Total: {total_all} companies",
        )
        st.plotly_chart(fig_pie, width='stretch')

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    for key, default in [
        ("logged_in", False), ("user_email", None), ("user_role", None), ("last_saved", None),
        ("op_count", 0), ("exp_r", set()), ("show_all_assets", False),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    if not st.session_state.logged_in:
        login_page()
        return

    cdf = get_companies()
    mdf = get_metrics()

    render_sidebar(cdf)

    tab1, tab2, tab3 = st.tabs(["📅 Daily Entry", "🏢 Companies", "📊 Analytics"])
    with tab1:
        tab_daily(cdf, mdf)
    with tab2:
        tab_companies(cdf)
    with tab3:
        tab_analytics(cdf, mdf)


if __name__ == "__main__":
    main()
