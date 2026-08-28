"""
audit_log.py — Etapa 4 do pipeline: trilha de auditoria.

Registra cada interação (pergunta, fonte consultada, decisão tomada) em
um arquivo JSONL append-only, com um trace_id curto por resposta. Também
oferece uma função de consulta por trace_id, que a squad deve conseguir
executar em até 60 segundos durante a pergunta de auditoria da banca
(ver Parte 5 e "Pergunta de auditoria" no desafio).

Este scaffold usa um arquivo local como trilha de auditoria para manter o
exemplo mínimo. A squad pode substituir por uma tabela (ex.: DynamoDB) se
preferir, desde que a consulta por trace_id continue funcionando ao vivo,
sem depender de ferramentas externas de log não preparadas para consulta
em tempo real.

Uso:
    python src/audit_log.py <trace_id>   # consulta um registro específico
"""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "audit_log.jsonl"


def log_interaction(
    question: str,
    decision: str,
    source: str | None,
    answer: str,
    top_score: float | None = None,
    guardrail: str | None = None,
) -> str:
    """Grava uma entrada na trilha de auditoria e retorna o trace_id gerado."""
    trace_id = uuid.uuid4().hex[:8]
    entry = {
        "trace_id": trace_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "source": source,
        "decision": decision,
        "answer": answer,
        "top_score": top_score,
        "guardrail": guardrail,
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return trace_id


def find_by_trace_id(trace_id: str) -> dict | None:
    """Busca um registro pelo trace_id. Deve responder em segundos mesmo
    com muitas linhas — ensaiem este comando antes da banca."""
    if not LOG_PATH.exists():
        return None
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            if entry.get("trace_id") == trace_id:
                return entry
    return None


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python src/audit_log.py <trace_id>")
        return
    entry = find_by_trace_id(sys.argv[1])
    if entry is None:
        print(f"Nenhum registro encontrado para trace_id={sys.argv[1]!r}")
        return
    print(json.dumps(entry, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
