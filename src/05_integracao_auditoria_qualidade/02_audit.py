"""Persistencia local da trilha de auditoria da Frente 5."""

import json
import os
from pathlib import Path
from typing import Any

from importlib import import_module


validate_interaction = import_module(
    ".00_contract", __package__
).validate_interaction


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_AUDIT_PATH = BASE_DIR / "data" / "processed" / "audit" / "audit_log.jsonl"


class AuditLogger:
    def __init__(self, path: Path | None = None) -> None:
        configured = os.getenv("AUDIT_LOG_PATH", "").strip()
        self.path = Path(path) if path is not None else Path(configured) if configured else DEFAULT_AUDIT_PATH

    def append(self, event: dict[str, Any]) -> None:
        validate_interaction(event)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event, ensure_ascii=False) + "\n")

    def find_by_trace_id(self, trace_id: str) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        with self.path.open(encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue
                event = json.loads(line)
                if event.get("trace_id") == trace_id:
                    return event
        return None
