from pathlib import Path

from src.rag.metadata import (
    carregar_documento,
    filter_vigentes,
)


CAMINHO_POLITICAS = Path(
    "data/raw/conectatel-dados/corpus/politicas"
)


def test_normalizacao_familia_reembolso():
    v1 = carregar_documento(
        CAMINHO_POLITICAS / "politica_reembolso_v1.md"
    )

    v2 = carregar_documento(
        CAMINHO_POLITICAS / "politica_reembolso_v2.md"
    )

    assert (
        v1["metadata"]["doc_family_id"]
        == v2["metadata"]["doc_family_id"]
    )


def test_filter_vigentes_remove_documento_revogado():
    v1 = carregar_documento(
        CAMINHO_POLITICAS / "politica_reembolso_v1.md"
    )

    v2 = carregar_documento(
        CAMINHO_POLITICAS / "politica_reembolso_v2.md"
    )

    documentos = [v1, v2]

    vigentes = filter_vigentes(documentos)

    assert len(vigentes) == 1

    assert (
        vigentes[0]["metadata"]["source"]
        == "politica_reembolso_v2.md"
    )

    assert (
        vigentes[0]["metadata"]["status"]
        == "vigente"
    )