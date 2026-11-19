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
