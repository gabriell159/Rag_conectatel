"""Executa o golden set e calcula métricas de decisão e fonte."""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from importlib import import_module
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
CASES_PATH = BASE_DIR / "data" / "05_golden_set_frente5.json"


def executar(
    cases_path: Path = CASES_PATH,
    output_path: Path | None = None,
    history_path: Path | None = None,
) -> dict:
    load_dotenv(BASE_DIR / ".env")
    if not os.getenv("AWS_PROFILE", "").strip():
        os.environ.pop("AWS_PROFILE", None)
    run_question = import_module("src.03_concierge.05_orchestrator").run_question
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    resultados = []
    for case in cases:
        evento = run_question(case["question"])
        decision_ok = evento["decision"] == case["expected_decision"]
        source_ok = not case.get("expected_source") or any(
            c["source_file"] == case["expected_source"].split("/")[-1]
            for c in evento["citations"]
        )
        expected_version = case.get("expected_version")
        version_ok = not expected_version or any(
            c.get("version_ordinal") == expected_version for c in evento["citations"]
        )
        resultados.append({
            "id": case["id"],
            "decision": evento["decision"],
            "decision_ok": decision_ok,
            "source_ok": source_ok,
            "version_ok": version_ok,
        })
    total = len(resultados)
    summary = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "total": total,
        "decision_accuracy": sum(r["decision_ok"] for r in resultados) / total if total else 0,
        "source_accuracy": sum(r["source_ok"] for r in resultados) / total if total else 0,
        "version_accuracy": sum(r["version_ok"] for r in resultados) / total if total else 0,
        "failed": [r["id"] for r in resultados if not (r["decision_ok"] and r["source_ok"] and r["version_ok"])],
        "results": resultados,
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if history_path:
        history_path.parent.mkdir(parents=True, exist_ok=True)
        with history_path.open("a", encoding="utf-8") as history:
            history.write(json.dumps(summary, ensure_ascii=False) + "\n")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Executa o golden set do Concierge")
    parser.add_argument("--file", type=Path, default=CASES_PATH)
    parser.add_argument("--output", type=Path, default=BASE_DIR / "data" / "processed" / "evaluation" / "golden_set_results.json")
    parser.add_argument("--history", type=Path, default=BASE_DIR / "data" / "processed" / "evaluation" / "golden_set_history.jsonl")
    args = parser.parse_args()
    print(json.dumps(executar(args.file, args.output, args.history), ensure_ascii=False, indent=2))
