import importlib

import pandas as pd
import pytest


pipeline = importlib.import_module("src.01_pipeline_tratamento.01_tratamento")
contract = importlib.import_module("src.01_pipeline_tratamento.05_contract")


def raw_frame():
    return pd.DataFrame(
        [
            {
                "chamado_id": "1",
                "data_abertura": "2026-01-02",
                "canal": " telefone ",
                "categoria": "cobertura",
                "subcategoria": "Sinal instável",
                "estado": "Rio de Janeiro",
                "cidade": "Rio de Janeiro",
                "duracao_minutos": "12",
                "resolvido_primeiro_contato": "S",
                "encaminhado_humano": "não",
                "satisfacao_1_a_5": "4",
                "plano_atual": "Conecta Básico",
                "resumo_atendimento": " queda de sinal ",
            },
            {
                "chamado_id": "1",
                "data_abertura": "2026-01-02",
                "canal": " telefone ",
                "categoria": "cobertura",
                "subcategoria": "Sinal instável",
                "estado": "Rio de Janeiro",
                "cidade": "Rio de Janeiro",
                "duracao_minutos": "12",
                "resolvido_primeiro_contato": "S",
                "encaminhado_humano": "não",
                "satisfacao_1_a_5": "4",
                "plano_atual": "Conecta Básico",
                "resumo_atendimento": " queda de sinal ",
            },
        ]
    )


def test_tratamento_normaliza_deduplica_e_preserva_schema(tmp_path):
    entrada = tmp_path / "raw.csv"
    saida = tmp_path / "clean.csv"
    raw_frame().to_csv(entrada, index=False)

    result = pipeline.processar_log_chamados(entrada, saida)

    assert len(result) == 1
    assert result.loc[0, "canal"] == "Telefone"
    assert result.loc[0, "estado"] == "RJ"
    assert bool(result.loc[0, "resolvido_primeiro_contato"]) is True
    assert bool(result.loc[0, "encaminhado_humano"]) is False
    contract.validate_processed_artifact(saida)


@pytest.mark.parametrize("duration", [0, -1, 181, "invalido"])
def test_tratamento_converte_duracao_invalida_em_nulo(tmp_path, duration):
    frame = raw_frame().iloc[[0]].copy()
    frame["duracao_minutos"] = frame["duracao_minutos"].astype(object)
    frame.loc[:, "duracao_minutos"] = duration
    entrada, saida = tmp_path / "raw.csv", tmp_path / "clean.csv"
    frame.to_csv(entrada, index=False)

    result = pipeline.processar_log_chamados(entrada, saida)

    assert pd.isna(result.loc[0, "duracao_minutos"])


def test_contrato_rejeita_id_duplicado():
    frame = raw_frame().iloc[[0, 0]].copy()
    with pytest.raises(ValueError, match="chamado_id"):
        contract.validate_processed_dataframe(frame)
