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
alter table public.companies add column if not exists website_count integer not null default 0;
alter table public.companies add column if not exists app integer not null default 0;
alter table public.companies add column if not exists digital_ads integer not null default 0;
alter table public.companies add column if not exists epubs integer not null default 0;
alter table public.companies add column if not exists software integer not null default 0;
alter table public.companies add column if not exists dam integer not null default 0;
alter table public.companies add column if not exists webserver integer not null default 0;
alter table public.companies add column if not exists start_date date;
alter table public.companies add column if not exists end_date date;
alter table public.companies add column if not exists start_time time;
alter table public.companies add column if not exists end_time time;

-- QA and FUD now store reviewer names (text) instead of booleans
-- This block is safe on both fresh and existing DBs.
do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema='public' and table_name='companies' and column_name='qa_status'
  ) then
    if (select data_type from information_schema.columns
        where table_schema='public' and table_name='companies' and column_name='qa_status') <> 'text' then
      -- Historical schemas may have qa_status as boolean; we intentionally discard old values.
      alter table public.companies alter column qa_status type text using null;
    end if;
    alter table public.companies alter column qa_status drop not null;
    alter table public.companies alter column qa_status set default null;
  else
    alter table public.companies add column qa_status text;
  end if;

  if exists (
    select 1 from information_schema.columns
    where table_schema='public' and table_name='companies' and column_name='fud_status'
  ) then
    if (select data_type from information_schema.columns
        where table_schema='public' and table_name='companies' and column_name='fud_status') <> 'text' then
      alter table public.companies alter column fud_status type text using null;
    end if;
    alter table public.companies alter column fud_status drop not null;
    alter table public.companies alter column fud_status set default null;
  else
    alter table public.companies add column fud_status text;
  end if;
end $$;

alter table public.companies add column if not exists qa_done_date  date;
alter table public.companies add column if not exists fud_done_date date;

-- 4. Wayback status tracking (per-company)
alter table public.companies add column if not exists wayback_status text not null default 'completed';
update public.companies set wayback_status = 'completed' where wayback_status is null;

-- ============================================================
-- Row Level Security (RLS)
-- Enable these if you want to lock down access.
-- The anon key used by the app must be allowed to read/write.
-- ============================================================

alter table public.companies     enable row level security;
alter table public.daily_metrics enable row level security;

-- Allow full access for the anon role (suitable for an internal tool)
do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname='public' and tablename='companies' and policyname='anon_all_companies'
  ) then
    create policy "anon_all_companies"
        on public.companies for all
        to anon
        using (true)
        with check (true);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname='public' and tablename='daily_metrics' and policyname='anon_all_metrics'
  ) then
    create policy "anon_all_metrics"
        on public.daily_metrics for all
        to anon
        using (true)
        with check (true);
  end if;
end $$;

-- Optional: immediately refresh PostgREST schema cache (same as Dashboard -> Settings -> API -> Reload schema)
select pg_notify('pgrst', 'reload schema');
