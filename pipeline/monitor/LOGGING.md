# Structured watcher logging

The watcher uses Python logging with one JSON rerank_completed record
per finished rerank attempt.

Successful records contain:
- time: UTC timestamp
- company
- duration_ms
- reason: llm or template
- top_5_ids: opportunity IDs in rank order
- status and exit_code

llm includes cached LLM-generated explanations; it does not prove a fresh
provider request. template means deterministic uncached fallback reasons.
No ranking weights are changed.

Duration starts before subprocess launch and includes interpreter/model
startup, embedding, explanations and publication, plus any delay before
the watcher observes completion. It excludes the initial edit-detection
poll and browser refresh.

Failed attempts use reason=unknown when no valid completion report exists.
Their records include error type and a local diagnostic-file path, not
exception contents, prompts, priorities or claim values.
Successful diagnostic files and temporary reports are removed.
Failed diagnostics remain under ignored pipeline/monitor/.cache/ for
local troubleshooting; do not publish that directory.

The rerank subprocess writes its completion report only after publication
and verification. It does not add columns to the matches table.

## Verification
    python eval/test_structured_logging.py
    python eval/check_logging_live.py
    python -m pipeline.monitor.verify_demo
    python eval/check_reasons.py

Four offline tests passed.
Actual subprocess publication passed in template and LLM modes, with
identical top-five IDs and OHT Verification at #4.
Observed durations: template 17016 ms; LLM mode 10312 ms.
These are backend observations, not UI timing guarantees.
Reason integrity afterward: 30/30 matches, 46/46 valid references.
Raw live measurements: eval/results/structured_logging.json.

Do not run the live check alongside another matching watcher or UI edits.
The invalid test key is scoped to the child environment; .env is unchanged.
