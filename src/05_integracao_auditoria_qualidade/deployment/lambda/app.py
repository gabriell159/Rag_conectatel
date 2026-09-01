"""Handler HTTP da demonstração interna do Concierge na AWS Lambda."""

import json
import logging
import os
import re
import time
from importlib import import_module
from typing import Any

import boto3
from botocore.exceptions import ClientError


LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)
_demo_state: bool | None = None
_demo_state_loaded_at = 0.0
DEMO_CACHE_SECONDS = 30
MAX_QUESTION_LENGTH = 800
MAX_RECENT_AUDITS = 20
TRACE_ID_PATTERN = "trc_"
run_question = import_module("src.03_concierge.05_orchestrator").run_question


def _response(status_code: int, payload: dict[str, Any]) -> dict[str, Any]:
    origin = os.getenv("ALLOWED_ORIGIN", "*")
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json; charset=utf-8",
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
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


def _trace_id_from_event(event: dict[str, Any]) -> str:
    body = event.get("body") or "{}"
    try:
        payload = json.loads(body) if isinstance(body, str) else body
    except json.JSONDecodeError as error:
        raise ValueError("O corpo deve ser um JSON válido.") from error
    trace_id = payload.get("trace_id") if isinstance(payload, dict) else None
    if not isinstance(trace_id, str) or not trace_id.startswith(TRACE_ID_PATTERN):
        raise ValueError("Informe um trace_id válido.")
    if len(trace_id) > 100 or not trace_id.replace("_", "").isalnum():
        raise ValueError("Informe um trace_id válido.")
    return trace_id


def _is_auditor(event: dict[str, Any]) -> bool:
    claims = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("jwt", {})
        .get("claims", {})
    )
    groups = claims.get("cognito:groups", "")
    if isinstance(groups, list):
        return "auditor" in groups
    # O API Gateway pode entregar o claim como "auditor", "auditor,operador"
    # ou como uma lista serializada, por exemplo '["auditor"]'.
    normalized_groups = {
        item.strip(" []'\"")
        for item in re.split(r"[,\s]+", str(groups))
        if item.strip(" []'\"")
    }
    return "auditor" in normalized_groups


def _load_audit_event(trace_id: str) -> dict[str, Any]:
    bucket = os.getenv("AUDIT_S3_BUCKET", "").strip()
    prefix = os.getenv("AUDIT_S3_PREFIX", "conectatel/audit").strip().strip("/")
    if not bucket:
        raise RuntimeError("Auditoria compartilhada não configurada.")
    key = f"{prefix}/{trace_id}.json"
    try:
        response = boto3.client("s3").get_object(Bucket=bucket, Key=key)
        return json.loads(response["Body"].read().decode("utf-8"))
    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code", "")
        if error_code in {"NoSuchKey", "404", "NotFound"}:
            raise ValueError("Trace não encontrado na auditoria.") from error
        raise


def _list_recent_audits() -> dict[str, list[dict[str, Any]]]:
    """Lista referências recentes sem expor o conteúdo dos eventos."""

    bucket = os.getenv("AUDIT_S3_BUCKET", "").strip()
    prefix = os.getenv("AUDIT_S3_PREFIX", "conectatel/audit").strip().strip("/")
    if not bucket:
        raise RuntimeError("Auditoria compartilhada não configurada.")

    client = boto3.client("s3")
    contents: list[dict[str, Any]] = []
    continuation_token: str | None = None
    while True:
        request: dict[str, Any] = {"Bucket": bucket, "Prefix": f"{prefix}/"}
        if continuation_token:
            request["ContinuationToken"] = continuation_token
        response = client.list_objects_v2(**request)
        contents.extend(response.get("Contents", []))
        if not response.get("IsTruncated"):
            break
        continuation_token = response.get("NextContinuationToken")

    items = []
    for item in sorted(contents, key=lambda value: value["LastModified"], reverse=True):
        key = item.get("Key", "")
        if not key.endswith(".json"):
            continue
        trace_id = key.rsplit("/", 1)[-1].removesuffix(".json")
        if trace_id.startswith(TRACE_ID_PATTERN):
            items.append({
                "trace_id": trace_id,
                "timestamp": item["LastModified"].isoformat(),
                "size_bytes": item.get("Size", 0),
            })
        if len(items) == MAX_RECENT_AUDITS:
            break
    return {"items": items}


def _path_from_event(event: dict[str, Any]) -> str:
    return event.get("rawPath") or event.get("requestContext", {}).get("http", {}).get("path", "/ask")


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    method = event.get("requestContext", {}).get("http", {}).get("method", "POST")
    path = _path_from_event(event)
    if method == "OPTIONS":
        return _response(204, {})
    if method != "POST":
        return _response(405, {"message": "Use POST."})
    if path == "/audit":
        if not _is_auditor(event):
            return _response(403, {"message": "Acesso restrito a auditores."})
        try:
            return _response(200, _load_audit_event(_trace_id_from_event(event)))
        except ValueError as error:
            return _response(400, {"message": str(error)})
        except Exception:
            LOGGER.exception("Erro ao consultar rastro de auditoria")
            return _response(500, {"message": "Não foi possível consultar a auditoria."})
    if path == "/audit/recent":
        if not _is_auditor(event):
            return _response(403, {"message": "Acesso restrito a auditores."})
        try:
            return _response(200, _list_recent_audits())
        except Exception:
            LOGGER.exception("Erro ao listar rastros de auditoria")
            return _response(500, {"message": "Não foi possível listar a auditoria."})
    if path != "/ask":
        return _response(404, {"message": "Rota não encontrada."})
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
