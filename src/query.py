"""
query.py — Etapa 3 do pipeline: consulta, filtro de vigência, geração e log.

Fluxo (ver Parte 2 e Parte 3 do desafio):
  1. Embute a pergunta do usuário.
  2. Filtra os candidatos por metadados de vigência de forma determinística
     (status == "vigente") ANTES de calcular similaridade — isso não pode
     ser delegado a uma instrução de prompt.
  3. Calcula similaridade de cosseno entre a pergunta e os chunks vigentes.
  4. Se o melhor score ficar abaixo de ABSTENTION_THRESHOLD, responde
     "não sei" sem chamar o modelo de geração.
  5. Caso contrário, gera a resposta com citação da fonte via Bedrock.
  6. Registra a interação na trilha de auditoria (ver src/audit_log.py).

Uso:
    python src/query.py "sua pergunta aqui"
"""

import json
import os
import sys
from pathlib import Path

import boto3
import numpy as np

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_log import log_interaction  # noqa: E402

INDEX_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "index.npz"

REGION = os.environ.get("AWS_REGION", "us-east-1")
EMBEDDING_MODEL_ID = os.environ.get("BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
GENERATION_MODEL_ID = os.environ.get(
    "BEDROCK_GENERATION_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"
)
ABSTENTION_THRESHOLD = float(os.environ.get("ABSTENTION_THRESHOLD", "0.35"))
TOP_K = 4


def embed_text(client, text: str) -> np.ndarray:
    response = client.invoke_model(
        modelId=EMBEDDING_MODEL_ID,
        body=json.dumps({"inputText": text}),
        contentType="application/json",
        accept="application/json",
    )
    payload = json.loads(response["body"].read())
    return np.array(payload["embedding"], dtype=np.float32)


def cosine_similarity(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-9)
    matrix_norm = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-9)
    return matrix_norm @ query_norm


def filter_vigentes(metadata: list[dict]) -> list[int]:
    """Filtro determinístico de vigência: retorna os índices de chunks com
    status == "vigente". Esta é a barreira que impede o sistema de citar
    uma versão revogada — ela roda ANTES da pontuação de similaridade,
    não depois, e não depende de o modelo "lembrar" de checar a data."""
    return [i for i, m in enumerate(metadata) if m.get("status") == "vigente"]


def generate_answer(client, question: str, context_chunks: list[dict]) -> str:
    context_text = "\n\n".join(
        f"[Fonte: {c['source_file']} | doc_family_id={c['doc_family_id']}]\n{c['text']}"
        for c in context_chunks
    )
    prompt = (
        "Responda à pergunta do usuário usando SOMENTE as fontes abaixo. "
        "Cite explicitamente o arquivo-fonte usado na resposta. "
        "Se as fontes não contiverem a resposta, diga que não sabe.\n\n"
        f"FONTES:\n{context_text}\n\nPERGUNTA: {question}"
    )
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 500,
        "messages": [{"role": "user", "content": prompt}],
    }
    response = client.invoke_model(
        modelId=GENERATION_MODEL_ID,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )
    payload = json.loads(response["body"].read())
    return payload.get("content", [{}])[0].get("text", "").strip()


def answer_question(question: str) -> dict:
    if not INDEX_PATH.exists():
        raise FileNotFoundError("Índice não encontrado. Rode src/ingest.py e src/index.py primeiro.")

    data = np.load(INDEX_PATH, allow_pickle=False)
    matrix = data["vectors"]
    metadata = json.loads(str(data["metadata"]))

    client = boto3.client("bedrock-runtime", region_name=REGION)
    query_vec = embed_text(client, question)

    vigente_idx = filter_vigentes(metadata)
    if not vigente_idx:
        result = {
            "question": question,
            "decision": "escalou",
            "source": None,
            "answer": "Não sei. Não há documento vigente que cubra esta pergunta no corpus.",
        }
        log_interaction(**result)
        return result

    sub_matrix = matrix[vigente_idx]
    similarities = cosine_similarity(query_vec, sub_matrix)
    ranked = sorted(zip(vigente_idx, similarities), key=lambda x: x[1], reverse=True)
    top_score = float(ranked[0][1])

    if top_score < ABSTENTION_THRESHOLD:
        result = {
            "question": question,
            "decision": "não sei",
            "source": None,
            "answer": "Não sei. Não encontrei uma fonte vigente com confiança suficiente para responder.",
            "top_score": top_score,
        }
        log_interaction(**result)
        return result

    top_chunks = [metadata[i] for i, _ in ranked[:TOP_K]]
    answer_text = generate_answer(client, question, top_chunks)

    result = {
        "question": question,
        "decision": "respondeu",
        "source": top_chunks[0]["source_file"],
        "answer": answer_text,
        "top_score": top_score,
    }
    log_interaction(**result)
    return result


def main() -> None:
    if len(sys.argv) < 2:
        print('Uso: python src/query.py "sua pergunta aqui"')
        return
    question = " ".join(sys.argv[1:])
    result = answer_question(question)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
