# Scaffold — Concierge ConectaTel

Repositório-scaffold mínimo para o desafio Concierge ConectaTel. Contém um
pipeline funcional de ponta a ponta (ingest → index → query → log) e a
estrutura de pastas sugerida para organizar os cinco entregáveis finais.
Use isto como ponto de partida — não como solução pronta: os limiares,
prompts e a lógica de escalonamento ainda precisam ser desenvolvidos e
calibrados pela squad.

## Pré-requisitos

- Python 3.10+
- Conta AWS individual com acesso ao Amazon Bedrock (ver "Acesso à API
  key" no desafio)
- Região AWS igual à usada nas Sprints anteriores

## Configuração

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # depois edite .env com seus valores
```

## Passo 0 — Validar acesso ao Bedrock ("hello Bedrock")

Antes de qualquer outra coisa, confirme que sua conta consegue chamar um
modelo Anthropic via Bedrock:

```bash
python hello_bedrock.py
```

Se falhar, revise o formulário de caso de uso da Anthropic no console do
Bedrock (ver seção "Acesso à API key" do desafio) antes de prosseguir.

## Pipeline de ponta a ponta

O scaffold já vem com dois documentos de exemplo em `data/raw/` (uma
política de reembolso vigente e sua versão revogada) só para validar que
o pipeline roda. Substitua pelo corpus real fornecido no pacote de
insumos antes de desenvolver a solução de verdade.

```bash
# 1. Ingestão: lê data/raw/, extrai metadados de vigência, gera chunks
python src/ingest.py

# 2. Indexação: gera embeddings (Titan via Bedrock) e salva o índice
python src/index.py

# 3. Consulta: filtra por vigência, calcula similaridade, decide
#    responder/"não sei", gera resposta com citação e registra na trilha
#    de auditoria
python src/query.py "Qual é o prazo para solicitar reembolso?"

# 4. Consultar a trilha de auditoria por trace_id (o trace_id é impresso
#    pelo passo 3)
python src/audit_log.py <trace_id>
```

## Testes de fumaça (sem chamar a AWS)

```bash
python tests/test_hello_bedrock.py
```

## Estrutura de pastas

```
conectatel-scaffold/
├── hello_bedrock.py          # teste mínimo de acesso ao Bedrock
├── requirements.txt
├── .env.example
├── src/
│   ├── ingest.py              # Etapa 1: leitura, front-matter, chunking
│   ├── index.py                # Etapa 2: embeddings + índice vetorial
│   ├── query.py                 # Etapa 3: filtro de vigência + geração
│   └── audit_log.py              # Etapa 4: trilha de auditoria (trace_id)
├── data/
│   ├── raw/                    # corpus de entrada (documentos com
│   │                            # front-matter de vigência)
│   └── processed/              # chunks, índice e log de auditoria
│                                # gerados pelo pipeline
├── tests/
│   └── test_hello_bedrock.py  # testes de fumaça da lógica pura
└── docs/                       # estrutura sugerida para os 5 entregáveis
    ├── 01_documento_principal/
    ├── 02_readme/
    ├── 03_codigo_fonte/
    ├── 04_slides/
    └── 05_reflexao/
```

## O que este scaffold NÃO faz por vocês

- Não calibra o limiar de abstenção ("não sei") — isso é decisão da squad,
  com o próprio conjunto de perguntas de teste (ver Parte 3 do desafio).
- Não implementa a lógica de escalonamento/triagem (Parte 4) nem os
  campos do registro de handoff — isso depende da política de suporte do
  corpus fornecido.
- Não usa um vector store gerenciado — o índice em memória (numpy) é só
  para manter o exemplo mínimo. Trocar por um vector store gerenciado é
  uma decisão de arquitetura da squad, não um requisito.
- Não implementa interface de demonstração — isso é uma sugestão de
  Stretch, não parte do scaffold.

## Referências

- Guia de metadados de vigência (fornecido junto com este scaffold)
- Grade de checklist de avaliação da banca (fornecido junto com este
  scaffold, para a squad se orientar sobre o que será avaliado)
