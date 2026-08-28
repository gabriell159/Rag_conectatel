"""Orquestrador da implementacao atual da Frente 1."""

import argparse
import runpy
from pathlib import Path


PIPELINE_DIR = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Executa o pipeline da Frente 1")
    parser.add_argument(
        "--upload",
        action="store_true",
        help="envia para o S3 apos concluir tratamento e analise",
    )
    args = parser.parse_args()

    runpy.run_path(str(PIPELINE_DIR / "01_tratamento.py"), run_name="__main__")
    runpy.run_path(str(PIPELINE_DIR / "02_analise.py"), run_name="__main__")

    if args.upload:
        runpy.run_path(str(PIPELINE_DIR / "04_upload_s3.py"), run_name="__main__")
    else:
        print("Upload S3 nao executado. Use --upload para habilita-lo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
