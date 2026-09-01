import datetime
import importlib
import uuid
from typing import Any, Dict, List, Optional

CANAIS_VALIDOS = {"chat", "telefone", "app", "loja"}


def normalize_canal(canal_origem: Optional[str]) -> str:
    """Normaliza o canal de origem, preservando valores nao previstos em vez de descarta-los."""
    if not canal_origem:
        return "chat"
    canal = canal_origem.strip().lower()
    return canal if canal in CANAIS_VALIDOS else canal_origem.strip()


def summarize_case(
    question: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    max_len: int = 240,
) -> str:
    """
    Resumo objetivo do relato do cliente utilizando sumarização semântica via LLM.
    """
    clean_q = " ".join(question.strip().split())
    if len(clean_q) <= 80 and not conversation_history:
        return clean_q

    try:
        bedrock_mod = importlib.import_module("src.03_concierge.bedrock_client")
        invoke_llm = getattr(bedrock_mod, "invoke_llm", None) or getattr(
            bedrock_mod, "call_bedrock", None
        )

        if invoke_llm:
            history_text = ""
            if conversation_history:
                turns = [
                    f"{msg.get('role', 'user').capitalize()}: {msg.get('content', '')}"
                    for msg in conversation_history
                ]
                history_text = "Histórico de Conversa:\n" + "\n".join(turns) + "\n\n"

            prompt = (
                "Você é um assistente de triagem. Resuma o relato do cliente em uma frase objetiva de no máximo 200 caracteres, "
                "destacando o problema principal, produtos envolvidos e valores mencionados.\n"
                f"{history_text}"
                f"Relato Atual do Cliente: {clean_q}\n"
                "Resumo:"
            )

            llm_summary = invoke_llm(prompt)
            if llm_summary and isinstance(llm_summary, str):
                summary_clean = " ".join(llm_summary.strip().split())
                if summary_clean:
                    return summary_clean[:max_len]
    except Exception:
        pass

    return clean_q[:max_len]


def build_historico_ja_levantado(
    question: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    Registra o que ja foi perguntado/confirmado com o cliente antes do
    escalonamento, a partir do historico real da conversa.
    """
    if not conversation_history:
        return (
            "Nenhuma interacao anterior registrada nesta conversa alem da "
            f"mensagem que motivou o escalonamento: '{question}'."
        )

    linhas = []
    for turn in conversation_history:
        papel = (turn.get("role") or "cliente").strip()
        conteudo = (turn.get("content") or "").strip()
        if conteudo:
            linhas.append(f"- {papel}: {conteudo}")

    if not linhas:
        return (
            "Nenhuma interacao anterior registrada nesta conversa alem da "
            f"mensagem que motivou o escalonamento: '{question}'."
        )

    return "Historico levantado antes do escalonamento:\n" + "\n".join(linhas)


def extract_contextual_info(question: str) -> Dict[str, str]:
    context = {
        "produto_servico": "telefonia_movel",
    }

    q_lower = question.lower()
    if any(
        k in q_lower for k in ["fibra", "internet fixa", "modem", "instalacao", "cabo"]
    ):
        context["produto_servico"] = "banda_larga_fibra"
    elif any(k in q_lower for k in ["fatura", "cobranca", "reembolso", "multa", "r$"]):
        context["produto_servico"] = "faturamento_e_planos"

    return context


def build_escalation_payload(
    question: str,
    rule_info: Dict[str, Any],
    source_document: Optional[str] = None,
    contact_data: Optional[str] = None,
    canal_origem: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Monta o payload de escalonamento.
    """
    context = extract_contextual_info(question)
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    protocolo = (
        f"PROT-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')}"
        f"-{uuid.uuid4().hex[:4].upper()}"
    )

    priority_map = {
        "alta": "HIGH",
        "media": "MEDIUM",
        "baixa": "LOW",
    }

    resumo = summarize_case(question, conversation_history=conversation_history)
    historico = build_historico_ja_levantado(question, conversation_history)

    documento_fonte = source_document or (
        "Nenhum documento da base de conhecimento foi consultado antes "
        "deste escalonamento."
    )

    dados_contato = contact_data or (
        "Nao informado pelo cliente ate o momento do escalonamento."
    )

    payload = {
        "protocolo_atendimento": protocolo,
        "data_hora_abertura": now_iso,
        "canal_origem": normalize_canal(canal_origem),
        "categoria_motivo": rule_info.get(
            "category_key", "Escalonamento Humano Mandatorio"
        ),
        "resumo_caso": resumo,
        "historico_ja_levantado": historico,
        "produto_servico_envolvido": context["produto_servico"],
        "documento_fonte_consultado": documento_fonte,
        "urgencia": rule_info.get("priority", "alta"),
        "dados_contato_retorno": dados_contato,
        "status_escalonamento": "pendente_atendimento_humano",
        "data_hora_escalonamento": now_iso,
        "reason": rule_info.get("category_key", "Escalonamento Humano Mandatorio"),
        "summary": resumo,
        "requested_action": (
            f"Atendimento humano especialista para tratamento da categoria: "
            f"{rule_info.get('category_key')}."
        ),
        "priority": priority_map.get(rule_info.get("priority", "alta").lower(), "HIGH"),
    }

    return payload
