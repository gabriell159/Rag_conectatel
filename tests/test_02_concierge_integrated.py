import importlib
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
        with tempfile.TemporaryDirectory() as directory:
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
