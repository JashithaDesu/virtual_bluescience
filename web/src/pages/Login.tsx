import { useState, type FormEvent } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { useAuth } from '../lib/auth';
import { USE_MOCK } from '../lib/supabase';
import { mockUsers } from '../lib/mock';
import Logo from '../components/Logo';

const POINTS = [
  'A profile built from public pages, every fact with its source',
  'Funding, events and testbeds ranked with a reason why',
  'Private priorities, visible only to your company',
];

export default function Login() {
  const { session, signIn } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (session) return <Navigate to="/" replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!email.trim()) { setError('Enter your email.'); return; }
    if (!USE_MOCK && !password) { setError('Enter your password.'); return; }
    setBusy(true);
    const err = await signIn(email, password);
    setBusy(false);
    if (err) { setError(err); return; }
    navigate('/');
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      <aside className="relative hidden w-[44%] flex-col justify-between overflow-hidden bg-brand-900 p-12 text-white lg:flex">
        <div className="flex items-center gap-3">
          <Logo size={36} />
          <span className="text-lg font-semibold">Virtual Science Park</span>
        </div>
        <div className="relative z-10 max-w-md">
          <h2 className="mb-6 text-3xl font-semibold leading-tight tracking-tight">
            Every member gets a living profile, and the opportunities that fit it.
          </h2>
          <ul className="space-y-3">
            {POINTS.map((p) => (
              <li key={p} className="flex gap-3 text-sm text-white/80">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-500 text-xs">{'\u2713'}</span>
                {p}
              </li>
            ))}
          </ul>
        </div>
        <p className="relative z-10 text-xs text-white/50">BUILD Hackathon 2026 {'\u00b7'} Blue Science Park challenge</p>
        <svg className="absolute -bottom-6 left-0 w-full" viewBox="0 0 600 160" preserveAspectRatio="none" aria-hidden="true">
          <path d="M0 80 C100 40 200 120 300 80 S500 40 600 80 V160 H0Z" fill="#123a52" />
          <path d="M0 110 C100 80 200 150 300 110 S500 80 600 110 V160 H0Z" fill="#1f9aa8" opacity="0.45" />
        </svg>
      </aside>

      <div className="flex flex-1 items-center justify-center p-6">
      <div className="w-full max-w-sm rounded-xl border border-gray-200 bg-white p-8 shadow-card">
        <div className="mb-6 flex items-center gap-3 lg:hidden">
          <Logo />
          <span className="font-semibold">Virtual Science Park</span>
        </div>
        <h1 className="mb-1 text-xl font-semibold tracking-tight text-gray-900">Sign in</h1>
        <p className="mb-6 text-sm text-gray-500">See your company profile and the opportunities matched to it.</p>
        <form onSubmit={onSubmit} className="space-y-3">
          <label className="block text-sm font-medium text-gray-700">
            Email
            <input
              type="email" value={email} autoComplete="username"
              onChange={(e) => { setEmail(e.target.value); setError(null); }}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </label>
          <label className="block text-sm font-medium text-gray-700">
            Password
            <input
              type="password" value={password} autoComplete="current-password"
              onChange={(e) => { setPassword(e.target.value); setError(null); }}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </label>
          <button
            type="submit" disabled={busy}
            className="w-full rounded-md bg-brand-600 px-3 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {busy ? 'Signing in...' : 'Sign in'}
          </button>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </form>
        {USE_MOCK && (
          <div className="mt-6 border-t border-gray-200 pt-4">
            <p className="mb-2 text-xs text-amber-800">Mock mode: any password works</p>
            <div className="flex flex-wrap gap-2">
              {Object.keys(mockUsers).map((u) => (
                <button
                  key={u} type="button" onClick={() => { setEmail(u); setError(null); }}
                  className="rounded border border-gray-300 px-2 py-1 text-xs hover:bg-gray-100"
                >
                  {u}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
    </div>
  );
}