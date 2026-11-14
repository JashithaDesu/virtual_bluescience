import json
import os

import torch
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

from pipeline.common import db
from pipeline.monitor.embed_companies import CACHE, load_profile, embed_profile
from pipeline.monitor.match import rank_profile

CID = "ocean-harvesting"
REJECT = "a91cbd7f-ca01-54f6-b751-ecfe64bf8b27"
PRIORITY = "EU funding to scale up production"


def main():
    load_dotenv()
    claims = (
        db.client().table("profile_claims")
        .select("id,company_id,field,value,type")
        .eq("id", REJECT).execute().data
    )
    if len(claims) != 1 or claims[0]["company_id"] != CID:
        raise SystemExit("Target claim not found on OHT. Stop and report.")
    print("Target claim:", claims[0]["value"], "|", claims[0]["type"])

    original_private = db.private_state(CID)
    original_matches = (
        db.client().table("matches").select("*")
        .eq("company_id", CID).order("opportunity_id").execute().data
    )

    # Reconstruct the baseline if P4 has already applied these exact edits.
    baseline = {
        **original_private,
        "rejected_claim_ids": [
            cid for cid in (original_private.get("rejected_claim_ids") or [])
            if cid != REJECT
        ],
        "priorities": [
            value for value in (original_private.get("priorities") or [])
            if value.strip().casefold() != PRIORITY.casefold()
        ],
    }
    scenarios = [
        ("BEFORE requested edits", baseline),
        ("A: reject oil-and-gas guess", {
            **baseline,
            "rejected_claim_ids": baseline["rejected_claim_ids"] + [REJECT],
        }),
        ("B: add EU scale-up priority only", {
            **baseline,
            "priorities": baseline["priorities"] + [PRIORITY],
        }),
        ("A+B: both edits", {
            **baseline,
            "rejected_claim_ids": baseline["rejected_claim_ids"] + [REJECT],
            "priorities": baseline["priorities"] + [PRIORITY],
        }),
    ]

    name = os.getenv("EMBED_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer(name, device=device)
    opportunities = json.loads(
        (CACHE.parent / "out/opportunities_embedded.json")
        .read_text(encoding="utf-8")
    )
    report = []
    before = None

    print("\nSIMULATED COMPARISON — no database writes")
    for label, private in scenarios:
        profile = load_profile(CID, private_override=private)
        if REJECT in private["rejected_claim_ids"]:
            assert REJECT not in {claim["id"] for claim in profile["claims"]}
        profile["embedding"] = embed_profile(model, profile)
        ranked = rank_profile(profile, opportunities)
        if before is None:
            before = {row["opportunity_id"]: row for row in ranked}

        print("\n" + label)
        for row in ranked[:5]:
            old = before.get(row["opportunity_id"])
            movement = (
                f"previous rank {old['rank']}; "
                f"score change {row['score'] - old['score']:+.4f}"
                if old else "new to ranked results"
            )
            print(f"{row['rank']}. {row['score']:.4f} "
                  f"{row['title']} | {movement}")
        report.append({"scenario": label, "matches": ranked})

    assert db.private_state(CID) == original_private
    current_matches = (
        db.client().table("matches").select("*")
        .eq("company_id", CID).order("opportunity_id").execute().data
    )
    assert current_matches == original_matches
    (CACHE / "oht_demo_edit_comparison.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("\nPASS: live private state and matches unchanged.")
    print("No P1 scripts run; frozen profile claims unchanged.")


if __name__ == "__main__":
    main()
