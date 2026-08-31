"""Handler HTTP da demonstração interna do Concierge na AWS Lambda."""

import json
import logging
import os
import time
from importlib import import_module
from typing import Any

import boto3


LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)
_demo_state: bool | None = None
_demo_state_loaded_at = 0.0
DEMO_CACHE_SECONDS = 30
MAX_QUESTION_LENGTH = 800
run_question = import_module("src.03_concierge.05_orchestrator").run_question


def _response(status_code: int, payload: dict[str, Any]) -> dict[str, Any]:
    origin = os.getenv("ALLOWED_ORIGIN", "*")
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json; charset=utf-8",
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        },
        "body": json.dumps(payload, ensure_ascii=False),
    }


def _is_demo_enabled() -> bool:
    """Obtém o estado compartilhado da demo, com cache curto por instância."""

    global _demo_state, _demo_state_loaded_at
    if _demo_state is not None and time.monotonic() - _demo_state_loaded_at < DEMO_CACHE_SECONDS:
        return _demo_state

    parameter_name = os.getenv("DEMO_ENABLED_PARAMETER", "").strip()
    value = os.getenv("DEMO_ENABLED", "false")
    if parameter_name:
        try:
            value = boto3.client("ssm").get_parameter(Name=parameter_name)["Parameter"]["Value"]
        except Exception as error:
            print(f"Não foi possível consultar o estado da demonstração: {error}")
            value = "false"  # Falha fechada: não gera chamadas Bedrock sem controle.

    _demo_state = value.strip().casefold() in {"1", "true", "on", "yes", "sim"}
    _demo_state_loaded_at = time.monotonic()
    return _demo_state


def _question_from_event(event: dict[str, Any]) -> str:
    body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raise ValueError("Corpo codificado em base64 não é suportado.")
    try:
        payload = json.loads(body) if isinstance(body, str) else body
    except json.JSONDecodeError as error:
        raise ValueError("O corpo deve ser um JSON válido.") from error
    question = payload.get("question") if isinstance(payload, dict) else None
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Informe uma pergunta no campo 'question'.")
    if len(question.strip()) > MAX_QUESTION_LENGTH:
        raise ValueError(f"A pergunta deve ter no máximo {MAX_QUESTION_LENGTH} caracteres.")
    return question.strip()


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    method = event.get("requestContext", {}).get("http", {}).get("method", "POST")
    if method == "OPTIONS":
        return _response(204, {})
    if method != "POST":
        return _response(405, {"message": "Use POST /ask."})
    if not _is_demo_enabled():
        return _response(503, {"status": "offline", "message": "A demonstração está desativada."})
    try:
        result = run_question(_question_from_event(event))
        return _response(200, result)
    except ValueError as error:
        return _response(400, {"message": str(error)})
    except Exception:
        LOGGER.exception("Erro ao processar uma pergunta no Concierge")
        return _response(500, {"message": "Não foi possível processar a pergunta."})
