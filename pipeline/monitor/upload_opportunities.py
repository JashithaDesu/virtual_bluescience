import json
import math
from importlib.metadata import version
from pathlib import Path

from pipeline.common import db

ROOT = Path(__file__).resolve().parent
COMPANIES = ["ocean-harvesting", "addsecure", "malvacom"]


def main():
    # Record the exact installed Supabase version for reproducibility.
    requirements = ROOT / "requirements.txt"
    lines = requirements.read_text(encoding="utf-8").splitlines()
    lines = [line for line in lines if not line.startswith("supabase")]
    lines.append("supabase==" + version("supabase"))
    requirements.write_text("\n".join(lines) + "\n", encoding="utf-8")

    client = db.client()
    companies = (
        client.table("companies").select("id")
        .in_("id", COMPANIES).execute().data
    )
    if {row["id"] for row in companies} != set(COMPANIES):
        raise RuntimeError("Not all three demo companies are visible; upload stopped.")

    rows = json.loads(
        (ROOT / "out/opportunities_embedded.json").read_text(encoding="utf-8")
    )
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate opportunity IDs")

    for row in rows:
        vector = row["embedding"]
        if len(vector) != 384 or not all(math.isfinite(x) for x in vector):
            raise ValueError("Invalid embedding: " + row["title"])
        if not row["next_step"].strip():
            raise ValueError("Missing next step: " + row["title"])
        if row["type"] == "funding" and row["eligibility"] != "potential":
            raise ValueError("Funding must be labelled potential")

    print("Upserted:", db.upsert_opportunities(rows))
    saved = (
        client.table("opportunities")
        .select("id,type,title")
        .in_("id", [row["id"] for row in rows])
        .execute().data
    )
    if {row["id"] for row in saved} != {row["id"] for row in rows}:
        raise RuntimeError("Upload verification failed")

    print("Verified in Supabase:", len(saved))
    for kind in ("funding", "event", "testbed", "support"):
        print(kind + ":", sum(row["type"] == kind for row in saved))


if __name__ == "__main__":
    main()
