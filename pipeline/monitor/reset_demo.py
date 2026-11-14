"""Reset the exact OHT demo priority; never modify agent claims."""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone

from pipeline.common import db
from pipeline.monitor.embed_companies import CACHE

CID = "ocean-harvesting"
PRIORITY = "Testing and validating our technology with a potential customer is a priority"
TARGET = "Verification of Innovations with Customers"


def normalise(value):
    return " ".join((value or "").split()).casefold()


def top_five(label):
    client = db.client()
    rows = (
        client.table("matches").select("opportunity_id,rank,score")
        .eq("company_id", CID).order("rank").execute().data
    )
    titles = {
        row["id"]: row["title"]
        for row in client.table("opportunities").select("id,title").execute().data
    }
    print("\n" + label, flush=True)
    for row in rows[:5]:
        print(
            f"{row['rank']}. {titles.get(row['opportunity_id'], 'UNKNOWN')} "
            f"| score={row['score']:.4f}",
            flush=True,
        )
    return rows, titles


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                        help="Remove exact demo input and rerank OHT")
    args = parser.parse_args()
    client = db.client()

    claims = (
        client.table("profile_claims").select("*")
        .eq("company_id", CID).eq("origin", "user").execute().data
    )
    selected = [
        row for row in claims
        if normalise(row.get("value")) == normalise(PRIORITY)
    ]
    private = db.private_state(CID)
    priorities = private.get("priorities") or []
    remaining = [
        value for value in priorities
        if normalise(value) != normalise(PRIORITY)
    ]
    before, _ = top_five("BEFORE RESET")
    print("\nExact matching user-origin claims:", len(selected))
    print("Exact matching private priorities:", len(priorities) - len(remaining))
    print("Agent claims will not be modified.")

    if not args.apply:
        print("\nPREVIEW ONLY: no writes or rerank.")
        print("Apply with: python -m pipeline.monitor.reset_demo --apply")
        return

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    CACHE.mkdir(exist_ok=True)
    backup = CACHE / f"demo_reset_backup_{stamp}.json"
    backup.write_text(
        json.dumps({
            "user_claims_to_remove": selected,
            "private_state_before": private,
            "matches_before": before,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("Local backup:", backup, flush=True)

    if remaining != priorities:
        if not private.get("updated_at"):
            raise RuntimeError("Missing updated_at; reset stopped")
        updated = (
            client.table("company_private").update({"priorities": remaining})
            .eq("company_id", CID)
            .eq("updated_at", private["updated_at"]).execute().data
        )
        if len(updated) != 1:
            raise RuntimeError("Concurrent private edit; reset stopped")

    if selected:
        (
            client.table("profile_claims").delete()
            .eq("company_id", CID).eq("origin", "user")
            .in_("id", [row["id"] for row in selected]).execute()
        )

    leftovers = (
        client.table("profile_claims").select("value")
        .eq("company_id", CID).eq("origin", "user").execute().data
    )
    if any(normalise(row["value"]) == normalise(PRIORITY) for row in leftovers):
        raise RuntimeError("User priority claim removal verification failed")
    if any(
        normalise(value) == normalise(PRIORITY)
        for value in (db.private_state(CID).get("priorities") or [])
    ):
        raise RuntimeError("Private priority removal verification failed")

    subprocess.run(
        [sys.executable, "-u", "-m", "pipeline.monitor.rerank", CID],
        check=True,
    )
    after, titles = top_five("AFTER RESET")
    targets = [row for row in after if titles[row["opportunity_id"]] == TARGET]
    if len(targets) != 1 or targets[0]["rank"] != 4:
        raise RuntimeError(
            "Reset inputs removed, but Verification is not uniquely rank 4. "
            "Do not force ranks; report this output."
        )
    print("\nPASS: demo priority removed; Verification restored to #4.")


if __name__ == "__main__":
    main()
