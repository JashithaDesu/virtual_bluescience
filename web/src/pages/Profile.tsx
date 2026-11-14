import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { useAuth } from '../lib/auth';
import { addUserClaim, fetchClaims, fetchPrivate, savePriorities, setClaimRejected } from '../lib/data';
import type { ClaimField, ClaimType, ProfileClaim } from '../lib/types';

const FIELD_LABELS: Record<ClaimField, string> = {
  offering: 'Offering', technology: 'Technology', expertise: 'Expertise',
  application_area: 'Application areas', market: 'Market', customer_group: 'Customer groups',
  geography: 'Geography', priority: 'Priorities', collaboration: 'Collaborations',
  domain: 'Domains', relevant_topic: 'Relevant topics', size: 'Size',
  founded: 'Founded', location: 'Location',
};
const FIELD_ORDER = Object.keys(FIELD_LABELS) as ClaimField[];

const TYPE_BADGE: Record<ClaimType, { label: string; cls: string }> = {
  stated: { label: 'Fact', cls: 'bg-green-100 text-green-800' },
  inferred: { label: 'Guess', cls: 'bg-blue-100 text-blue-800' },
  missing: { label: 'Missing', cls: 'bg-gray-200 text-gray-700' },
};

const fmtDate = (d: string | null) => (d ? new Date(d).toLocaleDateString('en-GB') : null);

interface RowProps {
  c: ProfileClaim; rejected: boolean; busy: boolean;
  onToggleReject: (c: ProfileClaim) => void;
  onAdd: (c: ProfileClaim, value: string) => Promise<boolean>;
}

function AddValue({ c, busy, onAdd }: Pick<RowProps, 'c' | 'busy' | 'onAdd'>) {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState('');
  if (!open) {
    return (
      <button onClick={() => setOpen(true)} className="mt-2 rounded-md border border-gray-300 px-2 py-0.5 text-xs hover:bg-gray-100">
        + Add
      </button>
    );
  }
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!value.trim()) return;
    if (await onAdd(c, value)) { setValue(''); setOpen(false); }
  }
  return (
    <form onSubmit={submit} className="mt-2 flex gap-2">
      <input autoFocus value={value} onChange={(e) => setValue(e.target.value)}
             placeholder="Type the correct information"
             className="flex-1 rounded-md border border-gray-300 px-2 py-1 text-sm" />
      <button type="submit" disabled={busy || !value.trim()}
              className="rounded-md bg-gray-900 px-3 py-1 text-xs font-medium text-white disabled:opacity-50">Save</button>
      <button type="button" onClick={() => setOpen(false)} className="text-xs text-gray-500">Cancel</button>
    </form>
  );
}

function ClaimRow({ c, rejected, busy, onToggleReject, onAdd }: RowProps) {
  const badge = TYPE_BADGE[c.type];
  return (
    <li className={`rounded-md border border-gray-200 bg-white p-3 ${rejected ? 'opacity-60' : ''}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded px-2 py-0.5 text-xs font-medium ${badge.cls}`}>{badge.label}</span>
        {c.type !== 'missing' && <span className="text-xs text-gray-500">confidence: {c.confidence}</span>}
        {c.verified && <span className="text-xs text-green-700">✓ verified</span>}
        {c.origin === 'user' && <span className="text-xs text-purple-700">added by you</span>}
        {rejected && <span className="text-xs text-red-700">rejected</span>}
        {c.type !== 'missing' && c.origin === 'agent' && (
          <button onClick={() => onToggleReject(c)} disabled={busy}
                  className="ml-auto rounded-md border border-gray-300 px-2 py-0.5 text-xs hover:bg-gray-100 disabled:opacity-50">
            {rejected ? 'Undo' : 'Not correct'}
          </button>
        )}
      </div>

      {c.type === 'missing' ? (
        <>
          <p className="mt-1 text-sm italic text-gray-500">Nothing found on public pages.</p>
          <AddValue c={c} busy={busy} onAdd={onAdd} />
        </>
      ) : (
        <p className={`mt-1 text-sm ${rejected ? 'line-through' : ''}`}>{c.value}</p>
      )}

      {c.origin === 'user' && (
        <p className="mt-2 text-xs text-gray-600">Added by your company · {fmtDate(c.created_at)} · not yet verified by staff</p>
      )}

      {c.type === 'stated' && c.origin === 'agent' && (
        <div className="mt-2 border-l-2 border-gray-300 pl-3 text-xs text-gray-600">
          {c.quote && <p className="italic">“{c.quote}”</p>}
          {c.source_url && (
            <a href={c.source_url} target="_blank" rel="noreferrer" className="break-all text-blue-700 underline">
              {c.source_url}
            </a>
          )}
          {c.retrieved_at && <span> · retrieved {fmtDate(c.retrieved_at)}</span>}
        </div>
      )}

      {c.type === 'inferred' && (
        <p className="mt-2 text-xs text-gray-600">
          {c.source_url ? (
            <>Inferred from{' '}
              <a href={c.source_url} target="_blank" rel="noreferrer" className="break-all text-blue-700 underline">{c.source_url}</a>
            </>
          ) : (
            <>Inferred from the whole profile · {fmtDate(c.created_at)}</>
          )}
        </p>
      )}
    </li>
  );
}

function Priorities({ items, busy, onSave }: { items: string[]; busy: boolean; onSave: (next: string[]) => void }) {
  const [draft, setDraft] = useState('');
  function add(e: FormEvent) {
    e.preventDefault();
    const v = draft.trim();
    if (!v || items.includes(v)) return;
    onSave([...items, v]);
    setDraft('');
  }
  return (
    <section className="mb-8 rounded-lg border border-gray-200 bg-white p-4">
      <h2 className="mb-1 text-sm font-semibold uppercase tracking-wide text-gray-700">Your priorities</h2>
      <p className="mb-3 text-xs text-gray-500">Private to your company. Used to rank your opportunities.</p>
      <div className="mb-3 flex flex-wrap gap-2">
        {items.length === 0 && <span className="text-sm text-gray-500">No priorities yet.</span>}
        {items.map((p) => (
          <span key={p} className="flex items-center gap-1 rounded-full bg-gray-100 px-3 py-1 text-sm">
            {p}
            <button onClick={() => onSave(items.filter((x) => x !== p))} disabled={busy}
                    aria-label={`Remove ${p}`} className="text-gray-500 hover:text-red-700">×</button>
          </span>
        ))}
      </div>
      <form onSubmit={add} className="flex gap-2">
        <input value={draft} onChange={(e) => setDraft(e.target.value)}
               placeholder="e.g. find a test site for offshore pilots"
               className="flex-1 rounded-md border border-gray-300 px-2 py-1 text-sm" />
        <button type="submit" disabled={busy || !draft.trim()}
                className="rounded-md bg-gray-900 px-3 py-1 text-xs font-medium text-white disabled:opacity-50">Add</button>
      </form>
    </section>
  );
}

export default function Profile() {
  const { company } = useAuth();
  const [claims, setClaims] = useState<ProfileClaim[]>([]);
  const [rejectedIds, setRejectedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [priorities, setPriorities] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    if (!company) return;
    let alive = true;
    setLoading(true);
    setError(null);
    Promise.all([fetchClaims(company.id), fetchPrivate(company.id)])
      .then(([cl, priv]) => {
        if (!alive) return;
        setClaims(cl);
        setRejectedIds(new Set(priv?.rejected_claim_ids ?? []));
        setPriorities(priv?.priorities ?? []);
      })
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [company]);

  async function run<T>(fn: () => Promise<T>): Promise<T | undefined> {
    setBusy(true);
    setSaveError(null);
    try {
      return await fn();
    } catch (e) {
      setSaveError((e as Error).message);
      return undefined;
    } finally {
      setBusy(false);
    }
  }

  async function toggleReject(c: ProfileClaim) {
    if (!company) return;
    const next = await run(() => setClaimRejected(company.id, c.id, !rejectedIds.has(c.id)));
    if (next) setRejectedIds(new Set(next));
  }

  async function addValue(c: ProfileClaim, value: string): Promise<boolean> {
    if (!company) return false;
    const created = await run(() => addUserClaim(company.id, c.field, value));
    if (!created) return false;
    setClaims((cl) => [...cl, created]);
    return true;
  }

  async function updatePriorities(next: string[]) {
    if (!company) return;
    const prev = priorities;
    setPriorities(next);
    const ok = await run(async () => { await savePriorities(company.id, next); return true; });
    if (!ok) setPriorities(prev);
  }

  const grouped = useMemo(() => {
    const g = new Map<ClaimField, ProfileClaim[]>();
    for (const c of claims) g.set(c.field, [...(g.get(c.field) ?? []), c]);
    return FIELD_ORDER.filter((f) => g.has(f)).map((f) => [f, g.get(f)!] as const);
  }, [claims]);

  const counts = useMemo(() => ({
    stated: claims.filter((c) => c.type === 'stated').length,
    inferred: claims.filter((c) => c.type === 'inferred').length,
    missing: claims.filter((c) => c.type === 'missing').length,
  }), [claims]);

  if (!company) return <p className="text-gray-500">No company linked to this account.</p>;

  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold">Company profile</h1>
      <p className="mb-1 text-gray-600">
        {company.name}
        {company.website && (
          <> · <a href={company.website} target="_blank" rel="noreferrer" className="text-blue-700 underline">{company.website}</a></>
        )}
      </p>
      <p className="mb-6 text-sm text-gray-500">
        Built automatically from public pages. Facts have a quote and a source; guesses are the agent's interpretation.
      </p>

      {loading && <p className="text-gray-500">Loading profile…</p>}
      {error && <p className="rounded-md bg-red-50 p-3 text-sm text-red-700">Could not load profile: {error}</p>}

      {!loading && !error && claims.length === 0 && (
        <p className="text-gray-500">No profile yet for this company.</p>
      )}

      {!loading && !error && claims.length > 0 && (
        <>
          <Priorities items={priorities} busy={busy} onSave={updatePriorities} />
          {saveError && (
            <p className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">Could not save: {saveError}</p>
          )}
          <p className="mb-4 text-sm text-gray-600">
            {counts.stated} facts · {counts.inferred} guesses · {counts.missing} missing
          </p>
          <div className="space-y-6">
            {grouped.map(([field, items]) => (
              <section key={field}>
                <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-gray-700">{FIELD_LABELS[field]}</h2>
                <ul className="space-y-2">
                  {items.map((c) => (
                    <ClaimRow key={c.id} c={c} rejected={rejectedIds.has(c.id)} busy={busy}
                              onToggleReject={toggleReject} onAdd={addValue} />
                  ))}
                </ul>
              </section>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
