import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '../lib/auth';
import { fetchFeed } from '../lib/data';
import type { FeedItem, OpportunityType } from '../lib/types';

const TYPE_BADGE: Record<OpportunityType, { label: string; cls: string }> = {
  funding: { label: 'Funding', cls: 'bg-amber-100 text-amber-900' },
  event: { label: 'Event', cls: 'bg-blue-100 text-blue-800' },
  testbed: { label: 'Testbed', cls: 'bg-teal-100 text-teal-800' },
  support: { label: 'Support', cls: 'bg-purple-100 text-purple-800' },
};
const FORMAT_LABEL = { online: 'Online', in_person: 'In person' } as const;
const REFRESH_MS = 3_000;

const fmtDate = (d: string | null) => {
  if (!d) return null;
  const t = new Date(d);
  return isNaN(t.getTime()) ? d : t.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
};

function Card({ item }: { item: FeedItem }) {
  const o = item.opportunity;
  if (!o) return null;
  const badge = TYPE_BADGE[o.type] ?? { label: o.type, cls: 'bg-gray-200 text-gray-700' };
  const when = fmtDate(o.date_or_deadline);
  return (
    <li className="rounded-lg border border-gray-200 bg-white p-4">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className={`rounded px-2 py-0.5 text-xs font-medium ${badge.cls}`}>{badge.label}</span>
        {o.type === 'funding' && (
          <span className="rounded border border-amber-300 px-2 py-0.5 text-xs text-amber-900">Potential match</span>
        )}
        {o.is_simulated && (
          <span className="rounded bg-gray-800 px-2 py-0.5 text-xs font-medium text-white">SIMULATED</span>
        )}
        {when && <span className="text-xs text-gray-600">{o.type === 'funding' ? 'Deadline' : 'Date'}: {when}</span>}
        {o.format && <span className="text-xs text-gray-600">Â· {FORMAT_LABEL[o.format]}</span>}
      </div>

      <h2 className="font-semibold">{o.title}</h2>
      {o.audience && <p className="text-xs text-gray-500">For: {o.audience}</p>}

      {item.reason && (
        <div className="mt-3 rounded-md bg-gray-50 p-3 text-sm">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-600">Why this matches</p>
          <p>{item.reason}</p>
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

export default function Feed() {
  const { company } = useAuth();
  const [items, setItems] = useState<FeedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);

  const load = useCallback(async () => {
    if (!company) return;
    try {
      const data = await fetchFeed(company.id);
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
        Matched to {company.name}'s profile Â· updates every 3 s
        {updatedAt && ` Â· last checked ${updatedAt.toLocaleTimeString('en-GB')}`}
      </p>

      {loading && items.length === 0 && <p className="text-gray-500">Loading opportunitiesâ€¦</p>}
      {error && <p className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">Could not load opportunities: {error}</p>}
      {!loading && !error && items.length === 0 && <p className="text-gray-500">No matches yet for this company.</p>}

      <ul className="space-y-4">
        {items.map((it, i) => <Card key={it.opportunity?.id ?? i} item={it} />)}
      </ul>
    </div>
  );
}
