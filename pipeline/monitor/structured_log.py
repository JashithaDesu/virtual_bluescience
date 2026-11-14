"""JSON logging for monitoring; never include prompts, claims or credentials."""
import json
import logging
import sys
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "time": datetime.fromtimestamp(
                record.created, timezone.utc
            ).isoformat(),
            "level": record.levelname,
            **getattr(record, "payload", {}),
        }
        return json.dumps(payload, ensure_ascii=False)


logger = logging.getLogger("vsp.monitor")
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)


def event(name, *, level=logging.INFO, **fields):
    logger.log(level, name, extra={"payload": {"event": name, **fields}})
