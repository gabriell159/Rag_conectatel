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
