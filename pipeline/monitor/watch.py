import argparse
import subprocess
import sys
import time
from datetime import datetime

from pipeline.common import db

COMPANIES = ["ocean-harvesting", "addsecure", "malvacom"]


def log(message):
    print(datetime.now().astimezone().isoformat(timespec="seconds"),
          message, flush=True)


def versions():
    rows = (
        db.client().table("company_private")
        .select("company_id,updated_at")
        .in_("company_id", COMPANIES).execute().data
    )
    result = {row["company_id"]: row["updated_at"] for row in rows}
    missing = set(COMPANIES) - set(result)
    if missing:
        raise RuntimeError("Missing company_private rows: " + ", ".join(missing))
    if any(value is None for value in result.values()):
        raise RuntimeError("Missing updated_at timestamp")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--initial", action="store_true",
                        help="Also rerank all three companies on startup")
    args = parser.parse_args()

    current = versions()
    log("Connected; private-state timestamps available for all 3 companies.")
    if args.check:
        log("CHECK ONLY: no reranks or database writes.")
        return

    completed = {} if args.initial else dict(current)
    retry_after = {}
    running = None
    log("Watcher started: polling every 5 seconds. Stop with Ctrl+C.")
    if not args.initial:
        log("Watching future edits; existing state is the startup baseline.")

    try:
        while True:
            if running is not None:
                process, company_id, version, started = running
                code = process.poll()
                if code is not None:
                    if code == 0:
                        completed[company_id] = version
                        retry_after.pop(company_id, None)
                        log(f"Published {company_id}; feed can refresh now.")
                    else:
                        retry_after[company_id] = time.monotonic() + 30
                        log(f"Rerank failed for {company_id}; retry after 30s.")
                    running = None
                elif time.monotonic() - started > 300:
                    process.kill()
                    process.wait()
                    retry_after[company_id] = time.monotonic() + 30
                    log(f"Rerank timed out for {company_id}; retry after 30s.")
                    running = None

            try:
                current = versions()
            except Exception as exc:
                log("Timestamp poll failed: " + type(exc).__name__)
                time.sleep(5)
                continue

            if running is None:
                for company_id in COMPANIES:
                    if current[company_id] == completed.get(company_id):
                        continue
                    if time.monotonic() < retry_after.get(company_id, 0):
                        continue
                    log("Detected pending state: " + company_id)
                    process = subprocess.Popen([
                        sys.executable, "-u", "-m",
                        "pipeline.monitor.rerank", company_id,
                    ])
                    running = (
                        process, company_id, current[company_id],
                        time.monotonic(),
                    )
                    break
            time.sleep(5)
    except KeyboardInterrupt:
        log("Stopping watcher.")
    finally:
        if running is not None and running[0].poll() is None:
            running[0].terminate()
            try:
                running[0].wait(timeout=5)
            except subprocess.TimeoutExpired:
                running[0].kill()
                running[0].wait()


if __name__ == "__main__":
    main()
