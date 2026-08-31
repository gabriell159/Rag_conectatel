"""Contrato dos artefatos produzidos pela Frente 01."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "chamado_id",
    "data_abertura",
    "canal",
    "categoria",
    "subcategoria",
    "estado",
    "cidade",
    "duracao_minutos",
    "resolvido_primeiro_contato",
    "encaminhado_humano",
    "satisfacao_1_a_5",
    "plano_atual",
    "resumo_atendimento",
}


def validate_processed_dataframe(df: pd.DataFrame) -> None:
    """Valida o schema mínimo do CSV tratado e suas invariantes principais."""
    missing = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing:
        raise ValueError(f"Colunas obrigatorias ausentes: {', '.join(missing)}")
    if df["chamado_id"].duplicated().any():
        raise ValueError("chamado_id deve ser unico no artefato tratado")
    if not df["duracao_minutos"].dropna().between(0, 180, inclusive="neither").all():
        raise ValueError("duracao_minutos deve estar entre 0 e 180")
    if not df["satisfacao_1_a_5"].dropna().between(1, 5).all():
        raise ValueError("satisfacao_1_a_5 deve estar entre 1 e 5")
    for column in ("resolvido_primeiro_contato", "encaminhado_humano"):
        valid = df[column].dropna().map(lambda value: isinstance(value, bool))
        if not valid.all():
            raise ValueError(f"{column} deve conter somente booleanos ou nulos")


def validate_processed_artifact(path: Path) -> pd.DataFrame:
    """Carrega e valida um artefato tratado já persistido em CSV."""
    if not path.exists():
        raise FileNotFoundError(f"Artefato tratado nao encontrado: {path}")
    df = pd.read_csv(path)
    validate_processed_dataframe(df)
    return df
