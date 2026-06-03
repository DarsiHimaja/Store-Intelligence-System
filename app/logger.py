import logging
import json
import uuid
from datetime import datetime, timezone


class StructuredFormatter(logging.Formatter):
    def format(self, record):
        log = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        for key in ("trace_id", "store_id", "endpoint", "latency_ms",
                    "event_count", "status_code"):
            if hasattr(record, key):
                log[key] = getattr(record, key)
        return json.dumps(log)


handler = logging.StreamHandler()
handler.setFormatter(StructuredFormatter())

logger = logging.getLogger("store_intelligence")
logger.setLevel(logging.INFO)
logger.addHandler(handler)
logger.propagate = False


def new_trace_id() -> str:
    return uuid.uuid4().hex[:12]
