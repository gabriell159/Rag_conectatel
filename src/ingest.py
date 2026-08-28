"""
ingest.py — Etapa 1 do pipeline: ingestão e chunking do corpus.

Lê documentos de data/raw/ (arquivos .md ou .txt), extrai os metadados de
vigência de um bloco de front-matter no topo de cada arquivo, divide o
texto em chunks e grava o resultado em data/processed/chunks.jsonl.

Formato esperado de front-matter no início de cada arquivo (delimitado por
linhas "---"), conforme o padrão do guia de metadados de vigência:

    ---
    doc_family_id: politica-reembolso
    version_ordinal: 2
    effective_from: 2026-01-01
    effective_to:
    status: vigente
    ---
    <corpo do documento>

Uso:
    python src/ingest.py
"""

import json
import re
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "chunks.jsonl"

CHUNK_SIZE_CHARS = 1200
CHUNK_OVERLAP_CHARS = 150

FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
REQUIRED_FIELDS = [
    "doc_family_id",
    "version_ordinal",
    "effective_from",
    "effective_to",
    "status",
]


def parse_front_matter(raw_text: str) -> tuple[dict, str]:
    """Extrai os campos de vigência do front-matter e retorna (metadados, corpo)."""
    match = FRONT_MATTER_RE.match(raw_text)
    if not match:
        raise ValueError(
            "Arquivo sem front-matter de vigência. Todo documento do corpus "
            "precisa declarar doc_family_id, version_ordinal, effective_from, "
            "effective_to e status (ver guia de metadados de vigência)."
        )
    meta_block, body = match.groups()
    metadata: dict = {}
    for line in meta_block.splitlines():
        if not line.strip():
            continue
        key, _, value = line.partition(":")
        metadata[key.strip()] = value.strip() or None

    missing = [f for f in REQUIRED_FIELDS if f not in metadata]
    if missing:
        raise ValueError(f"Front-matter incompleto — faltam campos: {missing}")

    if metadata.get("version_ordinal") is not None:
        metadata["version_ordinal"] = int(metadata["version_ordinal"])

    return metadata, body.strip()


def chunk_text(text: str, size: int = CHUNK_SIZE_CHARS, overlap: int = CHUNK_OVERLAP_CHARS) -> list[str]:
    """Divide o texto em chunks de tamanho fixo com sobreposição simples."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end].strip())
        start = end - overlap
    return [c for c in chunks if c]


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    source_files = sorted(RAW_DIR.glob("*.md")) + sorted(RAW_DIR.glob("*.txt"))
    if not source_files:
        print(
            f"Nenhum documento encontrado em {RAW_DIR}. Coloque o corpus "
            "fornecido (ou uma amostra para teste) nessa pasta antes de rodar."
        )
        return

    total_chunks = 0
    with open(OUT_PATH, "w", encoding="utf-8") as out_file:
        for path in source_files:
            raw_text = path.read_text(encoding="utf-8")
            try:
                metadata, body = parse_front_matter(raw_text)
            except ValueError as exc:
                print(f"[ERRO] {path.name}: {exc}")
                continue

            doc_chunks = chunk_text(body)
            for i, chunk in enumerate(doc_chunks):
                record = {
                    "chunk_id": f"{path.stem}_{i}",
                    "source_file": path.name,
                    "text": chunk,
                    **metadata,
                }
                out_file.write(json.dumps(record, ensure_ascii=False) + "\n")
                total_chunks += 1

    print(f"Ingestão concluída: {len(source_files)} arquivo(s), {total_chunks} chunk(s) gravados em {OUT_PATH}")


if __name__ == "__main__":
    main()
