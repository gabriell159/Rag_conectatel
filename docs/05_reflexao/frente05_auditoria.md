# Frente 05 — Auditoria e qualidade

## Contrato da interação

Cada resposta do fluxo real passa por `validate_interaction` antes de ser
persistida. O contrato exige `trace_id`, timestamp, duração, decisão, resposta,
citações e handoff. Uma resposta `ANSWER` precisa citar pelo menos um chunk de
documento vigente; `NO_ANSWER` não possui citações; `ESCALATE` possui handoff
com `reason`, `summary`, `requested_action` e `priority`.

## Ciclo de vida do `trace_id`

1. `src/03_concierge/05_orchestrator.py` gera um identificador `trc_<uuid>` no
   início da interação.
2. O mesmo identificador acompanha decisão, citações, handoff, duração e
   versões dos componentes.
3. O evento é gravado no JSONL local e, quando `AUDIT_S3_BUCKET` está definido,
   também em `s3://<bucket>/<prefix>/<trace_id>.json`.
4. Use `05_query_trace <trace_id>` para recuperar a interação local.

## Execução e relatórios

```powershell
.\.venv\Scripts\python.exe -m src.05_integracao_auditoria_qualidade.04_run_real "Qual e o prazo para pedir reembolso?"
.\.venv\Scripts\python.exe -m src.05_integracao_auditoria_qualidade.05_query_trace <trace_id>
.\.venv\Scripts\python.exe -m src.05_integracao_auditoria_qualidade.06_quality_report
```

O relatório registra decisões, latência, validade do contrato, cobertura de
citações em `ANSWER` e completude do handoff em `ESCALATE`. O mock permanece
restrito aos testes offline e não é usado pelo executor real.
