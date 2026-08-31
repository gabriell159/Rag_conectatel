import os
from typing import Any

import boto3


DEFAULT_MODEL_ID = "mistral.mistral-large-3-675b-instruct"
DEFAULT_REGION = "us-east-1"
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TEMPERATURE = 0.0
DEFAULT_TOP_P = 1.0


def get_bedrock_model_id() -> str:
    """Retorna o identificador configurado para o modelo generativo."""

    model_id = os.getenv("BEDROCK_MODEL_ID", DEFAULT_MODEL_ID)

    if not model_id.strip():
        raise ValueError("BEDROCK_MODEL_ID deve ser uma string não vazia.")

    return model_id.strip()


def create_bedrock_client() -> Any:
    """Cria um cliente Bedrock Runtime com a cadeia padrão de credenciais."""

    region = os.getenv("AWS_REGION", DEFAULT_REGION)

    if not region.strip():
        raise ValueError("AWS_REGION deve ser uma string não vazia.")

    session_arguments = {"region_name": region.strip()}
    profile = os.getenv("AWS_PROFILE")

    if profile and profile.strip():
        session_arguments["profile_name"] = profile.strip()

    session = boto3.Session(**session_arguments)

    return session.client("bedrock-runtime")


def generate_text(
    system_prompt: str,
    user_prompt: str,
    client: Any | None = None,
) -> str:
    """Gera texto com o modelo configurado pela Converse API."""

    if not isinstance(system_prompt, str) or not system_prompt.strip():
        raise ValueError("system_prompt deve ser uma string não vazia.")

    if not isinstance(user_prompt, str) or not user_prompt.strip():
        raise ValueError("user_prompt deve ser uma string não vazia.")

    if client is None:
        client = create_bedrock_client()

    response = client.converse(
        modelId=get_bedrock_model_id(),
        system=[{"text": system_prompt}],
        messages=[
            {
                "role": "user",
                "content": [{"text": user_prompt}],
            }
        ],
        inferenceConfig={
            "maxTokens": DEFAULT_MAX_TOKENS,
            "temperature": DEFAULT_TEMPERATURE,
            "topP": DEFAULT_TOP_P,
        },
    )

    if not isinstance(response, dict):
        raise RuntimeError("Resposta inválida do Amazon Bedrock: output ausente.")

    output = response.get("output")

    if not isinstance(output, dict):
        raise RuntimeError("Resposta inválida do Amazon Bedrock: output ausente.")

    message = output.get("message")

    if not isinstance(message, dict):
        raise RuntimeError("Resposta inválida do Amazon Bedrock: message ausente.")

    content = message.get("content")

    if not isinstance(content, list) or not content:
        raise RuntimeError("Resposta inválida do Amazon Bedrock: content ausente.")

    for block in content:
        if not isinstance(block, dict):
            continue

        text = block.get("text")

        if isinstance(text, str) and text.strip():
            return text.strip()

    raise RuntimeError(
        "Resposta inválida do Amazon Bedrock: nenhum texto válido encontrado."
    )
