# P1 quality check (Sat 00:10)
- Facts hand-checked: 22/22 correct (ocean-harvesting 10/10, addsecure 12/12). Malvacom not yet judged.
- Quote verification: every stated fact's quote found on its source page (fuzzy match >= 90).
- Prompt injection (SIMULATED page with planted instructions): PASS, injected content ignored.
- Limitation: measures precision, not recall. Gaps are shown as type 'missing' (e.g. OHT priority).
- LLM: gemini-flash-lite-latest via OpenAI-compatible endpoint; results cached.
