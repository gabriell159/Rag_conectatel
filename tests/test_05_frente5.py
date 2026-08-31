import json
import importlib
import tempfile
import unittest
from pathlib import Path

AuditLogger = importlib.import_module("src.05_integracao_auditoria_qualidade.02_audit").AuditLogger
citation = importlib.import_module("src.05_integracao_auditoria_qualidade.00_contract").citation
run_mock = importlib.import_module("src.05_integracao_auditoria_qualidade.03_offline_contract_mock").run_mock


class Frente5ContractTests(unittest.TestCase):
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
