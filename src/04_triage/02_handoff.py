"""Montagem do registro de escalonamento humano com 10 campos mínimos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, cast
import uuid

CATEGORIAS_ESCALONAMENTO: dict[str, str] = {
    "fraude": "Suspeita de fraude",
    "contestacao_alta_valor": "Contestação de valor de fatura igual ou superior a R$ 500,00",
    "multa_fidelidade_contestada": "Contestação de multa de fidelidade",
    "titularidade_falecimento": "Alteração de titularidade (falecimento ou documentação adicional)",
    "reclamacao_orgao_externo": "Reclamação registrada em órgão externo (Anatel/Procon) ou menção a ação judicial",
    "assedio_discriminacao": "Relato de assédio, discriminação ou conduta abusiva",
    "visita_tecnica": "Problema técnico que exige visita presencial",
    "sem_fonte_suficiente": "Pergunta sem fonte suficiente na base vigente (cliente insistiu ou tema sensível)",
}

URGENCIA_PADRAO: dict[str, str] = {
    "fraude": "alta",
    "contestacao_alta_valor": "media",
    "multa_fidelidade_contestada": "media",
    "titularidade_falecimento": "alta",
    "reclamacao_orgao_externo": "alta",
    "assedio_discriminacao": "alta",
    "visita_tecnica": "media",
    "sem_fonte_suficiente": "baixa",
}

DOCUMENTO_REFERENCIA_PADRAO: dict[str, str] = {
    "contestacao_alta_valor": "politica_reembolso_v2.md",
    "multa_fidelidade_contestada": "politica_cancelamento.md",
    "visita_tecnica": "politica_suporte_escalonamento.md",
}

Urgencia = Literal["baixa", "media", "alta"]


@dataclass
class Handoff:
    """Representa o registro de escalonamento com os 10 campos mínimos exigidos."""

    protocolo_atendimento: str
    data_hora_abertura: str
    canal_origem: str
    categoria_motivo: str
    resumo_caso: str
    historico_ja_levantado: str
    produto_servico_envolvido: str
    documento_fonte_consultado: str
    urgencia: Urgencia
    dados_contato_retorno: str

    def to_dict(self) -> dict:
        return {
            "protocolo_atendimento": self.protocolo_atendimento,
            "data_hora_abertura": self.data_hora_abertura,
            "canal_origem": self.canal_origem,
            "categoria_motivo": self.categoria_motivo,
            "resumo_caso": self.resumo_caso,
            "historico_ja_levantado": self.historico_ja_levantado,
            "produto_servico_envolvido": self.produto_servico_envolvido,
            "documento_fonte_consultado": self.documento_fonte_consultado,
            "urgencia": self.urgencia,
            "dados_contato_retorno": self.dados_contato_retorno,
        }


def _gerar_protocolo() -> str:
    return f"ESC-{uuid.uuid4().hex[:8].upper()}"


def build_escalation(
    *,
    question: str,
    category: str,
    resumo_caso: str | None = None,
    historico_ja_levantado: str | None = None,
    canal_origem: str = "chat",
    produto_servico_envolvido: str | None = None,
    documento_fonte_consultado: str | None = None,
    urgencia: Urgencia | None = None,
    dados_contato_retorno: str | None = None,
) -> dict:
    """Monta o registro de escalonamento completo."""
    if category not in CATEGORIAS_ESCALONAMENTO:
        category_key = "sem_fonte_suficiente"
        categoria_texto = CATEGORIAS_ESCALONAMENTO[category_key]
    else:
        category_key = category
        categoria_texto = CATEGORIAS_ESCALONAMENTO[category]

    resumo = resumo_caso.strip() if resumo_caso and resumo_caso.strip() else f"Cliente solicita atendimento referente a {question.strip()}"
    historico = (
        historico_ja_levantado.strip()
        if historico_ja_levantado and historico_ja_levantado.strip()
        else "Triagem automatizada realizada via regra determinística."
    )

    raw_urgencia = urgencia or URGENCIA_PADRAO.get(category_key, "media")
    resolved_urgencia = cast(Urgencia, raw_urgencia if raw_urgencia in ("baixa", "media", "alta") else "media")

    resolved_documento = (
        documento_fonte_consultado
        or DOCUMENTO_REFERENCIA_PADRAO.get(category_key)
        or "politica_suporte_escalonamento.md"
    )
    resolved_produto = produto_servico_envolvido or "telefonia_movel"
    resolved_contato = dados_contato_retorno or "Contato preferencial cadastrado do cliente"

    handoff = Handoff(
        protocolo_atendimento=_gerar_protocolo(),
        data_hora_abertura=datetime.now(timezone.utc).isoformat(),
        canal_origem=canal_origem,
        categoria_motivo=categoria_texto,
        resumo_caso=resumo,
        historico_ja_levantado=historico,
        produto_servico_envolvido=resolved_produto,
        documento_fonte_consultado=resolved_documento,
        urgencia=resolved_urgencia,
        dados_contato_retorno=resolved_contato,
    )

    return handoff.to_dict()