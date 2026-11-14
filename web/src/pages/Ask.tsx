import { useState, type FormEvent } from 'react';
import { useAuth } from '../lib/auth';
import { ask } from '../lib/data';
import { ASK_URL, USE_MOCK } from '../lib/supabase';
import type { AskResponse } from '../lib/types';

const STAFF_URL = 'https://www.bluesciencepark.se/kontakt/kontaktpersoner/';

interface Turn { question: string; res?: AskResponse; error?: string }

function Answer({ res, simulated }: { res: AskResponse; simulated: boolean }) {
  const neutral = res.route === 'refused' || res.route === 'unrelated' || res.route === 'unclear';
  const box =
    res.route === 'in_scope' ? 'border-gray-200 bg-white'
    : res.route === 'refer_to_staff' ? 'border-amber-300 bg-amber-50'
    : neutral ? 'border-gray-200 bg-gray-50 text-gray-700'
    : 'border-blue-200 bg-blue-50'; // unclear
  return (
    <div className={`rounded-lg border p-3 text-sm ${box}`}>
      {simulated && <span className="mb-2 inline-block rounded bg-gray-800 px-2 py-0.5 text-xs font-medium text-white">SIMULATED - mock answer</span>}
<p className="whitespace-pre-wrap">{res.answer}</p>
      {res.route === 'refer_to_staff' && (
        <a href={STAFF_URL} target="_blank" rel="noreferrer"
           className="mt-2 inline-block rounded-md bg-gray-900 px-3 py-1 text-xs font-medium text-white hover:bg-gray-700">
          Contact Blue Science Park staff
        </a>
      )}
      {res.sources.length > 0 && (
        <div className="mt-3 border-t border-gray-200 pt-2">
          <p className="mb-1 text-xs font-semibold text-gray-600">Sources</p>
          <ul className="space-y-1 text-xs">
            {res.sources.map((s, i) => (
              <li key={i}>
                <a href={s.url} target="_blank" rel="noreferrer" className="break-all text-blue-700 underline">{s.title || s.url}</a>
                {s.date && <span className="text-gray-500"> · {s.date}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function Ask() {
  const { session, company } = useAuth();
  const [question, setQuestion] = useState('');
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);
  const mockAnswers = USE_MOCK;
  const askMissing = !USE_MOCK && !ASK_URL;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q || busy || !session) return;
    setQuestion('');
    setBusy(true);
    setTurns((t) => [...t, { question: q }]);
    let turn: Turn;
    try {
      turn = { question: q, res: await ask(q, session.accessToken) };
    } catch (err) {
      turn = { question: q, error: (err as Error).message };
    }
    setTurns((t) => [...t.slice(0, -1), turn]);
    setBusy(false);
  }

  return (
    <div>
      <h1 className="mb-1 text-2xl font-bold">Ask</h1>
      <p className="mb-4 text-sm text-gray-500">
        Questions about {company?.name ?? 'your company'}'s opportunities and Blue Science Park's offers.
      </p>
      {mockAnswers && (
        <p className="mb-4 rounded-md bg-amber-50 p-2 text-xs text-amber-900">
          Mock mode: answers below are simulated and marked as such.
        </p>
      )}

      {askMissing && <p className="mb-4 rounded-md bg-red-50 p-2 text-xs text-red-700">The Ask service is not connected (VITE_ASK_URL is empty). Questions will not be answered.</p>}
<div className="mb-4 space-y-4">
        {turns.map((t, i) => (
          <div key={i} className="space-y-2">
            <p className="ml-auto max-w-[80%] rounded-lg bg-gray-900 px-3 py-2 text-sm text-white w-fit">{t.question}</p>
            {t.res && <Answer res={t.res} simulated={mockAnswers} />}
            {t.error && <p className="rounded-md bg-red-50 p-3 text-sm text-red-700">Could not get an answer: {t.error}</p>}
            {!t.res && !t.error && <p className="text-sm text-gray-500">Thinking…</p>}
          </div>
        ))}
      </div>

      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          value={question} onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. Which funding fits our wave energy work?"
          className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        <button type="submit" disabled={busy || !question.trim()}
                className="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700 disabled:opacity-50">
          Ask
        </button>
      </form>
    </div>
  );
}
