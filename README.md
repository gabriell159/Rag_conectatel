# Concierge ConectaTel

Repositorio de trabalho da squad para o desafio final Concierge ConectaTel.

Estado atual do projeto: a implementacao propria feita ate agora esta concentrada
na Frente 1, em `src/01_pipeline_tratamento`, com tratamento e analise do log de
chamados. Os arquivos do scaffold aparecem neste repositorio somente para
registrar a arquitetura inicial recebida; eles nao fazem parte do pipeline atual.

## O que existe hoje

- Tratamento do CSV sintetico de chamados.
- Geracao do arquivo limpo `chamados_clean.csv`.
- Analises descritivas iniciais sobre volume, resolucao no primeiro contato e
  escalonamento por canal.
- Script de apoio para inspecionar os dados.
- Script de upload da pasta `data/raw` para S3.
- Corpus oficial da ConectaTel disponivel localmente em
  `data/raw/conectatel-dados/corpus`.
- Arquivos do scaffold original, mantidos apenas como referencia da arquitetura
  inicial.

## Estrutura principal

```text
.
|-- data/
|   |-- raw/
|   |   |-- conectatel-dados/
|   |   |   |-- corpus/                 # documentos oficiais para RAG
|   |   |   `-- log_chamados/           # CSV bruto e dicionario
|   |   |-- exemplo_politica_reembolso_v1.md
|   |   `-- exemplo_politica_reembolso_v2.md
|   |-- 05_golden_set_frente5.json     # casos de avaliacao
|   `-- processed/                      # resultados do tratamento e etapas futuras
|-- schemas/
|   `-- 05_interaction.schema.json      # contrato da Frente 5
|-- docs/                               # estrutura dos entregaveis finais
|-- src/
|   |-- 01_pipeline_tratamento/        # implementacao atual da Frente 1
|   |   |-- 00_main.py                  # orquestracao
|   |   |-- 01_tratamento.py            # limpeza
|   |   |-- 01_tratamento.ipynb         # apoio exploratorio
|   |   |-- 02_analise.py               # analises
|   |   |-- 03_visualizacao.py          # inspecao
|   |   `-- 04_upload_s3.py             # upload
|   |-- 05_integracao_auditoria_qualidade/ # integracao, auditoria e qualidade
|   |   |-- 00_contract.py
|   |   |-- 01_trace.py
|   |   |-- 02_audit.py
|   |   |-- 03_mock_pipeline.py
|   |   |-- 04_run_mock.py
|   |   `-- 05_query_trace.py
|   |-- ingest.py                       # scaffold de referencia
|   |-- index.py                        # scaffold de referencia
|   |-- query.py                        # scaffold de referencia
|   `-- audit_log.py                    # scaffold de referencia
|-- tests/
|   `-- test_05_frente5.py
|-- hello_bedrock.py                    # teste de referencia para Bedrock
|-- requirements.txt
`-- README.md
```

## Pre-requisitos

- Python 3.10 ou superior.
- `pip`.
- Para rodar o upload S3: credenciais AWS configuradas.
- Para o notebook: Jupyter ou extensao equivalente no VS Code.

## Como preparar o ambiente

No Windows PowerShell, a partir da raiz do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Crie o arquivo local de configuracao a partir do modelo e preencha as
credenciais necessarias:

```powershell
Copy-Item .env.example .env
```

O arquivo `.env` e ignorado pelo Git. Nunca publique credenciais reais no
repositorio. Para usar credenciais temporarias da AWS, preencha tambem
`AWS_SESSION_TOKEN`. O boto3 tambem pode usar perfis configurados localmente,
e o upload atual carrega as variaveis do `.env` quando presentes.

Se o PowerShell bloquear a ativacao do ambiente virtual, rode:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Depois feche e abra o PowerShell novamente, ou execute de novo o comando de
ativacao.

## Dados usados atualmente

Entrada bruta:

```text
data/raw/conectatel-dados/log_chamados/log_chamados_sintetico.csv
```

Arquivo limpo gerado pela Frente 1:

```text
data/processed/log_chamados/chamados_clean.csv
```

Dicionario dos campos:

```text
data/raw/conectatel-dados/log_chamados/dicionario_dados.md
```

Corpus documental oficial para as proximas frentes:

```text
data/raw/conectatel-dados/corpus/
```

Importante: o log de chamados serve para a Parte 1, analise de dados e decisoes
de design. As respostas do Concierge devem usar somente os documentos do corpus.

## Como rodar o que ja foi montado

### 1. Rodar o tratamento do CSV

O tratamento pode ser executado diretamente pelo script:

```text
src/01_pipeline_tratamento/01_tratamento.py
```

O script le o arquivo:

```text
data/raw/conectatel-dados/log_chamados/log_chamados_sintetico.csv
```

e salva:

```text
data/processed/log_chamados/chamados_clean.csv
```

O notebook `01_tratamento.ipynb` permanece como apoio para exploracao e
apresentacao. Ele usa os mesmos caminhos de entrada e saida, mas nao e
necessario para executar o pipeline.

Principais tratamentos feitos:

- remocao de duplicidades;
- normalizacao de canais, categorias, cidades, planos e textos;
- padronizacao de estados para UF;
- conversao de booleanos para `True`/`False`;
- conversao e limpeza de datas;
- tratamento de duracoes invalidas ou fora de faixa;
- tratamento de satisfacao fora do intervalo 1 a 5.

### 2. Rodar as analises descritivas

Com o ambiente virtual ativado:

```powershell
python src/01_pipeline_tratamento/02_analise.py
```

O script imprime:

- volume percentual de chamados por categoria;
- taxa de resolucao no primeiro contato por categoria;
- taxa de escalonamento humano por canal.

### 3. Inspecionar os dados

```powershell
python src/01_pipeline_tratamento/03_visualizacao.py
```

Hoje esse script imprime as primeiras linhas do CSV bruto. Ele serve apenas como
apoio de inspecao.

### 4. Enviar dados para S3

Antes de rodar, copie `.env.example` para `.env` e preencha as credenciais AWS
necessarias. As variaveis atualmente reconhecidas sao:

```env
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_SESSION_TOKEN=...
AWS_REGION=us-east-1
S3_BUCKET_NAME=nome-do-bucket
S3_PREFIX=conectatel
```

Depois rode:

```powershell
python src/01_pipeline_tratamento/04_upload_s3.py
```

O script atual envia somente as fontes explicitamente configuradas para:

```text
s3://<S3_BUCKET_NAME>/<S3_PREFIX>/raw/log_chamados/
s3://<S3_BUCKET_NAME>/<S3_PREFIX>/raw/corpus/
s3://<S3_BUCKET_NAME>/<S3_PREFIX>/processed/log_chamados/
```

O upload valida `S3_BUCKET_NAME`, `AWS_REGION`, `S3_PREFIX` e as pastas locais
antes de iniciar. O bucket precisa existir previamente e ser provisionado pela
administracao AWS; o pipeline operacional nao executa `HeadBucket` nem
`CreateBucket`. Ao final, informa quantos arquivos foram enviados e lista
individualmente qualquer falha.

### 5. Executar o fluxo completo da Frente 1

Para tratamento e analise, sem enviar para a AWS:

```powershell
python src/01_pipeline_tratamento/00_main.py
```

Esse fluxo tambem prepara e valida `data/processed/vectorstore` a partir do
artefato validado em `vectorstore_backup` quando necessario.

Para executar tambem o upload:

```powershell
python src/01_pipeline_tratamento/00_main.py --upload
```

Com `--upload`, o vector store tambem e publicado em
`s3://<S3_BUCKET_NAME>/<S3_PREFIX>/vectorstore/`, junto dos dados brutos,
corpus e dados processados.

## Arquitetura inicial recebida

Os arquivos abaixo vieram como base do desafio:

- `hello_bedrock.py`
- `src/ingest.py`
- `src/index.py`
- `src/query.py`
- `src/audit_log.py`
- `tests/test_hello_bedrock.py`

Esses arquivos vieram no scaffold base do desafio e registram a arquitetura
inicial proposta:

```text
ingestao -> indexacao -> consulta -> auditoria
```

Eles nao sao executados pelo pipeline atual e nao representam componentes
implementados pela squad neste momento. A implementacao atual esta restrita ao
diretorio `src/01_pipeline_tratamento`.

## Pontos pendentes para as proximas frentes

- Criar contrato JSON comum entre RAG, Concierge, Triagem e Auditoria.
- Criar `trace_id` padronizado em toda saida.
- Criar schema de auditoria final.
- Criar fluxo ponta a ponta com mocks.
- Integrar o golden set aos componentes reais das outras frentes.
- Integrar os componentes reais das outras frentes quando estiverem prontos.
- Atualizar este README conforme a solucao evoluir.

## Frente 5: contrato e governanca

A implementacao inicial da Frente 5 esta em `src/05_integracao_auditoria_qualidade`. Ela e
independente do scaffold e usa mocks enquanto os componentes reais das outras
frentes nao estao integrados.

O contrato esta definido em `schemas/05_interaction.schema.json`. Cada interacao
tem `trace_id`, decisao (`ANSWER`, `NO_ANSWER` ou `ESCALATE`), citacoes,
handoff quando necessario, duracao e versao dos componentes. A auditoria local
e gravada em `data/processed/audit/audit_log.jsonl`.

Executar uma interacao simulada:

```powershell
python -m src.05_integracao_auditoria_qualidade.04_run_mock "Qual e o prazo de reembolso?"
```

## RAG (Frente 2)

O ponto de entrada numerado do Concierge esta em
`src/03_concierge/00_main.py`. Ele carrega o `.env`, recupera os chunks
vigentes e chama o Amazon Bedrock para gerar a resposta:

```powershell
python -m src.03_concierge.00_main "Qual e o prazo para pedir reembolso?"
```

Para esse fluxo, configure `AWS_PROFILE` (ou as credenciais AWS),
`AWS_REGION` e `S3_BUCKET_NAME`. O bucket deve conter o indice FAISS em
`vectorstore/index.faiss` e os metadados em `metadata/metadata.json`.
O pipeline RAG está centralizado em `src/02_rag`; o Concierge fica em `src/03_concierge`.

Cada execuÃ§Ã£o integrada gera `trace_id` e grava a interaÃ§Ã£o em
`data/processed/audit/audit_log.jsonl`. Para avaliar o conjunto completo:

```powershell
python -m src.03_concierge.06_golden_set
```

O resultado Ã© salvo por padrÃ£o em
`data/processed/evaluation/golden_set_results.json`. A execuÃ§Ã£o usa Bedrock e
grava uma auditoria para cada caso.

Para gerar novamente o Ã­ndice RAG do zero (incluindo embeddings e upload):

```powershell
python -m src.02_rag.08_build_index
```

Para confirmar que os objetos publicados sÃ£o exatamente os consumidos pelo
retriever:

```powershell
python -m src.02_rag.09_verify_s3
```

Consultar uma interacao pelo `trace_id` retornado:

```powershell
python -m src.05_integracao_auditoria_qualidade.05_query_trace <trace_id>
```

Casos simulados disponiveis:

```powershell
python -m src.05_integracao_auditoria_qualidade.04_run_mock "Qual e o prazo de reembolso?"
python -m src.05_integracao_auditoria_qualidade.04_run_mock "Qual e a previsao do tempo?"
python -m src.05_integracao_auditoria_qualidade.04_run_mock "Estou sem sinal no meu bairro."
```

Executar os testes da Frente 5:

```powershell
python -m unittest discover -s tests -p "test_05_frente5.py" -v
```

## Comandos uteis

Instalar dependencias:

```powershell
python -m pip install -r requirements.txt
```

Rodar analises da Frente 1:

```powershell
python src/01_pipeline_tratamento/02_analise.py
```

Inspecionar CSV:

```powershell
python src/01_pipeline_tratamento/03_visualizacao.py
```

Upload para S3:

```powershell
python src/01_pipeline_tratamento/04_upload_s3.py
```

## Limitacoes conhecidas no estado atual

- A solucao final de RAG ainda nao foi implementada pela squad.
- A triagem e o escalonamento ainda nao foram integrados.
- A auditoria final com `trace_id` ainda nao foi implementada.
- O bucket e os prefixos dependem do `.env` preenchido; o bucket deve existir previamente.
- O notebook de tratamento e opcional; o script Python e o ponto principal de execucao.
- Os scripts dependem das bibliotecas listadas em `requirements.txt`.
