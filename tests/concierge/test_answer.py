from unittest.mock import patch
import importlib

import pytest
from botocore.exceptions import ClientError

answer_module = importlib.import_module("src.03_concierge.answer")
confidence_module = importlib.import_module("src.03_concierge.confidence")
prompts_module = importlib.import_module("src.03_concierge.prompts")
answer_question = answer_module.answer_question
has_sufficient_evidence = confidence_module.has_sufficient_evidence
SYSTEM_PROMPT = prompts_module.SYSTEM_PROMPT
build_user_prompt = prompts_module.build_user_prompt


def make_chunk(
    score=0.51,
    content="O Conecta Básico possui 8 GB de franquia.",
    document="plano_conecta_basico.md",
    chunk_id="plano-conecta-basico-v1-chunk-001",
    status="vigente",
):
    return {
        "content": content,
        "document": document,
        "chunk_id": chunk_id,
        "score": score,
        "status": status,
        "metadata": {
            "doc_family_id": "plano-conecta-basico",
            "version_ordinal": 1,
            "effective_from": "2026-01-01",
            "effective_to": None,
            "status": status,
            "source": document,
            "category": "planos",
            "chunk_id": chunk_id,
        },
    }


@pytest.fixture(autouse=True)
def isolate_threshold_environment(monkeypatch):
    monkeypatch.delenv("ABSTENTION_THRESHOLD", raising=False)


@pytest.mark.parametrize("question", ["", "   ", None, 123])
def test_invalid_question_raises_value_error(question):
    with patch.object(answer_module, "generate_text") as generate_text:
        with pytest.raises(ValueError, match="question"):
            answer_question(question, [make_chunk()])

    generate_text.assert_not_called()


def test_question_is_stripped_at_the_edges():
    chunks = [make_chunk()]

    with patch.object(
        answer_module, "generate_text",
        return_value="O plano possui 8 GB.",
    ):
        result = answer_question("  Quantos GB possui o plano?  ", chunks)

    assert result["question"] == "Quantos GB possui o plano?"


def test_empty_chunks_return_no_answer_without_generation():
    with patch.object(answer_module, "build_user_prompt") as build_prompt:
        with patch.object(answer_module, "generate_text") as generate_text:
            result = answer_question("Pergunta sem contexto?", [])

    assert result == {
        "question": "Pergunta sem contexto?",
        "decision": "NO_ANSWER",
        "answer": "NO_ANSWER",
        "sources": [],
        "retrieval_score": None,
    }
    build_prompt.assert_not_called()
    generate_text.assert_not_called()


@pytest.mark.parametrize(
    "score",
    [
        # Amostras reais obtidas na calibração do Golden Set.
        0.28579118847846985,
        0.2639181315898895,
    ],
)
def test_calibrated_insufficient_scores_avoid_model_call(score):
    chunks = [make_chunk(score=score)]

    with patch.object(answer_module, "build_user_prompt") as build_prompt:
        with patch.object(answer_module, "generate_text") as generate_text:
            result = answer_question("Pergunta fora do corpus?", chunks)

    assert result["decision"] == "NO_ANSWER"
    assert result["answer"] == "NO_ANSWER"
    assert result["sources"] == []
    assert result["retrieval_score"] == score
    build_prompt.assert_not_called()
    generate_text.assert_not_called()


@pytest.mark.parametrize("score", [0.30, 0.31])
def test_score_at_or_above_threshold_reaches_generation(score):
    chunks = [make_chunk(score=score)]

    with patch.object(
        answer_module, "generate_text",
        return_value="Resposta sustentada.",
    ) as generate_text:
        result = answer_question("Pergunta respondível?", chunks)

    assert result["decision"] == "ANSWER"
    generate_text.assert_called_once()


def test_answer_question_delegates_confidence_decision():
    chunks = [make_chunk()]

    with patch.object(
        answer_module, "has_sufficient_evidence",
        wraps=has_sufficient_evidence,
    ) as sufficient_evidence:
        with patch.object(
            answer_module, "generate_text",
            return_value="Resposta sustentada.",
        ):
            answer_question("Pergunta respondível?", chunks)

    sufficient_evidence.assert_called_once_with(chunks)


def test_generation_uses_existing_prompt_components_once():
    chunks = [make_chunk()]
    question = "Quantos GB possui o Conecta Básico?"
    user_prompt = build_user_prompt(question, chunks)

    with patch.object(
        answer_module, "build_user_prompt",
        return_value=user_prompt,
    ) as build_prompt:
        with patch.object(
            answer_module, "generate_text",
            return_value="8 GB",
        ) as generate_text:
            result = answer_question(question, chunks)

    build_prompt.assert_called_once_with(question, chunks)
    generate_text.assert_called_once_with(SYSTEM_PROMPT, user_prompt)
    assert result["decision"] == "ANSWER"
    assert result["answer"] == "8 GB"


def test_recoverable_calibration_score_calls_model_once():
    chunks = [make_chunk(score=0.33892568945884705)]
    model_answer = "Reinicie o aparelho e verifique novamente o sinal."

    with patch.object(
        answer_module, "generate_text",
        return_value=model_answer,
    ) as generate_text:
        result = answer_question("Como restabeleço o sinal?", chunks)

    assert result["decision"] == "ANSWER"
    assert result["answer"] == model_answer
    generate_text.assert_called_once()


def test_exact_model_no_answer_remains_no_answer_without_sources():
    chunks = [make_chunk(score=0.75)]

    with patch.object(
        answer_module, "generate_text",
        return_value="NO_ANSWER",
    ) as generate_text:
        result = answer_question("Pergunta sem suporte textual?", chunks)

    assert result == {
        "question": "Pergunta sem suporte textual?",
        "decision": "NO_ANSWER",
        "answer": "NO_ANSWER",
        "sources": [],
        "retrieval_score": 0.75,
    }
    generate_text.assert_called_once()


def test_non_exact_no_answer_text_is_not_reinterpreted():
    chunks = [make_chunk()]

    with patch.object(
        answer_module, "generate_text",
        return_value="NO_ANSWER.",
    ):
        result = answer_question("Pergunta respondível?", chunks)

    assert result["decision"] == "ANSWER"
    assert result["answer"] == "NO_ANSWER."


def test_sources_are_deterministic_and_preserve_chunk_order():
    chunks = [
        make_chunk(
            score=0.42,
            content="Primeira evidência.",
            document="primeiro.md",
            chunk_id="chunk-001",
        ),
        make_chunk(
            score=0.81,
            content="Segunda evidência.",
            document="segundo.md",
            chunk_id="chunk-002",
        ),
    ]

    with patch.object(
        answer_module, "generate_text",
        return_value="Resposta sem referências produzidas pelo modelo.",
    ):
        result = answer_question("Qual é a resposta?", chunks)

    assert result["sources"] == [
        {
            "document": "primeiro.md",
            "chunk_id": "chunk-001",
            "score": 0.42,
            "status": "vigente",
        },
        {
            "document": "segundo.md",
            "chunk_id": "chunk-002",
            "score": 0.81,
            "status": "vigente",
        },
    ]
    assert all(
        set(source) == {"document", "chunk_id", "score", "status"}
        for source in result["sources"]
    )


def test_retrieval_score_uses_highest_score_not_first_chunk():
    chunks = [
        make_chunk(score=0.45, chunk_id="chunk-001"),
        make_chunk(score=0.82, chunk_id="chunk-002"),
        make_chunk(score=0.61, chunk_id="chunk-003"),
    ]

    with patch.object(
        answer_module, "generate_text",
        return_value="Resposta sustentada.",
    ):
        result = answer_question("Pergunta respondível?", chunks)

    assert result["retrieval_score"] == 0.82


def test_build_user_prompt_value_error_propagates():
    chunks = [make_chunk()]

    with patch.object(
        answer_module, "build_user_prompt",
        side_effect=ValueError("prompt inválido"),
    ):
        with patch.object(answer_module, "generate_text") as generate_text:
            with pytest.raises(ValueError, match="prompt inválido"):
                answer_question("Pergunta respondível?", chunks)

    generate_text.assert_not_called()


def test_generation_runtime_error_propagates():
    chunks = [make_chunk()]

    with patch.object(
        answer_module, "generate_text",
        side_effect=RuntimeError("resposta Bedrock inválida"),
    ):
        with pytest.raises(RuntimeError, match="Bedrock inválida"):
            answer_question("Pergunta respondível?", chunks)


def test_sdk_error_propagates_unchanged():
    chunks = [make_chunk()]
    error = ClientError(
        {
            "Error": {
                "Code": "AccessDeniedException",
                "Message": "Access denied",
            }
        },
        "Converse",
    )

    with patch.object(
        answer_module, "generate_text",
        side_effect=error,
    ):
        with pytest.raises(ClientError) as raised:
            answer_question("Pergunta respondível?", chunks)

    assert raised.value is error


@pytest.mark.parametrize(
    ("score", "model_answer"),
    [
        (0.20, None),
        (0.51, "NO_ANSWER"),
        (0.51, "Resposta sustentada."),
    ],
)
def test_answer_question_never_produces_escalate(score, model_answer):
    chunks = [make_chunk(score=score)]

    with patch.object(
        answer_module, "generate_text",
        return_value=model_answer,
    ):
        result = answer_question("Pergunta?", chunks)

    assert result["decision"] in {"ANSWER", "NO_ANSWER"}
    assert result["decision"] != "ESCALATE"
