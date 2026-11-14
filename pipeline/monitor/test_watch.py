import json
import os
import time
from datetime import datetime, timezone

import torch
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

from pipeline.common import db
from pipeline.monitor.embed_companies import CACHE, load_profile, embed_profile
from pipeline.monitor.match import rank_profile

CID = "ocean-harvesting"
MARKER = "SIMULATED watcher check: testing is a priority"


def wait_for_score(opportunity_id, expected, label):
    started = time.monotonic()
    while time.monotonic() - started < 240:
        rows = (
            db.client().table("matches").select("score")
            .eq("company_id", CID)
            .eq("opportunity_id", opportunity_id).execute().data
        )
        if rows and abs(rows[0]["score"] - expected) < 0.00001:
            print(f"PASS: {label} after {time.monotonic() - started:.1f}s",
                  flush=True)
            return
        time.sleep(5)
    raise RuntimeError("Timed out waiting for " + label)


def main():
    load_dotenv()
    original = db.private_state(CID)
    if not original.get("updated_at"):
        raise RuntimeError("Missing private-state timestamp")
    priorities = original.get("priorities") or []
    if MARKER in priorities:
        raise RuntimeError("Test marker already present; report before proceeding")

    local = json.loads(
        (CACHE.parent / "out/opportunities_embedded.json")
        .read_text(encoding="utf-8")
    )
    opportunities = (
        db.client().table("opportunities").select("*")
        .in_("id", [row["id"] for row in local]).execute().data
    )
    for item in opportunities:
        if isinstance(item["embedding"], str):
            item["embedding"] = json.loads(item["embedding"])

    name = os.getenv("EMBED_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer(name, device=device)

    baseline = load_profile(CID, private_override=original)
    baseline["embedding"] = embed_profile(model, baseline)
    before = rank_profile(baseline, opportunities)

    edited_state = {**original, "priorities": priorities + [MARKER]}
    edited = load_profile(CID, private_override=edited_state)
    edited["embedding"] = embed_profile(model, edited)
    after = rank_profile(edited, opportunities)

    target = next(row for row in after if row["type"] == "testbed")
    baseline_target = next(
        row for row in before
        if row["opportunity_id"] == target["opportunity_id"]
    )
    if abs(target["score"] - baseline_target["score"]) < 0.0001:
        raise RuntimeError("Test does not produce a measurable score change")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = CACHE / f"watch_test_private_backup_{stamp}.json"
    backup.write_text(
        json.dumps(original, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("SIMULATED LIVE TEST; original private state backed up locally.",
          flush=True)

    updated = (
        db.client().table("company_private")
        .update({"priorities": edited_state["priorities"]})
        .eq("company_id", CID)
        .eq("updated_at", original["updated_at"]).execute().data
    )
    if len(updated) != 1:
        raise RuntimeError("State changed before test; no test edit applied")
    test_version = updated[0]["updated_at"]

    try:
        wait_for_score(target["opportunity_id"], target["score"],
                       "watcher published simulated priority")
    finally:
        # Timestamp condition protects any concurrent user edits.
        restored = (
            db.client().table("company_private")
            .update({"priorities": priorities})
            .eq("company_id", CID)
            .eq("updated_at", test_version).execute().data
        )
        if len(restored) != 1:
            raise RuntimeError(
                "Concurrent edit detected: automatic restoration stopped. "
                "Report this output; do not overwrite user changes."
            )
        print("Original priorities restored; waiting for watcher.", flush=True)

    wait_for_score(target["opportunity_id"], baseline_target["score"],
                   "watcher restored baseline scoring")
    assert db.private_state(CID)["priorities"] == priorities
    print("PASS: automatic edit -> rerank -> restore -> rerank.", flush=True)


if __name__ == "__main__":
    main()
