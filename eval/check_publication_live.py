import json
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.common import db

CID = "ocean-harvesting"


def main():
    client = db.client()
    targets = (
        client.table("opportunities").select("id")
        .eq("title", "Verification of Innovations with Customers")
        .execute().data
    )
    if len(targets) != 1:
        raise RuntimeError("Expected exactly one Verification opportunity")
    target = targets[0]["id"]

    def verification_rank():
        rows = (
            client.table("matches").select("rank")
            .eq("company_id", CID).eq("opportunity_id", target)
            .execute().data
        )
        return rows[0]["rank"] if len(rows) == 1 else None

    if verification_rank() != 4:
        raise RuntimeError("Expected baseline rank #4; stop and report")

    stop = threading.Event()
    counts = []
    read_errors = []

    def observe():
        while not stop.is_set():
            try:
                rows = (
                    client.table("matches").select("opportunity_id,rank")
                    .eq("company_id", CID).execute().data
                )
                counts.append(len(rows))
            except Exception as exc:
                read_errors.append(type(exc).__name__)
            stop.wait(0.5)

    observer = threading.Thread(target=observe, daemon=True)
    observer.start()
    runs = []
    try:
        for number in range(1, 11):
            print(f"\n=== LIVE RERANK {number}/10 ===", flush=True)
            started = time.monotonic()
            result = subprocess.run(
                [sys.executable, "-u", "-m",
                 "pipeline.monitor.rerank", CID],
                timeout=240,
            )
            runs.append({
                "run": number,
                "duration_seconds": round(time.monotonic() - started, 3),
                "exit_code": result.returncode,
            })
            if result.returncode:
                raise RuntimeError(f"Rerank {number} failed")
    finally:
        stop.set()
        observer.join(timeout=35)
        report = {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "company_id": CID,
            "runs": runs,
            "database_samples": len(counts),
            "minimum_observed_rows": min(counts) if counts else None,
            "empty_reads": counts.count(0),
            "read_errors": read_errors,
            "browser_observation": "not recorded by this script",
            "scope": "single writer; sampled reads, not transactional isolation",
        }
        output = Path(__file__).resolve().parent / "results"
        output.mkdir(exist_ok=True)
        (output / "atomic_publication.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print("\n" + json.dumps(report, indent=2), flush=True)

    if len(runs) != 10 or not counts or 0 in counts or read_errors:
        raise RuntimeError("Live publication check failed or was incomplete")
    if verification_rank() != 4:
        raise RuntimeError("Verification baseline changed")
    print("\nPASS: 10 reranks; no sampled empty reads; Verification remains #4.")


if __name__ == "__main__":
    main()
