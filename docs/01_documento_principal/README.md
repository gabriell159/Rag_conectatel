# 1. Documento principal

Coloquem aqui o documento principal da entrega (PDF ou DOCX), contendo:

- Nomes da squad e papéis de cada integrante
- Arquitetura da solução
- Decisões de design das Partes 1 a 5
- Transcrições de 10 a 15 interações de teste com o assistente
- Riscos conhecidos

Ver a seção "O que entregar" do desafio para os requisitos completos.

---

### Gabriel Ferreira Oliveira

- **Papel:** Frente 1 (Pipeline de Dados e Análise)
- **Responsabilidades:** Ingestão local de logs de chamados via Pandas, tratamento de dados (limpeza e estruturação), análise exploratória gerando insights acionáveis para o design do assistente e integração de armazenamento na nuvem via AWS S3.

### Decisões de Design — Parte 1: Pipeline de Dados e Análise

### 1. Decisões de Tratamento e Limpeza

Durante a ingestão do arquivo `log_chamados_sintetico.csv`, foram identificadas diversas inconsistências típicas de logs operacionais. O pipeline de tratamento (`src/01_pipeline_tratamento/01_tratamento.py`) realizou as seguintes padronizações:

- **Desduplicação:** Remoção de linhas exatamente iguais.
- **Padronização Textual e Booleana:** Uniformização de categorias, canais e estados (ex: mapeamento para siglas UF em maiúsculas) e conversão de múltiplos formatos de resposta ("Sim", "S", "1") para booleanos nativos (`True`/`False`).
- **Tratamento de Valores Nulos (NaN) e Outliers:**
  - Para a coluna `data_abertura`, optamos por não excluir as linhas com datas ausentes (`NaN`). A exclusão reduziria o tamanho da amostra e causaria perda de informações valiosas sobre o comportamento das categorias e taxas de escalonamento. Esses registros serão ignorados apenas em eventuais agregações estritamente temporais.
  - Para as colunas `duracao_minutos` e `satisfacao_1_a_5`, foram encontradas algumas inconsistências nos valores. Por exemplo, a coluna de `duracao_minutos` recebeu um tratamento para valores considerados ruidosos, onde minutagens <= 0 ou > 180 são consideradas como valores nulos, decidimos **não aplicar técnicas de imputação (como preenchimento pela média)**. A ausência de resposta em uma pesquisa de satisfação (CSAT) é um comportamento orgânico do usuário. Preencher esses vazios com a média distorceria a métrica real, inflaria a base de respondentes e reduziria a variância natural do conjunto, o que prejudicaria análises estatísticas mais profundas. Agregações futuras lidarão com esses nulos omitindo-os nativamente via Pandas.

### 2. Análises Descritivas

Executamos agregações para entender o comportamento dos chamados. Os três principais _insights_ foram:

1. **Volume de Chamados por Categoria:** Foi possível notar que existe um certo nível de equilibrio relacionado a quantidade de chamados, onde a categoria 'Portabilidade' representa o maior volume da operação (16.25%) e a categoria 'Cobertura' apresenta o menor número de chamados (11.25%).
2. **Taxa de Resolução no 1º Contato (FCR):** As categorias 'Cobertura' e 'Tecnico' apresentam grande dificuldade de contenção, com apenas 50% e 58.14% dos casos resolvidos no primeiro contato, respectivamente.
3. **Escalonamento por Canal:** Foi possível observar um padrão próximo a 30% de necessidade de intervenção humana nos atendimentos. O canal de 'Loja Fisica' (29.17%) foi o que apresentou maior necessidade de atendimento humano.

> **Nota Analítica sobre a "Loja Física":** Identificamos uma anomalia nos dados, no canal 'Loja Fisica', a taxa de `encaminhado_humano` é de apenas 29.17%. Em um ambiente presencial convencional, é esperado um valor próximo a 100%. Decidimos **não alterar esse dado sintético no CSV**, pois essa inconsistência pode refletir falhas operacionais de registro no log ou a forte presença de totens de autoatendimento nas lojas. Optamos por preservar o dado bruto para expor o comportamento real da fonte, direcionando a nossa decisão de design para o gargalo técnico.

### 3. Síntese e Decisão de Design do Assistente

**Síntese dos Dados:**
A análise revela que, embora 'Portabilidade' e 'Fatura' tenham alto volume de chamados, elas possuem boas taxas de resolução (em torno de 70%). O verdadeiro gargalo operacional e de atrito com o cliente reside nas categorias técnicas ('Cobertura' e 'Tecnico'), que falham em ser resolvidas de primeira em quase metade das vezes.

**Decisão de Design do Concierge:**
Com base na análise descritiva, a decisão de design estrutural para o assistente será a implementação de um **guardrail de segurança, e também um nível de score mínimo para que o agente seja apto a responder**. Os logs revelam que os problemas estruturais da rede possuem as piores taxas de resolução no primeiro contato, especificamente nas categorias 'Cobertura' (apenas 50% de resolução) e 'Técnico' (58,14%). Aprofundando nas subcategorias, o gargalo operacional fica evidente: falhas como "Sem sinal" e "Sinal instável" geram as maiores taxas de escalonamento da operação, com 66,67% e 63,64%, respectivamente.

Como os dados provam a ineficiência do atendimento inicial nesses cenários, o agente será configurado para não tentar realizar diagnósticos imprecisos. Ao identificar essas intenções, o assistente informará claramente ao cliente que não possui as informações ou permissões sistêmicas necessárias para responder a problemas de infraestrutura de rede, garantindo que não haja alucinação de dados. Imediatamente após essa declaração, o sistema fará o transbordo para um especialista humano, repassando o contexto prévio para evitar que o cliente repita as informações.

---

### Pedro Henrique Oliveira Nascimento

- **Papel:** Frente 2 RAG (Retrieval-Augmented Generation)

- **Responsabilidades:** Construção do pipeline RAG, incluindo ingestão do corpus, controle de vigência documental, chunking, geração de embeddings com Amazon Bedrock, indexação vetorial com FAISS, recuperação semântica e persistência dos artefatos no Amazon S3.

### Decisões de Desenvolvimento

### 1. Ingestão e Chunking

O corpus é composto por 12 documentos Markdown, organizados entre FAQs, planos, políticas e procedimentos. Durante a ingestão, são preservados metadados como `doc_family_id`, versão, período de vigência, `status`, fonte e categoria.

Foi adotado **chunking estrutural baseado nos títulos Markdown**, preservando as divisões semânticas dos documentos. Como fallback para seções extensas, foram definidos `CHUNK_SIZE = 1000` e `CHUNK_OVERLAP = 150`.

Durante os testes, alguns títulos isolados com menos de 100 caracteres. A estratégia foi ajustada para agrupá-los na seção seguinte, reduzindo o corpus de 58 para **54 chunks**, com tamanho médio de aproximadamente 341 caracteres. Para blocos extensos, o algoritmo prioriza cortes naturais em parágrafos, frases ou palavras.

### 2. Embeddings e Indexação Vetorial

Os 54 chunks são transformados em embeddings utilizando o **Amazon Titan Text Embeddings V2**, através do Amazon Bedrock, produzindo vetores normalizados de **1024 dimensões**.

Para indexação foi utilizado o **FAISS `IndexFlatIP`**. Como o corpus é pequeno, foi feito uma busca exata em vez de estruturas aproximadas mais complexas. Com embeddings normalizados, o produto interno é utilizado como equivalente à similaridade de cosseno.

O índice é persistido em `index.faiss`, enquanto `metadata.json` mantém a associação entre os vetores, conteúdos e metadados.

### 3. Controle de Vigência e Recuperação

Um dos principais guardrails do RAG é o controle determinístico de vigência. Documentos com `status = revogado` são eliminados do conjunto de candidatos **antes do cálculo de similaridade**.

Esse comportamento foi validado utilizando as duas versões da Política de Reembolso. Mesmo em uma consulta contendo a regra antiga de "15 dias", a versão revogada não participou dos resultados.

Em uma consulta sobre o prazo vigente para contestação de fatura, o retriever recuperou corretamente a Política de Reembolso V2, contendo o prazo de **90 dias corridos**, com score aproximado de **0,8015**.

O retriever retorna `content`, documento de origem, `chunk_id`, score, status e metadados, garantindo rastreabilidade para as etapas seguintes.

### 4. Persistência AWS e Testes

Os dados do RAG são persistidos no **Amazon S3**, organizados nos prefixes:

- `corpus/`
- `metadata/`
- `vectorstore/`

Também foi implementada recuperação automática do vector store: caso os arquivos não estejam disponíveis localmente, o sistema realiza o download do S3 antes da consulta.

foi criado testes automatizados com `pytest`, cobrindo chunking, metadados, vigência e retrieval. Ao final da implementação foram obtidos:

**8 testes executados e os 8 testes aprovados.**

### 5. Síntese e Decisão de Design

A arquitetura do RAG foi projetada priorizando **qualidade da recuperação, rastreabilidade e segurança documental**.

O chunking estrutural preserva o contexto dos documentos, o Amazon Titan gera as representações vetoriais, o FAISS realiza a recuperação semântica e o S3 mantém os artefatos persistidos.

Como principal decisão de segurança, documentos revogados não participam da busca semântica, reduzindo o risco de o assistente fundamentar respostas em políticas obsoletas.

---

### Ana Lícia Ferreira Soares

- **Papel:** Frente 3 (Concierge / Bedrock)
- **Responsabilidades:** Seleção e integração do modelo generativo no Amazon Bedrock, definição do limiar de confiança, grounding das respostas, retorno seguro de `NO_ANSWER` e estruturação determinística das fontes utilizadas.

### Decisões de Desenvolvimento - Frente 3: Concierge / Bedrock

### 1. Seleção do Modelo Generativo

Foram comparados **Mistral Large 3**, **Amazon Nova Pro** e **Claude Haiku 4.5** no Amazon Bedrock Playground, utilizando o mesmo contexto, System Prompt e parâmetros.

Os critérios considerados foram **qualidade, grounding, aderência ao `NO_ANSWER`, latência e custo**.

| Modelo | `NO_ANSWER` estrito | Latência média | Custo aprox. dos 3 testes |
|---|---|---:|---:|
| **Mistral Large 3** | **Sim** | **494 ms** | **US$ 0,00109** |
| Amazon Nova Pro | Parcial | 455 ms | ~US$ 0,00163 |
| Claude Haiku 4.5 | Sim | 832 ms | ~US$ 0,00318 |

O **Mistral Large 3** foi escolhido por apresentar o melhor equilíbrio entre qualidade, previsibilidade, baixa latência e custo. A implementação utiliza `mistral.mistral-large-3-675b-instruct`, na região `us-east-1`, através da API Converse do Amazon Bedrock Runtime.

> **![Configuração da comparação](../../src/03_concierge/evidencias/Config_Testes_Modelos.png)**

*Figura 1 - Configuração dos modelos para comparação.*

> **![Teste 1 - Playground](../../src/03_concierge/evidencias/Teste2.png)**

*Figura 2 - Comparação dos modelos avaliados para a Frente 3 (Teste 1).*

> **![Teste 2 - Playground](../../src/03_concierge/evidencias/Teste5.png)**

*Figura 3 - Comparação dos modelos avaliados para a Frente 3 (Teste 2).*

> **![Teste 3 - Playground](../../src/03_concierge/evidencias/Teste7.png)**

*Figura 4 - Comparação dos modelos avaliados para a Frente 3 (Teste 3).*

### 2. Calibração do Threshold

O threshold foi calibrado utilizando o Golden Set do projeto. Foram considerados **26 casos `ANSWER` e 5 `NO_ANSWER`**. Os casos `ESCALATE` foram excluídos porque pertencem à decisão da Frente 4.

O maior score observado entre os casos `NO_ANSWER` foi **0.285791**, enquanto o menor `ANSWER` recuperável acima da região de sobreposição foi **0.338926**.

Com `ABSTENTION_THRESHOLD = 0.30`:

- **25/26** casos `ANSWER` foram liberados;
- **5/5** casos `NO_ANSWER` foram bloqueados;
- o acerto global foi de aproximadamente **96,8%**.

O único `ANSWER` bloqueado foi `dados_cadastrais`, caso em que a fonte esperada não apareceu no Top 3 do retrieval. Por isso, a Frente 3 não implementou workaround e manteve o comportamento seguro de `NO_ANSWER`.

> **![Calibração do Threshold 0.30](../../src/03_concierge/evidencias/Calibracao_Threshold.png)**

*Figura 5 - Validação local do threshold 0,30 com valores de referência obtidos na calibração do Golden Set.*

### 3. Implementação da Frente 3

A implementação foi dividida em quatro módulos:

- `confidence.py`: valida os chunks, verifica vigência e compara o maior score com o threshold;
- `prompts.py`: constrói o contexto e aplica grounding, restringindo a resposta às evidências recuperadas;
- `bedrock_client.py`: integra o Mistral Large 3 ao Amazon Bedrock Runtime via Boto3 e Converse API;
- `answer.py`: orquestra confiança, prompt e geração, retornando `ANSWER` ou `NO_ANSWER`.

Quando o maior score fica abaixo de `0.30`, ocorre **early exit** e o Mistral não é chamado. Quando o score é suficiente, o modelo recebe somente os chunks recuperados e pode retornar uma resposta grounded ou `NO_ANSWER`.

As fontes não são geradas pelo LLM. Elas são construídas diretamente a partir dos chunks, preservando `document`, `chunk_id`, `score` e `status`.

### 4. Testes e Validação Real

Os testes automatizados cobrem threshold, grounding, payload do Bedrock, early exit, fontes determinísticas e propagação de erros técnicos.

Ao final:

- **128 testes da Frente 3 foram aprovados**;
- junto às regressões locais seguras da Frente 2, foram obtidos **133 testes aprovados e 0 falhas**.

> **![Testes automatizados aprovados](../../src/03_concierge/evidencias/Testes_Automatizados.png)**

*Figura 6 - Resultado consolidado dos testes automatizados.*

Também foi realizado um smoke test real com o Mistral Large 3 no Amazon Bedrock. O modelo respondeu corretamente **`8 GB`** para o Conecta Básico e retornou exatamente **`NO_ANSWER`** para uma pergunta sem evidência.

> **![Smoke test real Mistral](../../src/03_concierge/evidencias/Teste_Smoke_Test_Mistral_Large_3.png)**

*Figura 7 - Smoke test real do Mistral Large 3 via Bedrock Converse.*

### 5. Integração Frente 2 → Frente 3

Foi realizado um teste ponta a ponta utilizando o retrieval real da Frente 2 e a geração da Frente 3.

Foram validados três cenários:

1. **eSIM — `ANSWER`**  
   A pergunta "Como ativo um eSIM?" recuperou `procedimento_troca_chip_esim.md` como Rank 1, com score **0.746229**, e gerou resposta correta.

2. **Fora do corpus — `NO_ANSWER`**  
   A pergunta "Qual será a previsão do tempo amanhã?" obteve score máximo **0.128005**, abaixo do threshold. O resultado foi `NO_ANSWER`, com `sources = []` e **Mistral chamado: False**.

3. **Vigência — Política de Reembolso**  
   A pergunta "Qual é o prazo para pedir reembolso?" recuperou somente `politica_reembolso_v2.md`, todos os chunks estavam `vigente`, a versão V1 não apareceu e a resposta correta foi **90 dias corridos**.

> **![eSIM / ANSWER](../../src/03_concierge/evidencias/Teste1_Integration_Test_Front2_Front3.png)**

> **![NO_ANSWER / Mistral chamado False](../../src/03_concierge/evidencias/Teste2_Integration_Test_Front2_Front3.png)**

> **![Vigência / Reembolso](../../src/03_concierge/evidencias/Teste3_Integration_Test_Front2_Front3.png)**

*Figuras 8 a 10 - Validação da integração real entre Frente 2 e Frente 3.*

### 6. Síntese e Decisão de Design

A Frente 3 foi projetada para combinar **confiança determinística, grounding e rastreabilidade**.

A principal decisão de segurança foi utilizar o threshold `0.30` para impedir geração quando a evidência é insuficiente. Isso reduz risco de alucinação, custo e latência.

O Mistral Large 3 foi selecionado pelo equilíbrio entre qualidade, aderência ao `NO_ANSWER`, desempenho e custo. As fontes permanecem determinísticas e derivadas dos chunks recuperados.

As responsabilidades de `ESCALATE`, `trace_id`, handoff e auditoria permanecem fora da Frente 3 e serão tratadas na integração com as Frentes 4 e 5.

---

Aqui está o documento contendo exclusivamente a documentação da sua parte (**Vinicius Goulart / Frente 4: Triagem e Escalonamento**), já integrado com as suas decisões de design, a checagem do contrato de handoff, os detalhes da sumarização semântica via Bedrock, as instruções de teste/execução local e a política de IAM especificada.

---

### Vinicius Nunes de Andrade

* **Papel:** Frente 4 (Triagem, Escalonamento e IAM)
* **Responsabilidades:** Implementação do classificador determinístico de triagem baseado nos 8 critérios obrigatórios da Política de Suporte e Escalonamento, desenvolvimento do mecanismo de sumarização semântica do caso via LLM (Amazon Bedrock), geração do payload padronizado de *handoff* para atendimento humano e especificação das políticas de segurança IAM de menor privilégio para a infraestrutura.

---

## Decisões de Design — Frente 4: Triagem e Escalonamento

### 1. Classificação Determinística e Regras Mandatórias

O módulo de triagem (`src/04_triage/01_classifier.py`) foi projetado para atuar como o primeiro *guardrail* determinístico do pipeline de atendimento. Em vez de delegar a decisão de escalonamento exclusivamente ao modelo generativo, a triagem avalia a entrada do cliente por meio de expressões regulares robustas e regras de negócio explícitas, garantindo 100% de aderência às diretrizes organizacionais.

Os 8 critérios mandatórios definidos na **Política de Suporte e Escalonamento** são mapeados da seguinte forma:

1. **Suspeita de Fraude:** Detecção de padrões associados a roubo de linha, clonagem, uso indevido de conta ou golpes relatados.
2. **Contestação de Fatura Alto Valor (>= R$ 500,00):** Captura de valores monetários na mensagem do cliente e validação antifraude quando o montante é igual ou superior ao limite estabelecido.
3. **Contestação de Multa de Fidelidade:** Identificação de disputas sobre multas em fluxos de cancelamento de contrato.
4. **Alteração de Titularidade (ex.: Falecimento):** Trata processos que exigem documentação física/legal específica.
5. **Reclamação Externa ou Ação Judicial:** Detecção de menções a órgãos reguladores (Anatel, Procon) ou termos jurídicos.
6. **Relato de Conduta Abusiva / Assédio:** Identificação de comportamentos inadequados por parte de colaboradores ou terceiros.
7. **Problema Técnico com Visita Presencial:** Encaminhamento imediato para casos de infraestrutura de rede, instalação de fibra ou reparos que exigem visita física.
8. **Ausência de Fonte Suficiente na Base (Abstenção):** Quando o retriever do RAG indica um score de confiança abaixo do limiar calibrado (`ABSTENTION_THRESHOLD = 0.30`), acionando o transbordo sem inferência de respostas falsas.

---

### 2. Sumarização Semântica do Caso via LLM

Para evitar que o atendimento humano receba relatos confusos ou muito extensos, foi descartada a abordagem de fatiamento extrativo de texto em favor de uma **sumarização semântica via LLM** (`summarize_case`).

* **Invocação Direta via Bedrock Runtime:** O assistente invoca o **Mistral Large 3** via Amazon Bedrock Runtime para sintetizar o problema principal, produtos citados e valores mencionados em uma frase objetiva de no máximo 200 caracteres.
* **Uso Integrado do Histórico (`conversation_history`):** O prompt envia o histórico completo das mensagens trocadas anteriormente entre cliente e assistente virtual. Isso garante que o resumo gerado capture todo o contexto da sessão, e não apenas a última frase isolada.
* **Fallback Seguro:** Em caso de indisponibilidade momentânea ou exceção técnica na chamada do Bedrock, o sistema realiza um *fallback* direto e seguro para o texto do relato original do cliente (respeitando o limite de caracteres `max_len`), garantindo que o pipeline nunca quebre a geração do *payload*.

---

### 3. Estruturação do Payload de Handoff e Conformidade de Contrato

A construção do registro de escalonamento (`src/04_triage/02_handoff.py`) gera uma estrutura JSON padronizada com **10 campos obrigatórios**, assegurando o cumprimento estrito do **Critério de Qualidade do Handoff** (permitir a continuidade do atendimento pelo atendente humano sem que o cliente precise repetir dados).

| Campo | Implementação / Origem dos Dados | Status |
| --- | --- | --- |
| `protocolo_atendimento` | Gerado automaticamente no formato `PROT-YYYYMMDDHHMMSS-XXXX`. | ✅ Conformidade total |
| `data_hora_abertura` | Data e hora exatas da criação do escalonamento em padrão ISO 8601 (UTC). | ✅ Conformidade total |
| `canal_origem` | Extraído do contexto da sessão (`chat`, `telefone`, `app`, `loja`) via `normalize_canal`. | ✅ Conformidade total |
| `categoria_motivo` | Chave exata correspondente a um dos 8 critérios mandatórios acionados. | ✅ Conformidade total |
| `resumo_caso` | Síntese objetiva gerada semanticamente pelo Mistral Large 3 no Amazon Bedrock. | ✅ Conformidade total |
| `historico_ja_levantado` | Registro textual estruturado contendo todas as interações e confirmações prévias da conversa. | ✅ Conformidade total |
| `produto_servico_envolvido` | Mapeamento contextual automático do serviço afetado (`telefonia_movel`, `banda_larga_fibra`, etc.). | ✅ Conformidade total |
| `documento_fonte_consultado` | Documento recuperado do RAG (mesmo quando insuficiente) ou marcação formal de ausência de consulta. | ✅ Conformidade total |
| `urgencia` | Mapeamento de prioridade de atendimento (`HIGH`, `MEDIUM`, `LOW`) de acordo com a regra ativada. | ✅ Conformidade total |
| `dados_contato_retorno` | Meio de contato validado do cliente repassado durante a autenticação/sessão. | ✅ Conformidade total |

---

### 4. Política de Segurança IAM (Menor Privilégio)

Embora a validação e execução dos testes da entrega tenham sido realizadas em ambiente de desenvolvimento local, foi desenhada a política de **IAM (Identity and Access Management)** de menor privilégio para ser aplicada à Role de execução da AWS Lambda em uma eventual implantação de produção para o cliente.

Esta política visa limitar estritamente o raio de acesso do assistente na conta AWS do cliente, impedindo a navegação não autorizada em outros recursos e controlando custos operacionais:

* **CloudWatch Logs:** Permite apenas a criação e gravação de logs de auditoria e métricas de execução (`logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`).
* **Amazon S3 (Somente Leitura):** Restringe o acesso do assistente a operações exclusivas de leitura (`s3:GetObject`, `s3:ListBucket`) restritas ao bucket específico de artefatos do RAG (`conectatel-squad1-2026-525530758961-us-east-1-an`).
* **Amazon Bedrock:** Concede a permissão estritamente necessária para invocação do modelo generativo (`bedrock:InvokeModel`).

#### JSON da Política IAM:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Sid": "S3ReadOnlyArtifacts",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::conectatel-squad1-2026",
        "arn:aws:s3:::conectatel-squad1-2026/*"
      ]
    },
    {
      "Sid": "BedrockInvokeModel",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": "*"
    }
  ]
}

```

---

### Kleidson Matos da Rocha

- **Papel:** Frente 5 (Integração, Auditoria e Qualidade)
- **Responsabilidades:** Integração do fluxo real entre RAG e Concierge, contrato de interação, rastreabilidade por `trace_id`, auditoria local e compartilhada no S3, validações de qualidade, testes ponta a ponta e disponibilização controlada da demonstração em AWS.

### Decisões de Design — Parte 5: Integração, Auditoria e Qualidade

### 1. Contrato de interação e guardrails

Foi definido um contrato único para toda interação do fluxo real, aplicado antes da persistência em auditoria. O contrato estabelece três decisões possíveis:

- **`ANSWER`:** exige resposta acompanhada de ao menos uma citação com `status = vigente`;
- **`NO_ANSWER`:** não pode conter citação, evitando evidência irrelevante para perguntas fora do corpus;
- **`ESCALATE`:** exige handoff completo, contendo motivo, resumo, ação solicitada e prioridade.

Essa validação garante que a resposta exibida ao usuário permaneça coerente com as fontes recuperadas e que casos sensíveis sejam encaminhados com contexto acionável.

### 2. Rastreabilidade e auditoria

Cada execução recebe um `trace_id` único e registra timestamp, duração, pergunta, decisão, resposta, citações, handoff, guardrail, score de recuperação e versões dos componentes. A auditoria é gravada localmente em JSONL e pode ser compartilhada no Amazon S3, usando um objeto por interação.

Também foram criados consulta por `trace_id` e relatório de qualidade. O relatório consolida volume por decisão, latência mínima/média/p95, validade do contrato, respostas com citações vigentes e escalonamentos com handoff completo.

### 3. Integração ponta a ponta

O mock foi mantido apenas como fixture offline para testes. O caminho principal utiliza o RAG e o Concierge reais, portanto a mesma regra documental de vigência e o mesmo modelo de decisão são usados na demonstração e na execução de linha de comando.

Foram validados três cenários de ponta a ponta: uma pergunta coberta pelo corpus retorna `ANSWER` com fontes vigentes; uma pergunta fora do domínio retorna `NO_ANSWER` sem fontes; e uma suspeita de fraude retorna `ESCALATE` com prioridade alta e handoff completo.

### 4. Demonstração interna em AWS

Para tornar a solução demonstrável sem expor credenciais de desenvolvimento, foi implantada uma arquitetura serverless composta por API Gateway HTTP, AWS Lambda em imagem de contêiner, IAM de menor privilégio, Amazon Bedrock, S3, CloudWatch Logs e Parameter Store. A Lambda obtém o vector store oficial do S3 e usa sua própria IAM Role; as credenciais do arquivo `.env` não são enviadas para a nuvem.

O parâmetro `/conectatel/demo/enabled` funciona como interruptor operacional. Quando está desativado, a API responde como indisponível e não dispara chamadas ao Bedrock. Isso permite manter a infraestrutura pronta para a banca, mas controlar o consumo e a exposição fora da apresentação.

### 5. Interface de demonstração

Foi desenvolvida uma interface estática hospedável no AWS Amplify. Ela apresenta conversa contínua, criação de novas conversas, histórico persistido no navegador, métricas locais da sessão, decisões, latência, citações expansíveis, guardrails, handoff e `trace_id`.

As métricas da interface são explicitamente locais à sessão do navegador; as métricas consolidadas de operação continuam sendo produzidas pelo relatório de qualidade baseado na auditoria. A hospedagem pode usar integração Git ou deploy manual por `.zip`, protegida por senha para uso interno.
