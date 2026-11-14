import argparse
import json
import os
from datetime import datetime, timezone

import numpy as np
import torch
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

from pipeline.common import db
from pipeline.monitor.embed_companies import CACHE, load_profile, embed_profile
from pipeline.monitor.explain import explain_profile
from pipeline.monitor.match import rank_profile
from pipeline.monitor.publish_matches import publish, signature

COMPANIES = ["ocean-harvesting", "addsecure", "malvacom"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("company_id", choices=COMPANIES)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_dotenv()
    name = os.getenv("EMBED_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer(name, device=device)

    profile = load_profile(args.company_id)
    profile["embedding"] = embed_profile(model, profile)

    # Limit to this pipeline's opportunities, excluding unrelated seed rows.
    local = json.loads(
        (CACHE.parent / "out/opportunities_embedded.json")
        .read_text(encoding="utf-8")
    )
    opportunities = (
        db.client().table("opportunities").select("*")
        .in_("id", [row["id"] for row in local])
        .execute().data
    )
    if not opportunities:
        raise RuntimeError("No pipeline opportunities found in Supabase")
    for item in opportunities:
        if isinstance(item["embedding"], str):
            item["embedding"] = json.loads(item["embedding"])
        if item["embedding"] is None:
            raise RuntimeError("Missing opportunity embedding: " + item["title"])

    ranked = rank_profile(profile, opportunities)
    if not ranked:
        raise RuntimeError("No relevant opportunities; existing matches preserved")

    print("Generating batched reasons for", args.company_id, flush=True)
    rows = explain_profile(profile, ranked, opportunities)

    # Detect edits made while embeddings/reasons were being generated.
    if signature(load_profile(args.company_id)) != signature(profile):
        raise RuntimeError("Profile changed during rerank; run again")

    titles = {item["id"]: item["title"] for item in opportunities}
    for row in rows:
        print(
            f"{row['rank']}. {row['score']:.3f} "
            f"{titles[row['opportunity_id']]}"
        )

    if args.dry_run:
        print("DRY RUN: no database writes.")
        return

    previous = (
        db.client().table("matches").select("*")
        .eq("company_id", args.company_id).execute().data
    )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    (CACHE / f"rerank_backup_{args.company_id}_{stamp}.json").write_text(
        json.dumps(previous, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    updated = (
        db.client().table("companies")
        .update({"profile_embedding": profile["embedding"]})
        .eq("id", args.company_id).execute().data
    )
    if len(updated) != 1:
        raise RuntimeError("Company embedding update failed")
    stored = (
        db.client().table("companies").select("profile_embedding")
        .eq("id", args.company_id).execute().data[0]["profile_embedding"]
    )
    if isinstance(stored, str):
        stored = json.loads(stored)
    if not np.allclose(stored, profile["embedding"], atol=1e-6):
        raise RuntimeError("Company embedding verification failed")

    saved = publish(args.company_id, rows)
    print("Published and verified:", len(saved), "matches.")


if __name__ == "__main__":
    main()
