from .bedrock_client import generate_text
from .confidence import (
    get_top_score,
    has_sufficient_evidence,
)
from .prompts import (
    GROUNDED_RETRY_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    build_grounded_retry_prompt,
    build_user_prompt,
)


GROUNDED_RETRY_THRESHOLD = 0.30


def answer_question(
    question: str,
    chunks: list[dict],
) -> dict:
    """Responde uma pergunta usando os chunks previamente recuperados."""

    if not isinstance(question, str) or not question.strip():
        raise ValueError("question deve ser uma string não vazia.")

    normalized_question = question.strip()
    sufficient_evidence = has_sufficient_evidence(chunks)
    retrieval_score = get_top_score(chunks)

    if not sufficient_evidence:
        return {
            "question": normalized_question,
            "decision": "NO_ANSWER",
            "answer": "NO_ANSWER",
            "sources": [],
            "retrieval_score": retrieval_score,
        }

    user_prompt = build_user_prompt(normalized_question, chunks)
    generated_answer = generate_text(SYSTEM_PROMPT, user_prompt)

    if (
        generated_answer == "NO_ANSWER"
        and retrieval_score is not None
        and retrieval_score >= GROUNDED_RETRY_THRESHOLD
    ):
        retry_prompt = build_grounded_retry_prompt(normalized_question, chunks)
        generated_answer = generate_text(GROUNDED_RETRY_SYSTEM_PROMPT, retry_prompt)

    if generated_answer == "NO_ANSWER":
        return {
            "question": normalized_question,
            "decision": "NO_ANSWER",
            "answer": "NO_ANSWER",
            "sources": [],
            "retrieval_score": retrieval_score,
        }

    sources = [
        {
            "document": chunk["document"],
            "chunk_id": chunk["chunk_id"],
            "score": chunk["score"],
            "status": chunk["status"],
        }
        for chunk in chunks
    ]

    return {
        "question": normalized_question,
        "decision": "ANSWER",
        "answer": generated_answer,
        "sources": sources,
        "retrieval_score": retrieval_score,
    }
