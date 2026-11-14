# P2 demo checklist

## Before the demo — on the actual demo laptop
Open Git Bash in the repository root:

    source .venv/Scripts/activate
    export PYTHONUTF8=1
    unset LLM_API_KEY
    python -m pipeline.monitor.watch --check
    python -m pipeline.monitor.watch

Leave this terminal running. Start exactly ONE watcher.
The default watcher observes future edits; it does not refresh on startup.
Do not run manual reranks concurrently.
Confirm the laptop stays awake and has network access.

In a second terminal, verify the published feeds:

    source .venv/Scripts/activate
    export PYTHONUTF8=1
    python -m pipeline.monitor.verify_demo

## Demonstrated priority edit
Log in as Ocean Harvesting and add:

    Testing and validating our technology with a potential customer is a priority

This is user-entered demo input, not a fact discovered by the profiling agent.
Do not reject the oil-and-gas claim merely to force a ranking change.
Only correct a claim that is genuinely wrong; preview the combined edit
separately if a correction is included.

Validated priority-only preview:
- Before: Concept Development #3; Verification with Customers #4.
- After: Verification with Customers #3; Concept Development #4.
- MTCoS remains #1.
- Funding remains a potential match, not confirmed eligibility.

Watch for the terminal message:
    Published ocean-harvesting; feed can refresh now.

The live watcher test took about 20 seconds per change.
P4's polling adds up to 10 seconds after publication.
These are observed timings, not guarantees.

## Read-only rehearsal
With current database inputs:

    python -m pipeline.monitor.rerank ocean-harvesting --dry-run \
      --simulate-priority "Testing and validating our technology with a potential customer is a priority"

Recheck before presenting: rankings depend on current accepted claims,
existing priorities, opportunities and scoring rules.
Do not add the same priority repeatedly.

## Manual fallback
Stop the watcher with Ctrl+C before running:

    python -m pipeline.monitor.rerank ocean-harvesting

Then refresh the UI.

## Outstanding integration check
Confirm a real UI save updates company_private, the watcher detects it,
and the refreshed feed displays the changed order.
The watcher must be checked and running on the actual demo laptop.
OHT profile claims remain frozen; do not rerun P1 profiling scripts.
