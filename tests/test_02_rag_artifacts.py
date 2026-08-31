import importlib


def test_verify_uses_exact_retriever_object_paths():
    verify = importlib.import_module("src.02_rag.09_verify_s3")

    class Client:
        def __init__(self):
            self.keys = []

        def head_object(self, **kwargs):
            self.keys.append(kwargs["Key"])
            return {"ContentLength": 10}

    client = Client()
    result = verify.verificar_objetos_s3(client, "bucket", lambda key: f"conectatel/{key}")

    assert [item["key"] for item in result] == [
        "conectatel/vectorstore/index.faiss",
        "conectatel/metadata/metadata.json",
        "conectatel/vectorstore/manifest.json",
    ]
    assert client.keys == [item["key"] for item in result]


def test_retriever_uses_backup_only_when_official_download_fails(monkeypatch):
    retriever = importlib.import_module("src.02_rag.07_retriever")

    monkeypatch.setattr(
        retriever,
        "download_vectorstore",
        lambda: (_ for _ in ()).throw(RuntimeError("S3 indisponível")),
    )
    index, records = retriever.carregar_vectorstore()

    assert index.ntotal == len(records)
    assert records
