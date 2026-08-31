"""Classificador determinístico para os 8 critérios da política de suporte."""

import re
from typing import Any, Dict

RULES: Dict[str, Dict[str, Any]] = {
    "fraude": {
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
        "category_key": "fraude",
        "urgencia": "alta",
    },
    "contestacao_alta_valor": {
        "patterns": [
            r"contestar.*r\$\s*([5-9]\d{2,}|\d{4,})",
            r"cobranca.*r\$\s*([5-9]\d{2,}|\d{4,})",
            r"fatura.*r\$\s*([5-9]\d{2,}|\d{4,})",
            r"reembolso.*r\$\s*([5-9]\d{2,}|\d{4,})",
            r"r\$\s*([5-9]\d{2,}|\d{4,})",
        ],
        "category_key": "contestacao_alta_valor",
        "urgencia": "media",
    },
    "multa_fidelidade_contestada": {
        "patterns": [
            r"multa.*cancelamento",
            r"cancelamento.*multa",
            r"fidelidade.*multa",
            r"multa.*fidelidade",
            r"nao concordo.*multa",
            r"contesta.*multa",
        ],
        "category_key": "multa_fidelidade_contestada",
        "urgencia": "media",
    },
    "titularidade_falecimento": {
        "patterns": [
            r"\bfalec\w*\b",
            r"\bobito\b",
            r"\bmorte\b",
            r"\bmorreu\b",
            r"titular.*faleceu",
            r"mudar titularidade.*falece",
        ],
        "category_key": "titularidade_falecimento",
        "urgencia": "alta",
    },
    "reclamacao_orgao_externo": {
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
        "category_key": "reclamacao_orgao_externo",
        "urgencia": "alta",
    },
    "assedio_discriminacao": {
        "patterns": [
            r"\bassedio\b",
            r"\bdiscriminacao\b",
            r"\bracismo\b",
            r"\babusiv[ao]\b",
            r"\bagressao\b",
            r"\bxingou\b",
            r"\boftend\w*\b",
        ],
        "category_key": "assedio_discriminacao",
        "urgencia": "alta",
    },
    "visita_tecnica": {
        "patterns": [
            r"visita tecnica",
            r"tecnico.*residencia",
            r"tecnico.*casa",
            r"reparo.*infraestrutura",
            r"instalacao.*fibra",
            r"reparo.*rede",
            r"tecnico presencial",
        ],
        "category_key": "visita_tecnica",
        "urgencia": "media",
    },
}


def _remove_accents(text: str) -> str:
    import unicodedata

    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def classify(question: str) -> Dict[str, Any]:
    """Avalia se a pergunta aciona um dos critérios de escalonamento."""
    if not isinstance(question, str) or not question.strip():
        return {
            "requires_human": False,
            "category": None,
            "urgencia": "baixa",
            "reason": None,
        }

    normalized_text = _remove_accents(question.strip().lower())

    value_match = re.search(r"(?:r\$\s*|valor\s*de\s*|fatura\s*de\s*)(\d+(?:\.\d{3})*(?:,\d{2})?)", normalized_text)
    if value_match:
        val_str = value_match.group(1).replace(".", "").replace(",", ".")
        try:
            val = float(val_str)
            if val >= 500.0 and any(kw in normalized_text for kw in ["fatura", "cobranca", "reembolso", "contest"]):
                return {
                    "requires_human": True,
                    "category": "contestacao_alta_valor",
                    "urgencia": "media",
                    "reason": f"Valor R$ {val:.2f} é igual ou superior ao limite de R$ 500,00.",
                }
        except ValueError:
            pass

    for rule_key, rule_data in RULES.items():
        if rule_key == "contestacao_alta_valor":
            continue

        for pattern in rule_data["patterns"]:
            if re.search(pattern, normalized_text):
                return {
                    "requires_human": True,
                    "category": rule_data["category_key"],
                    "urgencia": rule_data["urgencia"],
                    "reason": f"Gatilho ativado para a categoria {rule_data['category_key']}.",
                }

    return {
        "requires_human": False,
        "category": None,
        "urgencia": "baixa",
        "reason": None,
    }