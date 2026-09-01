import importlib
import pytest

classifier_mod = importlib.import_module("src.04_triage.01_classifier")
handoff_mod = importlib.import_module("src.04_triage.02_handoff")

classify_escalation = classifier_mod.classify_escalation
ESCALATION_RULES = classifier_mod.ESCALATION_RULES
build_escalation_payload = handoff_mod.build_escalation_payload


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

    def test_valor_alto_informativo_nao_e_escalonamento(self):
        should_escalate, rule_info = classify_escalation(
            "O plano premium custa R$ 599,00?"
        )
        assert should_escalate is False
        assert rule_info is None


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
        assert payload["rule_id"] == "fraude"
        assert payload["documento_fonte_consultado"] == "corpus/politicas/politica_suporte_escalonamento.md"
        assert "R$ 600,00" in payload["historico_ja_levantado"]

