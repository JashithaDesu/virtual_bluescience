import argparse
import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

from pipeline.common import db
from pipeline.monitor.structured_log import event

COMPANIES = ["ocean-harvesting", "addsecure", "malvacom"]
CACHE = Path(__file__).resolve().parent / ".cache"


def versions():
    rows = (
        db.client().table("company_private")
        .select("company_id,updated_at")
        .in_("company_id", COMPANIES).execute().data
    )
    result = {row["company_id"]: row["updated_at"] for row in rows}
    if set(COMPANIES) - set(result) or any(v is None for v in result.values()):
        raise RuntimeError("Missing company private-state timestamps")
    return result


def start_job(company, version):
    CACHE.mkdir(exist_ok=True)
    token = uuid4().hex
    report = CACHE / f"watch_report_{token}.json"
    diagnostics = CACHE / f"watch_run_{token}.log"
    started = time.monotonic()
    with diagnostics.open("w", encoding="utf-8") as output:
        process = subprocess.Popen(
            [
                sys.executable, "-u", "-m", "pipeline.monitor.rerank",
                company, "--report-file", str(report),
            ],
            stdout=output,
            stderr=subprocess.STDOUT,
        )
    return {
        "process": process, "company": company, "version": version,
        "started": started, "report": report, "diagnostics": diagnostics,
    }


def finish_job(job, timed_out=False):
    code = job["process"].returncode
    fields = {
        "company": job["company"],
        "duration_ms": round((time.monotonic() - job["started"]) * 1000),
        "exit_code": code,
    }
    try:
        if timed_out or code != 0:
            raise RuntimeError("timeout" if timed_out else "subprocess_failed")
        report = json.loads(job["report"].read_text(encoding="utf-8"))
        if (
            report.get("company") != job["company"]
            or report.get("reason") not in {"llm", "template"}
            or not isinstance(report.get("top_5_ids"), list)
            or not 1 <= len(report["top_5_ids"]) <= 5
            or any(not isinstance(value, str) for value in report["top_5_ids"])
        ):
            raise ValueError("Invalid completion report")
        event(
            "rerank_completed", status="success",
            reason=report["reason"], top_5_ids=report["top_5_ids"],
            **fields,
        )
        job["diagnostics"].unlink(missing_ok=True)
        return True
    except Exception as exc:
        event(
            "rerank_completed", level=logging.ERROR, status="failed",
            reason="unknown", top_5_ids=[],
            error_type=type(exc).__name__,
            timed_out=timed_out,
            diagnostic_log=str(job["diagnostics"]),
            **fields,
        )
        return False
    finally:
        job["report"].unlink(missing_ok=True)
        job["report"].with_suffix(".tmp").unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--initial", action="store_true")
    args = parser.parse_args()

    current = versions()
    event("watcher_connected", companies=COMPANIES)
    if args.check:
        event("watcher_check", status="success", database_writes=False)
        return

    completed = {} if args.initial else dict(current)
    retry_after = {}
    running = None
    event("watcher_started", poll_seconds=5, initial_rerank=args.initial)

    try:
        while True:
            if running is not None:
                code = running["process"].poll()
                timed_out = (
                    code is None
                    and time.monotonic() - running["started"] > 300
                )
                if timed_out:
                    running["process"].kill()
                    running["process"].wait()
                if code is not None or timed_out:
                    company = running["company"]
                    if finish_job(running, timed_out=timed_out):
                        completed[company] = running["version"]
                        retry_after.pop(company, None)
                    else:
                        retry_after[company] = time.monotonic() + 30
                    running = None

            try:
                current = versions()
            except Exception as exc:
                event("timestamp_poll_failed", level=logging.WARNING,
                      error_type=type(exc).__name__)
                time.sleep(5)
                continue

            if running is None:
                for company in COMPANIES:
                    if current[company] == completed.get(company):
                        continue
                    if time.monotonic() < retry_after.get(company, 0):
                        continue
                    try:
                        running = start_job(company, current[company])
                    except Exception as exc:
                        retry_after[company] = time.monotonic() + 30
                        event("rerank_start_failed", level=logging.ERROR,
                              company=company, error_type=type(exc).__name__)
                    break
            time.sleep(5)
    except KeyboardInterrupt:
        event("watcher_stopping")
    finally:
        if running is not None:
            process = running["process"]
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                finish_job(running, timed_out=True)
            else:
                finish_job(running)


if __name__ == "__main__":
    main()
