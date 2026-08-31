"""Confirma que os objetos S3 usados pelo retriever existem."""

import os
from dotenv import load_dotenv


def main() -> int:
    load_dotenv()
    if not os.getenv("AWS_PROFILE", "").strip():
        os.environ.pop("AWS_PROFILE", None)
    from importlib import import_module
    storage = import_module("src.02_rag.10_s3_storage")
    BUCKET_NAME, S3_PREFIX = storage.BUCKET_NAME, storage.S3_PREFIX
    criar_cliente_s3, chave_com_prefixo = storage.criar_cliente_s3, storage.chave_com_prefixo

    client = criar_cliente_s3()
    for relative_key in ("vectorstore/index.faiss", "metadata/metadata.json"):
        key = chave_com_prefixo(relative_key)
        response = client.head_object(Bucket=BUCKET_NAME, Key=key)
        print(f"OK s3://{BUCKET_NAME}/{key} ({response.get('ContentLength', 0)} bytes)")
    print(f"Prefixo validado: {S3_PREFIX}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
