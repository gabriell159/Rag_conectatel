import importlib

carregar_corpus = importlib.import_module("src.02_rag.01_ingest").carregar_corpus
gerar_chunks_corpus = importlib.import_module("src.02_rag.03_chunking").gerar_chunks_corpus


def test_chunking_corpus():
    documentos = carregar_corpus()

    chunks = gerar_chunks_corpus(documentos)

    assert len(documentos) == 12

    assert len(chunks) > 0


def test_chunks_possuem_identificador():
    documentos = carregar_corpus()

    chunks = gerar_chunks_corpus(documentos)

    chunk_ids = [
        chunk["metadata"]["chunk_id"]
        for chunk in chunks
    ]

    assert all(chunk_ids)

    assert len(chunk_ids) == len(set(chunk_ids))


def test_chunks_nao_sao_excessivamente_pequenos():
    documentos = carregar_corpus()

    chunks = gerar_chunks_corpus(documentos)

    tamanhos = [
        len(chunk["content"])
        for chunk in chunks
    ]

    assert min(tamanhos) >= 100
