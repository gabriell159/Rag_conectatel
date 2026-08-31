"""Executa uma pergunta no fluxo RAG + Concierge."""

import argparse
import json
import os
from dotenv import load_dotenv


def main() -> int:
    load_dotenv()
    # Uma variável AWS_PROFILE vazia ainda pode ser interpretada pelo botocore
    # como o nome literal de um perfil. Remova-a para usar as credenciais
    # padrão do ambiente (ou as chaves AWS_* do .env).
    if not os.getenv("AWS_PROFILE", "").strip():
        os.environ.pop("AWS_PROFILE", None)
    # O upload da Frente 1 usa S3_BUCKET_NAME; o RAG usa S3_BUCKET_NAME.
    # Mantemos ambos sem alterar os módulos das outras frentes.
    from importlib import import_module
    run_question = import_module("src.03_concierge.05_orchestrator").run_question

    parser = argparse.ArgumentParser(description="Executa o Concierge ConectaTel")
    parser.add_argument("question")
    args = parser.parse_args()
    result = run_question(args.question)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


