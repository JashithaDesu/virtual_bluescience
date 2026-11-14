import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import type { Session as SbSession } from '@supabase/supabase-js';
import { supabase, USE_MOCK } from './supabase';
import { mockUsers } from './mock';
import { fetchCompany, fetchMembership } from './data';
import type { Company, Membership } from './types';

export interface AppSession { email: string; userId: string; accessToken: string }

interface AuthCtx {
  loading: boolean;
  session: AppSession | null;
  membership: Membership | null;
  company: Company | null;
  error: string | null;
  signIn: (email: string, password: string) => Promise<string | null>; // returns error message or null
  signOut: () => Promise<void>;
}

const Ctx = createContext<AuthCtx | null>(null);
const MOCK_KEY = 'vsp_mock_email';

const toSession = (s: SbSession | null): AppSession | null =>
  s ? { email: s.user.email ?? '', userId: s.user.id, accessToken: s.access_token } : null;

const mockSession = (email: string): AppSession =>
  ({ email, userId: mockUsers[email].user_id, accessToken: 'mock-token' });

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AppSession | null>(null);
  const [sessionLoading, setSessionLoading] = useState(true);
  const [membership, setMembership] = useState<Membership | null>(null);
  const [company, setCompany] = useState<Company | null>(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 1) Track the auth session
  useEffect(() => {
    if (USE_MOCK || !supabase) {
      let stored: string | null = null;
      try { stored = sessionStorage.getItem(MOCK_KEY); } catch { /* storage unavailable */ }
      if (stored && mockUsers[stored]) setSession(mockSession(stored));
      setSessionLoading(false);
      return;
    }
    supabase.auth.getSession().then(({ data }) => {
      setSession(toSession(data.session));
      setSessionLoading(false);
    });
    // Do not call other supabase functions inside this callback (supabase-js can deadlock); effect 2 does that.
    const { data: sub } = supabase.auth.onAuthStateChange((_event, s) => setSession(toSession(s)));
    return () => sub.subscription.unsubscribe();
  }, []);

  // 2) When the user changes, load membership + company
  const userId = session?.userId ?? null;
  useEffect(() => {
    if (!userId) {
      setMembership(null); setCompany(null); setError(null); setProfileLoading(false);
      return;
    }
    let cancelled = false;
    setProfileLoading(true);
    setError(null);
    (async () => {
      try {
        const m = await fetchMembership(userId);
        if (cancelled) return;
        if (!m) {
          setMembership(null); setCompany(null);
          setError('Signed in, but no memberships row is visible for this user. Ask P3: is the user seeded in memberships, and is there an RLS SELECT policy on memberships with user_id = auth.uid()?');
          return;
        }
        setMembership(m);
        const c = m.company_id ? await fetchCompany(m.company_id) : null;
        if (cancelled) return;
        if (m.company_id && !c) setError(`Membership points to company "${m.company_id}" but that row is not readable in companies.`);
        setCompany(c);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setProfileLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [userId]);

  async function signIn(email: string, password: string): Promise<string | null> {
    const e = email.trim().toLowerCase();
    if (USE_MOCK || !supabase) {
      if (!mockUsers[e]) return `Unknown mock user. Use one of: ${Object.keys(mockUsers).join(', ')}`;
      try { sessionStorage.setItem(MOCK_KEY, e); } catch { /* ignore */ }
      setSession(mockSession(e));
      return null;
    }
    const { error } = await supabase.auth.signInWithPassword({ email: e, password });
    return error ? error.message : null;
  }

  async function signOut() {
    if (USE_MOCK || !supabase) {
      try { sessionStorage.removeItem(MOCK_KEY); } catch { /* ignore */ }
    } else {
      await supabase.auth.signOut();
    }
    setSession(null);
  }

  return (
    <Ctx.Provider value={{ loading: sessionLoading || profileLoading, session, membership, company, error, signIn, signOut }}>
      {children}
    </Ctx.Provider>
  );
}

export function useAuth(): AuthCtx {
  const v = useContext(Ctx);
  if (!v) throw new Error('useAuth must be used inside <AuthProvider>');
  return v;
}
