"""Gera relatório resumido de qualidade e latência da auditoria local."""

import json
import statistics
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = BASE_DIR / "data" / "processed" / "audit" / "audit_log.jsonl"
DEFAULT_OUTPUT = BASE_DIR / "data" / "processed" / "evaluation" / "quality_report.json"


def generate_report(input_path: Path = DEFAULT_INPUT, output_path: Path | None = None) -> dict:
    events = [json.loads(line) for line in input_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    durations = [event["duration_ms"] for event in events]
    report = {
        "total_interactions": len(events),
        "decisions": dict(Counter(event["decision"] for event in events)),
        "latency_ms": {
            "min": min(durations) if durations else 0,
            "max": max(durations) if durations else 0,
            "mean": round(statistics.mean(durations), 2) if durations else 0,
            "p95": sorted(durations)[max(0, int(len(durations) * 0.95) - 1)] if durations else 0,
        },
        "known_risks": [
            "auditoria local depende do caminho configurado em AUDIT_LOG_PATH",
            "respostas ANSWER dependem da qualidade e vigência do vector store",
            "integrações Bedrock podem falhar por credencial, quota ou rede",
        ],
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(generate_report(DEFAULT_INPUT, DEFAULT_OUTPUT), ensure_ascii=False, indent=2))
