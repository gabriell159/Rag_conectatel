"""Teste de fumaça local das funções oficiais do RAG, sem chamar AWS."""

from __future__ import annotations

import importlib


metadata = importlib.import_module("src.02_rag.02_metadata")
chunking = importlib.import_module("src.02_rag.03_chunking")


def test_dividir_secao_grande_respeita_tamanho_maximo():
    text = "palavra " * 500
    chunks = chunking.dividir_secao_grande(text, chunk_size=1000, overlap=100)

    assert chunks
    assert all(len(chunk) <= 1000 for chunk in chunks)


def test_extrair_front_matter_separa_metadados_e_conteudo(tmp_path):
    document = tmp_path / "teste.md"
    document.write_text(
        """---
doc_family_id: teste
version_ordinal: 1
effective_from: 2026-01-01
effective_to:
status: vigente
---
Corpo do documento de teste.
""",
        encoding="utf-8",
    )

    parsed_metadata, body = metadata.extrair_front_matter(document)

    assert parsed_metadata["doc_family_id"] == "teste"
    assert parsed_metadata["status"] == "vigente"
    assert body == "Corpo do documento de teste."


def test_filter_vigentes_exclui_documento_revogado():
    documents = [
        {"metadata": {"status": "vigente"}},
        {"metadata": {"status": "revogado"}},
        {"metadata": {"status": "vigente"}},
    ]

    current = metadata.filter_vigentes(documents)

    assert current == [documents[0], documents[2]]
