import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.common import db
from pipeline.monitor.watch import start_job, finish_job


def main():
    targets = (
        db.client().table("opportunities").select("id")
        .eq("title", "Verification of Innovations with Customers")
        .execute().data
    )
    if len(targets) != 1:
        raise RuntimeError("Expected one Verification opportunity")
    target = targets[0]["id"]

    def baseline_rank():
        rows = (
            db.client().table("matches").select("rank")
            .eq("company_id", "ocean-harvesting")
            .eq("opportunity_id", target).execute().data
        )
        return rows[0]["rank"] if len(rows) == 1 else None

    if baseline_rank() != 4:
        raise RuntimeError("Expected baseline #4; no test started")

    results = []
    for expected in ("template", "llm"):
        if expected == "template":
            with patch.dict(os.environ, {
                "LLM_API_KEY": "invalid", "P2_EXPLAIN_NO_CACHE": "1",
            }):
                job = start_job("ocean-harvesting", "logging-test")
        else:
            with patch.dict(os.environ):
                os.environ.pop("P2_EXPLAIN_NO_CACHE", None)
                job = start_job("ocean-harvesting", "logging-test")

        try:
            job["process"].wait(timeout=240)
        except TimeoutError:
            job["process"].kill()
            job["process"].wait()
            finish_job(job, timed_out=True)
            raise
        except Exception:
            if job["process"].poll() is None:
                job["process"].kill()
                job["process"].wait()
            finish_job(job, timed_out=True)
            raise

        report = (
            json.loads(job["report"].read_text(encoding="utf-8"))
            if job["report"].exists() else {}
        )
        duration = round((time.monotonic() - job["started"]) * 1000)
        success = finish_job(job)
        results.append({
            "expected_reason": expected,
            "observed_reason": report.get("reason"),
            "duration_ms": duration,
            "company": report.get("company"),
            "top_5_ids": report.get("top_5_ids"),
            "success": success,
        })

        output = Path("eval/results/structured_logging.json")
        output.parent.mkdir(exist_ok=True)
        output.write_text(json.dumps({
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "runs": results,
            "llm_mode_includes_cached_llm_output": True,
        }, indent=2), encoding="utf-8")

        if not success or report.get("reason") != expected:
            raise RuntimeError(
                "Unexpected completion mode; report output without retrying."
            )
        if baseline_rank() != 4:
            raise RuntimeError("Baseline changed unexpectedly")

    if results[0]["top_5_ids"] != results[1]["top_5_ids"]:
        raise RuntimeError("Top-five IDs differed between explanation modes")
    print("PASS: live template and LLM-mode completion logs; same top five; baseline #4.")


if __name__ == "__main__":
    main()
