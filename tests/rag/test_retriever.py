import pytest

from src.rag.retriever import buscar


@pytest.mark.integration
def test_retriever_recupera_versao_vigente():
    resultados = buscar(
        "Qual é o prazo para contestar "
        "valores cobrados na fatura?",
        top_k=3,
    )

    assert resultados

    primeiro = resultados[0]

    assert primeiro["document"] == (
        "politica_reembolso_v2.md"
    )

    assert primeiro["status"] == "vigente"

    assert "90 dias" in primeiro["content"]


@pytest.mark.integration
def test_retriever_nunca_retorna_versao_revogada():
    resultados = buscar(
        "O cliente pode solicitar reembolso integral "
        "em até 15 dias após a contratação?",
        top_k=5,
    )

    fontes = [
        resultado["document"]
        for resultado in resultados
    ]

    assert "politica_reembolso_v1.md" not in fontes

    assert all(
        resultado["status"] == "vigente"
        for resultado in resultados
    )


@pytest.mark.integration
def test_retriever_retorna_contrato_completo():
    resultados = buscar(
        "Como funciona a contestação de fatura?",
        top_k=1,
    )

    assert resultados

    resultado = resultados[0]

    assert "content" in resultado
    assert "document" in resultado
    assert "chunk_id" in resultado
    assert "score" in resultado
    assert "status" in resultado
    assert "metadata" in resultado