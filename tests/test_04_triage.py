import importlib
import json
import pytest
from unittest.mock import patch, MagicMock

classifier_mod = importlib.import_module("src.04_triage.01_classifier")
handoff_mod = importlib.import_module("src.04_triage.02_handoff")
handler_mod = importlib.import_module("src.04_triage.03_handler")

classify_escalation = classifier_mod.classify_escalation
ESCALATION_RULES = classifier_mod.ESCALATION_RULES
build_escalation_payload = handoff_mod.build_escalation_payload
process_event = handler_mod.process_event
lambda_handler = handler_mod.lambda_handler


class TestClassifier:
    @pytest.mark.parametrize(
        "question,expected_rule",
        [
            ("Estou sofrendo um golpe, minha linha foi clonada!", "fraude"),
            ("Quero contestar a cobrança de R$ 550,00 na minha fatura", "contestacao_alta_valor"),
            ("Não concordo com a multa por cancelamento antecipado", "multa_fidelidade_contestada"),
            ("O titular faleceu e preciso alterar o nome da conta", "titularidade_falecimento"),
            ("Abri uma reclamação no PROCON e vou acionar a justiça", "reclamacao_orgao_externo"),
            ("Fui vítima de discriminação e agressão por um atendente", "assedio_discriminacao"),
            ("Preciso de uma visita técnica pois estou sem sinal há dias", "visita_tecnica_presencial"),
        ],
    )
    def test_classify_escalation_positive_cases(self, question: str, expected_rule: str):
        should_escalate, rule_info = classify_escalation(question)
        assert should_escalate is True
        assert rule_info is not None
        assert rule_info["rule_id"] == expected_rule

    @pytest.mark.parametrize(
        "question",
        [
            "Como faço para consultar a segunda via da minha fatura?",
            "Qual o valor da multa rescisória em caso de cancelamento?",
            "Como funciona a portabilidade de número?",
            "Qual a franquia de dados do plano Conecta Básico?",
        ],
    )
    def test_classify_escalation_negative_cases(self, question: str):
        should_escalate, rule_info = classify_escalation(question)
        assert should_escalate is False
        assert rule_info is None

    def test_classify_escalation_abstention_threshold(self):
        should_escalate, rule_info = classify_escalation(
            question="Pergunta genérica sem palavras-chave",
            top_score=0.15,
            abstention_threshold=0.30,
        )
        assert should_escalate is True
        assert rule_info is not None
        assert rule_info["rule_id"] == "ausencia_fonte_suficiente"


class TestHandoff:
    def test_build_escalation_payload_structure(self):
        rule_info = {
            "rule_id": "fraude",
            "category_key": "Suspeita de fraude",
            "priority": "alta",
        }
        question = "Identifiquei uma cobrança indevida de R$ 600,00 por um golpe."

        payload = build_escalation_payload(question, rule_info)

        required_policy_fields = [
            "protocolo_atendimento",
            "categoria_motivo",
            "resumo_caso",
            "historico_ja_levantado",
            "documento_fonte_consultado",
            "dados_contato_retorno",
            "urgencia",
            "produto_servico_envolvido",
            "status_escalonamento",
            "data_hora_escalonamento",
        ]
        for field in required_policy_fields:
            assert field in payload
            assert payload[field] is not None

        required_contract_fields = ["reason", "summary", "requested_action", "priority"]
        for field in required_contract_fields:
            assert field in payload
            assert payload[field] is not None

        assert payload["priority"] == "HIGH"
        assert payload["reason"] == "Suspeita de fraude"
        assert "R$ 600,00" in payload["historico_ja_levantado"]


class TestHandler:
    def test_process_event_empty_question(self):
        response = process_event({"body": json.dumps({})})
        assert response["statusCode"] == 400
        assert "error" in response["body"]

    def test_process_event_escalation_trigger(self):
        event = {"question": "Minha linha foi clonada, sofri um golpe!"}
        response = process_event(event)

        assert response["statusCode"] == 200
        body = response["body"]
        assert body["decision"] == "ESCALATE"
        assert body["answer"] is None
        assert body["handoff"] is not None
        assert body["handoff"]["reason"] == "Suspeita de fraude"

    @patch("importlib.import_module")
    def test_process_event_rag_answer_trigger(self, mock_importlib):
        mock_retriever = MagicMock()
        mock_retriever.buscar.return_value = [{"content": "Informação sobre fatura", "score": 0.9}]

        mock_answer = MagicMock()
        mock_answer.answer_question.return_value = "Sua fatura vence todo dia 10."

        def import_side_effect(name):
            if name == "src.02_rag.07_retriever":
                return mock_retriever
            if name == "src.03_concierge.04_answer":
                return mock_answer
            raise ModuleNotFoundError(name)

        mock_importlib.side_effect = import_side_effect

        event = {"question": "Qual é a data de vencimento da minha fatura?"}
        response = process_event(event)

        assert response["statusCode"] == 200
        body = response["body"]
        assert body["decision"] == "ANSWER"
        assert body["answer"] == "Sua fatura vence todo dia 10."
        assert body["handoff"] is None

    @patch("importlib.import_module", side_effect=Exception("Falha na busca vetorial"))
    def test_process_event_exception_fallback(self, mock_importlib):
        event = {"question": "Qual é o plano mais barato?"}
        response = process_event(event)

        assert response["statusCode"] == 200
        body = response["body"]
        assert body["decision"] == "ESCALATE"
        assert "internal_error" in body
        assert body["handoff"]["reason"] == "Falha na execucao da cadeia RAG/Concierge"

    def test_lambda_handler_proxy(self):
        event = {"question": "Suspeita de fraude na minha conta"}
        response = lambda_handler(event)
        assert response["statusCode"] == 200
        assert response["body"]["decision"] == "ESCALATE"