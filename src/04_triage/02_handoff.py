import datetime
import re
import uuid
from typing import Any, Dict, Optional


def extract_contextual_info(question: str) -> Dict[str, str]:
    context = {
        "produto_servico": "telefonia_movel",
        "historico_extraido": f"Cliente relatou a seguinte solicitacao/ocorrencia: '{question}'."
    }

    q_lower = question.lower()
    if any(k in q_lower for k in ["fibra", "internet fixa", "modem", "instalacao", "cabo"]):
        context["produto_servico"] = "banda_larga_fibra"
    elif any(k in q_lower for k in ["fatura", "cobranca", "reembolso", "multa", "r$"]):
        context["produto_servico"] = "faturamento_e_planos"

    val_match = re.search(r"r\$\s*([\d.,]+)", question, re.IGNORECASE)
    if val_match:
        context["historico_extraido"] += f" Valor mencionado pelo cliente: R$ {val_match.group(1)}."

    return context


def build_escalation_payload(
    question: str,
    rule_info: Dict[str, Any],
    source_document: Optional[str] = "corpus/politicas/politica_suporte_escalonamento.md",
    contact_data: Optional[str] = "Cliente autenticado via sistema (canal digital)"
) -> Dict[str, Any]:
    context = extract_contextual_info(question)
    protocolo = f"PROT-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"

    priority_map = {
        "alta": "HIGH",
        "media": "MEDIUM",
        "baixa": "LOW"
    }

    payload = {
        "protocolo_atendimento": protocolo,
        "categoria_motivo": rule_info.get("category_key", "Escalonamento Humano Mandatorio"),
        "resumo_caso": question,
        "historico_ja_levantado": context["historico_extraido"],
        "documento_fonte_consultado": source_document,
        "dados_contato_retorno": contact_data,
        "urgencia": rule_info.get("priority", "alta"),
        "produto_servico_envolvido": context["produto_servico"],
        "status_escalonamento": "pendente_atendimento_humano",
        "data_hora_escalonamento": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "rule_id": rule_info.get("rule_id", "escalonamento_humano"),
        "reason": rule_info.get("category_key", "Escalonamento Humano Mandatorio"),
        "summary": question,
        "requested_action": f"Atendimento humano especialista para tratamento da categoria: {rule_info.get('category_key')}.",
        "priority": priority_map.get(rule_info.get("priority", "alta").lower(), "HIGH")
    }

    return payload
