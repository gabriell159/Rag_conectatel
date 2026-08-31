"""Pipeline reproduzível: ingestão, chunks, embeddings, FAISS e upload."""

import os
from dotenv import load_dotenv


def main() -> int:
    load_dotenv()
    if not os.getenv("AWS_PROFILE", "").strip():
        os.environ.pop("AWS_PROFILE", None)

    import importlib
    carregar_corpus = importlib.import_module("src.02_rag.01_ingest").carregar_corpus
    gerar_chunks_corpus = importlib.import_module("src.02_rag.03_chunking").gerar_chunks_corpus
    rag_embeddings = importlib.import_module("src.02_rag.04_embeddings")
    gerar_embeddings_chunks = rag_embeddings.gerar_embeddings_chunks
    index_embeddings = importlib.import_module("src.02_rag.06_index_embeddings")
    criar_indice_faiss, salvar_indice, validar_indice = index_embeddings.criar_indice_faiss, index_embeddings.salvar_indice, index_embeddings.validar_indice
    upload_vectorstore = importlib.import_module("src.02_rag.10_s3_storage").upload_vectorstore

    documentos = carregar_corpus()
    chunks = gerar_chunks_corpus(documentos)
    chunks_com_embeddings = gerar_embeddings_chunks(chunks)
    indice = criar_indice_faiss(chunks_com_embeddings)
    validar_indice(indice, chunks_com_embeddings)
    salvar_indice(indice, chunks_com_embeddings)
    upload_vectorstore()
    print("Pipeline RAG concluído e vector store publicado no S3.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
