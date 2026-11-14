"""Check the DB two ways: (1) service role: row counts; (2) as a logged-in member: what they can and can't see."""
import os, sys, getpass, pathlib, collections
from dotenv import load_dotenv
from supabase import create_client

ROOT = pathlib.Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=True)
URL = os.environ["SUPABASE_URL"]

print("=== 1. Service role (pipeline view)")
svc = create_client(URL, os.environ["SUPABASE_SERVICE_ROLE_KEY"])
for t in ["companies", "profile_claims", "opportunities", "matches", "company_private", "memberships"]:
    try:
        n = svc.table(t).select("*", count="exact").limit(1).execute().count
        print(f"  {t:<16} {n} rows")
    except Exception as e:
        print(f"  {t:<16} ERROR {str(e)[:80]}")
rows = svc.table("profile_claims").select("company_id,type,origin,is_simulated").execute().data
c = collections.Counter((r["company_id"], r["type"], "SIM" if r["is_simulated"] else "real") for r in rows)
for k in sorted(c):
    print(f"  claims {k[0]:<17} {k[1]:<9} {k[2]:<5} {c[k]}")

print("\n=== 2. As member-oht@demo (what the website will see)")
email = input("  email [member-oht@demo]: ").strip() or "member-oht@demo"
pw = getpass.getpass("  password (hidden): ")
user = create_client(URL, os.environ["SUPABASE_ANON_KEY"])
try:
    user.auth.sign_in_with_password({"email": email, "password": pw})
except Exception as e:
    print("  LOGIN FAILED:", str(e)[:120]); sys.exit(1)

def check(label, table, company, expect_zero):
    try:
        n = len(user.table(table).select("*").eq("company_id", company).execute().data)
        ok = (n == 0) if expect_zero else (n > 0)
        print(f"  {'PASS' if ok else 'FAIL'}  {label:<45} rows={n}")
    except Exception as e:
        print(f"  {'PASS' if expect_zero else 'FAIL'}  {label:<45} blocked ({str(e)[:50]})")

check("sees own profile claims (OHT)", "profile_claims", "ocean-harvesting", expect_zero=False)
check("sees AddSecure's public agent claims", "profile_claims", "addsecure", expect_zero=False)
check("CANNOT see AddSecure matches", "matches", "addsecure", expect_zero=True)
check("CANNOT see AddSecure private data", "company_private", "addsecure", expect_zero=True)
check("CANNOT see AddSecure chat", "chat_messages", "addsecure", expect_zero=True)
