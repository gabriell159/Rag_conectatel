# Pacote de dados — Concierge ConectaTel

Este pacote contém todos os dados e documentos fictícios da ConectaTel citados no desafio. Nenhum conteúdo aqui se refere a operadoras reais — tudo foi criado especificamente para este exercício e é a única fonte que a solução de cada squad deve usar para responder dúvidas de assinantes.

## Estrutura

```
conectatel-dados/
├── log_chamados/
│   ├── log_chamados_sintetico.csv     ← fonte da Parte 1 (Pipeline de dados)
│   └── dicionario_dados.md            ← dicionário de campos do CSV
└── corpus/                            ← fonte da Parte 2 (RAG) e Parte 3 (Concierge)
    ├── planos/
    │   ├── plano_conecta_basico.md
    │   ├── plano_conecta_plus.md
    │   └── plano_conecta_familia.md
    ├── politicas/
    │   ├── politica_reembolso_v1.md        ← revogada (intencional)
    │   ├── politica_reembolso_v2.md        ← vigente
    │   ├── politica_cancelamento.md
    │   └── politica_suporte_escalonamento.md  ← base da Parte 4 (Triagem e escalonamento)
    ├── faq/
    │   ├── faq_geral.md
    │   └── faq_cobertura_rede.md
    └── procedimentos/
        ├── procedimento_troca_chip_esim.md
        ├── procedimento_portabilidade.md
        └── procedimento_desbloqueio_aparelho.md
```

## Como usar cada parte

**Parte 1 — Pipeline de dados:** use `log_chamados/log_chamados_sintetico.csv`. O arquivo contém inconsistências propositais (duplicidades, valores ausentes, grafias diferentes para a mesma categoria, outliers de duração) — identificá-las e tratá-las faz parte do exercício. Consulte `dicionario_dados.md` para a descrição de cada campo.

**Parte 2 — Base de conhecimento e RAG:** use os documentos da pasta `corpus/`. Todos seguem o padrão de metadados de vigência descrito no guia de metadados (`doc_family_id`, `version_ordinal`, `effective_from`, `effective_to`, `status`), incluído no cabeçalho de cada arquivo. Preste atenção especial à família `pol-reembolso`, que tem duas versões: `politica_reembolso_v1.md` (revogada) e `politica_reembolso_v2.md` (vigente) — a solução deve responder sempre pela versão vigente.

**Parte 3 — Agente Concierge:** o assistente só pode responder com base nos documentos de `corpus/`. Perguntas fora do que está coberto por esses documentos devem ser respondidas com "não sei", nunca com informação inferida ou externa.

**Parte 4 — Triagem e escalonamento:** os critérios de quando o agente não deve resolver sozinho e os campos mínimos do registro de escalonamento estão definidos em `corpus/politicas/politica_suporte_escalonamento.md`.

## Regra importante

Somente os documentos desta pasta `corpus/` podem ser citados como fonte de resposta do assistente. O uso de qualquer informação externa sobre operadoras reais como fonte de resposta é considerado fora dos critérios de avaliação da dimensão RAG e Agente/escalonamento.
