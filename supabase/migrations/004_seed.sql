-- 004_seed.sql · owner P3 · run after creating the demo users (Authentication → Users)
insert into public.companies (id, name, website, bsp_url) values
  ('ocean-harvesting','Ocean Harvesting Technologies','https://www.oceanharvesting.com/','https://www.bluesciencepark.se/medlem/ocean-harvesting/'),
  ('addsecure','AddSecure','https://www.addsecure.se/elnatslosningar/','https://www.bluesciencepark.se/medlem/addsecure/'),
  ('malvacom','Malvacom','https://malvacom.com/','https://www.bluesciencepark.se/medlem/malvacom/'),
  ('c-marine-ab','C Marine AB','https://www.cmarine.se/','https://www.bluesciencepark.se/medlem/c-marine-ab/'),
  ('cleura','Cleura','https://cleura.com','https://www.bluesciencepark.se/medlem/cleura/')
on conflict (id) do nothing;

insert into public.company_private (company_id) select id from public.companies
on conflict (company_id) do nothing;

insert into public.memberships (user_id, company_id, role)
select id,
       case when email like 'member-oht@%'       then 'ocean-harvesting'
            when email like 'member-addsecure@%' then 'addsecure' end,
       case when email like 'staff@%' then 'staff' else 'member' end
from auth.users
where email like 'member-oht@%' or email like 'member-addsecure@%' or email like 'staff@%'
on conflict (user_id) do nothing;

-- SIMULATED placeholder opportunities + matches for the feed until P2 loads real data
insert into public.opportunities (source, type, title, url, summary, date_or_deadline, format, next_step, retrieved_at, is_simulated) values
  ('SIMULATED','funding','SIMULATED funding call','https://www.bluesciencepark.se/vara-tjanster/vagar-till-finansiering/','Placeholder',current_date + 60,null,'SIMULATED next step',now(),true),
  ('SIMULATED','event','SIMULATED event','https://www.bluesciencepark.se/event/','Placeholder',current_date + 14,'in_person','SIMULATED next step',now(),true);

insert into public.matches (company_id, opportunity_id, score, rank, reason)
select c, o.id, 0.5, row_number() over (partition by c order by o.title), 'SIMULATED reason'
from public.opportunities o cross join (values ('ocean-harvesting'),('addsecure')) v(c) where o.is_simulated
on conflict do nothing;
