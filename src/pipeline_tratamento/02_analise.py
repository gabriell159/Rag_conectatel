from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
arquivo_tratado = BASE_DIR / "data" / "processed" / "log_chamados" / "chamados_clean.csv"


def executar_analises() -> None:
    if not arquivo_tratado.exists():
        raise FileNotFoundError(f"Arquivo tratado nao encontrado: {arquivo_tratado}")

    df = pd.read_csv(arquivo_tratado)

    print("ANALISE 1: Volume de Chamados por Categoria")
    volume_categoria = df["categoria"].value_counts(normalize=True) * 100
    print(volume_categoria.round(2).astype(str) + "%")
    print("\n")

    print("ANALISE 2: Taxa de Resolucao no primeiro Contato por Categoria")
    resolucao_categoria = df.groupby("categoria")["resolvido_primeiro_contato"].mean() * 100
    print(resolucao_categoria.round(2).astype(str) + "%")
    print("\n")

    print("ANALISE 3: Taxa de Escalonamento Humano por Canal")
    escalonamento_canal = df.groupby("canal")["encaminhado_humano"].mean() * 100
    print(escalonamento_canal.sort_values(ascending=False).round(2).astype(str) + "%")


if __name__ == "__main__":
    executar_analises()
