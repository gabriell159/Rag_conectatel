import importlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


orchestrator = importlib.import_module("src.03_concierge.05_orchestrator")


class ConciergeIntegratedTests(unittest.TestCase):
    def test_contestar_de_forma_informativa_nao_escalona(self):
        self.assertIsNone(
            orchestrator.classify_handoff(
                "Por quanto tempo posso contestar uma cobranca na fatura?"
            )
        )

    def test_pergunta_sobre_regra_de_fraude_nao_escalona(self):
        self.assertIsNone(
            orchestrator.classify_handoff(
                "Quando uma suspeita de fraude deve ser escalada?"
            )
        )

    def test_relato_real_de_fraude_continua_escalonando(self):
        handoff = orchestrator.classify_handoff(
            "Acredito que fizeram fraude usando minha linha."
        )
        self.assertIsNotNone(handoff)
        self.assertEqual(handoff["reason"], "suspeita de fraude")
        self.assertEqual(handoff["rule_id"], "fraude")
        self.assertEqual(handoff["priority"], "alta")
        self.assertEqual(handoff["priority_code"], "HIGH")
        self.assertTrue(handoff["protocolo_atendimento"].startswith("PROT-"))

    def test_valor_alto_sem_contestacao_nao_escalona(self):
        self.assertIsNone(
            orchestrator.classify_handoff("O plano premium custa R$ 599,00?")
        )

    def test_valor_basico_com_evidencia_pode_ser_deterministico(self):
        chunks = [{
            "content": "O valor mensal do Conecta Basico e R$ 49,90.",
            "metadata": {"source": "plano_conecta_basico.md"},
        }]
        self.assertEqual(
            orchestrator._deterministic_answer(
                "Qual o valor mensal do Conecta Basico?", chunks
            ),
            "O valor mensal do Conecta Básico é R$ 49,90.",
        )

    def test_fraude_escalates_com_handoff_e_auditoria(self):
        # O teste cobre o contrato local; publicação S3 é coberta nas integrações.
        # Isso evita depender de credenciais, rede ou proxy durante a suíte unitária.
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"AUDIT_S3_BUCKET": ""}
        ):
            event = orchestrator.run_question(
                "Acho que fizeram uma fraude usando minha linha.",
                Path(directory) / "audit.jsonl",
            )
        self.assertEqual(event["decision"], "ESCALATE")
        self.assertEqual(event["handoff"]["priority"], "alta")
        self.assertTrue(event["trace_id"].startswith("trc_"))

    def test_pergunta_sem_evidencia_direta_recusa(self):
        chunks = [{
            "content": "O cliente pode contestar valores em até 90 dias.",
            "document": "politica_reembolso_v2.md",
            "chunk_id": "c1",
            "score": 0.8,
            "status": "vigente",
            "metadata": {"source": "politica_reembolso_v2.md", "doc_family_id": "politica-reembolso", "version_ordinal": 2, "status": "vigente"},
        }]
        self.assertFalse(orchestrator._direct_evidence("Qual o prazo para pedir reembolso?", chunks))


if __name__ == "__main__":
    unittest.main()
