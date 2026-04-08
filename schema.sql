-- ============================================================
-- Run this entire script in the Supabase SQL Editor
-- Dashboard → SQL Editor → New Query → Paste → Run
-- ============================================================

-- 1. Companies master table
--    One row per company. subsidiary_count is just an integer — no names stored.
create table if not exists companies (
    id               bigint generated always as identity primary key,
    company_name     text    not null,
    assigned_to      text,                          -- researcher name, null = unassigned
    status           text    not null default 'pending',  -- 'pending' | 'completed'
    subsidiary_count integer not null default 0,
    date_completed   date,
    created_at       timestamptz default now()
);

-- 2. Daily FUD & QA metrics (one row per researcher per day)
create table if not exists daily_metrics (
    id             bigint generated always as identity primary key,
    date           date not null,
    researcher     text not null,
    fud_completed  integer not null default 0,
    qa_done        integer not null default 0,
    constraint daily_metrics_date_researcher_key unique (date, researcher)
);

-- 3. Add company-level QA & FUD tracking columns
--    (Run this separately if the table already exists)
alter table companies add column if not exists qa_status  boolean not null default false;
alter table companies add column if not exists fud_status boolean not null default false;

-- ============================================================
-- Row Level Security (RLS)
-- Enable these if you want to lock down access.
-- The anon key used by the app must be allowed to read/write.
-- ============================================================

alter table companies     enable row level security;
alter table daily_metrics enable row level security;

-- Allow full access for the anon role (suitable for an internal tool)
create policy "anon_all_companies"
    on companies for all
    to anon
    using (true)
    with check (true);

create policy "anon_all_metrics"
    on daily_metrics for all
    to anon
    using (true)
    with check (true);
