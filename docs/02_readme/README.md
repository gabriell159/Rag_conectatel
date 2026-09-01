# Concierge ConectaTel

Assistente de atendimento interno da ConectaTel desenvolvido pela Squad 1 (PB AI/R). A solução trata chamados, constrói um RAG sobre o corpus oficial, responde com evidências vigentes, encaminha casos sensíveis e mantém uma trilha de auditoria consultável.

> Este é o guia de execução oficial da raiz do repositório. Uma pessoa que não participou da implementação deve conseguir instalar, executar, testar e demonstrar o projeto seguindo este documento.

## Visão geral

| Frente | Entrega |
| --- | --- |
| 01 — Pipeline | Limpeza, análise e publicação de dados de chamados. |
| 02 — RAG | Chunking, metadados de vigência, embeddings Titan, FAISS e S3. |
| 03 — Concierge | Retrieval, Bedrock, citações, `ANSWER` e `NO_ANSWER`. |
| 04 — Triagem | Regras determinísticas e handoff estruturado para `ESCALATE`. |
| 05 — Integração | Contrato, `trace_id`, auditoria, qualidade e demonstração serverless. |

```text
Corpus e chamados → Pipeline/RAG → S3 (vectorstore)
                                 ↓
Usuário → Amplify → API Gateway → Lambda → Bedrock
                                      ↓
                             S3 (auditoria) → Console Cognito
```

## Pré-requisitos

### Local

- Windows 10/11, Python 3.11+ e Git.
- Acesso de leitura a este repositório.

### AWS (RAG real, golden set e demonstração)

- AWS CLI autenticado;
- acesso a S3 e Bedrock em `us-east-1`;
- SAM CLI e Docker Desktop, apenas para publicar a demonstração;
- permissões de CloudFormation, Lambda, API Gateway, IAM, SSM e Cognito, apenas para o deploy.

Confira a instalação:

```powershell
py -3.11 --version
aws --version
sam --version
docker version
aws sts get-caller-identity
```

## Instalação do zero

Na raiz do projeto:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

A ativação é opcional. Se desejar usá-la somente nesta janela:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Os comandos deste README usam `.\.venv\Scripts\python.exe`, portanto também funcionam sem ativar o ambiente.

## Configuração do `.env`

Edite o `.env` criado no passo anterior. Nunca versione esse arquivo.

```env
# Escolha AWS_PROFILE ou credenciais temporárias; não publique nenhum segredo.
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_SESSION_TOKEN=
AWS_PROFILE=
AWS_REGION=us-east-1

S3_BUCKET_NAME=seu-bucket
S3_PREFIX=conectatel
BEDROCK_MODEL_ID=mistral.mistral-large-3-675b-instruct
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
ABSTENTION_THRESHOLD=0.30
RAG_VECTORSTORE_VERSION=v1

AUDIT_LOG_PATH=data/processed/audit/audit_log.jsonl
AUDIT_S3_BUCKET=seu-bucket
AUDIT_S3_PREFIX=conectatel/audit
```

Notas:

- Com AWS IAM Identity Center, configure `AWS_PROFILE` e execute `aws sso login --profile <perfil>`.
- Credenciais temporárias expiram; em caso de `ExpiredToken`, renove a sessão e rode `aws sts get-caller-identity`.
- O usuário/role remoto precisa de `s3:ListBucket`, `s3:GetObject`, `s3:PutObject` e `bedrock:InvokeModel`.
- Um `AWS_PROFILE` inexistente causa `ProfileNotFound`; remova a variável ou informe um perfil válido.

Validação inicial:

```powershell
.\.venv\Scripts\python.exe -c "import boto3, faiss, numpy; print('dependências OK')"
aws sts get-caller-identity
```

## Ordem da primeira execução

```text
Instalar dependências → configurar .env → Pipeline → construir RAG →
verificar S3 → Concierge → auditoria/golden set → testes
```

## 1. Pipeline de dados

Tratamento e análise dos chamados:

```powershell
.\.venv\Scripts\python.exe -m src.01_pipeline_tratamento.00_main
```

O principal resultado é `data/processed/log_chamados/chamados_clean.csv`.

Para publicar os artefatos da Frente 01 no S3:

```powershell
.\.venv\Scripts\python.exe -m src.01_pipeline_tratamento.00_main --upload
```

`--upload` não constrói o índice vetorial; execute a etapa RAG a seguir.

## 2. RAG

Fluxo: ingestão → metadados/vigência → chunking → embeddings → FAISS → S3.

Construa e publique o vector store:

```powershell
.\.venv\Scripts\python.exe -m src.02_rag.00_main --build
```

Verifique os objetos publicados:

```powershell
.\.venv\Scripts\python.exe -m src.02_rag.00_main --verify
```

Com `S3_PREFIX=conectatel`, são esperados:

```text
s3://SEU_BUCKET/conectatel/vectorstore/index.faiss
s3://SEU_BUCKET/conectatel/vectorstore/metadata.json
s3://SEU_BUCKET/conectatel/vectorstore/manifest.json  (quando gerado)
```

O filtro de vigência é aplicado pelos metadados antes da similaridade. Assim, documento revogado não é uma fonte válida. Os artefatos locais ficam em `data/processed/vectorstore/`.

## 3. Concierge e triagem

Pergunta real ao Concierge:

```powershell
.\.venv\Scripts\python.exe -m src.03_concierge.00_main "Qual e o prazo para pedir reembolso?"
```

A saída possui `trace_id`, `decision`, `answer`, `citations`, `handoff`, `guardrail`, `retrieval` e `component_versions`.

| Cenário | Decisão esperada |
| --- | --- |
| Evidência vigente suficiente | `ANSWER`, com citações. |
| Sem fonte ou score insuficiente | `NO_ANSWER`, sem inventar resposta. |
| Fraude, contestação, falecimento, órgão externo, abuso ou visita técnica | `ESCALATE`, com handoff. |

A triagem ocorre antes do RAG apenas em relatos que exigem ação. Perguntas informativas continuam no RAG. O handoff registra protocolo, categoria, urgência, ação solicitada e `rule_id`, evitando que o cliente repita contexto.

## 4. Auditoria e relatório de qualidade

Executar o fluxo integrado real:

```powershell
.\.venv\Scripts\python.exe -m src.05_integracao_auditoria_qualidade.04_run_real "Acredito que fizeram fraude usando minha linha."
```

Mock offline, útil para teste sem AWS:

```powershell
.\.venv\Scripts\python.exe -m src.05_integracao_auditoria_qualidade.04_run_mock "Preciso de visita técnica, estou sem sinal há dias."
```

Consultar um rastro local:

```powershell
.\.venv\Scripts\python.exe -m src.05_integracao_auditoria_qualidade.05_query_trace <trace_id>
```

Gerar relatório consolidado:

```powershell
.\.venv\Scripts\python.exe -m src.05_integracao_auditoria_qualidade.06_quality_report
```

Com `AUDIT_S3_BUCKET` configurado, cada evento validado é salvo em `<AUDIT_S3_PREFIX>/<trace_id>.json`, além do log local. Principais saídas:

```text
data/processed/audit/audit_log.jsonl
data/processed/evaluation/golden_set_results.json
data/processed/evaluation/golden_set_history.jsonl
data/processed/evaluation/quality_report.json
```

## 5. Golden set e testes

Executar golden set:

```powershell
.\.venv\Scripts\python.exe -m src.03_concierge.06_golden_set
```

Regenerar/validar sua expansão:

```powershell
.\.venv\Scripts\python.exe -m src.03_concierge.07_expand_golden_set
```

Testes locais (recomendado antes de publicar):

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m "not integration"
```

Testes de integração AWS e todos os testes:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m integration
.\.venv\Scripts\python.exe -m pytest -q
```

## 6. Demonstração interna AWS

O template SAM em `src/05_integracao_auditoria_qualidade/deployment/infra/template.yaml` provisiona API Gateway, Lambda em imagem Docker, IAM Role, Parameter Store, Cognito, CloudWatch e integrações S3/Bedrock.

Com Docker Desktop aberto e AWS autenticada:

```powershell
sam build --template-file src/05_integracao_auditoria_qualidade/deployment/infra/template.yaml
sam deploy --guided --resolve-image-repos --template-file .aws-sam/build/template.yaml
```

No primeiro deploy, informe:

```text
Stack Name: conectatel-demo
AWS Region: us-east-1
RagBucketName: bucket que contém conectatel/vectorstore/
AuditBucketName: bucket para conectatel/audit/
S3Prefix: conectatel
AllowedOrigin: https://SEU_DOMINIO.amplifyapp.com
BedrockModelId: mistral.mistral-large-3-675b-instruct
AuditCallbackUrl: https://SEU_DOMINIO.amplifyapp.com/audit.html
AuditUserPoolDomainPrefix: prefixo-globalmente-unico
```

Registre os outputs `ApiUrl`, `AuditApiUrl`, `AuditUserPoolId`, `AuditUserPoolClientId` e `AuditUserPoolDomain`.

### Interruptor operacional

A API pública começa desligada. Ligue-a apenas em testes/apresentação:

```powershell
aws ssm put-parameter --name /conectatel/demo/enabled --type String --value true --overwrite --region us-east-1
```

Desligue após o uso:

```powershell
aws ssm put-parameter --name /conectatel/demo/enabled --type String --value false --overwrite --region us-east-1
```

A Lambda pode manter o valor em cache por até 30 segundos.

## 7. Interface Amplify e console de auditoria

A interface estática está em `src/05_integracao_auditoria_qualidade/deployment/web/`. Atualize `config.js` com os outputs SAM:

```js
window.CONCIERGE_CONFIG = {
  apiUrl: "https://SUA_API.execute-api.REGION.amazonaws.com/ask",
  auditApiUrl: "https://SUA_API.execute-api.REGION.amazonaws.com/audit",
  auditUserPoolClientId: "OUTPUT_AuditUserPoolClientId",
  auditUserPoolDomain: "OUTPUT_AuditUserPoolDomain",
};
```

Para publicação manual, compacte o conteúdo da pasta web:

```powershell
Compress-Archive -Path src\05_integracao_auditoria_qualidade\deployment\web\* -DestinationPath .\conectatel-web-amplify.zip -Force
```

No AWS Amplify, escolha **Deploy without Git** e envie o ZIP. O domínio HTTPS real deve ser usado em `AllowedOrigin` e `AuditCallbackUrl`. Ative proteção por senha do Amplify para a demonstração interna.

### Usuário auditor

Abra `https://SEU_DOMINIO.amplifyapp.com/audit.html`. A console usa JWT Cognito e exige o grupo `auditor`; o navegador não recebe acesso direto ao S3.

```powershell
aws cognito-idp admin-create-user --user-pool-id <POOL_ID> --username <EMAIL> --user-attributes Name=email,Value=<EMAIL> Name=email_verified,Value=true --message-action SUPPRESS --region us-east-1
aws cognito-idp admin-set-user-password --user-pool-id <POOL_ID> --username <EMAIL> --password "<SENHA_FORTE>" --permanent --region us-east-1
aws cognito-idp admin-add-user-to-group --user-pool-id <POOL_ID> --username <EMAIL> --group-name auditor --region us-east-1
```

Após entrar, cole o `trace_id` fornecido pela banca ou use **Carregar últimos traces**. A lista mostra até 20 identificadores recentes e horários; após selecionar um, a tela recupera pergunta, resposta, decisão, fontes, guardrail, handoff e duração.

## Estrutura

```text
src/01_pipeline_tratamento/             Pipeline
src/02_rag/                             RAG e vector store
src/03_concierge/                       Orquestrador e golden set
src/04_triage/                          Regras de escalonamento
src/05_integracao_auditoria_qualidade/  Auditoria e deploy
data/raw/conectatel-dados/corpus/       Corpus oficial
data/processed/                         Artefatos gerados
schemas/05_interaction.schema.json      Contrato de interação
tests/                                  Testes automatizados
docs/                                   Documentação de entrega
```

## Problemas comuns

| Problema | Solução |
| --- | --- |
| `sam`/`aws` não reconhecido | Reabra o PowerShell após instalar e confira o `PATH`. |
| Docker não inicia | Habilite virtualização/WSL 2 e reinicie a máquina. |
| `ExpiredToken` | Renove SSO/credenciais e valide com `aws sts get-caller-identity`. |
| `ProfileNotFound` | Corrija/remova `AWS_PROFILE` ou execute `aws configure sso`. |
| Erro Bedrock | Confira região, acesso ao modelo e `bedrock:InvokeModel`. |
| API retorna 503 | Ligue o parâmetro SSM e aguarde até 30 segundos. |
| Console restringe acesso | Adicione o usuário ao grupo Cognito `auditor` e faça novo login. |
| Amplify exibe versão antiga | Faça `Ctrl + F5` e confira se o ZIP contém os arquivos na raiz. |

## Segurança e encerramento

- Nunca versione `.env`, senhas, tokens ou credenciais.
- `.aws-sam/` e ZIPs de publicação são artefatos locais e ficam no `.gitignore`.
- Ao terminar uma demonstração, desligue o interruptor SSM para evitar novas invocações Bedrock.
- Antes da entrega, execute os testes locais, faça o ensaio de reconstrução por `trace_id` e crie uma tag Git da versão congelada.

Mais detalhes operacionais: [docs/05_reflexao/deploy_interno.md](docs/05_reflexao/deploy_interno.md).
