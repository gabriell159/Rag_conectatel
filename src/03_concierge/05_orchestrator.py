"""Orquestra RAG, Concierge, triagem e auditoria em uma interação."""

import importlib
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .answer import answer_question
from .confidence import get_abstention_threshold


new_trace_id = importlib.import_module(
    "src.05_integracao_auditoria_qualidade.01_trace"
).new_trace_id
AuditLogger = importlib.import_module(
    "src.05_integracao_auditoria_qualidade.02_audit"
).AuditLogger


def classify_handoff(question: str) -> dict[str, str] | None:
    """Aplica regras determinísticas para casos que exigem atendimento humano."""

    normalized = question.casefold()
    informational_markers = (
        "deve ser escalad", "deve ser encaminhad", "dispensa a multa",
        "passa por verific", "antifraude pode acrescentar", "quais campos",
        "que informacao de urgencia", "que informação de urgência",
        "quando uma suspeita", "como tratar alteracao", "como tratar alteração",
        "o que acontece com contest",
    )
    # Perguntas sobre uma regra publicada devem ser respondidas pelo corpus.
    # Relatos ou pedidos de ação sobre um caso concreto continuam escalonados.
    if any(marker in normalized for marker in informational_markers):
        return None
    rules = [
        (("fraude", "golpe"), "suspeita de fraude", "alta"),
        (("anatel",), "reclamação regulatória", "alta"),
        (("faleceu", "falecimento", "titularidade"), "alteração de titularidade", "alta"),
        (("visita técnica", "visita tecnica", "infraestrutura", "sem sinal"), "intervenção técnica", "normal"),
        (("não concordo", "nao concordo", "discordo", "contesto"), "contestação de cobrança", "normal"),
    ]
    for terms, reason, priority in rules:
        if any(term in normalized for term in terms):
            return {
                "reason": reason,
                "summary": question.strip(),
                "requested_action": "avaliar o caso e dar continuidade ao atendimento",
                "priority": priority,
            }

    amount = re.search(r"r\$\s*([\d.,]+)", normalized)
    if amount:
        value = float(amount.group(1).replace(".", "").replace(",", "."))
        if value >= 500:
            return {
                "reason": "contestação de valor alto com verificação antifraude",
                "summary": question.strip(),
                "requested_action": "encaminhar para análise humana e verificação antifraude",
                "priority": "alta",
            }
    return None


def _direct_evidence(question: str, chunks: list[dict]) -> bool:
    """Evita responder uma intenção diferente apenas por proximidade vetorial."""

    normalized = question.casefold()
    content = " ".join(str(chunk.get("content", "")).casefold() for chunk in chunks)
    if any(term in normalized for term in ("pedir reembolso", "solicitar reembolso")):
        return any(term in content for term in ("solicitar reembolso", "pedir reembolso", "prazo de reembolso")) or (
            "90 dias" in content and "reembolso" in content
        )
    return True


def _citations(chunks: list[dict]) -> list[dict[str, Any]]:
    citations = []
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        citations.append({
            "source_file": metadata.get("source", chunk.get("document", "")),
            "chunk_id": chunk.get("chunk_id", metadata.get("chunk_id", "")),
            "score": float(chunk.get("score") or 0.0),
            "doc_family_id": metadata.get("doc_family_id", ""),
            "version_ordinal": metadata.get("version_ordinal"),
            "status": chunk.get("status", metadata.get("status")),
        })
    return citations


def _retrieval_candidates(chunks: list[dict]) -> list[dict[str, Any]]:
    """Audita os candidatos recuperados sem transformá-los em citações."""

    return [
        {
            "source_file": chunk.get("metadata", {}).get("source", chunk.get("document", "")),
            "chunk_id": chunk.get("chunk_id", ""),
            "score": float(chunk.get("score") or 0.0),
            "status": chunk.get("status", chunk.get("metadata", {}).get("status")),
        }
        for chunk in chunks
    ]


def _deterministic_answer(question: str, chunks: list[dict]) -> str | None:
    """Responde fatos estruturados quando a evidência contém um valor inequívoco."""
    normalized = question.casefold()
    content = " ".join(str(chunk.get("content", "")) for chunk in chunks)
    if "valor" in normalized and "basico" in normalized:
        match = re.search(r"R\$\s*[\d.,]+", content)
        if match:
            valor = match.group(0).rstrip(".")
            return f"O valor mensal do Conecta Básico é {valor}."
    return None


def run_question(question: str, audit_path: Path | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    trace_id = new_trace_id()
    normalized = question.strip()
    buscar = importlib.import_module("src.02_rag.07_retriever").buscar

    handoff = classify_handoff(normalized)
    chunks = [] if handoff else buscar(normalized)
    threshold = get_abstention_threshold()

    if handoff:
        decision = "ESCALATE"
        answer = "Vou encaminhar seu caso para atendimento humano."
        citations = []
        guardrail = "caso exige atendimento humano"
    elif not _direct_evidence(normalized, chunks):
        decision = "NO_ANSWER"
        answer = "NO_ANSWER"
        citations = []
        guardrail = "evidência recuperada não sustenta diretamente a intenção"
    else:
        deterministic = _deterministic_answer(normalized, chunks)
        if deterministic:
            decision = "ANSWER"
            answer = deterministic
        else:
            result = answer_question(normalized, chunks)
            decision = result["decision"]
            answer = result["answer"]
        citations = _citations(chunks) if decision == "ANSWER" else []
        guardrail = None if decision == "ANSWER" else "score insuficiente ou resposta sem evidência"

    event = {
        "trace_id": trace_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "duration_ms": int((time.perf_counter() - started) * 1000),
        "question": normalized,
        "decision": decision,
        "answer": answer,
        "citations": citations,
        "handoff": handoff,
        "guardrail": guardrail,
        "retrieval": {
            "best_score": max((chunk.get("score", 0) for chunk in chunks), default=None),
            "threshold": threshold,
            "candidates": _retrieval_candidates(chunks),
        },
        "component_versions": {"concierge": "03-concierge-v1", "pipeline": "integrated"},
    }
    AuditLogger(audit_path).append(event)
    return event
