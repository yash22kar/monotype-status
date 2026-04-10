"""
Research Team Productivity Dashboard
Streamlit + Supabase
"""
import streamlit as st
import pandas as pd
from datetime import date, datetime
import plotly.express as px
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
CREDENTIALS = {"email": "yash.baviskar@centralogic.net", "password": "Krishna@123"}

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
            "qa_status", "fud_status", "qa_done_date", "fud_done_date", "created_at"
        ])
    df = pd.DataFrame(data)
    df["subsidiary_count"] = pd.to_numeric(
        df.get("subsidiary_count", 0), errors="coerce"
    ).fillna(0).astype(int)
    df["website_count"] = pd.to_numeric(
        df.get("website_count", 0), errors="coerce"
    ).fillna(0).astype(int)
    for col in ["qa_status", "fud_status"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("")
    for col in ["qa_done_date", "fud_done_date"]:
        if col not in df.columns:
            df[col] = None
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

# ─── DB Write Operations ──────────────────────────────────────────────────────
def complete_companies(updates: list, date_str: str):
    """Mark as LEM/AM complete.
    updates = [{"id": int, "subsidiary_count": int, "qa_status": bool, "fud_status": bool}]"""
    sb = get_sb()
    for u in updates:
        sb.table("companies").update({
            "status": "completed",
            "subsidiary_count": u["subsidiary_count"],
            "website_count": u.get("website_count", 0),
            "date_completed": date_str,
            "qa_status":      u.get("qa_status")  or None,
            "fud_status":     u.get("fud_status") or None,
            "qa_done_date":   date_str if (u.get("qa_status")  or None) else None,
            "fud_done_date":  date_str if (u.get("fud_status") or None) else None,
        }).eq("id", u["id"]).execute()
    bust_cache()

def save_qa_fud(entries: list, today_str: str):
    """Save counts + QA/FUD reviewer names and auto-manage done dates."""
    sb = get_sb()
    for e in entries:
        qa  = e.get("qa_status")  or None
        fud = e.get("fud_status") or None
        existing_qa_date  = e.get("qa_done_date")  or None
        existing_fud_date = e.get("fud_done_date") or None
        sb.table("companies").update({
            "subsidiary_count": e.get("subsidiary_count", 0),
            "website_count":    e.get("website_count", 0),
            "qa_status":        qa,
            "fud_status":       fud,
            "qa_done_date":     (existing_qa_date  or today_str) if qa  else None,
            "fud_done_date":    (existing_fud_date or today_str) if fud else None,
        }).eq("id", e["id"]).execute()
    bust_cache()

def revert_companies(ids: list):
    sb = get_sb()
    for cid in ids:
        sb.table("companies").update({
            "status": "pending",
            "subsidiary_count": 0,
            "date_completed": None,
            "qa_status": None,
            "fud_status": None,
            "qa_done_date": None,
            "fud_done_date": None,
        }).eq("id", cid).execute()
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
            if st.form_submit_button("Sign In", use_container_width=True, type="primary"):
                if email == CREDENTIALS["email"] and password == CREDENTIALS["password"]:
                    st.session_state.update(logged_in=True, user_email=email, last_saved=None)
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
                        st.dataframe(df_up.head(5), use_container_width=True)
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
        if st.button("🚪 Logout", use_container_width=True):
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
    m1.markdown(colored_metric("LEM/AM Done Today",   n_lem,  "linear-gradient(135deg,#1a6b3c,#27ae60)", "✅"), unsafe_allow_html=True)
    m2.markdown(colored_metric("Subsidiaries Today",   n_sub,  "linear-gradient(135deg,#1a4a7a,#2980b9)", "📦"), unsafe_allow_html=True)
    m3.markdown(colored_metric("QA Done Today",        n_qa,   "linear-gradient(135deg,#5a1a7a,#8e44ad)", "🔍"), unsafe_allow_html=True)
    m4.markdown(colored_metric("FUD Done Today",       n_fud,  "linear-gradient(135deg,#7a3a0a,#d35400)", "📋"), unsafe_allow_html=True)

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
        use_container_width=True,
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

        if row_cols[6].button(
            "▲ Close" if is_exp else "▼ Open",
            key=f"tog_{researcher}",
            use_container_width=True,
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
        if is_exp:
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
                        hc0, hc1, hc2, hc3, hc4 = st.columns([5, 1.5, 1.5, 3, 3])
                        hc0.markdown("**LEM/AM ↗ Company Name**")
                        hc1.markdown("**Subsidiaries**")
                        hc2.markdown("**Websites**")
                        hc3.markdown("**QA Reviewer**")
                        hc4.markdown("**FUD Reviewer**")
                        st.markdown("<hr style='margin:4px 0 8px 0'>", unsafe_allow_html=True)

                        all_entries = []
                        to_complete = []

                        for _, row in r_pending.iterrows():
                            cc0, cc1, cc2, cc3, cc4 = st.columns([5, 1.5, 1.5, 3, 3])
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
                            _qa_val = row.get("qa_status") or ""
                            _qa_idx = QA_REVIEWERS.index(_qa_val) + 1 if _qa_val in QA_REVIEWERS else 0
                            qa = cc3.selectbox(
                                "QA", options=["— None —"] + QA_REVIEWERS,
                                index=_qa_idx,
                                key=f"qa_{row['id']}_{date_str}", label_visibility="collapsed",
                            )
                            _fud_val = row.get("fud_status") or ""
                            _fud_idx = FUD_REVIEWERS.index(_fud_val) + 1 if _fud_val in FUD_REVIEWERS else 0
                            fud = cc4.selectbox(
                                "FUD", options=["— None —"] + FUD_REVIEWERS,
                                index=_fud_idx,
                                key=f"fud_{row['id']}_{date_str}", label_visibility="collapsed",
                            )
                            entry = {
                                "id": int(row["id"]), "subsidiary_count": sub,
                                "website_count": web,
                                "qa_status":      "" if qa  == "— None —" else qa,
                                "fud_status":     "" if fud == "— None —" else fud,
                                "qa_done_date":   row.get("qa_done_date"),
                                "fud_done_date":  row.get("fud_done_date"),
                            }
                            all_entries.append(entry)
                            if lem_am:
                                to_complete.append(entry)

                        st.markdown("")
                        bc1, bc2 = st.columns(2)
                        save_qf  = bc1.form_submit_button("💾 Save QA / FUD Status", use_container_width=True)
                        mark_lem = bc2.form_submit_button("✅ Mark LEM/AM Complete", type="primary", use_container_width=True)

                        if mark_lem:
                            if to_complete:
                                complete_ids = {e["id"] for e in to_complete}
                                non_complete = [e for e in all_entries if e["id"] not in complete_ids]
                                if non_complete:
                                    save_qa_fud(non_complete, date_str)
                                complete_companies(to_complete, date_str)
                                st.session_state.last_saved = _now_ts()
                                st.session_state.op_count += 1
                                st.success(f"Marked {len(to_complete)} companies as LEM/AM complete!")
                                st.rerun()
                            else:
                                st.warning("Check at least one LEM/AM checkbox to mark complete.")
                        if save_qf:
                            save_qa_fud(all_entries, date_str)
                            st.session_state.last_saved = _now_ts()
                            st.session_state.op_count += 1
                            st.success("QA / FUD status saved!")
                            st.rerun()

                # Completed today with unmark
                if not r_done_today.empty:
                    st.divider()
                    st.markdown(f"**✅ Completed Today ({len(r_done_today)})** — check to unmark:")
                    with st.form(f"unmark_{researcher}_{date_str}"):
                        hc0, hc1, hc2, hc3, hc4 = st.columns([5, 1.5, 1.5, 3, 3])
                        hc0.markdown("**Unmark ↗ Company Name**")
                        hc1.markdown("**Subsidiaries**")
                        hc2.markdown("**Websites**")
                        hc3.markdown("**QA Reviewer**")
                        hc4.markdown("**FUD Reviewer**")
                        st.markdown("<hr style='margin:4px 0 8px 0'>", unsafe_allow_html=True)
                        to_unmark = []
                        done_entries = []
                        for _, row in r_done_today.sort_values("company_name").iterrows():
                            uc0, uc1, uc2, uc3, uc4 = st.columns([5, 1.5, 1.5, 3, 3])
                            chk = uc0.checkbox(
                                str(row["company_name"]), value=False,
                                key=f"unk_{row['id']}_{date_str}",
                            )
                            uc1.markdown(f"`{int(row['subsidiary_count'])}`")
                            uc2.markdown(f"`{int(row.get('website_count', 0))}`")
                            _qa_val  = row.get("qa_status")  or ""
                            _fud_val = row.get("fud_status") or ""
                            _qa_idx  = QA_REVIEWERS.index(_qa_val)  + 1 if _qa_val  in QA_REVIEWERS  else 0
                            _fud_idx = FUD_REVIEWERS.index(_fud_val) + 1 if _fud_val in FUD_REVIEWERS else 0
                            qa_sel  = uc3.selectbox("QA",  options=["— None —"] + QA_REVIEWERS,
                                index=_qa_idx,  key=f"dqa_{row['id']}_{date_str}",  label_visibility="collapsed")
                            fud_sel = uc4.selectbox("FUD", options=["— None —"] + FUD_REVIEWERS,
                                index=_fud_idx, key=f"dfud_{row['id']}_{date_str}", label_visibility="collapsed")
                            if chk:
                                to_unmark.append(int(row["id"]))
                            done_entries.append({
                                "id":            int(row["id"]),
                                "subsidiary_count": int(row["subsidiary_count"]),
                                "website_count":    int(row.get("website_count", 0)),
                                "qa_status":     "" if qa_sel  == "— None —" else qa_sel,
                                "fud_status":    "" if fud_sel == "— None —" else fud_sel,
                                "qa_done_date":  row.get("qa_done_date"),
                                "fud_done_date": row.get("fud_done_date"),
                            })
                        st.markdown("")
                        sb1, sb2 = st.columns(2)
                        save_done_qf = sb1.form_submit_button("💾 Save QA / FUD", use_container_width=True)
                        unmark_btn   = sb2.form_submit_button("↩️ Unmark Selected (revert to Pending)", use_container_width=True)
                        if save_done_qf:
                            save_qa_fud(done_entries, date_str)
                            st.session_state.last_saved = _now_ts()
                            st.session_state.op_count += 1
                            st.success("QA / FUD reviewers saved!")
                            st.rerun()
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
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

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
            use_container_width=True,
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
        use_container_width=True,
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
            use_container_width=True,
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
            use_container_width=True,
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
            with st.popover("✏️ Edit Subsidiary Count", use_container_width=True):
                new_sub = st.number_input("New Subsidiary Count", min_value=0, value=0, key="new_sub_val")
                if st.button("Save", type="primary", key="btn_save_sub"):
                    sb = get_sb()
                    for cid in selected["ID"].tolist():
                        sb.table("companies").update({"subsidiary_count": new_sub}).eq("id", cid).execute()
                    bust_cache()
                    st.session_state.op_count += 1
                    st.success(f"Updated subsidiary count to {new_sub} for {n_sel} company/companies.")
                    st.rerun()

# ─── Tab 3: Analytics ─────────────────────────────────────────────────────────
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

    # Overview — all from company-level data
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("✅ LEM/AM Completed", len(done_range))
    m2.metric("📦 Subsidiaries", int(done_range["subsidiary_count"].sum()) if not done_range.empty else 0)
    m3.metric("🌐 Websites", int(done_range["website_count"].sum()) if not done_range.empty else 0)
    m4.metric("🔍 QA Done", int(done_range["qa_status"].astype(bool).sum()) if not done_range.empty else 0)
    m5.metric("📋 FUD Done", int(done_range["fud_status"].astype(bool).sum()) if not done_range.empty else 0)

    st.divider()

    # ── Researcher summary table ──
    st.markdown("### Researcher Summary")
    rows = []
    for r in RESEARCHERS:
        r_done = done_range[_safe_col(done_range, "assigned_to") == r]
        rows.append({
            "Researcher": r,
            "LEM/AM Done": len(r_done),
            "Subsidiaries": int(r_done["subsidiary_count"].sum()) if not r_done.empty else 0,
            "Websites": int(r_done["website_count"].sum()) if not r_done.empty else 0,
            "QA Done": int(r_done["qa_status"].astype(bool).sum()) if not r_done.empty else 0,
            "FUD Done": int(r_done["fud_status"].astype(bool).sum()) if not r_done.empty else 0,
        })
    summary = pd.DataFrame(rows)
    totals = {
        "Researcher": "TOTAL",
        "LEM/AM Done": summary["LEM/AM Done"].sum(),
        "Subsidiaries": summary["Subsidiaries"].sum(),
        "Websites": summary["Websites"].sum(),
        "QA Done": summary["QA Done"].sum(),
        "FUD Done": summary["FUD Done"].sum(),
    }
    st.dataframe(
        pd.concat([summary, pd.DataFrame([totals])], ignore_index=True),
        use_container_width=True,
        hide_index=True,
    )

    if done_range.empty:
        st.info("No completed companies in the selected date range.")
        return

    st.divider()

    # ── Bar chart: Companies per researcher ──
    st.markdown("### Companies Completed by Researcher")
    chart_data = summary[summary["LEM/AM Done"] > 0]
    fig_bar = px.bar(
        chart_data,
        x="Researcher",
        y="LEM/AM Done",
        color="LEM/AM Done",
        color_continuous_scale="Blues",
        text="LEM/AM Done",
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
    st.plotly_chart(fig_bar, use_container_width=True)

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

    fig_line = px.line(
        daily,
        x="date_completed",
        y=["Companies", "Subsidiaries"],
        markers=True,
        title="Daily Companies & Subsidiaries Completed",
        labels={"date_completed": "Date", "value": "Count", "variable": "Metric"},
    )
    fig_line.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig_line, use_container_width=True)

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
        st.plotly_chart(fig_pie, use_container_width=True)

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    for key, default in [
        ("logged_in", False), ("user_email", None), ("last_saved", None),
        ("op_count", 0), ("exp_r", set()),
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
