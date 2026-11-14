import { useState, type FormEvent } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { useAuth } from '../lib/auth';
import { USE_MOCK } from '../lib/supabase';
import { mockUsers } from '../lib/mock';

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
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-6">
      <div className="w-full max-w-sm rounded-lg border border-gray-200 bg-white p-6">
        <h1 className="mb-1 text-xl font-bold">Virtual Science Park</h1>
        <p className="mb-6 text-sm text-gray-500">Sign in to see your company profile and opportunities.</p>
        <form onSubmit={onSubmit} className="space-y-3">
          <label className="block text-sm">
            Email
            <input
              type="email" value={email} autoComplete="username"
              onChange={(e) => { setEmail(e.target.value); setError(null); }}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2"
            />
          </label>
          <label className="block text-sm">
            Password
            <input
              type="password" value={password} autoComplete="current-password"
              onChange={(e) => { setPassword(e.target.value); setError(null); }}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2"
            />
          </label>
          <button
            type="submit" disabled={busy}
            className="w-full rounded-md bg-gray-900 px-3 py-2 text-sm font-medium text-white hover:bg-gray-700 disabled:opacity-50"
          >
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </form>
        {USE_MOCK && (
          <div className="mt-6 border-t border-gray-200 pt-4">
            <p className="mb-2 text-xs text-amber-800">Mock mode — any password works</p>
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
  );
}
