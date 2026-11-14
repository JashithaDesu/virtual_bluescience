# Match publication verification

Branch: p2-atomic

## Change
The shared replace_matches helper validates a nonempty batch, bulk-upserts
on (company_id, opportunity_id), then deletes only stale opportunities for
that company. P2 publication delegates to this shared helper.

An upsert failure cannot trigger cleanup. Empty or malformed batches are
rejected before database access. Other companies' matches are preserved.

## Verification
- Four offline tests passed: successful replacement, upsert failure,
  cleanup failure, and invalid batches.
- Ten live OHT reranks completed successfully.
- 265 sampled database reads: zero empty reads, zero read errors.
- Minimum observed OHT feed size: 10 rows.
- Backend rerank durations: 14.297–21.078 seconds.
- verify_demo passed for all three companies.
- OHT baseline Verification rank: #4.
- Simulated testing-priority preview: Verification #3.
- Ranking weights unchanged.

Raw measurements: atomic_publication.json.

## Limits
This uses two database requests, not a single transaction.
It requires one publisher per company. During cleanup failure, old and new
rows can coexist until a later successful publication.
Sampling does not prove transactional isolation or capture every instant.
Browser empty-state observation has not been confirmed.
Backend durations exclude watcher detection and UI refresh latency.
