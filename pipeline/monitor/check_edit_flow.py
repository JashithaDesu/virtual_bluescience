import json
import os

import numpy as np
import torch
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

from pipeline.common import db
from pipeline.monitor.embed_companies import CACHE, load_profile, embed_profile
from pipeline.monitor.match import rank_profile


def main():
    load_dotenv()
    company_id = "ocean-harvesting"
    original = load_profile(company_id)
    original_private = db.private_state(company_id)
    original_matches = (
        db.client().table("matches").select("*")
        .eq("company_id", company_id).order("opportunity_id").execute().data
    )

    claim = next(
        c for c in original["claims"]
        if c["field"] == "offering" and c["origin"] == "agent"
    )
    simulated_private = {
        **original_private,
        "rejected_claim_ids": list(dict.fromkeys(
            (original_private.get("rejected_claim_ids") or []) + [claim["id"]]
        )),
        "priorities": (
            original_private.get("priorities") or []
        ) + ["testing is a priority"],
    }
    edited = load_profile(company_id, private_override=simulated_private)
    assert claim["id"] not in {c["id"] for c in edited["claims"]}
    assert len(edited["claims"]) == len(original["claims"]) - 1
    assert "testing is a priority" in edited["priorities"]

    name = os.getenv("EMBED_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer(name, device=device)
    original["embedding"] = embed_profile(model, original)
    edited["embedding"] = embed_profile(model, edited)
    assert not np.allclose(original["embedding"], edited["embedding"])

    opportunities = json.loads(
        (CACHE.parent / "out/opportunities_embedded.json")
        .read_text(encoding="utf-8")
    )
    before = rank_profile(original, opportunities)
    after = rank_profile(edited, opportunities)
    assert before and after

    # Isolate the explicit priority adjustment from embedding changes.
    without_priority = {**edited, "priorities": original["priorities"]}
    comparison = {
        row["opportunity_id"]: row
        for row in rank_profile(without_priority, opportunities)
    }
    testbeds = [row for row in after if row["type"] == "testbed"]
    assert testbeds, "Expected a relevant testbed"
    for row in testbeds:
        baseline = comparison[row["opportunity_id"]]
        assert np.isclose(row["score"] - baseline["score"], 0.15)

    assert db.private_state(company_id) == original_private
    current_matches = (
        db.client().table("matches").select("*")
        .eq("company_id", company_id).order("opportunity_id").execute().data
    )
    assert current_matches == original_matches

    print("SIMULATED EDIT CHECK — no database writes")
    print("PASS: rejected claim excluded")
    print("PASS: priority included; company embedding changed")
    print("PASS: relevant testbed receives explicit priority boost")
    print("PASS: live private state and matches unchanged")
    for label, rows in (("BEFORE", before), ("AFTER SIMULATED EDIT", after)):
        print("\n" + label)
        for row in rows[:5]:
            print(f"{row['rank']}. {row['score']:.3f} {row['title']}")


if __name__ == "__main__":
    main()
