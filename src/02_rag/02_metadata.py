from pathlib import Path
from datetime import date

import yaml


CAMPOS_OBRIGATORIOS = {
    "doc_family_id",
    "version_ordinal",
    "effective_from",
    "effective_to",
    "status",
}

STATUS_VALIDOS = {"vigente", "revogado"}

FAMILY_ALIASES = {
    "pol-reembolso": "politica-reembolso",
}


def normalizar_doc_family_id(doc_family_id: str) -> str:
    """
    Normaliza identificadores equivalentes de uma mesma família documental.
    """
    return FAMILY_ALIASES.get(doc_family_id, doc_family_id)


def extrair_front_matter(caminho_arquivo: Path) -> tuple[dict, str]:
    """
    Separa os metadados YAML do conteúdo Markdown.
    """

    texto = caminho_arquivo.read_text(encoding="utf-8")

    if not texto.startswith("---"):
        raise ValueError(
            f"O arquivo {caminho_arquivo.name} não possui front matter YAML."
        )

    partes = texto.split("---", 2)

    if len(partes) < 3:
        raise ValueError(
            f"Front matter inválido no arquivo {caminho_arquivo.name}."
        )

    yaml_texto = partes[1]
    conteudo = partes[2].strip()

    metadata = yaml.safe_load(yaml_texto)

    if not isinstance(metadata, dict):
        raise ValueError(
            f"Metadados inválidos no arquivo {caminho_arquivo.name}."
        )

    return metadata, conteudo


def validar_metadata(metadata: dict, nome_arquivo: str) -> None:
    """
    Valida os metadados obrigatórios de vigência.
    """

    campos_faltantes = CAMPOS_OBRIGATORIOS - metadata.keys()

    if campos_faltantes:
        raise ValueError(
            f"{nome_arquivo}: campos obrigatórios ausentes: "
            f"{', '.join(sorted(campos_faltantes))}"
        )

    if metadata["status"] not in STATUS_VALIDOS:
        raise ValueError(
            f"{nome_arquivo}: status inválido: {metadata['status']}"
        )

    if not isinstance(metadata["version_ordinal"], int):
        raise ValueError(
            f"{nome_arquivo}: version_ordinal deve ser inteiro."
        )

    for field in ("effective_from", "effective_to"):
        value = metadata[field]
        if value in (None, ""):
            continue
        try:
            date.fromisoformat(str(value))
        except ValueError as error:
            raise ValueError(f"{nome_arquivo}: {field} deve estar em AAAA-MM-DD.") from error

    if metadata["effective_to"] and str(metadata["effective_from"]) >= str(metadata["effective_to"]):
        raise ValueError(f"{nome_arquivo}: effective_to deve ser posterior a effective_from.")


def carregar_documento(caminho_arquivo: Path) -> dict:
    """
    Carrega e valida um documento do corpus.
    """

    metadata, conteudo = extrair_front_matter(caminho_arquivo)

    validar_metadata(
        metadata=metadata,
        nome_arquivo=caminho_arquivo.name,
    )

    metadata["doc_family_id"] = normalizar_doc_family_id(
        metadata["doc_family_id"]
    )

    metadata["source"] = caminho_arquivo.name

    return {
        "content": conteudo,
        "metadata": metadata,
    }


def filter_vigentes(documentos: list[dict]) -> list[dict]:
    """
    Mantém somente documentos vigentes.

    Deve ser aplicado antes da busca por similaridade.
    """

    return [
        documento
        for documento in documentos
        if documento["metadata"]["status"] == "vigente"
    ]
