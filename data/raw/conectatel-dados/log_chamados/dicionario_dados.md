# Dicionário de dados — Log de chamados sintético

Arquivo: `log_chamados_sintetico.csv` (324 linhas, separador vírgula, codificação UTF-8)

Este log representa o histórico de atendimentos da ConectaTel ao longo de um período de aproximadamente três meses. Os dados são sintéticos e foram gerados para simular um log operacional real, incluindo inconsistências típicas desse tipo de fonte (valores ausentes, variações de grafia, duplicidades e outliers). Faz parte do escopo da Parte 1 do desafio identificar e tratar essas inconsistências antes de qualquer análise.

| Campo | Tipo | Descrição |
|---|---|---|
| `chamado_id` | texto | Identificador do chamado. Podem existir linhas duplicadas com o mesmo `chamado_id`. |
| `data_abertura` | data (AAAA-MM-DD) | Data de abertura do chamado. Pode estar ausente em algumas linhas. |
| `canal` | texto | Canal de atendimento (chat, telefone, app, loja física). Grafia não padronizada entre linhas. |
| `categoria` | texto | Categoria do chamado (Fatura, Plano, Cobertura, Técnico, Cancelamento, Portabilidade, Outros). Grafia não padronizada entre linhas. |
| `subcategoria` | texto | Detalhamento do motivo do chamado dentro da categoria. |
| `estado` | texto | Unidade federativa do cliente. Grafia não padronizada (sigla, nome por extenso, maiúsculas/minúsculas). |
| `cidade` | texto | Cidade do cliente. |
| `duracao_minutos` | numérico | Duração do atendimento em minutos. Pode conter valores ausentes ou fora de faixa plausível. |
| `resolvido_primeiro_contato` | texto (booleano) | Indica se o chamado foi resolvido no primeiro contato. Valores não padronizados: "Sim"/"sim"/"S"/"1" e "Não"/"não"/"N"/"0". |
| `encaminhado_humano` | texto (booleano) | Indica se o chamado foi encaminhado para atendimento humano. Mesma variação de formato do campo anterior. |
| `satisfacao_1_a_5` | numérico (1 a 5) | Nota de satisfação informada pelo cliente ao final do atendimento. Pode estar ausente. |
| `plano_atual` | texto | Plano contratado pelo cliente no momento do chamado (Conecta Básico, Conecta Plus, Conecta Família ou "N/A" quando não identificado). |
| `resumo_atendimento` | texto | Descrição curta do motivo do contato. |

## Observações para a Parte 1 (Pipeline de dados)

- O arquivo contém linhas duplicadas (mesmo `chamado_id` e mesmo conteúdo) — parte do exercício de limpeza é identificá-las e decidir como tratá-las.
- Os campos de texto booleano (`resolvido_primeiro_contato`, `encaminhado_humano`) e as colunas categóricas (`canal`, `categoria`, `estado`) não seguem uma grafia única — normalizar antes de agregar.
- `duracao_minutos` contém alguns valores implausíveis (zero, negativo ou muito acima do padrão) que merecem tratamento explícito e documentado.
- Este log é a fonte de dados da Parte 1 apenas. Ele não deve ser usado como fonte de resposta do assistente Concierge — essa função é do corpus documental (pasta `corpus/`).
