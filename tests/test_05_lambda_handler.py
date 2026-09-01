import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch


HANDLER_PATH = Path("src/05_integracao_auditoria_qualidade/deployment/lambda/app.py")
SPEC = importlib.util.spec_from_file_location("concierge_lambda_handler", HANDLER_PATH)
handler = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(handler)


def event(question: str) -> dict:
    return {
        "requestContext": {"http": {"method": "POST"}},
        "body": json.dumps({"question": question}),
    }


def audit_event(trace_id: str, groups: str = "auditor") -> dict:
    return {
        "rawPath": "/audit",
        "requestContext": {
            "http": {"method": "POST", "path": "/audit"},
            "authorizer": {"jwt": {"claims": {"cognito:groups": groups}}},
        },
        "body": json.dumps({"trace_id": trace_id}),
    }


def test_lambda_bloqueia_demo_desativada():
    with patch.object(handler, "_is_demo_enabled", return_value=False):
        response = handler.lambda_handler(event("Qual o prazo de reembolso?"), None)

    assert response["statusCode"] == 503
    assert json.loads(response["body"])["status"] == "offline"


def test_lambda_encaminha_pergunta_quando_demo_ativa():
    expected = {"trace_id": "trc_demo", "decision": "ANSWER", "answer": "90 dias", "citations": [], "handoff": None}
    with patch.object(handler, "_is_demo_enabled", return_value=True), patch.object(
        handler, "run_question", return_value=expected
    ) as run_question:
        response = handler.lambda_handler(event("Qual o prazo de reembolso?"), None)

    assert response["statusCode"] == 200
    assert json.loads(response["body"])["trace_id"] == "trc_demo"
    run_question.assert_called_once_with("Qual o prazo de reembolso?")


def test_lambda_rejeita_corpo_invalido():
    invalid_event = {"requestContext": {"http": {"method": "POST"}}, "body": "{}"}
    with patch.object(handler, "_is_demo_enabled", return_value=True):
        response = handler.lambda_handler(invalid_event, None)

    assert response["statusCode"] == 400


def test_lambda_consulta_auditoria_apenas_para_grupo_auditor():
    expected = {"trace_id": "trc_demo", "decision": "ANSWER", "question": "Pergunta"}
    with patch.object(handler, "_load_audit_event", return_value=expected) as load_audit:
        response = handler.lambda_handler(audit_event("trc_demo"), None)

    assert response["statusCode"] == 200
    assert json.loads(response["body"])["trace_id"] == "trc_demo"
    load_audit.assert_called_once_with("trc_demo")


def test_lambda_rejeita_consulta_sem_grupo_auditor():
    response = handler.lambda_handler(audit_event("trc_demo", groups="viewer"), None)

    assert response["statusCode"] == 403


def test_lambda_aceita_claim_de_grupo_serializado():
    event_with_serialized_group = audit_event("trc_demo", groups='["auditor"]')

    assert handler._is_auditor(event_with_serialized_group) is True


def test_lambda_lista_rastros_recentes_para_auditor():
    recent_event = audit_event("trc_demo")
    recent_event["rawPath"] = "/audit/recent"
    recent_event["requestContext"]["http"]["path"] = "/audit/recent"
    expected = {"items": [{"trace_id": "trc_demo", "timestamp": "2026-09-01T12:00:00+00:00", "size_bytes": 10}]}
    with patch.object(handler, "_list_recent_audits", return_value=expected):
        response = handler.lambda_handler(recent_event, None)

    assert response["statusCode"] == 200
    assert json.loads(response["body"])["items"][0]["trace_id"] == "trc_demo"


def test_lista_rastros_recentes_ordena_e_omite_objetos_que_nao_sao_traces():
    client = Mock()
    client.list_objects_v2.return_value = {
        "IsTruncated": False,
        "Contents": [
            {
                "Key": "conectatel/audit/trc_antigo.json",
                "LastModified": datetime(2026, 9, 1, 10, tzinfo=timezone.utc),
                "Size": 11,
            },
            {
                "Key": "conectatel/audit/trc_recente.json",
                "LastModified": datetime(2026, 9, 1, 12, tzinfo=timezone.utc),
                "Size": 12,
            },
            {
                "Key": "conectatel/audit/indice.txt",
                "LastModified": datetime(2026, 9, 1, 13, tzinfo=timezone.utc),
                "Size": 13,
            },
        ],
    }
    with patch.dict("os.environ", {"AUDIT_S3_BUCKET": "audit-bucket"}, clear=False), patch.object(
        handler.boto3, "client", return_value=client
    ):
        result = handler._list_recent_audits()

    assert [item["trace_id"] for item in result["items"]] == ["trc_recente", "trc_antigo"]
    client.list_objects_v2.assert_called_once_with(Bucket="audit-bucket", Prefix="conectatel/audit/")
