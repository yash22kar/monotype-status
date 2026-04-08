# Research Team Productivity Dashboard

Streamlit dashboard for tracking research team progress across 500 companies, backed by Supabase.

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Create Supabase project
1. Go to [supabase.com](https://supabase.com) → New project
2. Open **SQL Editor** → paste the contents of `schema.sql` → **Run**
3. Go to **Project Settings → API** and copy:
   - **Project URL**
   - **anon / public** key

### 3. Add credentials
Edit `.streamlit/secrets.toml`:
```toml
SUPABASE_URL = "https://your-project-ref.supabase.co"
SUPABASE_KEY = "your-anon-public-key"
```

### 4. Run the app
```bash
python -m streamlit run app.py
```

---

## Login
| Field    | Value                          |
|----------|-------------------------------|
| Email    | yash.baviskar@centralogic.net |
| Password | Krishna@123                   |

---

## Features

### 📅 Daily Entry
- Select a date → see 4 summary metrics for that day
- Each researcher has an expandable section showing:
  - **FUD / QA** number inputs (saved independently)
  - **Pending companies** checklist — tick boxes + enter subsidiary count → Mark Complete
  - **Completed today** summary list

### 🏢 Companies
- Overall progress stats (X / 500 completed)
- Per-researcher assignment summary table
- Filterable company table (by researcher, status, name search)
- Revert completed companies back to pending
- Re-assign companies to a different researcher

### 📊 Analytics
- Date-range selector
- Aggregated table per researcher (companies, subsidiaries, FUD, QA)
- Bar chart: companies completed per researcher
- Line chart: daily completion trend
- Pie chart: overall completed vs pending

### Sidebar (Admin)
- **Import Companies (CSV)** — CSV with `company_name` column (optional: `assigned_to`)
- **Add Company** — add a single company and optionally assign it
- **Assign Companies** — pick unassigned companies and assign to a researcher

---

## Data Schema

**`companies` table**
| Column | Type | Notes |
|---|---|---|
| id | bigint | Auto-generated PK |
| company_name | text | Company name |
| assigned_to | text | Researcher name (null = unassigned) |
| status | text | `pending` or `completed` |
| subsidiary_count | integer | Count only — no names stored |
| date_completed | date | Set when marked complete |

**`daily_metrics` table**
| Column | Type | Notes |
|---|---|---|
| date | date | Entry date |
| researcher | text | Researcher name |
| fud_completed | integer | FUD count for that day |
| qa_done | integer | QA count for that day |

---

## Importing 500 companies via CSV

Create a CSV file:
```
company_name,assigned_to
Acme Corp,Ashwini Jadhav
Globex Inc,Bhushan Joshi
...
```
Upload via **Sidebar → Import Companies (CSV)** → Import All.

If `assigned_to` is omitted or blank, companies appear as unassigned and can be assigned later.
