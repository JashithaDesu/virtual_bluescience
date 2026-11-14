# Virtual Science Park (BUILD Hackathon 2026, Blue Science Park challenge)

AI agents that build a **verified profile** of each Blue Science Park member company from public
information, and match it to **funding, events, testbeds and support** with an explanation of *why*.
Each company sees only its own data; BSP staff see the network view.

## What it does
1. **Profiles companies from public sources:** the BSP member page, the company website and BSP news.
   Every fact keeps its quote, source URL and retrieval date, and is either *stated*, *inferred* or *missing*.
2. **Verifies the facts:** each quote is fuzzy-matched against its source (>= 90), facts are cross-checked
   across sources, and each gets a corroboration score (CONFIRMED / PLAUSIBLE / STALE).
3. **Matches opportunities:** ranks funding calls, BSP events and test/support offers per company,
   with reasons that cite the profile facts they are based on.
4. **Reacts to the member:** when a member corrects a fact or adds a priority, the ranking updates
   automatically (about 20 s).
5. **Answers questions:** the Ask assistant answers questions about the member's own profile and matches only,
   with a guard against prompt injection, cross-company requests and eligibility guarantees.

## The agents
| Agent | Owner | What it does |
|---|---|---|
| Profiler | P1 | Two-pass LLM extraction (facts, then topics) + quote validator, dedupe, caps |
| Gap-filling agent | P1 | Observe gaps -> search BSP news -> decide -> fetch -> re-profile -> diff (logged) |
| Refresh / change detection | P1 | Hash-based change detection; re-profiles only what changed |
| Corroboration | P1 | Scores each fact by agreement, source quality, recency and conflicts |
| Connector | P1 | Suggests members with similar profiles (staff view, files only) |
| Monitor + Match & Explain | P2 | Opportunity ingestion, embedding ranking, reasons, watcher re-rank |
| Ask agent + guard | P3 | FastAPI `/ask` using the member's own login token (RLS enforced) |
| Web app | P4 | Profile (reject / add / priorities), Opportunities, Ask, Compare |

## Architecture
```
public pages -> fetch/cache -> Profiler -> Validator -> Corroboration -> Supabase (profile_claims)
                                    ^ Gap agent / Refresh                     |
opportunities -> Monitor -> Match & Explain (watcher re-rank) <---------------+
                                                                              |
web app (React)  <-- Supabase RLS (member sees own company only) -->  /ask (FastAPI, user token)
```
- **Database:** Supabase Postgres + Auth + Row Level Security + pgvector.
- **LLM:** Gemini (`gemini-flash-lite-latest`) via the OpenAI-compatible API, with retry and a disk cache.
- **Embeddings:** `paraphrase-multilingual-MiniLM-L12-v2` (Swedish + English).

## Run the demo locally
```bash
# 1. Python
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, LLM_* (never commit .env)

# 2. Ask API (port 8000)
uvicorn api.main:app --port 8000

# 3. Re-rank watcher
python -m pipeline.monitor.watch

# 4. Web app (port 8080)
cd web && npm install && npm run dev   # web/.env.local: VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY, VITE_ASK_URL
```
Demo accounts: `member-oht@demo.com`, `member-addsecure@demo.com`, `staff@demo.com`
(the password is given to the judges separately).

## Evidence that it works
| Check | Result | Where |
|---|---|---|
| Profile accuracy (hand-checked) | 31/34 = **91%** | `eval/results/QUALITY.md` |
| Every fact traceable to quote + URL + date | yes | `profile_claims` |
| Prompt-injection test (simulated page) | **PASS** | `eval/injection_test.py` |
| Data isolation (RLS, as a member) | **5/5 PASS** | `eval/check_db.py` |
| Ask routes end-to-end | **6/6** | P3's API tests |
| Baseline scale | all 56 BSP members profiled (files) | `pipeline/profiler/out/baseline/` |

## Limitations (honest)
- Only 3 companies are fully loaded into the database; the other 53 are a files-only baseline.
- Opportunities are a curated set (Energimyndigheten, BSP events, BSP test/support), not a live crawl of every funder.
- Eligibility is never confirmed by the assistant; it points to the call's own criteria.
- Data marked **SIMULATED** is used only for demo scenarios (e.g. a simulated website change).
- Facts from news articles 3+ years old are marked STALE / low confidence instead of removed.

## Next steps
- Load all 56 members, schedule a weekly refresh, and add more funders (Vinnova, EU calls).
- Let BSP staff approve connector suggestions before members see them.
- Track matching quality over time (precision@5 per company).

## Tools used
Built by a team of 4 in about 24 hours. We used Claude and Gemini as coding and extraction tools;
architecture, data decisions and all verification (hand-checks, RLS and injection tests) were done by the team.

## Security notes
- The service-role key is used only by the pipelines, never by the web app or `/ask`.
- No LLM key in the web app (`VITE_` variables are public in the browser).
- All keys used during the event are rotated afterwards.
