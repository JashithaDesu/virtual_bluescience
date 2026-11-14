import json
import os
from pathlib import Path

import numpy as np
import torch
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

from pipeline.common import db

COMPANIES = ["ocean-harvesting", "addsecure", "malvacom"]
FIELDS = {
    "offering", "technology", "expertise", "application_area", "market",
    "customer_group", "domain", "relevant_topic", "priority", "collaboration",
}
CACHE = Path(__file__).resolve().parent / ".cache"


def load_profile(company_id, private_override=None):
    client = db.client()
    companies = (
        client.table("companies").select("id,name,domains")
        .eq("id", company_id).execute().data
    )
    if len(companies) != 1:
        raise ValueError("Company missing: " + company_id)

    private = (db.private_state(company_id)
               if private_override is None else private_override)
    rejected = set(private.get("rejected_claim_ids") or [])
    claims = (
        client.table("profile_claims")
        .select("id,field,value,type,origin,source_url,is_simulated,confidence")
        .eq("company_id", company_id)
        .neq("type", "missing")
        .execute().data
    )
    accepted = [
        claim for claim in claims
        if claim["id"] not in rejected
        and not (
            claim["origin"] == "agent"
            and claim["field"] == "priority"
            and claim.get("confidence") == "low"
        )
        and str(claim.get("value") or "").strip()
        and (claim["field"] in FIELDS or claim["origin"] == "user")
    ]
    if not accepted:
        raise ValueError("No accepted matching claims: " + company_id)

    return {
        **companies[0],
        "claims": accepted,
        "priorities": [
            value.strip() for value in (private.get("priorities") or [])
            if isinstance(value, str) and value.strip()
        ],
        "private_updated_at": private.get("updated_at"),
        "excluded_rejected_count": sum(
            claim["id"] in rejected for claim in claims
        ),
    }


def embed_profile(model, profile):
    # Encode claims separately so a long profile is not silently truncated.
    texts = [
        f"{claim['field']}: {claim['value']}"
        for claim in profile["claims"]
    ]
    weights = [1.0] * len(texts)
    for priority in profile["priorities"]:
        texts.append("Current company priority: " + priority)
        weights.append(2.0)

    vectors = model.encode(texts, normalize_embeddings=True)
    vector = np.average(vectors, axis=0, weights=weights)
    norm = np.linalg.norm(vector)
    if not np.isfinite(vector).all() or norm <= 0:
        raise ValueError("Invalid company embedding")
    vector = vector / norm
    if vector.shape != (384,):
        raise ValueError("Expected a 384-dimensional embedding")
    return vector.tolist()


def main():
    load_dotenv()
    name = os.getenv("EMBED_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer(name, device=device)
    profiles = []

    for company_id in COMPANIES:
        profile = load_profile(company_id)
        profile["embedding"] = embed_profile(model, profile)
        profile["embedding_model"] = name

        updated = (
            db.client().table("companies")
            .update({"profile_embedding": profile["embedding"]})
            .eq("id", company_id).execute().data
        )
        if len(updated) != 1:
            raise RuntimeError("Company embedding update failed: " + company_id)

        saved = (
            db.client().table("companies").select("id,profile_embedding")
            .eq("id", company_id).execute().data[0]["profile_embedding"]
        )
        if isinstance(saved, str):
            saved = json.loads(saved)
        if len(saved) != 384 or not np.allclose(
            saved, profile["embedding"], atol=1e-6
        ):
            raise RuntimeError("Embedding verification failed: " + company_id)

        profiles.append(profile)
        print(
            company_id,
            "| accepted claims:", len(profile["claims"]),
            "| priorities:", len(profile["priorities"]),
            "| rejected excluded:", profile["excluded_rejected_count"],
            "| verified: 384 dimensions",
        )
        print("  Public company domains:", profile["domains"])

    CACHE.mkdir(exist_ok=True)
    (CACHE / "profiles.json").write_text(
        json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Private matching inputs saved in ignored .cache/profiles.json")


if __name__ == "__main__":
    main()
