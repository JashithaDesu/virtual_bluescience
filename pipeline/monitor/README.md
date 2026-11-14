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
