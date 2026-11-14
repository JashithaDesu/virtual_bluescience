import { useEffect, useMemo, useState } from 'react';
import { fetchCompany, fetchFeed } from '../lib/data';
import type { FeedItem } from '../lib/types';
import Connections from '../components/Connections';

const DEMO = ['ocean-harvesting', 'addsecure', 'malvacom'];

const cleanReason = (r: string) => r.replace(/\s*\[claim [0-9a-f-]+\]/gi, '').replace(/\s{2,}/g, ' ').trim();

type Column = { items: FeedItem[]; error?: string; loading: boolean };

const TYPE_STYLE: Record<string, string> = {
  funding: 'bg-amber-50 text-amber-800',
  event: 'bg-sky-50 text-sky-800',
  testbed: 'bg-emerald-50 text-emerald-800',
  support: 'bg-violet-50 text-violet-800',
};

export default function Compare() {
  const [left, setLeft] = useState('ocean-harvesting');
  const [right, setRight] = useState('addsecure');
  const [names, setNames] = useState<Record<string, string>>({});
  const [cols, setCols] = useState<Record<string, Column>>({});

  useEffect(() => {
    Promise.all(
      DEMO.map((id) =>
        fetchCompany(id).then((c) => [id, c?.name ?? id] as const).catch(() => [id, id] as const),
      ),
    ).then((pairs) => setNames(Object.fromEntries(pairs)));
  }, []);

  useEffect(() => {
    let alive = true;
    const load = async (id: string): Promise<Column> => {
      try {
        const feed = await fetchFeed(id);
        return { items: feed.slice(0, 5), loading: false };
      } catch (e) {
        return { items: [], loading: false, error: e instanceof Error ? e.message : String(e) };
      }
    };
    const run = () =>
      Promise.all([left, right].map(async (id) => [id, await load(id)] as const)).then((r) => {
        if (alive) setCols(Object.fromEntries(r));
      });
    run();
    const t = setInterval(run, 10000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [left, right]);

  const idsOf = (id: string) => new Set((cols[id]?.items ?? []).map((i) => i.opportunity?.id).filter(Boolean));
  const shared = useMemo(() => {
    const a = idsOf(left);
    const b = idsOf(right);
    return new Set([...a].filter((x) => b.has(x)));
  }, [cols, left, right]);

  const picker = (value: string, set: (v: string) => void, other: string) => (
    <select
      className="rounded border border-gray-300 bg-white px-3 py-2 text-sm"
      value={value}
      onChange={(e) => set(e.target.value)}
    >
      {DEMO.filter((id) => id !== other).map((id) => (
        <option key={id} value={id}>
          {names[id] ?? id}
        </option>
      ))}
    </select>
  );

  const column = (id: string) => {
    const col = cols[id];
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <h2 className="mb-1 text-lg font-semibold">{names[id] ?? id}</h2>
        <p className="mb-3 text-xs text-gray-500">Top 5 recommendations</p>
        {!col && <p className="text-sm text-gray-500">Loading…</p>}
        {col?.error && <p className="text-sm text-red-600">Could not load: {col.error}</p>}
        {col && !col.error && col.items.length === 0 && (
          <p className="text-sm text-gray-500">No recommendations yet.</p>
        )}
        <ol className="space-y-3">
          {col?.items.map((it) => {
            const o = it.opportunity;
            if (!o) return null;
            const isShared = shared.has(o.id);
            return (
              <li key={o.id} className="rounded border border-gray-100 p-3">
                <div className="mb-1 flex flex-wrap items-center gap-2 text-xs">
                  <span className="font-semibold text-gray-700">#{it.rank}</span>
                  <span className={`rounded px-2 py-0.5 ${TYPE_STYLE[o.type] ?? 'bg-gray-100 text-gray-700'}`}>
                    {o.type}
                  </span>
                  {o.type === 'funding' && (
                    <span className="rounded bg-gray-100 px-2 py-0.5 text-gray-700">Potential match</span>
                  )}
                  {o.is_simulated && (
                    <span className="rounded bg-red-50 px-2 py-0.5 text-red-700">SIMULATED</span>
                  )}
                  <span className={isShared ? 'text-gray-500' : 'font-medium text-emerald-700'}>
                    {isShared ? 'in both top 5' : 'only here'}
                  </span>
                </div>
                <a href={o.url} target="_blank" rel="noreferrer" className="font-medium text-blue-700 underline">
                  {o.title}
                </a>
                {it.reason && <p className="mt-1 text-sm text-gray-700">{cleanReason(it.reason)}</p>}
              </li>
            );
          })}
        </ol>
      </div>
    );
  };

  const total = Math.max(cols[left]?.items.length ?? 0, cols[right]?.items.length ?? 0);
  const differing = total - shared.size;

  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold">Compare companies</h1>
      <p className="mb-4 text-sm text-gray-500">
        Staff view. Same opportunities, different companies: the ranking follows each company's profile and
        priorities. Only public recommendations are shown, never a company's private notes or chat.
      </p>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        {picker(left, setLeft, right)}
        <span className="text-gray-400">vs</span>
        {picker(right, setRight, left)}
        {total > 0 && (
          <span className="text-sm text-gray-700">
            {differing} of {total} top recommendations differ
          </span>
        )}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {column(left)}
        {column(right)}
      </div>
      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <Connections companyId={left} names={names} />
        <Connections companyId={right} names={names} />
      </div>
    </div>
  );
}
