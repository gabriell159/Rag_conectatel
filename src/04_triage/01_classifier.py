import re
import unicodedata
from typing import Any, Dict, Optional, Tuple


ESCALATION_RULES: Dict[str, Dict[str, Any]] = {
    "fraude": {
        "category_key": "Suspeita de fraude",
        "priority": "alta",
        "patterns": [
            r"\bfraude\b",
            r"\bgolpe\b",
            r"\buso indevido\b",
            r"\bclonad[ao]\b",
            r"\bsim swap\b",
            r"\binvasao\b",
            r"\binvadiu\b",
            r"\broubo de linha\b",
            r"\bse passaram por mim\b",
        ],
    },
    "contestacao_alta_valor": {
        "category_key": "Contestacao de valor igual ou superior a R$ 500,00",
        "priority": "alta",
        "patterns": [
            r"contesta.*r\$\s*([5-9]\d{2,}|\d{4,})",
            r"cobranca.*r\$\s*([5-9]\d{2,}|\d{4,})",
            r"fatura.*r\$\s*([5-9]\d{2,}|\d{4,})",
            r"reembolso.*r\$\s*([5-9]\d{2,}|\d{4,})",
            r"r\$\s*([5-9]\d{2,}|\d{4,})",
        ],
    },
    "multa_fidelidade_contestada": {
        "category_key": "Contestacao de multa de fidelidade",
        "priority": "media",
        "patterns": [
            r"multa.*cancelamento.*(nao concordo|discordo|contesto|abusiva|incabivel)",
            r"cancelamento.*multa.*(nao concordo|discordo|contesto|abusiva|incabivel)",
            r"(nao concordo|discordo|contesto|contestacao).*(multa|fidelidade)",
            r"multa.*(fidelidade|cancelamento).*(nao concordo|discordo|contesto)",
            r"\bcontestar multa\b",
            r"\bmulta abusiva\b",
        ],
    },
    "titularidade_falecimento": {
        "category_key": "Alteracao de titularidade por falecimento ou documentacao especial",
        "priority": "alta",
        "patterns": [
            r"\bfalec\w*\b",
            r"\bobito\b",
            r"\bmorte\b",
            r"\bmorreu\b",
            r"titular.*faleceu",
            r"mudar titularidade.*falece",
            r"alterar titularidade.*falec",
        ],
    },
    "reclamacao_orgao_externo": {
        "category_key": "Reclamacao registrada em orgao externo ou mencao a acao judicial",
        "priority": "alta",
        "patterns": [
            r"\banatel\b",
            r"\bprocon\b",
            r"\bconsumidor\.gov\b",
            r"\bprocesso\b",
            r"\bjudicial\b",
            r"\badvogado\b",
            r"\bjustica\b",
            r"\bacao judicial\b",
        ],
    },
    "assedio_discriminacao": {
        "category_key": "Relato de assedio, discriminacao ou conduta abusiva",
        "priority": "alta",
        "patterns": [
            r"\bassedio\b",
            r"\bdiscriminacao\b",
            r"\bracismo\b",
            r"\babusiv[ao]\b",
            r"\bagressao\b",
            r"\bofensa\b",
            r"\bme xingou\b",
            r"\bma conduta\b",
        ],
    },
    "visita_tecnica_presencial": {
        "category_key": "Problema tecnico que exige visita presencial",
        "priority": "media",
        "patterns": [
            r"\bvisita tecnica\b",
            r"\bvisita presencial\b",
            r"\btecnico na minha residencia\b",
            r"\breparo de infraestrutura\b",
            r"\binstalacao de fibra\b",
            r"\binstalacao de internet fixa\b",
            r"\bcabo rompido\b",
            r"sem sinal h[a|a\s] (horas|dias)",
        ],
    },
}


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    without_accents = "".join(c for c in normalized if not unicodedata.combining(c))
    return without_accents.lower().strip()


def check_high_value_contest(text: str) -> bool:
    """Identifica valores altos somente quando existe intenção de contestação.

    Uma pergunta informativa, como "o plano custa R$ 599?", deve seguir para
    o RAG; o valor isolado não caracteriza um caso de atendimento humano.
    """
    contestation_markers = (
        "contest", "cobranca indevida", "nao reconheco", "nao concordo",
        "discordo", "indevida", "reembolso", "golpe",
    )
    if not any(marker in text for marker in contestation_markers):
        return False

    match = re.search(r"r\$\s*([\d.,]+)", text)
    if match:
        try:
            val_str = match.group(1).replace(".", "").replace(",", ".")
            value = float(val_str)
            return value >= 500.0
        except ValueError:
            return False
    return False


def classify_escalation(
    question: str,
    top_score: Optional[float] = None,
    abstention_threshold: float = 0.30
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    normalized_question = normalize_text(question)

    for rule_id, rule_info in ESCALATION_RULES.items():
        if rule_id == "contestacao_alta_valor":
            if check_high_value_contest(normalized_question):
                return True, {
                    "rule_id": rule_id,
                    "category_key": rule_info["category_key"],
                    "priority": rule_info["priority"],
                }
            continue

        for pattern in rule_info["patterns"]:
            if re.search(pattern, normalized_question):
                return True, {
                    "rule_id": rule_id,
                    "category_key": rule_info["category_key"],
                    "priority": rule_info["priority"],
                }

    if top_score is not None and top_score < abstention_threshold:
        return True, {
            "rule_id": "ausencia_fonte_suficiente",
            "category_key": "Pergunta sem fonte suficiente na base de conhecimento vigente",
            "priority": "baixa",
        }

    return False, None
