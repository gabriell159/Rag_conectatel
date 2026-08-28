import json
from pathlib import Path
import faiss
import numpy as np

from src.rag.embeddings import gerar_embedding
from src.rag.s3_storage import download_vectorstore

VECTORSTORE_PATH = Path("data/processed/vectorstore")
INDEX_PATH = VECTORSTORE_PATH / "index.faiss"
METADATA_PATH = VECTORSTORE_PATH / "metadata.json"


def carregar_vectorstore(
    index_path: Path = INDEX_PATH,
    metadata_path: Path = METADATA_PATH,
):
    """
    Carrega o índice FAISS e os metadados que fram persistidos no data/processed/vectorstore.
    """

    if not index_path.exists() or not metadata_path.exists():
        print(
            "Vector store local não encontrado. "
            "Recuperando do Amazon S3..."
        )

    download_vectorstore()

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

    quantidade_resultados = min(
        top_k,
        len(indices_vigentes),
    )

    scores, posicoes = indice_vigente.search(
        vetor_pergunta,
        quantidade_resultados,
    )

    resultados = []

    for score, posicao_vigente in zip(
        scores[0],
        posicoes[0],
    ):
        indice_original = indices_vigentes[
            int(posicao_vigente)
        ]

        registro = registros[indice_original]

        resultados.append(
    {
        "content": registro["content"],
        "document": registro["metadata"]["source"],
        "chunk_id": registro["metadata"]["chunk_id"],
        "score": float(score),
        "status": registro["metadata"]["status"],
        "metadata": registro["metadata"],
    }
)

    return resultados