"""Fluxo simulado para validar o contrato antes da integracao real."""

import time
from datetime import datetime, timezone
from typing import Any

from importlib import import_module


AuditLogger = import_module(".02_audit", __package__).AuditLogger
citation = import_module(".00_contract", __package__).citation
new_trace_id = import_module(".01_trace", __package__).new_trace_id


def run_mock(question: str, audit_path=None) -> dict[str, Any]:
    started = time.perf_counter()
    normalized = question.lower()

    if "reembolso" in normalized:
        decision = "ANSWER"
        answer = "A politica vigente permite solicitar reembolso em ate 7 dias corridos, conforme a politica citada."
        citations = [
            citation(
                "corpus/politicas/politica_reembolso_v2.md",
                "politica-reembolso",
                2,
            )
        ]
        handoff = None
        reason = None
    elif any(term in normalized for term in ("sinal", "cobertura", "tecnico", "falha")):
        decision = "ESCALATE"
        answer = "Vou encaminhar seu caso para atendimento humano."
        citations = []
        handoff = {
            "reason": "triagem_tecnica",
            "summary": question,
            "requested_action": "avaliar e resolver o problema tecnico informado",
            "priority": "normal",
        }
        reason = "caso tecnico requer atendimento humano"
    else:
        decision = "NO_ANSWER"
        answer = "Nao sei responder com base no corpus oficial disponivel."
        citations = []
        handoff = None
        reason = "evidencia insuficiente no corpus"

    event = {
        "trace_id": new_trace_id(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "duration_ms": int((time.perf_counter() - started) * 1000),
        "question": question,
        "decision": decision,
        "answer": answer,
        "citations": citations,
        "handoff": handoff,
        "guardrail": reason,
        "component_versions": {"pipeline": "mock-frente5-v1"},
    }
    AuditLogger(audit_path).append(event)
    return event
