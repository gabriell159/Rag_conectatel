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
    for item in event["citations"]:
        if not isinstance(item, dict):
            raise ValueError("cada citacao deve ser um objeto")
        required_citation = {"source_file", "doc_family_id", "version_ordinal", "status"}
        missing_citation = required_citation - item.keys()
        if missing_citation:
            raise ValueError("citacao incompleta: " + ", ".join(sorted(missing_citation)))
        if item["status"] != "vigente":
            raise ValueError("Somente documentos vigentes podem ser citados")
        if not item.get("source_file") or not item.get("chunk_id"):
            raise ValueError("citacao deve informar fonte e chunk")
        if not isinstance(item.get("version_ordinal"), int):
            raise ValueError("version_ordinal deve ser inteiro")
    if event["decision"] == "ANSWER" and not event["citations"]:
        raise ValueError("ANSWER precisa ter ao menos uma citacao")
    if event["decision"] == "NO_ANSWER" and event["citations"]:
        raise ValueError("NO_ANSWER nao pode ter citacoes")
    if event["decision"] == "ESCALATE" and not event.get("handoff"):
        raise ValueError("ESCALATE precisa ter handoff")
    if event["decision"] == "ESCALATE":
        required_handoff = {"reason", "summary", "requested_action", "priority"}
        missing_handoff = required_handoff - event["handoff"].keys()
        if missing_handoff:
            raise ValueError("handoff incompleto: " + ", ".join(sorted(missing_handoff)))
    if event.get("handoff") is not None and not isinstance(event["handoff"], dict):
        raise ValueError("handoff deve ser um objeto ou null")


def citation(
    source_file: str,
    doc_family_id: str,
    version_ordinal: int,
    status: str = "vigente",
    chunk_id: str = "mock-chunk-001",
) -> dict[str, Any]:
    if status != "vigente":
        raise ValueError("Somente documentos vigentes podem ser citados")
    return {
        "source_file": source_file,
        "chunk_id": chunk_id,
        "doc_family_id": doc_family_id,
        "version_ordinal": version_ordinal,
        "status": status,
    }
