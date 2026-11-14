import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '../lib/auth';
import { fetchFeed } from '../lib/data';
import { clearRerankPending, lastRanks, moves, rerankPendingSince, type Move } from '../lib/rerank';
import type { FeedItem, OpportunityType } from '../lib/types';

const TYPE_BADGE: Record<OpportunityType, { label: string; cls: string }> = {
  funding: { label: 'Funding', cls: 'bg-amber-100 text-amber-900' },
  event: { label: 'Event', cls: 'bg-blue-100 text-blue-800' },
  testbed: { label: 'Testbed', cls: 'bg-teal-100 text-teal-800' },
  support: { label: 'Support', cls: 'bg-purple-100 text-purple-800' },
};
const FORMAT_LABEL = { online: 'Online', in_person: 'In person' } as const;
const STRIPE: Record<string, string> = { funding: 'border-l-amber-400', event: 'border-l-blue-400', testbed: 'border-l-brand-500', support: 'border-l-purple-400' };
const cleanReason = (r: string) => r.replace(/\s*\[claim [0-9a-f-]+\]/gi, '').replace(/\s{2,}/g, ' ').trim();
const REFRESH_MS = 3_000;
const MOVE_SHOW_MS = 60_000;     // rank arrows stay visible this long
const PENDING_MAX_MS = 60_000;   // give up waiting for a re-rank after this long
const RESULT_SHOW_MS = 10_000;   // "updated" / "no change" message stays this long

type Banner = { kind: 'updating' | 'updated' | 'nochange'; at: number } | null;

const fmtDate = (d: string | null) => {
  if (!d) return null;
  const t = new Date(d);
  return isNaN(t.getTime()) ? d : t.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
};

function MoveBadge({ move, rank }: { move: Move; rank: number | null }) {
  if (move.from === null) {
    return <span className="rounded bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-800">{'\u2605'} new in your list</span>;
  }
  if (rank == null || move.from === rank) return null;
  return move.from > rank ? (
    <span className="rounded bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-800">{'\u2191'} moved up from #{move.from}</span>
  ) : (
    <span className="rounded bg-gray-200 px-2 py-0.5 text-xs font-semibold text-gray-700">{'\u2193'} from #{move.from}</span>
  );
}

function Card({ item, move }: { item: FeedItem; move?: Move }) {
  const o = item.opportunity;
  if (!o) return null;
  const badge = TYPE_BADGE[o.type] ?? { label: o.type, cls: 'bg-gray-200 text-gray-700' };
  const when = fmtDate(o.date_or_deadline);
  return (
    <li className={`rounded-lg border border-l-4 bg-white p-4 ${STRIPE[o.type] ?? 'border-l-gray-300'} ${move ? 'border-green-400 ring-2 ring-green-200' : 'border-gray-200'}`}>
      <div className="mb-2 flex flex-wrap items-center gap-2">
        {item.rank != null && <span className="text-sm font-bold text-gray-500">#{item.rank}</span>}
        {move && <MoveBadge move={move} rank={item.rank} />}
        <span className={`rounded px-2 py-0.5 text-xs font-medium ${badge.cls}`}>{badge.label}</span>
        {o.type === 'funding' && (
          <span className="rounded border border-amber-300 px-2 py-0.5 text-xs text-amber-900">Potential match</span>
        )}
        {o.is_simulated && (
          <span className="rounded bg-gray-800 px-2 py-0.5 text-xs font-medium text-white">SIMULATED</span>
        )}
        {when && <span className="text-xs text-gray-600">{o.type === 'funding' ? 'Deadline' : 'Date'}: {when}</span>}
        {o.format && <span className="text-xs text-gray-600">{'\u00b7'} {FORMAT_LABEL[o.format]}</span>}
      </div>

      <h2 className="font-semibold">{o.title}</h2>
      {o.audience && <p className="text-xs text-gray-500">For: {o.audience}</p>}

      {item.reason && (
        <div className="mt-3 rounded-md bg-gray-50 p-3 text-sm">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-600">Why this matches</p>
          <p>{cleanReason(item.reason)}</p>
        </div>
      )}

      {o.type === 'funding' && o.eligibility_note && (
        <p className="mt-2 text-xs text-gray-600">Eligibility: {o.eligibility_note} (check the call before applying)</p>
      )}

      <p className="mt-3 text-sm"><span className="font-medium">Next step:</span> {o.next_step}</p>

      <a href={o.url} target="_blank" rel="noreferrer" className="mt-2 inline-block break-all text-sm text-blue-700 underline">
        {o.source ? `Source: ${o.source}` : o.url}
      </a>
    </li>
  );
}

function BannerBox({ banner }: { banner: Banner }) {
  if (!banner) return null;
  if (banner.kind === 'updating') {
    return (
      <div className="mb-4 flex items-center gap-3 rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900">
        <span className="inline-block h-3 w-3 animate-pulse rounded-full bg-blue-500" />
        Updating your recommendations... Your profile change is being re-ranked (about 20 seconds).
      </div>
    );
  }
  if (banner.kind === 'updated') {
    return <div className="mb-4 rounded-md border border-green-300 bg-green-50 p-3 text-sm text-green-900">{'\u2713'} Recommendations updated from your profile change.</div>;
  }
  return <div className="mb-4 rounded-md border border-gray-200 bg-gray-50 p-3 text-sm text-gray-700">No change in ranking from your last edit.</div>;
}

export default function Feed() {
  const { company } = useAuth();
  const [items, setItems] = useState<FeedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);
  const [banner, setBanner] = useState<Banner>(null);
  const [activeMoves, setActiveMoves] = useState<Record<string, Move>>({});

  const load = useCallback(async () => {
    if (!company) return;
    try {
      const data = await fetchFeed(company.id);
      const now = Date.now();

      // Compare with the ranks seen last time (kept across page switches in this tab).
      const prev = lastRanks.get(company.id);
      // P2 replaces a company's matches by delete + insert; a poll can land in between and see
      // an empty list. Treat that as transient: keep the current view and wait for the next poll.
      if (prev && Object.keys(prev).length > 0 && data.length === 0) return;
      const mv: Record<string, Move> = { ...(moves.get(company.id) ?? {}) };
      const cur: Record<string, number> = {};
      let changed = false;
      for (const it of data) {
        const id = it.opportunity?.id;
        if (!id || it.rank == null) continue;
        cur[id] = it.rank;
        if (!prev) continue; // first load: no arrows
        const old = prev[id];
        if (old === undefined) { mv[id] = { from: null, at: now }; changed = true; }
        else if (old !== it.rank) { mv[id] = { from: old, at: now }; changed = true; }
      }
      for (const id of Object.keys(mv)) if (now - mv[id].at > MOVE_SHOW_MS || !(id in cur)) delete mv[id];
      moves.set(company.id, mv);
      lastRanks.set(company.id, cur);

      // "Updating" banner after a profile edit.
      const since = rerankPendingSince(company.id);
      if (since !== null) {
        if (changed) { clearRerankPending(company.id); setBanner({ kind: 'updated', at: now }); }
        else if (now - since > PENDING_MAX_MS) { clearRerankPending(company.id); setBanner({ kind: 'nochange', at: now }); }
        else setBanner({ kind: 'updating', at: since });
      } else {
        setBanner((b) => (b && b.kind !== 'updating' && now - b.at > RESULT_SHOW_MS ? null : b));
      }

      setActiveMoves(mv);
      setItems(data);
      setError(null);
      setUpdatedAt(new Date());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [company]);

  useEffect(() => {
    setLoading(true);
    load();
    const t = setInterval(load, REFRESH_MS);
    return () => clearInterval(t);
  }, [load]);

  if (!company) return <p className="text-gray-500">No company linked to this account.</p>;

  return (
    <div>
      <div className="mb-1 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold">Opportunities</h1>
        <button
          onClick={() => { setLoading(true); load(); }}
          className="ml-auto rounded-md border border-gray-300 px-3 py-1 text-sm hover:bg-gray-100"
        >
          Refresh
        </button>
      </div>
      <p className="mb-6 text-sm text-gray-500">
        Matched to {company.name}'s profile {'\u00b7'} updates every 3 s
        {updatedAt && ` \u00b7 last checked ${updatedAt.toLocaleTimeString('en-GB')}`}
      </p>

      <BannerBox banner={banner} />
      {loading && items.length === 0 && <p className="text-gray-500">Loading opportunities...</p>}
      {error && <p className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">Could not load opportunities: {error}</p>}
      {!loading && !error && items.length === 0 && <p className="text-gray-500">No matches yet for this company.</p>}

      <ul className="space-y-4">
        {items.map((it, i) => (
          <Card key={it.opportunity?.id ?? i} item={it} move={it.opportunity ? activeMoves[it.opportunity.id] : undefined} />
        ))}
      </ul>
    </div>
  );
}