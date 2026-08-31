import os


DEFAULT_ABSTENTION_THRESHOLD = 0.30
MIN_SIMILARITY_SCORE = -1.0
MAX_SIMILARITY_SCORE = 1.0


def _is_valid_score(value: object) -> bool:
    """Verifica se um valor pertence ao dominio esperado do score."""

    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and MIN_SIMILARITY_SCORE <= value <= MAX_SIMILARITY_SCORE
    )


def get_abstention_threshold() -> float:
    """Retorna o threshold configurado para abstencao."""

    configured_value = os.getenv("ABSTENTION_THRESHOLD")

    if configured_value is None:
        return DEFAULT_ABSTENTION_THRESHOLD

    try:
        threshold = float(configured_value)
    except ValueError as error:
        raise ValueError(
            "ABSTENTION_THRESHOLD deve ser um numero entre -1.0 e 1.0."
        ) from error

    if not _is_valid_score(threshold):
        raise ValueError(
            "ABSTENTION_THRESHOLD deve estar entre -1.0 e 1.0."
        )

    return threshold


def get_top_score(chunks: list[dict]) -> float | None:
    """Retorna o maior score quando todos os scores sao validos."""

    if not isinstance(chunks, list) or not chunks:
        return None

    scores = []

    for chunk in chunks:
        if not isinstance(chunk, dict):
            return None

        score = chunk.get("score")

        if not _is_valid_score(score):
            return None

        scores.append(float(score))

    return max(scores)


def has_valid_evidence_contract(chunks: list[dict]) -> bool:
    """Valida defensivamente o contrato de evidencias da Frente 2."""

    if not isinstance(chunks, list) or not chunks:
        return False

    for chunk in chunks:
        if not isinstance(chunk, dict):
            return False

        if not _is_valid_score(chunk.get("score")):
            return False

        if chunk.get("status") != "vigente":
            return False

    return True


def has_sufficient_evidence(
    chunks: list[dict],
    threshold: float | None = None,
) -> bool:
    """Indica se as evidencias validas atingem o threshold configurado."""

    if not has_valid_evidence_contract(chunks):
        return False

    if threshold is None:
        effective_threshold = get_abstention_threshold()
    else:
        if not _is_valid_score(threshold):
            raise ValueError(
                "threshold deve ser um numero entre -1.0 e 1.0."
            )

        effective_threshold = float(threshold)

    top_score = get_top_score(chunks)

    return top_score is not None and top_score >= effective_threshold
