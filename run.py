"""Ponto de entrada seguro para os fluxos oficiais do Concierge ConectaTel.

Cada comando encaminha para o módulo responsável. Não existe comando "all":
operações remotas, como Bedrock, S3 e golden set, precisam ser escolhidas
explicitamente por quem executa o projeto.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from typing import Sequence


def _run_module(module: str, arguments: Sequence[str] = ()) -> int:
    """Executa um módulo usando o mesmo interpretador do ambiente virtual."""

    completed = subprocess.run([sys.executable, "-m", module, *arguments], check=False)
    return completed.returncode


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Atalhos para os fluxos oficiais do Concierge ConectaTel."
    )
    commands = parser.add_subparsers(dest="command", required=True, title="comandos")

    pipeline = commands.add_parser("pipeline", help="executa tratamento e análise dos chamados")
    pipeline.add_argument("--upload", action="store_true", help="publica os artefatos da Frente 01 no S3")

    commands.add_parser("rag-build", help="gera o vector store e publica no S3")
    commands.add_parser("rag-verify", help="verifica o vector store publicado no S3")

    ask = commands.add_parser("ask", help="faz pergunta no Concierge")
    ask.add_argument("question", help="pergunta a ser respondida")

    run_real = commands.add_parser("run-real", help="executa Concierge integrado com auditoria")
    run_real.add_argument("question", help="pergunta a ser processada")

    run_mock = commands.add_parser("run-mock", help="executa fluxo simulado, sem AWS")
    run_mock.add_argument("question", help="pergunta a ser processada")

    trace = commands.add_parser("trace", help="consulta auditoria local por trace_id")
    trace.add_argument("trace_id", help="identificador trc_ retornado pelo Concierge")

    commands.add_parser("quality-report", help="gera relatório consolidado da auditoria")
    commands.add_parser("golden-set", help="executa o golden set (consome serviços AWS)")

    test = commands.add_parser("test", help="executa testes automatizados")
    test.add_argument(
        "--scope",
        choices=("local", "integration", "all"),
        default="local",
        help="local é o padrão e não chama integrações AWS",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()

    if args.command == "pipeline":
        return _run_module(
            "src.01_pipeline_tratamento.00_main",
            ("--upload",) if args.upload else (),
        )
    if args.command == "rag-build":
        return _run_module("src.02_rag.00_main", ("--build",))
    if args.command == "rag-verify":
        return _run_module("src.02_rag.00_main", ("--verify",))
    if args.command == "ask":
        return _run_module("src.03_concierge.00_main", (args.question,))
    if args.command == "run-real":
        return _run_module("src.05_integracao_auditoria_qualidade.04_run_real", (args.question,))
    if args.command == "run-mock":
        return _run_module("src.05_integracao_auditoria_qualidade.04_run_mock", (args.question,))
    if args.command == "trace":
        return _run_module("src.05_integracao_auditoria_qualidade.05_query_trace", (args.trace_id,))
    if args.command == "quality-report":
        return _run_module("src.05_integracao_auditoria_qualidade.06_quality_report")
    if args.command == "golden-set":
        return _run_module("src.03_concierge.06_golden_set")
    if args.command == "test":
        markers = {"local": "not integration", "integration": "integration"}
        test_args = ["-q"]
        if args.scope != "all":
            test_args.extend(("-m", markers[args.scope]))
        completed = subprocess.run([sys.executable, "-m", "pytest", *test_args], check=False)
        return completed.returncode

    raise AssertionError(f"Comando não tratado: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
