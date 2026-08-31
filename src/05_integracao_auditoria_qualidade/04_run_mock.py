"""Executa uma interacao simulada e imprime o trace_id gerado."""

import argparse
import json

from importlib import import_module


run_mock = import_module(".03_offline_contract_mock", __package__).run_mock


def main() -> int:
    parser = argparse.ArgumentParser(description="Executa o fluxo simulado da Frente 5")
    parser.add_argument("question")
    args = parser.parse_args()
    event = run_mock(args.question)
    print(json.dumps(event, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
