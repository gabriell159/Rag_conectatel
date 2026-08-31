import json
import hashlib
import os
import re
import unicodedata
from pathlib import Path
import faiss
import numpy as np

import importlib

gerar_embedding = importlib.import_module("src.02_rag.04_embeddings").gerar_embedding
download_vectorstore = importlib.import_module("src.02_rag.10_s3_storage").download_vectorstore

BASE_DIR = Path(__file__).resolve().parents[2]
VECTORSTORE_PATH = BASE_DIR / "data" / "processed" / "vectorstore"
BACKUP_VECTORSTORE_PATH = BASE_DIR / "data" / "processed" / "vectorstore_backup"
INDEX_PATH = VECTORSTORE_PATH / "index.faiss"
METADATA_PATH = VECTORSTORE_PATH / "metadata.json"


def carregar_vectorstore(
    index_path: Path = INDEX_PATH,
    metadata_path: Path = METADATA_PATH,
):
    """
    Carrega o índice FAISS e os metadados que fram persistidos no data/processed/vectorstore.
    """

    origem = VECTORSTORE_PATH
    if not index_path.exists() or not metadata_path.exists():
        print(
            "Vector store local não encontrado. "
            "Recuperando do Amazon S3..."
        )

        try:
            download_vectorstore()
        except Exception as error:
            backup_index = BACKUP_VECTORSTORE_PATH / "index.faiss"
            backup_metadata = BACKUP_VECTORSTORE_PATH / "metadata.json"
            if backup_index.exists() and backup_metadata.exists() and index_path == INDEX_PATH:
                print(f"Aviso: S3 indisponível; usando backup local ({error}).")
                index_path, metadata_path = backup_index, backup_metadata
                origem = BACKUP_VECTORSTORE_PATH
            else:
                raise

    if not index_path.exists():
        raise FileNotFoundError(
            f"Índice FAISS não encontrado: {index_path}"
        )

    if not metadata_path.exists():
        raise FileNotFoundError(
            f"Metadados não encontrados: {metadata_path}"
        )
    
    indice = faiss.read_index(str(index_path))

    with metadata_path.open(
        "r",
        encoding="utf-8",
    ) as arquivo:
        registros = json.load(arquivo)

    if indice.ntotal != len(registros):
        raise ValueError(
            "Quantidade de vetores no FAISS diferente "
            "da quantidade de registros."
        )

    manifest_path = origem / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        esperado = manifest.get("metadata_sha256")
        atual = hashlib.sha256(metadata_path.read_bytes()).hexdigest()
        if esperado and esperado != atual:
            raise ValueError("Hash do metadata.json diferente do manifesto.")
        if manifest.get("chunk_count") not in (None, len(registros)):
            raise ValueError("Quantidade de chunks diferente do manifesto.")
        if manifest.get("dimensions") not in (None, indice.d):
            raise ValueError("Dimensão do índice diferente do manifesto.")

    return indice, registros



def obter_indices_vigentes(registros: list[dict]) -> list[int]:
    """
    Ele retorna as posições dos chunks vigentes. O filtro é aplicado antes do cálculo de similaridade.
    """

    return [
        indice
        for indice, registro in enumerate(registros)
        if registro["metadata"]["status"] == "vigente"
    ]


def _tokens(texto: str) -> set[str]:
    normalizado = unicodedata.normalize("NFKD", texto.casefold())
    normalizado = "".join(c for c in normalizado if not unicodedata.combining(c))
    return set(re.findall(r"[a-z0-9]{3,}", normalizado))


def _lexical_overlap(pergunta: str, conteudo: str) -> float:
    """Sinal lexical leve para desempatar consultas com score vetorial baixo."""
    stopwords = {"qual", "quais", "como", "para", "posso", "minha", "meu", "uma", "tem"}
    query = _tokens(pergunta) - stopwords
    content = _tokens(conteudo)
    return len(query & content) / len(query) if query else 0.0


def buscar(
    pergunta: str,
    top_k: int = 3,
) -> list[dict]:
    """
    Recupera os chunks vigentes semanticamente mais próximos da pergunta.
    """

    if not pergunta or not pergunta.strip():
        raise ValueError(
            "A pergunta não pode estar vazia."
        )

    if top_k <= 0:
        raise ValueError(
            "top_k deve ser maior que zero."
        )

    indice, registros = carregar_vectorstore()

    indices_vigentes = obter_indices_vigentes(registros)

    if not indices_vigentes:
        return []

    ''' muda só os vetores dos candidatos vigentes.'''
    vetores_vigentes = np.array(
        [
            indice.reconstruct(indice_original)
            for indice_original in indices_vigentes
        ],
        dtype="float32",
    )

    ''' Cria um índice temporário contendo somente candidatos vigentes.'''
    dimensao = indice.d

    indice_vigente = faiss.IndexFlatIP(dimensao)
    indice_vigente.add(vetores_vigentes)

    ''' Gera embedding da pergunta. Para comparar. '''
    embedding_pergunta = gerar_embedding(pergunta)

    vetor_pergunta = np.array(
        [embedding_pergunta],
        dtype="float32",
    )

    # Recupera todos os candidatos vigentes (o corpus é pequeno) e aplica um
    # desempate lexical leve. Isso evita que perguntas com termos exatos,
    # mas embedding menos próximo, sejam abstidas indevidamente.
    quantidade_resultados = len(indices_vigentes)

    scores, posicoes = indice_vigente.search(
        vetor_pergunta,
        quantidade_resultados,
    )

    candidatos = []
    for score, posicao_vigente in zip(scores[0], posicoes[0]):
        indice_original = indices_vigentes[
            int(posicao_vigente)
        ]

        registro = registros[indice_original]
        score_final = float(score) + 0.15 * _lexical_overlap(
            pergunta, registro["content"]
        )
        candidatos.append((score_final, registro))

    candidatos.sort(key=lambda item: item[0], reverse=True)
    resultados = []
    for score_final, registro in candidatos[:top_k]:

        resultados.append(
    {
        "content": registro["content"],
        "document": registro["metadata"]["source"],
        "chunk_id": registro["metadata"]["chunk_id"],
        "score": score_final,
        "status": registro["metadata"]["status"],
        "metadata": registro["metadata"],
    }
)

    return resultados


def retrieve(question: str, top_k: int = 3) -> dict:
    """Interface pública estável do retriever para as outras frentes."""

    return {"results": buscar(question, top_k=top_k)}
