import json
import os
import time
import boto3
from botocore.exceptions import BotoCoreError, ClientError

REGION = os.getenv("AWS_REGION", "us-east-1")
MODEL_ID = "amazon.titan-embed-text-v2:0"
EMBEDDING_DIMENSIONS = 1024


def criar_sessao_boto3() -> boto3.Session:
    """
    A função é para criar uma sessão boto3.
    Em ambiente local, pode usar AWS_PROFILE.
    Em Lambda/AWS, utiliza automaticamente a IAM Role.
    """

    profile = os.getenv("AWS_PROFILE")

    if profile:
        return boto3.Session(
            profile_name=profile,
            region_name=REGION,
        )

    return boto3.Session(
        region_name=REGION,
    )


def criar_cliente_bedrock():
    """
    Cria o cliente do Amazon Bedrock Runtime, para poder rodar as chamadas.
    """

    session = criar_sessao_boto3()

    return session.client(
        "bedrock-runtime",
        region_name=REGION,
    )


# def gerar_embedding(texto: str) -> list[float]:
#     """
#     Gera o embedding de um texto usando
#     Amazon Titan Text Embeddings V2.
#     """

#     if not texto or not texto.strip():
#         raise ValueError(
#             "Não é possível gerar embedding de texto vazio."
#         )

#     cliente = criar_cliente_bedrock()

#     body = {
#         "inputText": texto,
#         "dimensions": EMBEDDING_DIMENSIONS,
#         "normalize": True,
#     }

#     try:
#         response = cliente.invoke_model(
#             modelId=MODEL_ID,
#             contentType="application/json",
#             accept="application/json",
#             body=json.dumps(body),
#         )

#         response_body = json.loads(
#             response["body"].read()
#         )

#         return response_body["embedding"]

#     except (ClientError, BotoCoreError) as error:
#         raise RuntimeError(
#             f"Erro ao gerar embedding no Amazon Bedrock: {error}"
#         ) from error

def gerar_embedding(
    texto: str,
    max_tentativas: int = 3,
) -> list[float]:
    """
    Gera os embeddings usando Amazon Titan Text Embeddings V2.
    Em caso de erro transitório, realiza novas tentativas
    antes de interromper o processamento.
    (Não tantas, para não sobrecarregar o serviço e evitar custos desnecessários.)
    """

    if not texto or not texto.strip():
        raise ValueError(
            "Não é possível gerar embedding de texto vazio."
        )

    cliente = criar_cliente_bedrock()

    body = {
        "inputText": texto,
        "dimensions": EMBEDDING_DIMENSIONS,
        "normalize": True,
    }

    for tentativa in range(1, max_tentativas + 1):
        try:
            response = cliente.invoke_model(
                modelId=MODEL_ID,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body),
            )

            response_body = json.loads(
                response["body"].read()
            )

            return response_body["embedding"]

        except (ClientError, BotoCoreError) as error:
            if tentativa == max_tentativas:
                raise RuntimeError(
                    "Falha ao gerar embedding após "
                    f"{max_tentativas} tentativas: {error}"
                ) from error

            espera = tentativa * 2

            print(
                f"Erro na tentativa {tentativa}. "
                f"Nova tentativa em {espera}s..."
            )

            time.sleep(espera)

    raise RuntimeError(
        "Não foi possível gerar o embedding."
    )

def gerar_embeddings_chunks(
    chunks: list[dict],
) -> list[dict]:
    """
    Gera embeddings para uma lista de chunks.
    """

    chunks_com_embeddings = []

    total = len(chunks)

    for indice, chunk in enumerate(chunks, start=1):
        print(
            f"Gerando embedding {indice}/{total}: "
            f"{chunk['metadata']['chunk_id']}"
        )

        embedding = gerar_embedding(
            chunk["content"]
        )

        chunks_com_embeddings.append(
            {
                "content": chunk["content"],
                "metadata": chunk["metadata"],
                "embedding": embedding,
            }
        )

    return chunks_com_embeddings