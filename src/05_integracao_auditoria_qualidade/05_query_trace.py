"""Consulta uma interacao registrada por trace_id."""

import argparse
import json

from importlib import import_module


AuditLogger = import_module(".02_audit", __package__).AuditLogger


def main() -> int:
    parser = argparse.ArgumentParser(description="Consulta a auditoria por trace_id")
    parser.add_argument("trace_id")
    args = parser.parse_args()
    event = AuditLogger().find_by_trace_id(args.trace_id)
    if event is None:
        print(f"Nenhum registro encontrado para trace_id={args.trace_id}")
        return 1
    print(json.dumps(event, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
