"""Contrato comum das interacoes do Concierge."""

from typing import Any


DECISIONS = {"ANSWER", "NO_ANSWER", "ESCALATE"}


def validate_interaction(event: dict[str, Any]) -> None:
    required = {
        "trace_id", "timestamp", "duration_ms", "question", "decision",
        "answer", "citations", "handoff",
    }
    missing = sorted(required - event.keys())
    if missing:
        raise ValueError(f"Campos obrigatorios ausentes: {', '.join(missing)}")
    if not isinstance(event["trace_id"], str) or not event["trace_id"].strip():
        raise ValueError("trace_id deve ser uma string nao vazia")
    if event["decision"] not in DECISIONS:
        raise ValueError(f"decision invalida: {event['decision']}")
    if not isinstance(event["duration_ms"], int) or event["duration_ms"] < 0:
        raise ValueError("duration_ms deve ser um inteiro nao negativo")
    if not isinstance(event["citations"], list):
        raise ValueError("citations deve ser uma lista")
    if event["decision"] == "ANSWER" and not event["citations"]:
        raise ValueError("ANSWER precisa ter ao menos uma citacao")
    if event["decision"] == "NO_ANSWER" and event["citations"]:
        raise ValueError("NO_ANSWER nao pode ter citacoes")
    if event["decision"] == "ESCALATE" and not event.get("handoff"):
        raise ValueError("ESCALATE precisa ter handoff")


def citation(
    source_file: str,
    doc_family_id: str,
    version_ordinal: int,
    status: str = "vigente",
) -> dict[str, Any]:
    if status != "vigente":
        raise ValueError("Somente documentos vigentes podem ser citados")
    return {
        "source_file": source_file,
        "doc_family_id": doc_family_id,
        "version_ordinal": version_ordinal,
        "status": status,
    }
