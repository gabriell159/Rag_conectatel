"""Prepara o vector store FAISS para consumo pelas etapas seguintes."""

import shutil
import json
from pathlib import Path

import faiss


BASE_DIR = Path(__file__).resolve().parents[2]
VECTORSTORE_DIR = BASE_DIR / "data" / "processed" / "vectorstore"
BACKUP_DIR = BASE_DIR / "data" / "processed" / "vectorstore_backup"
REQUIRED_FILES = ("index.faiss", "metadata.json")


def preparar_vectorstore() -> Path:
    """Promove o artefato validado e garante os dois arquivos obrigatórios."""

    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
    for filename in REQUIRED_FILES:
        destino = VECTORSTORE_DIR / filename
        origem = BACKUP_DIR / filename
        if not destino.exists() and origem.exists():
            shutil.copy2(origem, destino)

    faltantes = [name for name in REQUIRED_FILES if not (VECTORSTORE_DIR / name).exists()]
    if faltantes:
        raise FileNotFoundError("Vector store incompleto. Faltam: " + ", ".join(faltantes))

    indice = faiss.read_index(str(VECTORSTORE_DIR / "index.faiss"))
    registros = json.loads((VECTORSTORE_DIR / "metadata.json").read_text(encoding="utf-8"))
    if indice.ntotal != len(registros):
        raise ValueError("index.faiss e metadata.json possuem quantidades diferentes.")

    print(f"Vector store pronto em: {VECTORSTORE_DIR}")
    return VECTORSTORE_DIR


if __name__ == "__main__":
    preparar_vectorstore()
