"""Load out/profile_<slug>.json into Supabase via the shared db.py (service role, pipeline only)."""
import sys, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.common import db

OUT = pathlib.Path(__file__).parent / "out"

def load(cid: str) -> None:
    p = OUT / f"profile_{cid}.json"
    r = json.loads(p.read_text())
    claims = r["claims"]
    n = db.upsert_claims(claims)
    db.remove_stale_agent_claims(cid, [c["id"] for c in claims])
    db.set_company_domains(cid, r["domains"])
    check = db.client().table("profile_claims").select("id", count="exact").eq("company_id", cid).eq("origin", "agent").execute()
    print(f"{cid:<17} upserted={n}  in_db={check.count}  domains={r['domains']}")

if __name__ == "__main__":
    targets = sys.argv[1:] or [p.stem.removeprefix("profile_") for p in sorted(OUT.glob("profile_*.json"))]
    for cid in targets:
        try:
            load(cid)
        except Exception as e:
            print(f"{cid:<17} FAILED: {e}")
