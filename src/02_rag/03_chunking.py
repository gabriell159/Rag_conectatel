import re
from copy import deepcopy


CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
MIN_CHUNK_SIZE = 100 #Adicionando para testar
"""
def dividir_por_secoes_markdown(texto: str) -> list[str]:
    
    # Divide um documento Markdown preservando títulos junto ao conteúdode cada seção.

    padrao = r"(?=^#{1,3}\s)"

    secoes = re.split(
        padrao,
        texto,
        flags=re.MULTILINE,
    )

    return [
        secao.strip()
        for secao in secoes
        if secao.strip()
    ]
"""

def dividir_por_secoes_markdown(
    texto: str,
    min_chunk_size: int = MIN_CHUNK_SIZE,
) -> list[str]:
    """
    Divide o Markdown por títulos e evita seções pequenas
    demais para possuírem contexto semântico suficiente.
    """

    padrao = r"(?=^#{1,3}\s)"

    secoes = re.split(
        padrao,
        texto,
        flags=re.MULTILINE,
    )

    secoes = [
        secao.strip()
        for secao in secoes
        if secao.strip()
    ]

    secoes_ajustadas = []
    indice = 0

    while indice < len(secoes):
        secao = secoes[indice]

        if (
            len(secao) < min_chunk_size
            and indice + 1 < len(secoes)
        ):
            secao = f"{secao}\n\n{secoes[indice + 1]}"
            indice += 1

        secoes_ajustadas.append(secao)
        indice += 1

    return secoes_ajustadas

# def dividir_secao_grande(
#     texto: str,
#     chunk_size: int = CHUNK_SIZE,
#     overlap: int = CHUNK_OVERLAP,
# ) -> list[str]:
#     """
#     Divide uma seção que excede o tamanho máximo, mantendo uma sobreposição entre os chunks pra não perder contexto."""

#     if len(texto) <= chunk_size:
#         return [texto]

#     chunks = []

#     inicio = 0

#     while inicio < len(texto):
#         fim = inicio + chunk_size

#         chunk = texto[inicio:fim].strip()

#         if chunk:
#             chunks.append(chunk)

#         if fim >= len(texto):
#             break

#         inicio = fim - overlap

#     return chunks

def dividir_secao_grande(
    texto: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """
    Divide seções grandes tentando preservar limites naturais
    de parágrafo, frase e palavra.
    """

    if len(texto) <= chunk_size:
        return [texto]

    chunks = []
    inicio = 0

    while inicio < len(texto):
        fim_maximo = min(inicio + chunk_size, len(texto))

        if fim_maximo == len(texto):
            chunk = texto[inicio:].strip()

            if chunk:
                chunks.append(chunk)

            break

        trecho = texto[inicio:fim_maximo]

        candidatos = [
            trecho.rfind("\n\n"),
            trecho.rfind("\n"),
            trecho.rfind(". "),
            trecho.rfind("? "),
            trecho.rfind("! "),
            trecho.rfind(" "),
        ]

        ponto_corte = max(candidatos)

        '''Evitando um corte excessivamente pequeno, para não gerar chunks muito pequenos.'''
        limite_minimo = int(chunk_size * 0.6)

        if ponto_corte < limite_minimo:
            ponto_corte = len(trecho)

        else:
            '''
            Inclui pontuação quando o corte ocorreu após final de frase.
            '''
            if trecho[ponto_corte:ponto_corte + 2] in {
                ". ",
                "? ",
                "! ",
            }:
                ponto_corte += 1

        fim = inicio + ponto_corte

        chunk = texto[inicio:fim].strip()

        if chunk:
            chunks.append(chunk)

        if fim >= len(texto):
            break

        novo_inicio = max(fim - overlap, inicio + 1)
        '''
         Aqui evita começar o próximo chunk no meio de palavra. Nos testes que eu estava fazendo
         mesmo com o chunk sendo direcionado para começar no fim do chunk anterior, ele estava cortando palavras. 
        '''
        while (
            novo_inicio < fim
            and novo_inicio > 0
            and not texto[novo_inicio - 1].isspace()
        ):
            novo_inicio += 1

        inicio = novo_inicio

    return chunks

def gerar_chunks_documento(
    documento: dict,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[dict]:
    """Gera chunks de um documento preservando seus metadados."""

    conteudo = documento["content"]
    metadata_documento = documento["metadata"]

    secoes = dividir_por_secoes_markdown(conteudo)

    chunks = []
    contador = 1

    for secao in secoes:
        partes = dividir_secao_grande(
            secao,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        for parte in partes:
            metadata = deepcopy(metadata_documento)

            chunk_id = (
                f"{metadata['doc_family_id']}"
                f"-v{metadata['version_ordinal']}"
                f"-chunk-{contador:03d}"
            )

            metadata["chunk_id"] = chunk_id

            chunks.append(
                {
                    "content": parte,
                    "metadata": metadata,
                }
            )

            contador += 1

    return chunks

def gerar_chunks_corpus(documentos: list[dict]) -> list[dict]:
    """
    Gera chunks para todos os documentos do corpus.
    """

    todos_chunks = []

    for documento in documentos:
        chunks = gerar_chunks_documento(documento)
        todos_chunks.extend(chunks)

    return todos_chunks