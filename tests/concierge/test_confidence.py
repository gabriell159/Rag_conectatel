import importlib

import pytest

_confidence = importlib.import_module("src.03_concierge.confidence")
DEFAULT_ABSTENTION_THRESHOLD = _confidence.DEFAULT_ABSTENTION_THRESHOLD
get_abstention_threshold = _confidence.get_abstention_threshold
get_top_score = _confidence.get_top_score
has_sufficient_evidence = _confidence.has_sufficient_evidence
has_valid_evidence_contract = _confidence.has_valid_evidence_contract


def make_chunk(score, status="vigente"):
    return {
        "score": score,
        "status": status,
    }


def test_empty_chunks_have_no_sufficient_evidence():
    assert get_top_score([]) is None
    assert has_valid_evidence_contract([]) is False
    assert has_sufficient_evidence([]) is False


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.29, False),
        (0.30, True),
        (0.31, True),
    ],
)
def test_sufficient_evidence_compares_score_with_default_threshold(
    monkeypatch,
    score,
    expected,
):
    monkeypatch.delenv("ABSTENTION_THRESHOLD", raising=False)

    assert has_sufficient_evidence([make_chunk(score)]) is expected


def test_top_score_uses_highest_value_without_modifying_chunks():
    chunks = [
        make_chunk(0.42),
        make_chunk(0.81),
        make_chunk(0.55),
    ]
    original_chunks = [chunk.copy() for chunk in chunks]

    assert get_top_score(chunks) == 0.81
    assert chunks == original_chunks


def test_current_chunk_has_valid_contract():
    assert has_valid_evidence_contract([make_chunk(0.40)]) is True


def test_any_revoked_chunk_invalidates_contract():
    chunks = [
        make_chunk(0.70),
        make_chunk(0.80, status="revogado"),
    ]

    assert has_valid_evidence_contract(chunks) is False
    assert has_sufficient_evidence(chunks) is False


def test_missing_status_invalidates_contract():
    chunks = [{"score": 0.50}]

    assert has_valid_evidence_contract(chunks) is False
    assert has_sufficient_evidence(chunks) is False


def test_missing_score_invalidates_contract():
    chunks = [{"status": "vigente"}]

    assert get_top_score(chunks) is None
    assert has_valid_evidence_contract(chunks) is False
    assert has_sufficient_evidence(chunks) is False


def test_non_dict_chunk_invalidates_contract():
    chunks = [make_chunk(0.50), "invalid"]

    assert get_top_score(chunks) is None
    assert has_valid_evidence_contract(chunks) is False
    assert has_sufficient_evidence(chunks) is False


@pytest.mark.parametrize(
    "invalid_score",
    [
        "0.30",
        None,
        True,
        -1.0001,
        1.0001,
        float("nan"),
        float("inf"),
    ],
)
def test_invalid_score_fails_closed(invalid_score):
    chunks = [make_chunk(invalid_score)]

    assert get_top_score(chunks) is None
    assert has_valid_evidence_contract(chunks) is False
    assert has_sufficient_evidence(chunks) is False


@pytest.mark.parametrize("score", [-1.0, 1.0])
def test_score_range_boundaries_are_valid(score):
    chunks = [make_chunk(score)]

    assert get_top_score(chunks) == score
    assert has_valid_evidence_contract(chunks) is True


def test_missing_environment_threshold_uses_default(monkeypatch):
    monkeypatch.delenv("ABSTENTION_THRESHOLD", raising=False)

    assert get_abstention_threshold() == DEFAULT_ABSTENTION_THRESHOLD
    assert get_abstention_threshold() == 0.30


def test_valid_environment_threshold_overrides_default(monkeypatch):
    monkeypatch.setenv("ABSTENTION_THRESHOLD", "0.32")

    assert get_abstention_threshold() == 0.32
    assert has_sufficient_evidence([make_chunk(0.31)]) is False


@pytest.mark.parametrize("configured_value", ["invalid", ""])
def test_non_numeric_environment_threshold_raises_value_error(
    monkeypatch,
    configured_value,
):
    monkeypatch.setenv("ABSTENTION_THRESHOLD", configured_value)

    with pytest.raises(ValueError, match="ABSTENTION_THRESHOLD"):
        get_abstention_threshold()


@pytest.mark.parametrize(
    "configured_value",
    ["nan", "inf", "-inf", "-1.01", "1.01"],
)
def test_out_of_range_environment_threshold_raises_value_error(
    monkeypatch,
    configured_value,
):
    monkeypatch.setenv("ABSTENTION_THRESHOLD", configured_value)

    with pytest.raises(ValueError, match="ABSTENTION_THRESHOLD"):
        get_abstention_threshold()


def test_explicit_threshold_overrides_environment(monkeypatch):
    monkeypatch.setenv("ABSTENTION_THRESHOLD", "0.90")

    assert has_sufficient_evidence(
        [make_chunk(0.50)],
        threshold=0.40,
    ) is True


@pytest.mark.parametrize(
    "invalid_threshold",
    ["0.30", True, -1.1, 1.1, float("nan"), float("inf")],
)
def test_invalid_explicit_threshold_raises_value_error(
    invalid_threshold,
):
    with pytest.raises(ValueError, match="threshold"):
        has_sufficient_evidence(
            [make_chunk(0.50)],
            threshold=invalid_threshold,
        )


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        # Amostras reais obtidas na calibracao do Golden Set.
        (0.28579118847846985, False),
        (0.33892568945884705, True),
        (0.2639181315898895, False),
    ],
)
def test_golden_set_calibration_regression(score, expected):
    assert has_sufficient_evidence(
        [make_chunk(score)],
        threshold=0.30,
    ) is expected
