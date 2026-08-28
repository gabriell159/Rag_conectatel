"""Geracao de identificadores de rastreabilidade."""

from uuid import uuid4


def new_trace_id() -> str:
    return f"trc_{uuid4().hex}"
