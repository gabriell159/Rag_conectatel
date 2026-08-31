# TODO — ConectaTel

Pendências organizadas por frente. Itens concluídos anteriormente não são
repetidos aqui; cada alteração deve ser acompanhada de teste e atualização da
documentação correspondente.

## Frente 01 — Pipeline de tratamento

- [ ] Ampliar testes de limpeza, deduplicação, normalização, nulos e outliers.
- [ ] Validar o contrato dos artefatos com exemplos de entrada e saída.
- [ ] Registrar estatísticas da execução (linhas lidas, removidas e produzidas).
- [ ] Tornar o pipeline idempotente e documentar como reproduzir uma execução.
- [ ] Validar nomes, quantidade e hash dos arquivos publicados no S3.
- [ ] Corrigir e padronizar a codificação UTF-8 dos relatórios gerados.

## Frente 02 — RAG

- [ ] Garantir que o índice consumido seja sempre o produzido pelo build oficial.
- [ ] Manter `vectorstore_backup` apenas como fallback explícito e auditado.
- [ ] Automatizar a verificação dos caminhos publicados e consumidos no S3.
- [ ] Registrar no manifest modelo de embedding, dimensão, chunks e hashes.
- [ ] Definir política de versionamento e evitar consumo acidental de índices antigos.
- [ ] Medir cobertura, latência e qualidade do retrieval em conjunto representativo.
- [ ] Testar comportamento quando S3, embeddings ou arquivos locais estão indisponíveis.

## Frente 03 — Concierge

- [ ] Investigar e corrigir os casos falhos do golden set após a última expansão.
- [ ] Melhorar recuperação de perguntas com score baixo e variações de linguagem.
- [ ] Recalibrar o threshold de abstention com métricas e regressão automatizada.
- [ ] Garantir que respostas sejam sustentadas pelas citações retornadas.
- [ ] Diferenciar dúvida informativa, contestação e solicitação de atendimento humano.
- [ ] Ampliar o golden set com erros de digitação, perguntas ambíguas e paráfrases.
- [ ] Medir separadamente decisão, fonte, versão, latência e taxa de abstention.
- [ ] Documentar formatos de saída e exemplos reais de `ANSWER`, `NO_ANSWER` e `ESCALATE`.

## Frente 05 — Integração, auditoria e qualidade

- [x] Executar o contrato de interação em todas as respostas do fluxo real.
- [x] Adicionar testes ponta a ponta entre RAG, Concierge, contrato e auditoria.
- [x] Garantir citações vigentes em `ANSWER` e ausência de citações em `NO_ANSWER`.
- [x] Garantir handoff completo, acionável e rastreável em todo `ESCALATE`.
- [x] Definir persistência compartilhada opcional em S3 além do JSONL local.
- [x] Documentar esquema de auditoria, ciclo de vida do `trace_id` e consultas.
- [x] Gerar relatório final com qualidade, latência, falhas conhecidas e riscos.
- [x] Manter o mock somente como fixture offline, sem divergência do fluxo real.

## Qualidade e entrega

- [ ] Executar o README do zero em uma máquina limpa e registrar o resultado.
- [ ] Corrigir qualquer problema de codificação nos documentos versionados.
- [ ] Atualizar README e documentos das frentes após cada mudança de fluxo.
- [ ] Executar testes unitários, integração e golden set antes de cada release.
- [ ] Conferir que `.env`, credenciais e artefatos temporários não entram no commit.
- [ ] Registrar em cada avaliação a data, versão dos componentes e arquivos usados.
