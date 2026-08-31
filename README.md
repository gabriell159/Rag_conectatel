# Concierge ConectaTel

Projeto de Concierge com pipeline de dados, RAG, Bedrock, triagem, auditoria e avaliação.

## Frentes

- **01 — Pipeline:** limpeza/análise de chamados e publicação de dados no S3.
- **02 — RAG:** ingestão, vigência, chunking, embeddings Titan, FAISS e S3.
- **03 — Concierge:** retrieval, guardrails, Bedrock e decisões ANSWER/NO_ANSWER/ESCALATE.
- **05 — Integração:** contrato, trace_id, handoff, auditoria, relatórios e demonstração serverless na AWS.

O tratamento e os testes unitários rodam localmente. RAG/Concierge real, upload S3 e golden set exigem AWS.

> O projeto não é executado sem instalação prévia: é necessário ter Python,
> as dependências do `requirements.txt` e, para o fluxo real, acesso AWS.

## Instalação no Windows

Pré-requisitos: Windows 10/11 e Python 3.11+.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

A ativação é opcional. Se quiser ativar:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Se o PowerShell bloquear scripts, use diretamente ` .\.venv\Scripts\python.exe ` nos comandos.

## Configuração AWS

```powershell
Copy-Item .env.example .env
```

Preencha no `.env`:

```env
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_SESSION_TOKEN=
AWS_REGION=us-east-1
AWS_PROFILE=
S3_BUCKET_NAME=seu-bucket
S3_PREFIX=conectatel
BEDROCK_MODEL_ID=mistral.mistral-large-3-675b-instruct
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
ABSTENTION_THRESHOLD=0.30
RAG_VECTORSTORE_VERSION=v1
AUDIT_LOG_PATH=data/processed/audit/audit_log.jsonl
AUDIT_S3_BUCKET=
AUDIT_S3_PREFIX=conectatel/audit
```

Use credenciais `AWS_*` ou `AWS_PROFILE`. Nunca commite o `.env`.

Valide a instalação e a identidade AWS antes de executar as etapas remotas:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -c "import boto3; print(boto3.__version__)"
aws sts get-caller-identity
```

O usuário/role precisa conseguir ler e gravar os objetos do bucket configurado
(`s3:ListBucket`, `s3:GetObject` e `s3:PutObject`) e invocar os modelos
habilitados no Bedrock (`bedrock:InvokeModel`). A região do `.env` deve ser uma
região em que esses modelos estejam disponíveis para a conta.

## Ordem recomendada da primeira execução

```text
instalar dependências → configurar .env → executar Frente 01
→ gerar/publicar o RAG → verificar S3 → executar Concierge
→ executar testes e golden set
```

## Frente 01 — pipeline

```powershell
.\.venv\Scripts\python.exe -m src.01_pipeline_tratamento.00_main
```

Saída: `data/processed/log_chamados/chamados_clean.csv`.

Publicar somente os dados da Frente 01:

```powershell
.\.venv\Scripts\python.exe -m src.01_pipeline_tratamento.00_main --upload
```

O `--upload` publica apenas os artefatos da Frente 01. Ele não substitui a
construção do índice RAG; execute também `src.02_rag.00_main --build`.

## Frente 02 — RAG

Fluxo oficial:

```text
ingestão → metadados/vigência → chunking → embeddings → FAISS → upload S3
```

Gerar o vector store do zero:

```powershell
.\.venv\Scripts\python.exe -m src.02_rag.00_main --build
```

Artefatos locais em `data/processed/vectorstore/`:

- `index.faiss`: embeddings Titan normalizados, 1024 dimensões.
- `metadata.json`: conteúdo e metadados dos chunks.
- `manifest.json`: versão, modelo, dimensão, quantidade e hash (opcional para compatibilidade com artefatos legados).

Verificar os objetos S3:

```powershell
.\.venv\Scripts\python.exe -m src.02_rag.00_main --verify
```

Com `S3_PREFIX=conectatel`:

```text
s3://SEU_BUCKET/conectatel/vectorstore/index.faiss
s3://SEU_BUCKET/conectatel/vectorstore/metadata.json
# opcional quando o pipeline o gerar:
s3://SEU_BUCKET/conectatel/vectorstore/manifest.json
```

O retriever usa o vector store oficial local, depois tenta o S3. `vectorstore_backup` é apenas salvaguarda quando o download oficial falha.

## Frente 03 — Concierge real

```powershell
.\.venv\Scripts\python.exe -m src.03_concierge.00_main "Qual e o prazo para pedir reembolso?"
```

A saída JSON contém `trace_id`, `decision`, `answer`, `citations`, `handoff`, `retrieval` e `component_versions`.

Exemplo resumido de resposta informativa:

```json
{
  "decision": "ANSWER",
  "answer": "90 dias corridos a partir da data de vencimento da fatura.",
  "citations": [{"document": "politica_reembolso_v2.md", "status": "vigente"}]
}
```

Perguntas fora do corpus retornam `NO_ANSWER`; solicitações que exigem ação
humana retornam `ESCALATE` com um `handoff` rastreável.

## Frente 05 — integração e auditoria

Executor real:

```powershell
.\.venv\Scripts\python.exe -m src.05_integracao_auditoria_qualidade.04_run_real "Qual e o prazo para pedir reembolso?"
```

Mock offline, somente para testes:

```powershell
.\.venv\Scripts\python.exe -m src.05_integracao_auditoria_qualidade.04_run_mock "Estou sem sinal."
```

Consultar uma interação:

```powershell
.\.venv\Scripts\python.exe -m src.05_integracao_auditoria_qualidade.05_query_trace <trace_id>
```

Gerar métricas:

```powershell
.\.venv\Scripts\python.exe -m src.05_integracao_auditoria_qualidade.06_quality_report
```

O contrato exige citações vigentes para `ANSWER`, nenhuma citação para `NO_ANSWER` e handoff completo para `ESCALATE`.

### Demonstração interna na AWS

A Frente 05 possui uma opção de demonstração serverless. Ela usa **API Gateway
HTTP → Lambda → RAG no S3/Bedrock**, registra logs no CloudWatch e mantém o
controle operacional em `/conectatel/demo/enabled` no Parameter Store. A
Lambda usa IAM Role própria; o arquivo `.env` não é publicado.

Pré-requisitos adicionais: AWS CLI autenticado, Docker Desktop em execução e
AWS SAM CLI. Faça o build e o deploy:

```powershell
sam build --template-file src/05_integracao_auditoria_qualidade/deployment/infra/template.yaml
sam deploy --guided --resolve-image-repos --template-file .aws-sam/build/template.yaml
```

No assistente, informe `RagBucketName`, `AuditBucketName`, `S3Prefix` e
`AllowedOrigin`. Use o bucket que contém o vector store oficial. O output
`ApiUrl` deve ser configurado em
`src/05_integracao_auditoria_qualidade/deployment/web/config.js`.

Ligue a demonstração apenas durante testes/apresentação:

```powershell
aws ssm put-parameter --name /conectatel/demo/enabled --type String --value true --overwrite --region us-east-1
```

Para desligá-la, altere `true` para `false`. A Lambda pode manter o valor em
cache por até 30 segundos. Desligada, ela não invoca Bedrock nem grava novas
interações de auditoria.

#### Interface no Amplify

A pasta `src/05_integracao_auditoria_qualidade/deployment/web/` contém uma
interface estática com chat, múltiplas conversas locais, histórico no navegador,
métricas da sessão, citações, handoff e `trace_id`. As métricas exibidas na
interface são locais; o relatório consolidado continua sendo gerado pela Frente
05 a partir da auditoria.

O deploy pode usar integração Git no Amplify ou publicação manual. Para a
publicação manual, compacte o **conteúdo** da pasta web e envie o ZIP em
**Amplify → Deploy without Git**:

```powershell
Compress-Archive -Path src\05_integracao_auditoria_qualidade\deployment\web\* -DestinationPath .\conectatel-web-amplify.zip
```

Após obter a URL HTTPS do Amplify, atualize `AllowedOrigin` com o domínio exato
do site para substituir o CORS temporário `*`. Use a proteção por senha do
Amplify em uma demonstração interna. `.aws-sam/` e os ZIPs de publicação são
artefatos locais e não devem ser commitados.

Consulte o guia detalhado em
[`docs/05_reflexao/deploy_interno.md`](docs/05_reflexao/deploy_interno.md).

## Golden set

O conjunto possui 200 perguntas fundamentadas nos documentos oficiais.

```powershell
.\.venv\Scripts\python.exe -m src.03_concierge.06_golden_set
```

Saídas: `data/processed/evaluation/golden_set_results.json` e `golden_set_history.jsonl`.

Os principais artefatos de avaliação e auditoria são:

```text
data/processed/evaluation/golden_set_results.json
data/processed/evaluation/golden_set_history.jsonl
data/processed/evaluation/quality_report.json
data/processed/audit/audit_log.jsonl
```

O JSONL é a persistência local padrão. Para uma trilha compartilhada, preencha
`AUDIT_S3_BUCKET` e `AUDIT_S3_PREFIX`; cada evento será validado pelo contrato
e gravado como `<prefix>/<trace_id>.json` no S3, além da cópia local.

Regenerar/validar o conjunto:

```powershell
.\.venv\Scripts\python.exe -m src.03_concierge.07_expand_golden_set
```

## Testes

Unitários e locais:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m "not integration"
```

Integração com AWS:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m integration
```

Todos:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Estrutura

```text
src/01_pipeline_tratamento/             Frente 01
src/02_rag/                             Frente 02
src/03_concierge/                       Frente 03
src/05_integracao_auditoria_qualidade/  Frente 05
data/raw/conectatel-dados/corpus/       corpus oficial
data/processed/vectorstore/             índice RAG
data/processed/audit/                   auditoria
schemas/05_interaction.schema.json      contrato
tests/                                  testes
docs/                                   documentação
TODO.md                                pendências
```

## Problemas comuns

- **Python não encontrado:** use `py -3.11`.
- **PowerShell bloqueado:** use `RemoteSigned` ou o Python do `.venv`.
- **ProfileNotFound:** deixe `AWS_PROFILE=` vazio ou informe um perfil existente.
- **404 no S3:** execute o build e confira bucket, prefixo e caminhos.
- **Erro no Bedrock:** confira região, modelo habilitado e `bedrock:InvokeModel`.
- **Golden set demorado:** acompanhe `data/processed/audit/audit_log.jsonl`.
