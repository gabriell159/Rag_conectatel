"""Orquestrador do fluxo principal de atendimento e transbordo humano."""

from datetime import datetime, timezone
import importlib
import time
from typing import Any, Dict

classifier_mod = importlib.import_module("src.04_triage.01_classifier")
handoff_mod = importlib.import_module("src.04_triage.02_handoff")
retriever_mod = importlib.import_module("src.rag.retriever")
answer_mod = importlib.import_module("src.concierge.answer")

trace_mod = importlib.import_module("src.05_integracao_auditoria_qualidade.01_trace")
audit_mod = importlib.import_module("src.05_integracao_auditoria_qualidade.02_audit")


def process_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Executa o pipeline completo de atendimento."""
    start_time = time.perf_counter()

    question = str(event.get("question", "")).strip()
    channel = str(event.get("channel", "chat")).strip()
    product = str(event.get("product", "telefonia_movel")).strip()

    trace_id = trace_mod.new_trace_id()
    now_iso = datetime.now(timezone.utc).isoformat()

    triage_result = classifier_mod.classify(question)

    if triage_result["requires_human"]:
        handoff_data = handoff_mod.build_escalation(
            question=question,
            category=triage_result.get("category", "sem_fonte_suficiente"),
            resumo_caso=f"Solicitação enquadrada em regra de transbordo: {question}",
            canal_origem=channel,
            produto_servico_envolvido=product,
            urgencia=triage_result.get("urgencia"),
        )

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        response_event = {
            "trace_id": trace_id,
            "timestamp": now_iso,
            "duration_ms": duration_ms,
            "question": question,
            "decision": "ESCALATE",
            "answer": "Sua solicitação precisa ser tratada por um especialista humano. Estou encaminhando seu atendimento.",
            "citations": [],
            "handoff": handoff_data,
            "guardrail": triage_result.get("reason"),
            "component_versions": {"pipeline": "v1.0-frente4"},
        }

        audit_mod.AuditLogger().append(response_event)
        return response_event

    chunks = retriever_mod.buscar(question, top_k=3)
    concierge_result = answer_mod.answer_question(question, chunks)
    decision = concierge_result["decision"]

    handoff_data = None
    if decision == "NO_ANSWER":
        handoff_data = handoff_mod.build_escalation(
            question=question,
            category="sem_fonte_suficiente",
            resumo_caso=f"Pergunta sem fonte de conhecimento suficiente: {question}",
            canal_origem=channel,
            produto_servico_envolvido=product,
            historico_ja_levantado="Busca vetorial executada no FAISS. Nenhuma evidência com score suficiente foi retornada.",
        )

    citations = []
    if decision == "ANSWER":
        for src in concierge_result.get("sources", []):
            citations.append({
                "source_file": src.get("document", ""),
                "doc_family_id": src.get("metadata", {}).get("doc_family_id", "desconhecido"),
                "version_ordinal": int(src.get("metadata", {}).get("version_ordinal", 1)),
                "status": "vigente",
            })

    duration_ms = int((time.perf_counter() - start_time) * 1000)

    response_event = {
        "trace_id": trace_id,
        "timestamp": now_iso,
        "duration_ms": duration_ms,
        "question": question,
        "decision": decision,
        "answer": concierge_result.get("answer", "NO_ANSWER"),
        "citations": citations,
        "handoff": handoff_data,
        "guardrail": "Sem evidências suficientes no corpus" if decision == "NO_ANSWER" else None,
        "component_versions": {"pipeline": "v1.0-frente4"},
    }

    audit_mod.AuditLogger().append(response_event)
    return response_event


def lambda_handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """Ponto de entrada padrão para invocação da AWS Lambda."""
    return process_event(event)