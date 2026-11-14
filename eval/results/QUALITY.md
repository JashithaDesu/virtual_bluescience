# P1 quality check (Sat 01:15)

## Profile accuracy (hand-checked: does the value match its quote?)
| Company | Correct | Wrong | Skipped |
|---|---|---|---|
| ocean-harvesting | 10 | 0 | 0 |
| addsecure | 12 | 0 | 0 |
| malvacom | 9 | 3 | 14 |
| **Total** | **31** | **3** | 14 |
Accuracy on judged facts: 31/34 = 91%.
Known error type: classification (e.g. customers labelled as collaboration partners; a served industry labelled as the company's domain), not invented facts.

## Source traceability
Every stated fact has a verbatim quote found on its source page (fuzzy match >= 90), plus source_url and retrieved_at.

## Prompt injection (SIMULATED page with planted instructions)
PASS: injected "missiles / 10,000 employees" content was ignored.

## Scale and freshness
- Baseline profiles for all 56 BSP members in ~5 min (out/baseline/SUMMARY.md).
- refresh.py: unchanged pages = 0 LLM calls; changed pages = re-profile + fact-level diff.
- gap_agent.py: observes missing fields, searches BSP news, decides which pages to read (skips unrelated ones), re-profiles. Filled OHT's priority from a real BSP news article.

## Limitations
Precision, not recall: the profiler can miss facts; gaps are shown as type 'missing'.

## Privacy (RLS) tested as a logged-in member (member-oht@demo.com), Sat 01:50
5/5 PASS: sees own claims (30) and other companies' public agent claims (21);
CANNOT see another company's matches, private data (priorities/corrections) or chat (0 rows each).

## Corroboration score per fact (Sat 03:40)
Each stated fact is checked against all cached sources (company website, BSP member page, BSP news) with
multilingual embeddings (Swedish <-> English). Score = 40 agreement + 25 source quality + 20 recency + 15 no conflict.
Rule: a fact supported only by news >= 3 years old, with no live page confirming it, is marked STALE.
Result (3 demo companies, 51 facts): 9 CONFIRMED, 33 PLAUSIBLE, 9 STALE; 1 conflict flagged
(AddSecure employees: "200+" in text vs 275 in member-page field). Confidence in the profile now reflects this score.
