import io
import json
import logging
import sys
import tempfile
import time
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.monitor import explain_fallback as fallback
from pipeline.monitor.structured_log import JsonFormatter, logger
from pipeline.monitor.watch import finish_job


@contextmanager
def capture_logs():
    output = io.StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(JsonFormatter())
    previous = logger.handlers[:]
    logger.handlers = [handler]
    try:
        yield output
    finally:
        logger.handlers = previous


class LoggingTests(unittest.TestCase):
    def test_template_mode_and_error_do_not_log_private_text(self):
        payload = json.dumps({
            "accepted_claims": [{
                "id": "claim-1", "field": "offering",
                "value": "PRIVATE_SENTINEL", "type": "stated",
                "origin": "agent",
            }],
            "matches": [{
                "opportunity": {
                    "id": "opportunity-1", "title": "Testing",
                    "summary": "Technical testing", "type": "testbed",
                },
            }],
        })
        with capture_logs() as output:
            with patch.object(
                fallback, "llm_chat_json",
                side_effect=RuntimeError("PRIVATE_SENTINEL"),
            ):
                result = fallback.chat_json("system", payload)
        self.assertEqual(fallback.EXPLANATION_MODE.get(), "template")
        self.assertEqual(result["items"][0]["claim_ids"], ["claim-1"])
        record = json.loads(output.getvalue())
        self.assertEqual(record["reason"], "template")
        self.assertEqual(record["error_type"], "RuntimeError")
        self.assertNotIn("PRIVATE_SENTINEL", output.getvalue())

    def test_success_resets_mode_to_llm(self):
        fallback.EXPLANATION_MODE.set("template")
        with patch.object(
            fallback, "llm_chat_json", return_value={"items": []}
        ) as call:
            fallback.chat_json("system", "{}")
        self.assertEqual(fallback.EXPLANATION_MODE.get(), "llm")
        self.assertEqual(call.call_args.kwargs["retries"], 1)

    def test_success_emits_one_completion_for_each_mode(self):
        for mode in ("llm", "template"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                report = folder / "report.json"
                diagnostics = folder / "diagnostics.log"
                diagnostics.write_text("PRIVATE_SENTINEL", encoding="utf-8")
                ids = ["opportunity-1", "opportunity-2"]
                report.write_text(json.dumps({
                    "company": "ocean-harvesting",
                    "reason": mode,
                    "top_5_ids": ids,
                }), encoding="utf-8")
                job = {
                    "process": SimpleNamespace(returncode=0),
                    "company": "ocean-harvesting",
                    "started": time.monotonic() - 1,
                    "report": report,
                    "diagnostics": diagnostics,
                }
                with capture_logs() as output:
                    self.assertTrue(finish_job(job))
                records = output.getvalue().splitlines()
                self.assertEqual(len(records), 1)
                record = json.loads(records[0])
                self.assertEqual(record["event"], "rerank_completed")
                self.assertEqual(record["status"], "success")
                self.assertEqual(record["reason"], mode)
                self.assertEqual(record["top_5_ids"], ids)
                self.assertGreaterEqual(record["duration_ms"], 1000)
                self.assertIn("time", record)
                self.assertNotIn("PRIVATE_SENTINEL", records[0])
                self.assertFalse(report.exists())
                self.assertFalse(diagnostics.exists())

    def test_failed_process_logs_once_and_retains_local_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            diagnostics = folder / "diagnostics.log"
            diagnostics.write_text("PRIVATE_SENTINEL", encoding="utf-8")
            job = {
                "process": SimpleNamespace(returncode=1),
                "company": "ocean-harvesting",
                "started": time.monotonic(),
                "report": folder / "missing.json",
                "diagnostics": diagnostics,
            }
            with capture_logs() as output:
                self.assertFalse(finish_job(job))
            lines = output.getvalue().splitlines()
            self.assertEqual(len(lines), 1)
            record = json.loads(lines[0])
            self.assertEqual(record["status"], "failed")
            self.assertEqual(record["reason"], "unknown")
            self.assertTrue(diagnostics.exists())
            self.assertNotIn("PRIVATE_SENTINEL", lines[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
