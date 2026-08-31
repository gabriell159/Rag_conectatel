import importlib.util
import json
from pathlib import Path
from unittest.mock import patch


HANDLER_PATH = Path("src/05_integracao_auditoria_qualidade/deployment/lambda/app.py")
SPEC = importlib.util.spec_from_file_location("concierge_lambda_handler", HANDLER_PATH)
handler = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(handler)


def event(question: str) -> dict:
    return {
        "requestContext": {"http": {"method": "POST"}},
        "body": json.dumps({"question": question}),
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
