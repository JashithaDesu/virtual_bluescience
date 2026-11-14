import json
import re
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / ".cache"

TOPICS = {
    "marine": r"\b(marine|maritime|ocean|wave|underwater|offshore)\b",
    "energy": r"\b(energy|electricity|renewable|grid|power plant|wave power)\b",
    "smart_grid": r"\b(smart.grid|power.grid|grid.monitoring)\b",
    "iot": r"\b(iot|internet of things|connected.devices|sensor)\b",
    "cybersecurity": r"\b(cybersecurity|cyber.security|secure.*communication)\b",
    "digitalisation": r"\b(digitalisation|digitalization|software|ai|automation|system integration)\b",
    "software": r"\b(software|programming|backend|firmware)\b",
}
CORE_FIELDS = {"offering", "technology", "application_area", "expertise"}
SECTORS = {
    "biogas": r"\b(biogas|biomethane|manure)\b",
    "forestry": r"\b(forestry|forest|timber|wood.based)\b",
    "buildings": r"\b(buildings|building.energy|heating|hvac|proptech|real estate)\b",
}


def core_text(profile):
    return "\n".join(
        claim["value"] for claim in profile["claims"]
        if claim["field"] in CORE_FIELDS or claim["origin"] == "user"
    ) + "\n" + "\n".join(profile["priorities"])


def effective_domains(profile):
    text = core_text(profile)
    return {
        domain for domain, pattern in TOPICS.items()
        if re.search(pattern, text, re.I)
    }


def cosine(left, right):
    a = np.asarray(left, dtype=float)
    b = np.asarray(right, dtype=float)
    if a.shape != (384,) or b.shape != (384,):
        raise ValueError("Expected 384-dimensional vectors")
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("Non-finite embedding")
    denominator = np.linalg.norm(a) * np.linalg.norm(b)
    if denominator <= 0:
        raise ValueError("Zero embedding")
    return float(np.dot(a, b) / denominator)


def rank_profile(profile, opportunities):
    domains = effective_domains(profile)
    core = core_text(profile)
    # Customer/market evidence may demonstrate a specialised application.
    context = core + "\n" + "\n".join(
        claim["value"] for claim in profile["claims"]
        if claim["field"] in {"customer_group", "market"}
    )
    today = datetime.now().astimezone().date().isoformat()
    ranked = []

    for opportunity in opportunities:
        deadline = opportunity.get("date_or_deadline")
        if deadline and deadline < today:
            continue

        opportunity_domains = set(opportunity["domains"])
        shared = domains & opportunity_domains
        general = "business_development" in opportunity_domains

        # Generic business tags do not establish an energy funding fit.
        if opportunity["type"] == "funding":
            if "energy" in opportunity_domains and "energy" not in domains:
                continue
            if not shared and not general:
                continue

            restriction_text = opportunity["title"] + "\n" + opportunity["summary"]
            unsupported_sector = any(
                re.search(pattern, restriction_text, re.I)
                and not re.search(pattern, context, re.I)
                for pattern in SECTORS.values()
            )
            if unsupported_sector:
                continue
        elif opportunity["type"] in {"testbed", "support"} and not shared:
            continue
        elif not shared and not general:
            continue

        similarity = cosine(profile["embedding"], opportunity["embedding"])
        # Specific topical overlap outranks broad energy-only overlap.
        specific = shared - {"energy"}
        topic_fit = 1.0 if specific else (0.5 if shared else 0.0)
        practical_fit = (
            1.0 if shared and opportunity["type"] in {"testbed", "support"}
            else 0.0
        )
        testing_priority = any(
            re.search(r"\b(testing|testbed|validation|pilot)\b", priority, re.I)
            and not re.search(
                r"\b(not|no|avoid|deprioriti[sz]e)\b", priority, re.I
            )
            for priority in profile["priorities"]
        )
        priority_boost = (
            0.15 if testing_priority
            and opportunity["type"] == "testbed" and shared else 0.0
        )
        score = (
            0.65 * similarity + 0.25 * topic_fit
            + 0.10 * practical_fit + priority_boost
        )

        ranked.append({
            "company_id": profile["id"],
            "opportunity_id": opportunity["id"],
            "score": float(score),
            "cosine": similarity,
            "topic_fit": topic_fit,
            "practical_fit": practical_fit,
            "title": opportunity["title"],
            "type": opportunity["type"],
            "shared_domains": sorted(shared),
        })

    ranked.sort(key=lambda row: (-row["score"], row["opportunity_id"]))
    return [
        {**row, "rank": index}
        for index, row in enumerate(ranked[:10], start=1)
    ]


def main():
    profiles = json.loads(
        (CACHE / "profiles.json").read_text(encoding="utf-8")
    )
    opportunities = json.loads(
        (ROOT / "out/opportunities_embedded.json").read_text(encoding="utf-8")
    )
    matches = []
    for profile in profiles:
        ranked = rank_profile(profile, opportunities)
        matches.extend(ranked)
        print("\n" + profile["id"])
        print("Core domains:", ", ".join(sorted(effective_domains(profile))))
        print("Matches:", len(ranked))
        for row in ranked[:5]:
            print(
                f"  {row['rank']}. score={row['score']:.3f} "
                f"cosine={row['cosine']:.3f} [{row['type']}] {row['title']}"
            )

    (CACHE / "matches_draft.json").write_text(
        json.dumps(matches, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("\nDraft saved locally. No database matches changed.")


if __name__ == "__main__":
    main()
