-- 002_rls.sql · access rules · contract v1.3 · owner P3
create or replace function public.my_company_id() returns text
language sql stable security definer set search_path = public as $$
  select company_id from public.memberships where user_id = auth.uid() $$;
create or replace function public.is_staff() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.memberships where user_id = auth.uid() and role = 'staff') $$;
revoke execute on function public.my_company_id(), public.is_staff() from anon;

alter table public.companies       enable row level security;
alter table public.profile_claims  enable row level security;
alter table public.opportunities   enable row level security;
alter table public.memberships     enable row level security;
alter table public.company_private enable row level security;
alter table public.matches         enable row level security;
alter table public.feedback        enable row level security;
alter table public.chat_messages   enable row level security;

create policy companies_read     on public.companies     for select to authenticated using (true);
create policy opportunities_read on public.opportunities for select to authenticated using (true);

create policy claims_read on public.profile_claims for select to authenticated
  using (origin = 'agent' or company_id = (select public.my_company_id()));
create policy claims_user_insert on public.profile_claims for insert to authenticated
  with check (origin = 'user' and verified = false and company_id = (select public.my_company_id()));
create policy claims_user_update on public.profile_claims for update to authenticated
  using      (origin = 'user' and company_id = (select public.my_company_id()))
  with check (origin = 'user' and verified = false and company_id = (select public.my_company_id()));

create policy memberships_self on public.memberships for select to authenticated
  using (user_id = (select auth.uid()));

create policy private_read   on public.company_private for select to authenticated
  using (company_id = (select public.my_company_id()));
create policy private_insert on public.company_private for insert to authenticated
  with check (company_id = (select public.my_company_id()));
create policy private_update on public.company_private for update to authenticated
  using (company_id = (select public.my_company_id()))
  with check (company_id = (select public.my_company_id()));

create policy matches_read on public.matches for select to authenticated
  using (company_id = (select public.my_company_id()));

create policy feedback_read   on public.feedback for select to authenticated
  using (company_id = (select public.my_company_id()));
create policy feedback_insert on public.feedback for insert to authenticated
  with check (company_id = (select public.my_company_id()) and user_id = (select auth.uid()));
create policy feedback_update on public.feedback for update to authenticated
  using (company_id = (select public.my_company_id()) and user_id = (select auth.uid()))
  with check (company_id = (select public.my_company_id()) and user_id = (select auth.uid()));

create policy chat_read   on public.chat_messages for select to authenticated
  using (company_id = (select public.my_company_id()) and user_id = (select auth.uid()));
create policy chat_insert on public.chat_messages for insert to authenticated
  with check (company_id = (select public.my_company_id()) and user_id = (select auth.uid()));

-- v1.4: staff may read all matches, read-only, for the compare view
create policy matches_staff_read on public.matches for select to authenticated
  using ((select public.is_staff()));
