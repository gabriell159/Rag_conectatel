import importlib
import json
from typing import Any, Dict

classifier_mod = importlib.import_module("src.04_triage.01_classifier")
handoff_mod = importlib.import_module("src.04_triage.02_handoff")

classify_escalation = classifier_mod.classify_escalation
build_escalation_payload = handoff_mod.build_escalation_payload


def process_event(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    body = event.get("body", event)
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            body = {}

    question = body.get("question", "")
    if not question:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Campo 'question' e obrigatorio."})
        }

    should_escalate, rule_info = classify_escalation(question)

    if should_escalate and rule_info is not None:
        handoff_data = build_escalation_payload(question, rule_info)
        return {
            "statusCode": 200,
            "body": {
                "decision": "ESCALATE",
                "answer": None,
                "handoff": handoff_data
            }
        }

    try:
        retriever_mod = importlib.import_module("src.02_rag.07_retriever")
        answer_mod = importlib.import_module("src.03_concierge.04_answer")
        
        search_results = retriever_mod.buscar(question)
        response_text = answer_mod.answer_question(question, search_results)
        
        return {
            "statusCode": 200,
            "body": {
                "decision": "ANSWER",
                "answer": response_text,
                "handoff": None
            }
        }
    except Exception as err:
        fallback_rule = {
            "category_key": "Falha na execucao da cadeia RAG/Concierge",
            "priority": "alta"
        }
        handoff_data = build_escalation_payload(question, fallback_rule)
        return {
            "statusCode": 200,
            "body": {
                "decision": "ESCALATE",
                "answer": None,
                "handoff": handoff_data,
                "internal_error": str(err)
            }
        }


def lambda_handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    return process_event(event, context)