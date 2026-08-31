"""Executa uma interação real do Concierge com auditoria da Frente 05."""

import argparse
import json
from pathlib import Path

from importlib import import_module


run_question = import_module("src.03_concierge.05_orchestrator").run_question


def main() -> int:
    parser = argparse.ArgumentParser(description="Executa o fluxo real Concierge + RAG")
    parser.add_argument("question")
    parser.add_argument("--audit-path", type=Path, default=None)
    args = parser.parse_args()
    event = run_question(args.question, audit_path=args.audit_path)
    print(json.dumps(event, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
