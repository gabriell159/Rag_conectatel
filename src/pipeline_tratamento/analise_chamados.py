import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
arquivo_tratado = BASE_DIR / "data" / "raw" / "conectatel-dados" / "log_chamados" / "chamados_clean.csv"

df = pd.read_csv(arquivo_tratado)

print("ANÁLISE 1: Volume de Chamados por Categoria")

volume_categoria = df['categoria'].value_counts(normalize=True) * 100
print(volume_categoria.round(2).astype(str) + '%')
print("\n")

print("ANÁLISE 2: Taxa de Resolução no primeiro Contato por Categoria")

resolucao_categoria = df.groupby('categoria')['resolvido_primeiro_contato'].mean() * 100
print(resolucao_categoria.round(2).astype(str) + '%')
print("\n")

print("ANÁLISE 3: Taxa de Escalonamento Humano por Canal")

escalonamento_canal = df.groupby('canal')['encaminhado_humano'].mean() * 100
print(escalonamento_canal.sort_values(ascending=False).round(2).astype(str) + '%')