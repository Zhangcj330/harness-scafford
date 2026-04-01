from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any


class JsonEventLogger:
    def emit(self, event_type: str, **payload: Any) -> dict[str, Any]:
        event = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event_type": event_type,
            **payload,
        }
        print(json.dumps(event, sort_keys=True))
        return event
