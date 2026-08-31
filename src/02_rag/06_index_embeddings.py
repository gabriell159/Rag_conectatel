import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import faiss
import numpy as np


VECTORSTORE_PATH = Path("data/processed/vectorstore")
INDEX_PATH = VECTORSTORE_PATH / "index.faiss"
METADATA_PATH = VECTORSTORE_PATH / "metadata.json"


def criar_indice_faiss(chunks_com_embeddings: list[dict]):
    """
    Criando um índice FAISS usando produto interno.
    Como os embeddings do Titan são normalizados,
    o produto interno equivale à similaridade de cosseno.
    """

    if not chunks_com_embeddings:
        raise ValueError(
            "Nenhum chunk com embedding foi fornecido."
        )

    embeddings = np.array(
        [
            chunk["embedding"]
            for chunk in chunks_com_embeddings
        ],
        dtype="float32",
    )

    dimensao = embeddings.shape[1]

    indice = faiss.IndexFlatIP(dimensao)

    indice.add(embeddings)

    return indice



def preparar_metadata(chunks_com_embeddings: list[dict]) -> list[dict]:
    """
    Remove os embeddings da estrutura que será salva em JSON.
    O FAISS armazena os vetores.
    O JSON armazena conteúdo e metadados.
    """

    registros = []

    for chunk in chunks_com_embeddings:
        registros.append(
            {
                "content": chunk["content"],
                "metadata": chunk["metadata"],
            }
        )

    return registros



def salvar_indice(
    indice,
    chunks_com_embeddings: list[dict],
    vectorstore_path: Path = VECTORSTORE_PATH,
) -> None:
    """
    Persiste o índice FAISS e os metadados que serão utilizados para recuperar os chunks.
    Que sãp correspondentes aos vetores armazenados no índice.
    """

    vectorstore_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    index_path = vectorstore_path / "index.faiss"
    metadata_path = vectorstore_path / "metadata.json"

    faiss.write_index(
        indice,
        str(index_path),
    )

    metadata = preparar_metadata(
        chunks_com_embeddings
    )

    with metadata_path.open(
        "w",
        encoding="utf-8",
    ) as arquivo:
        json.dump(
            metadata,
            arquivo,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    metadata_bytes = metadata_path.read_bytes()
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "chunk_count": len(metadata),
        "embedding_model": "amazon.titan-embed-text-v2:0",
        "dimensions": indice.d,
        "metadata_sha256": hashlib.sha256(metadata_bytes).hexdigest(),
    }
    (vectorstore_path / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Índice salvo em: {index_path}")
    print(f"Metadados salvos em: {metadata_path}")


def validar_indice(indice, chunks_com_embeddings: list[dict]) -> None:
    """
    Valida se todos os embeddings foram adicionados ao índice FAISS.
    """

    quantidade_indice = indice.ntotal
    quantidade_chunks = len(chunks_com_embeddings)

    if quantidade_indice != quantidade_chunks:
        raise ValueError(
            "Quantidade de vetores no índice diferente "
            "da quantidade de chunks."
        )

    print("Índice FAISS validado com sucesso!")
    print(f"Vetores indexados: {quantidade_indice}")
    print(f"Dimensão: {indice.d}")
