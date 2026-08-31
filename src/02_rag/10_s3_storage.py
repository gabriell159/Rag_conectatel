import os
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError


BASE_DIR = Path(__file__).resolve().parents[2]
REGION = os.getenv("AWS_REGION", "us-east-1")
BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_PREFIX = os.getenv("S3_PREFIX", "conectatel").strip(" /")

LOCAL_VECTORSTORE = BASE_DIR / "data" / "processed" / "vectorstore"


def criar_cliente_s3():
    """
    Cria um cliente S3, localmente pode utilizar AWS_PROFILE, mas em ambiente AWS utiliza automaticamente a IAM Role.
    """

    profile = (os.getenv("AWS_PROFILE") or "").strip() or None

    if profile:
        session = boto3.Session(
            profile_name=profile,
            region_name=REGION,
        )
    else:
        session = boto3.Session(
            region_name=REGION,
        )

    return session.client("s3")



def validar_bucket_configurado() -> None:
    """
    Garante que o nome do bucket foi configurado.
    """

    if not BUCKET_NAME:
        raise ValueError(
            "A variável S3_BUCKET_NAME não foi configurada."
        )


def chave_com_prefixo(chave: str) -> str:
    """Monta a chave S3 dentro do prefixo operacional da squad."""

    if not S3_PREFIX:
        raise ValueError("A variável S3_PREFIX não foi configurada.")
    return f"{S3_PREFIX}/{chave.lstrip('/')}"


def upload_arquivo(
    caminho_local: Path,
    chave_s3: str,
) -> None:
    """
    Envia um arquivo local para o bucket S3.
    """

    validar_bucket_configurado()

    if not caminho_local.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {caminho_local}"
        )

    s3 = criar_cliente_s3()

    try:
        s3.upload_file(
            str(caminho_local),
            BUCKET_NAME,
            chave_com_prefixo(chave_s3),
        )

    except (ClientError, BotoCoreError) as error:
        raise RuntimeError(
            f"Erro ao enviar arquivo para o S3: {error}"
        ) from error


def upload_vectorstore() -> None:
    """
    Envia o índice FAISS e seus metadados para o S3.
    """

    upload_arquivo(
        LOCAL_VECTORSTORE / "index.faiss",
        "vectorstore/index.faiss",
    )

    upload_arquivo(
        LOCAL_VECTORSTORE / "metadata.json",
        "metadata/metadata.json",
    )

    manifest = LOCAL_VECTORSTORE / "manifest.json"
    if manifest.exists():
        upload_arquivo(manifest, "vectorstore/manifest.json")

    print("Vector store enviado ao S3 com sucesso.")


def download_arquivo(
    chave_s3: str,
    caminho_local: Path,
) -> None:
    """
    Baixa um arquivo do S3.
    """

    validar_bucket_configurado()

    caminho_local.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    s3 = criar_cliente_s3()

    try:
        s3.download_file(
            BUCKET_NAME,
            chave_com_prefixo(chave_s3),
            str(caminho_local),
        )

    except (ClientError, BotoCoreError) as error:
        raise RuntimeError(
            f"Erro ao baixar arquivo do S3: {error}"
        ) from error


def download_vectorstore() -> None:
    """
    Recupera índice FAISS e metadados persistidos no S3.
    """

    download_arquivo(
        "vectorstore/index.faiss",
        LOCAL_VECTORSTORE / "index.faiss",
    )

    download_arquivo(
        "metadata/metadata.json",
        LOCAL_VECTORSTORE / "metadata.json",
    )

    print("Vector store recuperado do S3 com sucesso.")

