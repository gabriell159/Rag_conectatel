import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

arquivo_base = BASE_DIR / "data" / "raw" / "conectatel-dados" / "log_chamados" / "log_chamados_sintetico.csv"
arquivo_tratado = BASE_DIR / "data" / "raw" / "conectatel-dados" / "log_chamados" / "chamados_clean.csv"

df = pd.read_csv(arquivo_tratado)
df1 = pd.read_csv(arquivo_base)

print(df1.head(100).to_string())
#print(df.head(100).to_string())