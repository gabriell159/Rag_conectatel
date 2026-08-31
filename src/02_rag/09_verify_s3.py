"""Confirma que os objetos S3 usados pelo retriever existem."""

import os
from dotenv import load_dotenv


EXPECTED_OBJECTS = (
    "vectorstore/index.faiss",
    "metadata/metadata.json",
    "vectorstore/manifest.json",
)


def verificar_objetos_s3(client, bucket: str, prefix_fn) -> list[dict]:
    """Confirma a existência dos artefatos consumidos pelo retriever."""
    encontrados = []
    for relative_key in EXPECTED_OBJECTS:
        key = prefix_fn(relative_key)
        response = client.head_object(Bucket=bucket, Key=key)
        encontrados.append({"key": key, "size": response.get("ContentLength", 0)})
    return encontrados


def main() -> int:
    load_dotenv()
    if not os.getenv("AWS_PROFILE", "").strip():
        os.environ.pop("AWS_PROFILE", None)
    from importlib import import_module
    storage = import_module("src.02_rag.10_s3_storage")
    BUCKET_NAME, S3_PREFIX = storage.BUCKET_NAME, storage.S3_PREFIX
    criar_cliente_s3, chave_com_prefixo = storage.criar_cliente_s3, storage.chave_com_prefixo

    client = criar_cliente_s3()
    for item in verificar_objetos_s3(client, BUCKET_NAME, chave_com_prefixo):
        print(f"OK s3://{BUCKET_NAME}/{item['key']} ({item['size']} bytes)")
    print(f"Prefixo validado: {S3_PREFIX}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
