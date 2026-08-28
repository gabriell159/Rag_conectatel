"""
Teste de fumaça (smoke test) local, sem chamar a AWS — apenas valida a
lógica pura do pipeline (chunking, filtro de vigência, similaridade),
para que a squad tenha um exemplo de teste automatizado desde o início.

Uso:
    python -m pytest tests/ -v
ou, sem pytest instalado:
    python tests/test_hello_bedrock.py
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ingest import chunk_text, parse_front_matter  # noqa: E402
from query import cosine_similarity, filter_vigentes  # noqa: E402


def test_chunk_text_respects_size():
    text = "a" * 3000
    chunks = chunk_text(text, size=1000, overlap=100)
    assert all(len(c) <= 1000 for c in chunks)
    assert len(chunks) >= 3


def test_parse_front_matter_extracts_required_fields():
    raw = (
        "---\n"
        "doc_family_id: teste\n"
        "version_ordinal: 1\n"
        "effective_from: 2026-01-01\n"
        "effective_to:\n"
        "status: vigente\n"
        "---\n"
        "Corpo do documento de teste."
    )
    metadata, body = parse_front_matter(raw)
    assert metadata["doc_family_id"] == "teste"
    assert metadata["status"] == "vigente"
    assert body == "Corpo do documento de teste."


def test_filter_vigentes_excludes_revoked():
    metadata = [
        {"status": "vigente"},
        {"status": "revogado"},
        {"status": "vigente"},
    ]
    assert filter_vigentes(metadata) == [0, 2]


def test_cosine_similarity_ranks_closer_vector_higher():
    query = np.array([1.0, 0.0], dtype=np.float32)
    matrix = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    scores = cosine_similarity(query, matrix)
    assert scores[0] > scores[1]


if __name__ == "__main__":
    test_chunk_text_respects_size()
    test_parse_front_matter_extracts_required_fields()
    test_filter_vigentes_excludes_revoked()
    test_cosine_similarity_ranks_closer_vector_higher()
    print("Todos os testes de fumaça passaram.")
