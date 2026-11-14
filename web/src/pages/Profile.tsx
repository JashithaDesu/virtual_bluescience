import { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../lib/auth';
import { fetchClaims, fetchPrivate } from '../lib/data';
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

function ClaimRow({ c, rejected }: { c: ProfileClaim; rejected: boolean }) {
  const badge = TYPE_BADGE[c.type];
  return (
    <li className={`rounded-md border border-gray-200 bg-white p-3 ${rejected ? 'opacity-60' : ''}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded px-2 py-0.5 text-xs font-medium ${badge.cls}`}>{badge.label}</span>
        {c.type !== 'missing' && <span className="text-xs text-gray-500">confidence: {c.confidence}</span>}
        {c.verified && <span className="text-xs text-green-700">✓ verified</span>}
        {c.origin === 'user' && <span className="text-xs text-purple-700">added by you</span>}
        {rejected && <span className="text-xs text-red-700">rejected</span>}
      </div>

      {c.type === 'missing' ? (
        <p className="mt-1 text-sm italic text-gray-500">Nothing found on public pages.</p>
      ) : (
        <p className={`mt-1 text-sm ${rejected ? 'line-through' : ''}`}>{c.value}</p>
      )}

      {c.type === 'stated' && (
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

export default function Profile() {
  const { company } = useAuth();
  const [claims, setClaims] = useState<ProfileClaim[]>([]);
  const [rejectedIds, setRejectedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
      })
      .catch((e: Error) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [company]);

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
          <p className="mb-4 text-sm text-gray-600">
            {counts.stated} facts · {counts.inferred} guesses · {counts.missing} missing
          </p>
          <div className="space-y-6">
            {grouped.map(([field, items]) => (
              <section key={field}>
                <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-gray-700">{FIELD_LABELS[field]}</h2>
                <ul className="space-y-2">
                  {items.map((c) => <ClaimRow key={c.id} c={c} rejected={rejectedIds.has(c.id)} />)}
                </ul>
              </section>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
