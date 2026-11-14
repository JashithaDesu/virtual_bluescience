import json
import os
import subprocess
import sys
from datetime import datetime, timezone

from pipeline.common import db
from pipeline.monitor.embed_companies import CACHE

CID = "ocean-harvesting"
PRIORITY = "Testing and validating our technology with a potential customer is a priority"
TITLE = "Verification of Innovations with Customers"


def rank():
    opportunities = (
        db.client().table("opportunities").select("id")
        .eq("title", TITLE).execute().data
    )
    if len(opportunities) != 1:
        raise RuntimeError("Expected one Verification opportunity")
    rows = (
        db.client().table("matches").select("rank")
        .eq("company_id", CID)
        .eq("opportunity_id", opportunities[0]["id"]).execute().data
    )
    return rows[0]["rank"] if len(rows) == 1 else None


def rerank():
    env = dict(os.environ)
    env["LLM_API_KEY"] = "invalid"
    env["P2_EXPLAIN_NO_CACHE"] = "1"
    subprocess.run(
        [sys.executable, "-u", "-m", "pipeline.monitor.rerank", CID],
        env=env, check=True, timeout=180,
    )


def main():
    original = db.private_state(CID)
    if rank() != 4:
        raise RuntimeError("Expected reset baseline #4; stop and report")
    priorities = original.get("priorities") or []
    if PRIORITY in priorities:
        raise RuntimeError("Demo priority already present")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    (CACHE / f"fallback_test_backup_{stamp}.json").write_text(
        json.dumps(original, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    updated = (
        db.client().table("company_private")
        .update({"priorities": priorities + [PRIORITY]})
        .eq("company_id", CID)
        .eq("updated_at", original["updated_at"]).execute().data
    )
    if len(updated) != 1:
        raise RuntimeError("Concurrent edit; test stopped")

    print("SIMULATED LIVE TEST: invalid key; cache bypassed.", flush=True)
    try:
        rerank()
        if rank() != 3:
            raise RuntimeError("Expected published rank #3")
        print("PASS: invalid key still published Verification at #3.", flush=True)
    finally:
        restored = (
            db.client().table("company_private")
            .update({"priorities": priorities})
            .eq("company_id", CID)
            .eq("updated_at", updated[0]["updated_at"]).execute().data
        )
        if len(restored) != 1:
            raise RuntimeError(
                "Concurrent edit: restoration stopped to protect user changes."
            )
        print("Original priorities restored; republishing baseline.", flush=True)
        rerank()
        if rank() != 4:
            raise RuntimeError("Baseline did not return to #4")
        print("PASS: invalid key also restored Verification to #4.", flush=True)


if __name__ == "__main__":
    main()
