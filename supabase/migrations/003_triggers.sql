-- 003_triggers.sql · owner P3
create or replace function public.touch_updated_at() returns trigger
language plpgsql as $$ begin new.updated_at := now(); return new; end $$;
create trigger company_private_touch before update on public.company_private
  for each row execute function public.touch_updated_at();

create or replace function public.touch_private_on_user_claim() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if coalesce(new.origin, old.origin) = 'user' then
    insert into public.company_private (company_id) values (coalesce(new.company_id, old.company_id))
    on conflict (company_id) do update set updated_at = now();
  end if;
  return coalesce(new, old);
end $$;
create trigger user_claim_touch after insert or update or delete on public.profile_claims
  for each row execute function public.touch_private_on_user_claim();
