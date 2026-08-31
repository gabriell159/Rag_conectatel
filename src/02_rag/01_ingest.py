from pathlib import Path
import importlib

carregar_documento = importlib.import_module("src.02_rag.02_metadata").carregar_documento

CORPUS_PATH = Path("data/raw/conectatel-dados/corpus")


def listar_arquivos_corpus(corpus_path: Path = CORPUS_PATH) -> list[Path]:
    """
    Localiza todos os arquivos Markdown do corpus.
    """

    if not corpus_path.exists():
        raise FileNotFoundError(
            f"Diretório do corpus não encontrado: {corpus_path}"
        )

    arquivos = sorted(corpus_path.rglob("*.md"))

    if not arquivos:
        raise FileNotFoundError(
            f"Nenhum documento Markdown encontrado em: {corpus_path}"
        )

    return arquivos

def carregar_corpus(corpus_path: Path = CORPUS_PATH) -> list[dict]:
    """
    Carrega e valida os documentos Markdown do corpus.
    """

    arquivos = listar_arquivos_corpus(corpus_path)
    documentos = []
    
    for arquivo in arquivos:
        documento = carregar_documento(arquivo)
        documento["metadata"]["category"] = arquivo.parent.name
        documento["metadata"]["source"] = (
            "corpus/" + arquivo.relative_to(corpus_path).as_posix()
        )
        documentos.append(documento)

    return documentos
