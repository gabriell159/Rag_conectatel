"""Upload controlado dos artefatos da Frente 1 para o S3."""

import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

UPLOAD_SOURCES = {
    "data/raw/conectatel-dados/log_chamados": "raw/log_chamados",
    "data/raw/conectatel-dados/corpus": "raw/corpus",
    "data/processed/log_chamados": "processed/log_chamados",
}


def load_config() -> tuple[str, str, str]:
    bucket = os.getenv("S3_BUCKET_NAME", "").strip()
    region = os.getenv("AWS_REGION", "").strip()
    prefix = os.getenv("S3_PREFIX", "").strip(" /")

    missing = []
    if not bucket:
        missing.append("S3_BUCKET_NAME")
    if not region:
        missing.append("AWS_REGION")
    if not prefix:
        missing.append("S3_PREFIX")
    if missing:
        raise RuntimeError(
            f"Configuracao incompleta: preencha {', '.join(missing)} no arquivo .env."
        )
    return bucket, region, prefix


def collect_files() -> list[tuple[Path, str]]:
    files = []
    missing_sources = []
    for local_relative, s3_relative in UPLOAD_SOURCES.items():
        local_dir = BASE_DIR / local_relative
        if not local_dir.exists():
            missing_sources.append(str(local_dir))
            continue
        for path in sorted(local_dir.rglob("*")):
            if path.is_file():
                relative_path = path.relative_to(local_dir).as_posix()
                files.append((path, f"{s3_relative}/{relative_path}"))

    if missing_sources:
        raise FileNotFoundError(
            "Pastas obrigatorias nao encontradas:\n- " + "\n- ".join(missing_sources)
        )
    if not files:
        raise FileNotFoundError("Nenhum arquivo encontrado para upload.")
    return files


def ensure_bucket_exists(client, bucket: str, region: str) -> None:
    try:
        client.head_bucket(Bucket=bucket)
        print(f"Bucket ja existente: s3://{bucket}/")
        return
    except ClientError as exc:
        error_code = str(exc.response.get("Error", {}).get("Code", ""))
        if error_code not in {"404", "NoSuchBucket"}:
            raise RuntimeError(
                f"Nao foi possivel validar o bucket '{bucket}'. "
                "Verifique as credenciais e a permissao s3:HeadBucket."
            ) from exc

    try:
        params = {"Bucket": bucket}
        if region != "us-east-1":
            params["CreateBucketConfiguration"] = {"LocationConstraint": region}
        client.create_bucket(**params)
        print(f"Bucket criado: s3://{bucket}/ ({region})")
    except ClientError as exc:
        error_code = str(exc.response.get("Error", {}).get("Code", ""))
        if error_code in {"BucketAlreadyExists", "BucketAlreadyOwnedByYou"}:
            raise RuntimeError(
                f"O bucket '{bucket}' ja existe, mas nao esta acessivel nesta conta."
            ) from exc
        raise RuntimeError(
            f"Nao foi possivel criar o bucket '{bucket}'. "
            "Verifique a regiao e a permissao s3:CreateBucket."
        ) from exc


def upload_configurado() -> dict[str, int]:
    bucket, region, prefix = load_config()
    files = collect_files()
    client = boto3.client("s3", region_name=region)
    ensure_bucket_exists(client, bucket, region)
    summary = {"sucesso": 0, "falha": 0}

    print(f"Iniciando upload de {len(files)} arquivo(s) para s3://{bucket}/{prefix}/")
    for local_path, relative_key in files:
        key = f"{prefix}/{relative_key}"
        try:
            client.upload_file(str(local_path), bucket, key)
            summary["sucesso"] += 1
            print(f"OK   {local_path} -> s3://{bucket}/{key}")
        except Exception as exc:
            summary["falha"] += 1
            print(
                f"ERRO {local_path} -> s3://{bucket}/{key}: "
                f"{type(exc).__name__}: {exc}"
            )

    print(
        f"Resumo do upload: {summary['sucesso']} sucesso(s), "
        f"{summary['falha']} falha(s)."
    )
    if summary["falha"]:
        raise RuntimeError("O upload terminou com falhas; verifique os erros acima.")
    return summary


if __name__ == "__main__":
    upload_configurado()
