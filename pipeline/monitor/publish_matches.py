import json
import math
from datetime import datetime, timezone
from pathlib import Path

from pipeline.common import db
from pipeline.monitor.embed_companies import load_profile

CACHE = Path(__file__).resolve().parent / ".cache"
COMPANIES = ["ocean-harvesting", "addsecure", "malvacom"]


def signature(profile):
    return {
        "claims": sorted(profile["claims"], key=lambda claim: claim["id"]),
        "priorities": profile["priorities"],
        "domains": profile["domains"],
        "private_updated_at": profile["private_updated_at"],
    }


def publish(company_id, rows):
    if not rows or any(row["company_id"] != company_id for row in rows):
        raise ValueError("Invalid company match batch")
    if sorted(row["rank"] for row in rows) != list(range(1, len(rows) + 1)):
        raise ValueError("Ranks must be consecutive")
    ids = [row["opportunity_id"] for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate opportunity IDs")
    for row in rows:
        if not math.isfinite(row["score"]) or not row["reason"].strip():
            raise ValueError("Invalid score or reason")

    client = db.client()
    client.table("matches").upsert(
        rows, on_conflict="company_id,opportunity_id"
    ).execute()

    # Remove stale matches only after the new batch was successfully written.
    (
        client.table("matches").delete()
        .eq("company_id", company_id)
        .not_.in_("opportunity_id", ids)
        .execute()
    )
    saved = (
        client.table("matches")
        .select("company_id,opportunity_id,score,rank,reason")
        .eq("company_id", company_id).order("rank")
        .execute().data
    )
    expected = {row["opportunity_id"]: row for row in rows}
    if len(saved) != len(rows):
        raise RuntimeError("Published count verification failed")
    for row in saved:
        original = expected.get(row["opportunity_id"])
        if (
            original is None
            or row["rank"] != original["rank"]
            or row["reason"] != original["reason"]
            or not math.isclose(row["score"], original["score"], abs_tol=1e-6)
        ):
            raise RuntimeError("Published match verification failed")
    return saved


def main():
    ready = json.loads(
        (CACHE / "matches_ready.json").read_text(encoding="utf-8")
    )
    profiles = json.loads(
        (CACHE / "profiles.json").read_text(encoding="utf-8")
    )
    snapshots = {profile["id"]: profile for profile in profiles}

    # Check all companies before the first write.
    for company_id in COMPANIES:
        if signature(load_profile(company_id)) != signature(snapshots[company_id]):
            raise RuntimeError(
                company_id + ": profile changed; stop and rerank before publishing."
            )
        if not any(row["company_id"] == company_id for row in ready):
            raise RuntimeError("Missing match batch: " + company_id)

    previous = (
        db.client().table("matches").select("*")
        .in_("company_id", COMPANIES).execute().data
    )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = CACHE / f"matches_backup_{stamp}.json"
    backup.write_text(
        json.dumps(previous, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Existing demo-company matches backed up locally.")

    total = 0
    for company_id in COMPANIES:
        rows = [row for row in ready if row["company_id"] == company_id]
        saved = publish(company_id, rows)
        total += len(saved)
        print(company_id, "| published and verified:", len(saved))

    print("Total verified matches:", total)


if __name__ == "__main__":
    main()
