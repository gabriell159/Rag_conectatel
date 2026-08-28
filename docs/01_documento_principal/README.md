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
* **Papel:** Frente 1 (Pipeline de Dados e Análise)
* **Responsabilidades:** Ingestão local de logs de chamados via Pandas, tratamento de dados (limpeza e estruturação), análise exploratória gerando insights acionáveis para o design do assistente e integração de armazenamento na nuvem via AWS S3.

### Decisões de Design — Parte 1: Pipeline de Dados e Análise

### 1. Decisões de Tratamento e Limpeza
Durante a ingestão do arquivo `log_chamados_sintetico.csv`, foram identificadas diversas inconsistências típicas de logs operacionais. O pipeline de tratamento (`src/01_pipeline_tratamento/01_tratamento.py`) realizou as seguintes padronizações:
* **Desduplicação:** Remoção de linhas exatamente iguais.
* **Padronização Textual e Booleana:** Uniformização de categorias, canais e estados (ex: mapeamento para siglas UF em maiúsculas) e conversão de múltiplos formatos de resposta ("Sim", "S", "1") para booleanos nativos (`True`/`False`).
* **Tratamento de Valores Nulos (NaN) e Outliers:** 
  * Para a coluna `data_abertura`, optamos por não excluir as linhas com datas ausentes (`NaN`). A exclusão reduziria o tamanho da amostra e causaria perda de informações valiosas sobre o comportamento das categorias e taxas de escalonamento. Esses registros serão ignorados apenas em eventuais agregações estritamente temporais.
  * Para as colunas `duracao_minutos` e `satisfacao_1_a_5`, foram encontradas algumas inconsistências nos valores. Por exemplo, a coluna de `duracao_minutos` recebeu um tratamento para valores considerados ruidosos, onde minutagens <= 0 ou > 180 são consideradas como valores nulos, decidimos **não aplicar técnicas de imputação (como preenchimento pela média)**. A ausência de resposta em uma pesquisa de satisfação (CSAT) é um comportamento orgânico do usuário. Preencher esses vazios com a média distorceria a métrica real, inflaria a base de respondentes e reduziria a variância natural do conjunto, o que prejudicaria análises estatísticas mais profundas. Agregações futuras lidarão com esses nulos omitindo-os nativamente via Pandas.

### 2. Análises Descritivas
Executamos agregações para entender o comportamento dos chamados. Os três principais *insights* foram:
1. **Volume de Chamados por Categoria:** Foi possível notar que existe um certo nível de equilibrio relacionado a quantidade de chamados, onde a categoria 'Portabilidade' representa o maior volume da operação (16.25%) e a categoria 'Cobertura' apresenta o menor número de chamados (11.25%).
2. **Taxa de Resolução no 1º Contato (FCR):** As categorias 'Cobertura' e 'Tecnico' apresentam grande dificuldade de contenção, com apenas 50% e 58.14% dos casos resolvidos no primeiro contato, respectivamente.
3. **Escalonamento por Canal:** Foi possível observar um padrão próximo a 30% de necessidade de intervenção humana nos atendimentos. O canal de 'Loja Fisica' (29.17%) foi o que apresentou maior necessidade de atendimento humano.

> **Nota Analítica sobre a "Loja Física":** Identificamos uma anomalia nos dados, no canal 'Loja Fisica', a taxa de `encaminhado_humano` é de apenas 29.17%. Em um ambiente presencial convencional, é esperado um valor próximo a 100%. Decidimos **não alterar esse dado sintético no CSV**, pois essa inconsistência pode refletir falhas operacionais de registro no log ou a forte presença de totens de autoatendimento nas lojas. Optamos por preservar o dado bruto para expor o comportamento real da fonte, direcionando a nossa decisão de design para o gargalo técnico.

### 3. Síntese e Decisão de Design do Assistente
**Síntese dos Dados:**
A análise revela que, embora 'Portabilidade' e 'Fatura' tenham alto volume de chamados, elas possuem boas taxas de resolução (em torno de 70%). O verdadeiro gargalo operacional e de atrito com o cliente reside nas categorias técnicas ('Cobertura' e 'Tecnico'), que falham em ser resolvidas de primeira em quase metade das vezes.

**Decisão de Design do Concierge:**
Com base nessa análise, a decisão de design estrutural para o assistente será a implementação de um **guardrail de triagem técnica estrita (fast-track)**. Como os dados provam que problemas de 'Cobertura' e 'Tecnico' têm baixíssima resolução inicial, o agente será configurado para não tentar resolver esse tipo de problema (pois levaria muito tempo, e provavelmente com possiveis afirmaçoes erradas). Ao identificar a intenção de falha de rede ou técnica, o assistente apenas dirá que não sabe responder.
