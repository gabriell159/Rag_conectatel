import json
import importlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

AuditLogger = importlib.import_module("src.05_integracao_auditoria_qualidade.02_audit").AuditLogger
citation = importlib.import_module("src.05_integracao_auditoria_qualidade.00_contract").citation
run_mock = importlib.import_module("src.05_integracao_auditoria_qualidade.03_offline_contract_mock").run_mock
orchestrator = importlib.import_module("src.03_concierge.05_orchestrator")
retriever = importlib.import_module("src.02_rag.07_retriever")


class Frente5ContractTests(unittest.TestCase):
    def test_fluxo_real_answer_valida_contrato_e_audita(self):
        chunks = [{
            "content": "O prazo de reembolso e de 90 dias corridos.",
            "score": 0.91,
            "status": "vigente",
            "chunk_id": "reembolso-001",
            "metadata": {
                "source": "politica_reembolso_v2.md",
                "doc_family_id": "politica-reembolso",
                "version_ordinal": 2,
                "status": "vigente",
            },
        }]
        with tempfile.TemporaryDirectory() as directory, patch.object(
            retriever, "buscar", return_value=chunks
        ), patch.object(
            orchestrator, "answer_question",
            return_value={"decision": "ANSWER", "answer": "90 dias corridos."},
        ):
            event = orchestrator.run_question(
                "Qual e o prazo de reembolso?", Path(directory) / "audit.jsonl"
            )
        self.assertEqual(event["decision"], "ANSWER")
        self.assertEqual(event["citations"][0]["status"], "vigente")
        self.assertIsNone(event["handoff"])

    def test_fluxo_real_no_answer_remove_citacoes(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
            retriever, "buscar", return_value=[]
        ), patch.object(
            orchestrator, "answer_question",
            return_value={"decision": "NO_ANSWER", "answer": "NO_ANSWER"},
        ):
            event = orchestrator.run_question(
                "Qual e a previsao do tempo?", Path(directory) / "audit.jsonl"
            )
        self.assertEqual(event["decision"], "NO_ANSWER")
        self.assertEqual(event["citations"], [])
        self.assertIsNone(event["handoff"])

    def test_answer_cita_somente_documento_vigente(self):
        with tempfile.TemporaryDirectory() as directory:
            event = run_mock("Qual e o prazo de reembolso?", Path(directory) / "audit.jsonl")
        self.assertEqual(event["decision"], "ANSWER")
        self.assertEqual(event["citations"][0]["version_ordinal"], 2)
        self.assertNotIn("v1", event["citations"][0]["source_file"])

    def test_no_answer_nao_tem_fonte(self):
        with tempfile.TemporaryDirectory() as directory:
            event = run_mock("Qual e a previsao do tempo?", Path(directory) / "audit.jsonl")
        self.assertEqual(event["decision"], "NO_ANSWER")
        self.assertEqual(event["citations"], [])

    def test_escalate_tem_handoff_completo(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            event = run_mock("Estou sem sinal.", path)
            recovered = AuditLogger(path).find_by_trace_id(event["trace_id"])
        self.assertEqual(event["decision"], "ESCALATE")
        self.assertEqual(set(event["handoff"]), {"reason", "summary", "requested_action", "priority"})
        self.assertEqual(recovered["trace_id"], event["trace_id"])

    def test_contrato_rejeita_citacao_revogada(self):
        with self.assertRaises(ValueError):
            citation("politica_reembolso_v1.md", "politica-reembolso", 1, "revogado")

    def test_golden_set_tem_casos_minimos(self):
        cases = json.loads(Path("data/05_golden_set_frente5.json").read_text(encoding="utf-8"))
        self.assertEqual({case["expected_decision"] for case in cases}, {"ANSWER", "NO_ANSWER", "ESCALATE"})


if __name__ == "__main__":
    unittest.main()
