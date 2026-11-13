"""pipeline/common/db.py · shared Supabase access for pipelines (P1, P2).
Uses SUPABASE_SERVICE_ROLE_KEY: server-side scripts only, never in the web app or /ask."""
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
_client: Client | None = None


def client() -> Client:
    global _client
    if _client is None:
        _client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    return _client


def _rows(items):
    return [i.model_dump(mode="json") if hasattr(i, "model_dump") else dict(i) for i in items]


# ---------- P1 ----------
def upsert_claims(claims) -> int:
    rows = _rows(claims)
    for r in rows:
        if not r.get("id"):
            raise ValueError("claim id missing: uuid5 required (contract v1.4)")
        if r.get("origin", "agent") != "agent":
            raise ValueError("pipelines write origin='agent' claims only")
    if rows:
        client().table("profile_claims").upsert(rows, on_conflict="id").execute()
    return len(rows)


def remove_stale_agent_claims(company_id: str, keep_ids: list[str]) -> None:
    """After a refresh: delete this company's agent claims that the new run no longer produced."""
    q = client().table("profile_claims").delete().eq("company_id", company_id).eq("origin", "agent")
    if keep_ids:
        q = q.not_.in_("id", keep_ids)
    q.execute()


def set_company_domains(company_id: str, domains: list[str]) -> None:
    client().table("companies").update({"domains": domains}).eq("id", company_id).execute()


# ---------- P2 ----------
def upsert_opportunities(opps) -> int:
    rows = _rows(opps)
    if rows:
        client().table("opportunities").upsert(rows, on_conflict="id").execute()
    return len(rows)


def replace_matches(company_id: str, matches) -> int:
    client().table("matches").delete().eq("company_id", company_id).execute()
    rows = _rows(matches)
    if rows:
        client().table("matches").insert(rows).execute()
    return len(rows)


def private_state(company_id: str) -> dict:
    """For P2's watcher: priorities, rejected_claim_ids, updated_at."""
    r = client().table("company_private").select("*").eq("company_id", company_id).execute()
    return r.data[0] if r.data else {}
