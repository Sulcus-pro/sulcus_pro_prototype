-- Sulcus.pro v2 — Supabase schema for NovaCorp operational intelligence.
-- Run this once against a fresh Supabase project (SQL Editor -> New query -> Run).

create extension if not exists pgcrypto;

-- --------------------------------------------------------------------------
-- events: the raw operational event stream across all NovaCorp departments.
-- --------------------------------------------------------------------------
create table if not exists events (
    id              uuid primary key default gen_random_uuid(),
    created_at      timestamptz default now(),
    department      text not null check (department in (
                        'Engineering', 'Product', 'Sales', 'Marketing',
                        'Finance', 'HR', 'Legal', 'DevOps'
                    )),
    source          text not null check (source in (
                        'slack', 'github', 'jira', 'gmail', 'outlook',
                        'salesforce', 'pagerduty', 'datadog', 'confluence',
                        'figma', 'workday', 'notion'
                    )),
    actor           text not null,
    content         text not null,
    risk_level      text not null check (risk_level in ('low', 'medium', 'high', 'critical')),
    risk_reason     text not null,
    tick            integer not null check (tick between 0 and 9),
    is_tombstoned   boolean not null default false,
    tags            text[] not null default '{}'
);

create index if not exists idx_events_department on events (department);
create index if not exists idx_events_tick on events (tick);
create index if not exists idx_events_risk_level on events (risk_level);
create index if not exists idx_events_created_at on events (created_at);

-- --------------------------------------------------------------------------
-- audit_log: the temporal-brain history trail (human actions + system/brain
-- actions written by the circadian consolidation loop).
-- --------------------------------------------------------------------------
create table if not exists audit_log (
    id              uuid primary key default gen_random_uuid(),
    created_at      timestamptz default now(),
    entry_type      text not null check (entry_type in ('HUMAN', 'BRAIN', 'SYSTEM')),
    actor           text not null,
    action          text not null,
    detail          text not null default '',
    tick            integer not null check (tick between 0 and 9),
    department      text
);

create index if not exists idx_audit_log_department on audit_log (department);
create index if not exists idx_audit_log_tick on audit_log (tick);
create index if not exists idx_audit_log_created_at on audit_log (created_at);

-- --------------------------------------------------------------------------
-- chat_history: Claude-powered Sulcus chat transcript.
-- --------------------------------------------------------------------------
create table if not exists chat_history (
    id              uuid primary key default gen_random_uuid(),
    created_at      timestamptz default now(),
    role            text not null check (role in ('user', 'assistant')),
    content         text not null,
    session_id      text not null
);

create index if not exists idx_chat_history_session_id on chat_history (session_id);
create index if not exists idx_chat_history_created_at on chat_history (created_at);

-- --------------------------------------------------------------------------
-- Row Level Security: open read/write for the anon key, suitable for a demo
-- prototype. Tighten before any production use.
-- --------------------------------------------------------------------------
alter table events enable row level security;
alter table audit_log enable row level security;
alter table chat_history enable row level security;

drop policy if exists "events_anon_all" on events;
create policy "events_anon_all" on events for all using (true) with check (true);

drop policy if exists "audit_log_anon_all" on audit_log;
create policy "audit_log_anon_all" on audit_log for all using (true) with check (true);

drop policy if exists "chat_history_anon_all" on chat_history;
create policy "chat_history_anon_all" on chat_history for all using (true) with check (true);
