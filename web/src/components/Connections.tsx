import data from '../data/connections.json';

type Suggestion = {
  partner: string;
  basis_a: string;
  basis_b: string;
  why: string;
  confidence: string;
  similarity: number;
  already_connected?: boolean;
};
type ByCompany = Record<string, { candidates: string[]; suggestions: Suggestion[] }>;

const BY_COMPANY = (data as { by_company: ByCompany }).by_company;

const NAMES: Record<string, string> = {
  nkt: 'NKT', 'njord-x': 'Njord-X', 'lassen-construction': 'Lassen Construction',
  'mj-marcable-consulting-ab': 'MJ Marcable Consulting', techinova: 'Techinova', allbinary: 'AllBinary',
  cleura: 'Cleura', embeddedart: 'EmbeddedArt', energimyndigheten: 'Energimyndigheten', spirius: 'Spirius',
  ericsson: 'Ericsson', nexer: 'Nexer', knowit: 'Knowit', 'dxc-technology': 'DXC Technology',
};
const nice = (slug: string) =>
  NAMES[slug] ?? slug.split('-').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');

const CONF_STYLE: Record<string, string> = {
  high: 'bg-emerald-50 text-emerald-800',
  medium: 'bg-amber-50 text-amber-800',
  low: 'bg-gray-100 text-gray-700',
};

export default function Connections({ companyId, names }: { companyId: string; names: Record<string, string> }) {
  const entry = BY_COMPANY[companyId];
  const self = names[companyId] ?? nice(companyId);
  const readable = (text: string) =>
    Object.entries({ ...names, [companyId]: self }).reduce((t, [id, n]) => t.split(id).join(n), text);

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <h2 className="mb-1 text-lg font-semibold">{self}: possible member connections</h2>
      <p className="mb-3 text-xs text-gray-500">
        Suggested by the Connector agent from public facts on both sides. Possibilities for staff to review, not
        expressed interest.
      </p>
      {!entry || entry.suggestions.length === 0 ? (
        <p className="text-sm text-gray-500">No suggestions for this company yet.</p>
      ) : (
        <ul className="space-y-3">
          {entry.suggestions.map((s) => (
            <li key={s.partner} className="rounded border border-gray-100 p-3">
              <div className="mb-1 flex flex-wrap items-center gap-2 text-xs">
                <span className="text-sm font-medium text-gray-900">{nice(s.partner)}</span>
                <span className={`rounded px-2 py-0.5 ${CONF_STYLE[s.confidence] ?? CONF_STYLE.low}`}>
                  {s.confidence}
                </span>
                <span className="text-gray-500">similarity {s.similarity.toFixed(2)}</span>
                {s.already_connected && (
                  <span className="rounded bg-sky-50 px-2 py-0.5 text-sky-800">already connected (public)</span>
                )}
              </div>
              <p className="text-sm text-gray-700">{readable(s.why)}</p>
              <p className="mt-1 text-xs text-gray-500">
                Basis: {self}: "{s.basis_a}" · {nice(s.partner)}: "{s.basis_b}"
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
