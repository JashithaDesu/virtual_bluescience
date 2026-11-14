# P2 — Opportunities and matching

## Delivered
- 15 sourced opportunities: 9 funding, 3 event series, 2 testbeds, 1 support.
- English presentation text; original-language evidence in out/evidence.json.
- Fetch cache with retrieved_at and content_hash.
- Local multilingual embeddings, 384 dimensions.
- Company embeddings exclude missing/rejected claims and include user claims
  and private priorities.
- Distinct feeds: Ocean Harvesting leads with MTCoS; AddSecure with Tech
  Concept Lab; Malvacom with digital consultant support.
- Batched, claim-citing explanations; unsupported recommendations omitted.
- Manual per-company reranking.

## Setup
Use Python 3.12. From the repository root in Git Bash:

    export PYTHONUTF8=1
    python -m venv .venv
    source .venv/Scripts/activate
    python -m pip install -r pipeline/monitor/requirements-lock.txt
    git fetch origin
    git checkout origin/p1-profiling -- pipeline/common/

Shared helpers: db.py, llm.py, models.py. P3 owns the database schema.
Configure .env locally; never commit it:

    SUPABASE_URL=<project API URL>
    SUPABASE_SERVICE_ROLE_KEY=<server-side key>
    LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
    LLM_API_KEY=<your own Gemini key>
    LLM_MODEL=gemini-flash-lite-latest
    EMBED_MODEL=paraphrase-multilingual-MiniLM-L12-v2

Service credentials are for pipeline scripts only, never browser code or /ask.
Keep .env, .venv/, .llm_cache/, __pycache__/ and pipeline/monitor/.cache/
excluded from Git. The monitor cache contains PRIVATE matching inputs,
priorities, explanations and backups.

## Sources
- https://www.bluesciencepark.se/event/
- https://www.energimyndigheten.se/utlysningar/
- https://www.bluesciencepark.se/vara-tjanster/test-utveckling/
- https://www.bluesciencepark.se/projekt-erbjudande/

BSP content uses its Elementor page container, excluding cookie UI.
Vinnova was inspected but its JS-driven listing was not used.
Funding detail links are discovered from the official listing.

## Initial build
Requires seeded companies and P1 claims in Supabase:

    python -m pipeline.monitor.fetch
    python -m pipeline.monitor.extract
    python -m pipeline.monitor.embed_opportunities
    python -m pipeline.monitor.upload_opportunities
    python -m pipeline.monitor.embed_companies
    python -m pipeline.monitor.explain
    python -m pipeline.monitor.publish_matches

The publish command refuses stale profile snapshots.

## Demo operation after a profile edit
P4 writes corrections to company_private.rejected_claim_ids and priorities
to company_private.priorities. Then P2 runs:

    python -m pipeline.monitor.rerank ocean-harvesting

Other supported IDs: addsecure, malvacom.
Preview without database writes:

    python -m pipeline.monitor.rerank ocean-harvesting --dry-run

Reload the feed after completion. There is no automatic watcher.
Reranking reads current claims, rejected IDs, priorities and opportunity
records, and updates only the selected company's embedding and matches.
Reasons use one batched LLM call per company on a cache miss.

## Matching
Core offerings, technologies, application areas and expertise establish
topic fit; user claims and priorities are included. Inferred interests
also contribute to the company embedding.
Claims are embedded separately and averaged; private priorities receive
weight 2. Vectors are normalised.

Domain filtering precedes scoring. Specialised buildings, forestry and
biogas opportunities require supporting profile context. A broad energy
tag alone does not establish these application fits.
Specialised testbeds/support require a shared core topic.

Score = 0.65 * cosine + 0.25 * topic fit + 0.10 * practical fit.
Topic fit: 1 for specific overlap, 0.5 for energy-only overlap, otherwise 0.
Practical fit: 1 for a relevant testbed/support offer, otherwise 0.
An explicit positive testing priority adds 0.15 to relevant testbeds.
Scores are ranking heuristics, not probabilities or eligibility assessments.
Keep up to 10 matches; never pad feeds with unsupported recommendations.

## Verification
    python -m pipeline.monitor.check_edit_flow
    python -m pipeline.monitor.verify_demo

The first check SIMULATES a rejected offering and testing priority in
memory. It verifies filtering, embedding changes, testbed score adjustment
and preservation of live private state/matches.
The second verifies live distinct feeds, consecutive ranks, accepted claim
citations, links, retrieval dates, next steps and potential-only funding.

## Limits and handover
- Funding is always a potential match. BSP staff confirm eligibility.
- Undated recurring events/offers have null date_or_deadline.
  Show retrieved_at separately; never present it as the event date.
- Confirm schedules and support availability with BSP.
- 2022–2025 dates on the support page refer to the predecessor project.
- The funding pool is energy-focused; digital coverage comes from BSP offers.
- Relevance filters and priority recognition use English keyword heuristics.
- Exact quote checks verify source presence; extraction still needs review.
- Reranking filters expired items but does not automatically refresh sources.
- Keep the same embedding model for companies and opportunities.
- Match publication uses several REST calls, not a single transaction.
  Avoid concurrent reranks/edits during publication.
- P3 owns RLS/auth; these pipeline checks do not prove frontend privacy.
- P4 still needs to verify a real user correction + manual rerank + feed reload.
- No watcher, cron, alerts, staff dashboard or extra sources are required
  for the Saturday prototype.

## Automatic reranking — added after initial handover
The optional watcher is now implemented and live-tested. This supersedes
the earlier statements that no watcher exists.

Start exactly one watcher from the repository root:

    export PYTHONUTF8=1
    python -m pipeline.monitor.watch

It polls company_private.updated_at every five seconds and runs one
company rerank at a time. Further edits remain pending while a rerank
runs. Failed reranks retry after 30 seconds.
Stop with Ctrl+C. Keep the terminal/laptop running during the demo.

Default startup watches future edits only. To refresh all companies
on startup:

    python -m pipeline.monitor.watch --initial

Connection-only check:

    python -m pipeline.monitor.watch --check

Do not run manual reranks concurrently with the watcher.
P1 profile refreshes do not trigger this watcher; manually rerank those
companies when P1 announces changed profiles.
Publication is not transactional; a feed may briefly see partial updates.

Observed live test:
- Simulated testing-priority edit published after 20.4 seconds.
- Original priorities restored and baseline scoring published after 20.3 seconds.
- OHT profile claims were not modified.
These timings are observations, not latency guarantees. UI polling adds
up to another ten seconds after publication.

Optional reversible live test, while the watcher is already running:

    python -m pipeline.monitor.test_watch

Run the test in a second terminal. Avoid concurrent edits to OHT during it.
The test backs up private state locally and uses a timestamp condition
to avoid overwriting concurrent changes.

## Latest verification and evaluation status
After P1 refreshed AddSecure and Malvacom, both were reranked successfully.
All three feeds passed live verification, with 30 matches at that check.
OHT remained frozen; no P1 profiling scripts were run on it.

The oil-and-gas rejection / EU scale-up priority comparison was simulated:
- Rejection alone: no top-five rank changes.
- Priority alone: Verification moved 4 to 3; Concept Development 3 to 4.
- Combined edits: original top-five order remained; scores changed.
This does not establish that recommended calls are EU funding.

Human precision@5 evaluation was not completed. No precision score is claimed.
Full UI edit-to-feed integration remains pending P4 readiness.

## Final demo refinements
Low-confidence agent-generated priority claims are excluded from matching
and explanation inputs. This prevents OHT's June 2022 testing plan from
being treated as a current priority. Stored profile claims are unchanged;
user-entered priorities remain included.

Read-only priority preview requires --dry-run:

    python -m pipeline.monitor.rerank ocean-harvesting --dry-run \
      --simulate-priority "Testing and validating our technology with a potential customer is a priority"

After excluding the historical priority, the validated preview showed:
- Verification of Innovations with Customers: rank 4 -> 3.
- Concept Development: rank 3 -> 4.
- MTCoS remained first; score changed from approximately 0.680 to 0.840.
These are simulated user preferences, not agent-discovered company facts.
Funding remains a potential match; eligibility is not established.

The corrected OHT baseline was published and all three feeds passed
verification afterward. See DEMO_CHECKLIST.md for laptop startup,
watcher operation, rehearsal and manual fallback.

## LLM failure fallback
Explanation requests make one LLM attempt. On a request/helper exception,
reranking uses deterministic reasons citing accepted claims from the
current company. Inferred interests remain labelled; funding eligibility
remains unconfirmed. Template responses are never written to the LLM cache.
Ranking weights are unchanged.

Verified with LLM_API_KEY=invalid and P2_EXPLAIN_NO_CACHE=1:
- Adding the demo priority published Verification at #3.
- Restoring original priorities published Verification back at #4.
- Reason integrity: 30/30 matches, 49/49 references; zero cross-company refs.
- Live feed verification passed for all three companies.

The invalid key was scoped to test subprocesses; .env was unchanged.
Request timeouts can still delay fallback. Invalid-key testing does not
measure UI latency or reproduce every provider failure.
