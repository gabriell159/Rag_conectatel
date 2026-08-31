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
        self.s3_bucket = os.getenv("AUDIT_S3_BUCKET", "").strip()
        self.s3_prefix = os.getenv("AUDIT_S3_PREFIX", "conectatel/audit").strip().strip("/")

    def append(self, event: dict[str, Any]) -> None:
        validate_interaction(event)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event, ensure_ascii=False) + "\n")
        if self.s3_bucket:
            self._append_s3(event)

    def _append_s3(self, event: dict[str, Any]) -> None:
        """Replica cada evento em S3 quando a persistência compartilhada está configurada."""
        import boto3

        key = f"{self.s3_prefix}/{event['trace_id']}.json"
        # Um AWS_PROFILE vazio não é um perfil válido; nesse caso deixe o
        # boto3 seguir a cadeia padrão (AWS_* ou IAM Role).
        profile = os.getenv("AWS_PROFILE", "").strip()
        if profile:
            session = boto3.Session(
                profile_name=profile,
                region_name=os.getenv("AWS_REGION", "us-east-1"),
            )
        else:
            os.environ.pop("AWS_PROFILE", None)
            session = boto3.Session(region_name=os.getenv("AWS_REGION", "us-east-1"))
        session.client("s3").put_object(
            Bucket=self.s3_bucket,
            Key=key,
            Body=(json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8"),
            ContentType="application/json",
        )

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
