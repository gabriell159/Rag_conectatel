---
doc_family_id: pol-suporte-escalonamento
version_ordinal: 1
effective_from: 2026-01-01
effective_to:
status: vigente
---

# Política de Suporte e Escalonamento

Esta política define quais situações o assistente virtual (Concierge ConectaTel) **não deve tentar resolver sozinho** e os campos mínimos que qualquer registro de escalonamento precisa conter para permitir a continuidade do atendimento por um humano.

## Casos de escalonamento obrigatório

O assistente deve encaminhar o atendimento a um humano, sem tentar concluir a solução sozinho, quando o caso se enquadrar em qualquer uma das situações abaixo:

1. **Suspeita de fraude** — uso indevido de linha, conta ou dados do cliente, ou tentativa de golpe relatada pelo cliente.
2. **Contestação de valor de fatura igual ou superior a R$ 500,00** — conforme regra de verificação antifraude da Política de Reembolso e Contestação de Fatura vigente.
3. **Contestação de multa de fidelidade** em processo de cancelamento.
4. **Titularidade da linha em caso de falecimento do titular** ou qualquer alteração de titularidade que exija documentação adicional.
5. **Reclamação já registrada em órgão externo** (ex.: Anatel, Procon) ou menção a possível ação judicial contra a ConectaTel.
6. **Relato de assédio, discriminação ou conduta abusiva** por parte de atendente, técnico ou terceiro.
7. **Problema técnico que exige visita presencial** de um técnico (instalação de internet fixa, reparo de infraestrutura de rede).
8. **Pergunta sem fonte suficiente na base de conhecimento vigente** — quando o assistente não encontra informação para responder com segurança, ele deve reconhecer a limitação ("não sei") e, se o cliente insistir ou o tema parecer sensível, oferecer o encaminhamento a um humano em vez de inferir uma resposta.

Fora dessas situações, o assistente deve tentar resolver o atendimento diretamente com base no corpus documental vigente.

## Campos mínimos do registro de escalonamento

Todo escalonamento gerado pelo assistente deve conter, no mínimo, os seguintes campos, de forma que o atendente humano consiga continuar o atendimento sem pedir ao cliente para repetir informações já fornecidas:

| Campo | Descrição |
|---|---|
| `protocolo_atendimento` | Identificador único do atendimento (gerado automaticamente). |
| `data_hora_abertura` | Data e hora em que o escalonamento foi criado. |
| `canal_origem` | Canal em que o atendimento começou (chat, telefone, app, loja). |
| `categoria_motivo` | Qual dos 8 critérios de escalonamento acima foi acionado. |
| `resumo_caso` | Resumo objetivo do que o cliente relatou, em linguagem natural. |
| `historico_ja_levantado` | O que o assistente já perguntou e confirmou com o cliente antes de escalonar (para evitar repetição). |
| `produto_servico_envolvido` | Plano, linha ou serviço relacionado ao caso. |
| `documento_fonte_consultado` | Documento do corpus consultado pelo assistente, mesmo quando insuficiente para responder. |
| `urgencia` | Classificação de urgência (baixa, média, alta), conforme o critério acionado. |
| `dados_contato_retorno` | Meio de contato preferido do cliente para retorno do atendimento humano. |

## Critério de qualidade do handoff

Um escalonamento é considerado bem-sucedido quando o atendente humano, ao abrir o registro, consegue dar continuidade ao atendimento **sem pedir ao cliente para repetir** nenhuma informação que já havia sido fornecida ao assistente virtual.
