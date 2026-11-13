-- 001_tables.sql · contract v1.3 · owner P3. [P3] = addition that changes no contract column.
create extension if not exists vector with schema extensions;

create table public.companies (
  id text primary key, name text not null, website text, bsp_url text,
  domains text[] default '{}', profile_embedding vector(384),
  is_simulated boolean default false, created_at timestamptz default now());

create table public.profile_claims (
  id uuid primary key default gen_random_uuid(),
  company_id text not null references public.companies(id) on delete cascade,
  field text check (field in ('offering','technology','expertise','application_area','market',
        'customer_group','geography','priority','collaboration','domain','relevant_topic','size','founded','location')),
  value text, type text check (type in ('stated','inferred','missing')),
  quote text, source_url text, retrieved_at timestamptz,
  confidence text default 'medium' check (confidence in ('high','medium','low')),
  origin text default 'agent' check (origin in ('agent','user')),
  verified boolean default false, is_simulated boolean default false,
  created_at timestamptz default now());

create table public.opportunities (
  id uuid primary key default gen_random_uuid(), source text not null,
  type text check (type in ('funding','event','testbed','support')),
  title text not null, url text not null, summary text, date_or_deadline date,
  format text check (format in ('online','in_person')),
  audience text, eligibility text default 'potential', eligibility_note text,
  next_step text not null, domains text[] default '{}', embedding vector(384),
  retrieved_at timestamptz not null, content_hash text, is_simulated boolean default false);

create table public.memberships (
  user_id uuid primary key references auth.users(id) on delete cascade,
  company_id text references public.companies(id) on delete cascade,
  role text check (role in ('member','staff')),
  constraint staff_has_no_company check ((role = 'staff') = (company_id is null)));  -- [P3]

create table public.company_private (
  company_id text primary key references public.companies(id) on delete cascade,
  priorities text[] default '{}', notes text,
  rejected_claim_ids uuid[] default '{}',
  updated_at timestamptz default now());

create table public.matches (
  company_id text references public.companies(id) on delete cascade,
  opportunity_id uuid references public.opportunities(id) on delete cascade,
  score real, rank int, reason text, created_at timestamptz default now(),
  primary key (company_id, opportunity_id));

create table public.feedback (
  id uuid primary key default gen_random_uuid(),
  company_id text references public.companies(id) on delete cascade,
  opportunity_id uuid references public.opportunities(id) on delete cascade,
  user_id uuid default auth.uid(),                                    -- [P3] default
  saved boolean default false,
  rating smallint default 0 check (rating in (-1,0,1)),
  created_at timestamptz default now());

create table public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  company_id text references public.companies(id) on delete cascade,
  user_id uuid default auth.uid(),                                    -- [P3] default
  role text check (role in ('user','assistant')), content text, route text,
  created_at timestamptz default now());

create index on public.profile_claims (company_id);
create index on public.matches (company_id, rank);
create index on public.chat_messages (company_id, user_id, created_at desc);
