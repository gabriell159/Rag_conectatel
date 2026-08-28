"""
index.py — Etapa 2 do pipeline: geração de embeddings e indexação.

Lê data/processed/chunks.jsonl, gera um embedding por chunk usando o
modelo Titan Embeddings via Bedrock, e salva um índice vetorial simples
(array numpy + metadados) em data/processed/index.npz.

Este scaffold usa um índice em memória (numpy) para manter o exemplo
mínimo e sem dependências externas de banco vetorial. A squad pode
substituir esta etapa por um vector store gerenciado (ex.: OpenSearch
Serverless, coleção vetorial gerenciada) mantendo os mesmos campos de
metadados de vigência em cada registro.

Uso:
    python src/index.py
"""

import json
import os
from pathlib import Path

import boto3
import numpy as np

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

CHUNKS_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "chunks.jsonl"
INDEX_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "index.npz"

REGION = os.environ.get("AWS_REGION", "us-east-1")
EMBEDDING_MODEL_ID = os.environ.get("BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")


def embed_text(client, text: str) -> list[float]:
    response = client.invoke_model(
        modelId=EMBEDDING_MODEL_ID,
        body=json.dumps({"inputText": text}),
        contentType="application/json",
        accept="application/json",
    )
    payload = json.loads(response["body"].read())
    return payload["embedding"]


def main() -> None:
    if not CHUNKS_PATH.exists():
        print(f"Arquivo {CHUNKS_PATH} não encontrado. Rode src/ingest.py primeiro.")
        return

    records = [json.loads(line) for line in CHUNKS_PATH.read_text(encoding="utf-8").splitlines() if line]
    if not records:
        print("Nenhum chunk para indexar.")
        return

    client = boto3.client("bedrock-runtime", region_name=REGION)

    vectors = []
    metadata = []
    for i, record in enumerate(records, start=1):
        vector = embed_text(client, record["text"])
        vectors.append(vector)
        metadata.append(record)
        if i % 10 == 0 or i == len(records):
            print(f"Embeddings gerados: {i}/{len(records)}")

    matrix = np.array(vectors, dtype=np.float32)
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        INDEX_PATH,
        vectors=matrix,
        metadata=json.dumps(metadata, ensure_ascii=False),
    )
    print(f"Índice salvo em {INDEX_PATH} ({matrix.shape[0]} vetores, dimensão {matrix.shape[1]})")


if __name__ == "__main__":
    main()
