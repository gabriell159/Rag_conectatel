"""Tratamento reproduzivel do log de chamados da Frente 1."""

from pathlib import Path
import unicodedata

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
INPUT_PATH = BASE_DIR / "data" / "raw" / "conectatel-dados" / "log_chamados" / "log_chamados_sintetico.csv"
OUTPUT_PATH = BASE_DIR / "data" / "processed" / "log_chamados" / "chamados_clean.csv"

BOOLEAN_MAP = {
    "sim": True, "s": True, "1": True, "true": True,
    "nao": False, "n": False, "0": False, "false": False,
}
STATE_MAP = {
    "sao paulo": "SP", "sp": "SP", "rio de janeiro": "RJ", "rj": "RJ",
    "minas gerais": "MG", "mg": "MG", "bahia": "BA", "ba": "BA",
    "parana": "PR", "pr": "PR", "rio grande do sul": "RS", "rs": "RS",
    "ceara": "CE", "ce": "CE", "pernambuco": "PE", "pe": "PE",
}


def remove_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_boolean(value: object) -> bool | None:
    if pd.isna(value):
        return None
    return BOOLEAN_MAP.get(remove_accents(str(value).strip().lower()))


def normalize_state(value: object) -> str | None:
    if pd.isna(value):
        return None
    normalized = remove_accents(str(value).strip().lower())
    return STATE_MAP.get(normalized, str(value).strip().upper())


def processar_log_chamados(
    caminho_entrada: Path = INPUT_PATH,
    caminho_saida: Path = OUTPUT_PATH,
) -> pd.DataFrame:
    if not caminho_entrada.exists():
        raise FileNotFoundError(f"Arquivo de entrada nao encontrado: {caminho_entrada}")

    df = pd.read_csv(caminho_entrada, encoding="utf-8")
    linhas_entrada = len(df)
    df = df.drop_duplicates()

    if "data_abertura" in df.columns:
        df["data_abertura"] = pd.to_datetime(
            df["data_abertura"], errors="coerce"
        ).dt.strftime("%Y-%m-%d")

    text_columns = [
        "canal", "categoria", "subcategoria", "cidade",
        "plano_atual", "resumo_atendimento",
    ]
    for column in text_columns:
        if column not in df.columns:
            continue
        df[column] = df[column].astype("string").str.strip()
        if column in {"canal", "categoria", "cidade", "plano_atual"}:
            df[column] = df[column].str.title()
        df[column] = df[column].map(
            lambda value: remove_accents(value) if pd.notna(value) else value
        )

    if "estado" in df.columns:
        df["estado"] = df["estado"].apply(normalize_state)

    for column in ("resolvido_primeiro_contato", "encaminhado_humano"):
        if column in df.columns:
            df[column] = df[column].apply(normalize_boolean)

    if "duracao_minutos" in df.columns:
        df["duracao_minutos"] = pd.to_numeric(df["duracao_minutos"], errors="coerce")
        invalid_duration = (df["duracao_minutos"] <= 0) | (df["duracao_minutos"] > 180)
        df.loc[invalid_duration, "duracao_minutos"] = None

    if "satisfacao_1_a_5" in df.columns:
        df["satisfacao_1_a_5"] = pd.to_numeric(
            df["satisfacao_1_a_5"], errors="coerce"
        )
        df.loc[~df["satisfacao_1_a_5"].between(1, 5), "satisfacao_1_a_5"] = None

    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(caminho_saida, index=False, encoding="utf-8")
    print(
        f"Tratamento concluido: {linhas_entrada} -> {len(df)} linhas. "
        f"Saida: {caminho_saida}"
    )
    return df


if __name__ == "__main__":
    processar_log_chamados()
