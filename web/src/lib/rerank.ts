// In-memory state for this browser tab, shared between pages, so the Opportunities page can
// show rank movement and an "updating" banner after an edit made on the Profile page.
// UI only: nothing here is written to the database.
import { fetchFeed } from './data';

export interface Move { from: number | null; at: number } // from = null: new in the list

const pending = new Map<string, number>();                       // companyId -> time of last edit
export const lastRanks = new Map<string, Record<string, number>>(); // companyId -> opportunityId -> rank
export const moves = new Map<string, Record<string, Move>>();      // companyId -> opportunityId -> move

/** Call after a profile edit is saved. Snapshots the current ranks if the feed has not been seen yet,
 *  so the Opportunities page can still show arrows when the re-rank lands. */
export async function markRerankPending(companyId: string): Promise<void> {
  pending.set(companyId, Date.now());
  if (lastRanks.has(companyId)) return;
  try {
    const feed = await fetchFeed(companyId);
    const snap: Record<string, number> = {};
    for (const it of feed) if (it.opportunity && it.rank != null) snap[it.opportunity.id] = it.rank;
    if (!lastRanks.has(companyId)) lastRanks.set(companyId, snap);
  } catch {
    /* the feed page will take its own first snapshot */
  }
}

export const rerankPendingSince = (companyId: string): number | null => pending.get(companyId) ?? null;
export const clearRerankPending = (companyId: string): void => { pending.delete(companyId); };