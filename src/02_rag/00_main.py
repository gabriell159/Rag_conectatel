"""Ponto de entrada do pipeline RAG."""

import argparse
import runpy
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Executa etapas do RAG")
    parser.add_argument("--build", action="store_true", help="gera embeddings, FAISS e publica no S3")
    parser.add_argument("--verify", action="store_true", help="verifica objetos do RAG no S3")
    args = parser.parse_args()
    if args.build:
        runpy.run_path(str(BASE_DIR / "08_build_index.py"), run_name="__main__")
    if args.verify:
        runpy.run_path(str(BASE_DIR / "09_verify_s3.py"), run_name="__main__")
    if not args.build and not args.verify:
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
