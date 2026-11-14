import json
import os

import torch
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

from pipeline.common import db
from pipeline.monitor.embed_companies import CACHE, load_profile, embed_profile
from pipeline.monitor.match import rank_profile

CANDIDATES = [
    "Testing and validating our technology with a potential customer is a priority",
    "Funding early-stage prototype development is a priority",
    "Funding to scale up production and commercialise our energy technology is a priority",
    "Finding investors for an energy technology investment round is a priority",
    "Exploring the German market for our energy technology is a priority",
]


def main():
    load_dotenv()
    name = os.getenv("EMBED_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer(name, device=device)

    local = json.loads(
        (CACHE.parent / "out/opportunities_embedded.json")
        .read_text(encoding="utf-8")
    )
    opportunities = (
        db.client().table("opportunities").select("*")
        .in_("id", [item["id"] for item in local]).execute().data
    )
    for item in opportunities:
        if isinstance(item["embedding"], str):
            item["embedding"] = json.loads(item["embedding"])

    report = []
    print("SIMULATED PRIORITY SEARCH — no database writes or LLM calls.")
    print("Candidate priorities are hypothetical user input, not company facts.")

    for company_id in ("ocean-harvesting", "addsecure"):
        private = db.private_state(company_id)
        baseline = load_profile(company_id, private_override=private)
        baseline["embedding"] = embed_profile(model, baseline)
        before = rank_profile(baseline, opportunities)
        previous = {row["opportunity_id"]: row["rank"] for row in before}

        print("\nCOMPANY:", company_id)
        print("CURRENT RECOMPUTED TOP FIVE:")
        for row in before[:5]:
            print(f"  {row['rank']}. {row['score']:.4f} {row['title']}")

        for priority in CANDIDATES:
            simulated = {
                **private,
                "priorities": (private.get("priorities") or []) + [priority],
            }
            profile = load_profile(company_id, private_override=simulated)
            profile["embedding"] = embed_profile(model, profile)
            after = rank_profile(profile, opportunities)
            promotions = [
                row for row in after[:3]
                if previous.get(row["opportunity_id"], 999) > 3
            ]

            print("\nSIMULATED PRIORITY:", priority)
            for row in after[:3]:
                old = previous.get(row["opportunity_id"])
                print(
                    f"  {row['rank']}. {row['score']:.4f} {row['title']}"
                    f" | previous rank: {old if old else 'outside top ten'}"
                )
            print("ENTERS TOP THREE:", len(promotions))
            report.append({
                "company_id": company_id,
                "simulated_priority": priority,
                "before": before,
                "after": after,
                "enters_top_three": promotions,
            })

        if db.private_state(company_id) != private:
            raise RuntimeError(
                "Private state changed during comparison; rerun with stable inputs."
            )

    (CACHE / "demo_priority_search.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("\nComparison saved in ignored cache. No live data changed.")


if __name__ == "__main__":
    main()
