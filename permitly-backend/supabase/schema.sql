-- Run this once in Supabase: SQL Editor -> New query -> paste -> Run.

-- B8: one row per API request. NO user text is stored, only timing.
create table if not exists public.request_logs (
  id          uuid primary key default gen_random_uuid(),
  created_at  timestamptz not null default now(),
  request_id  text not null,
  method      text not null,
  path        text not null,
  status      integer not null,
  latency_ms  integer not null
);
create index if not exists request_logs_created_at_idx on public.request_logs (created_at desc);

-- Security: turn Row Level Security ON and add NO policies.
-- Then the public/anon key can read nothing; only our backend (service key) can write.
alter table public.request_logs enable row level security;


-- B4: States supported by Permitly.
create table if not exists public.states (
    code text primary key,
    name text not null,
    license_type text not null default 'money_transmission',
    statute text,
    source_date date
);

-- B4: Licensing requirements and supporting legal citations.
create table if not exists public.state_requirements (
    id bigint generated always as identity primary key,
    state_code text not null references public.states(code),
    field_name text not null,
    value jsonb,
    section text,
    quote text,
    note text default '',
    unique (state_code, field_name)
);

-- Restrict direct access to these tables.
-- The backend accesses them using its secret Supabase key.
alter table public.states enable row level security;
alter table public.state_requirements enable row level security;