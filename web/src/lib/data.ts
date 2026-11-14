// The ONLY place that talks to Supabase. Pages call these functions, never supabase directly.
// Every function has a mock branch so the UI works before the database is ready.
import { supabase, USE_MOCK } from './supabase';
import { mockClaims, mockCompanies, mockMatches, mockOpportunities, mockPrivate, mockUsers } from './mock';
import { ASK_URL } from './supabase';
import type { AskResponse, ClaimField, Company, CompanyPrivate, FeedItem, Membership, ProfileClaim } from './types';

export async function fetchMembership(userId: string): Promise<Membership | null> {
  if (USE_MOCK || !supabase) {
    return Object.values(mockUsers).find((u) => u.user_id === userId) ?? null;
  }
  const { data, error } = await supabase
    .from('memberships')
    .select('user_id, company_id, role')
    .eq('user_id', userId)
    .maybeSingle();
  if (error) throw new Error(`memberships: ${error.message}`);
  return data as Membership | null;
}

export async function fetchCompany(id: string): Promise<Company | null> {
  if (USE_MOCK || !supabase) return mockCompanies.find((c) => c.id === id) ?? null;
  const { data, error } = await supabase
    .from('companies')
    .select('id, name, website, bsp_url, domains, is_simulated, created_at')
    .eq('id', id)
    .maybeSingle();
  if (error) throw new Error(`companies: ${error.message}`);
  return data as Company | null;
}

// ---------- Profile ----------
const CLAIM_COLS =
  'id, company_id, field, value, type, quote, source_url, retrieved_at, confidence, verified, origin, is_simulated, created_at';

export async function fetchClaims(companyId: string): Promise<ProfileClaim[]> {
  if (USE_MOCK || !supabase) return mockClaims.filter((c) => c.company_id === companyId);
  const { data, error } = await supabase
    .from('profile_claims')
    .select(CLAIM_COLS)
    .eq('company_id', companyId)
    .order('field');
  if (error) throw new Error(`profile_claims: ${error.message}`);
  return (data ?? []) as ProfileClaim[];
}

export async function fetchPrivate(
  companyId: string,
): Promise<Pick<CompanyPrivate, 'priorities' | 'rejected_claim_ids'> | null> {
  if (USE_MOCK || !supabase) return mockPrivate.find((p) => p.company_id === companyId) ?? null;
  const { data, error } = await supabase
    .from('company_private')
    .select('priorities, rejected_claim_ids')
    .eq('company_id', companyId)
    .maybeSingle();
  if (error) throw new Error(`company_private: ${error.message}`);
  return data as Pick<CompanyPrivate, 'priorities' | 'rejected_claim_ids'> | null;
}

// ---------- Opportunities feed ----------
const FEED_SELECT =
  'rank, score, reason, opportunity:opportunities(id, title, type, url, source, date_or_deadline, format, audience, eligibility, eligibility_note, next_step, is_simulated)';

export async function fetchFeed(companyId: string): Promise<FeedItem[]> {
  if (USE_MOCK || !supabase) {
    return mockMatches
      .filter((m) => m.company_id === companyId)
      .sort((a, b) => (a.rank ?? 99) - (b.rank ?? 99))
      .map((m) => ({
        rank: m.rank, score: m.score, reason: m.reason,
        opportunity: mockOpportunities.find((o) => o.id === m.opportunity_id) ?? null,
      }));
  }
  const { data, error } = await supabase
    .from('matches')
    .select(FEED_SELECT)
    .eq('company_id', companyId)
    .order('rank');
  if (error) throw new Error(`matches: ${error.message}`);
  return (data ?? []) as unknown as FeedItem[];
}

// ---------- Ask ----------
// Contract: POST {VITE_ASK_URL}/ask  {question}  ->  {answer, route, sources[]}
export async function ask(question: string, accessToken: string): Promise<AskResponse> {
  if (USE_MOCK) return mockAsk(question);
  // Real mode: never fall back to fake answers. A missing URL is shown as an error on the page.
  if (!ASK_URL) throw new Error('The Ask service is not configured (VITE_ASK_URL is empty).');
  const res = await fetch(`${ASK_URL.replace(/\/$/, '')}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error(`/ask: HTTP ${res.status} ${await res.text().catch(() => '')}`.trim());
  return (await res.json()) as AskResponse;
}

// Mock answers that exercise every route, so the UI can be checked before /ask is up.
function mockAsk(q: string): Promise<AskResponse> {
  const s = q.toLowerCase();
  let r: AskResponse;
  if (/ignore|system prompt|password|other compan/.test(s)) {
    r = { route: 'refused', answer: 'MOCK: I can only answer about your own company and Blue Science Park offers.', sources: [] };
  } else if (/weather|football|recipe/.test(s)) {
    r = { route: 'unrelated', answer: 'MOCK: That is outside what I can help with here.', sources: [] };
  } else if (/contract|legal|price|invoice|staff/.test(s)) {
    r = { route: 'refer_to_staff', answer: 'MOCK: This needs a person at Blue Science Park.', sources: [] };
  } else if (s.trim().split(/\s+/).length < 3) {
    r = { route: 'unclear', answer: 'MOCK: Could you say a bit more about what you are looking for?', sources: [] };
  } else {
    r = {
      route: 'in_scope',
      answer: 'MOCK: The marine test environment fits your wave energy hardware. Next step: contact the test coordinator.',
      sources: [{ title: 'MOCK: Test & utveckling', url: 'https://www.bluesciencepark.se/vara-tjanster/test-utveckling/', date: null }],
    };
  }
  return new Promise((ok) => setTimeout(() => ok(r), 400));
}

// ---------- Profile editing (member) ----------
// RLS: members may only write their own company's company_private row and origin='user' claims.
type PrivateState = Pick<CompanyPrivate, 'priorities' | 'rejected_claim_ids'>;

async function upsertPrivate(companyId: string, patch: Partial<PrivateState>): Promise<void> {
  if (USE_MOCK || !supabase) {
    let row = mockPrivate.find((p) => p.company_id === companyId);
    if (!row) {
      row = { company_id: companyId, priorities: [], rejected_claim_ids: [], notes: null, updated_at: new Date().toISOString() };
      mockPrivate.push(row);
    }
    Object.assign(row, patch, { updated_at: new Date().toISOString() });
    return;
  }
  const { error } = await supabase
    .from('company_private')
    .upsert({ company_id: companyId, ...patch }, { onConflict: 'company_id' });
  if (error) throw new Error(`company_private: ${error.message}`);
}

/** Reject (or un-reject) one claim. Re-reads first so two tabs do not overwrite each other. */
export async function setClaimRejected(companyId: string, claimId: string, rejected: boolean): Promise<string[]> {
  const current = (await fetchPrivate(companyId))?.rejected_claim_ids ?? [];
  const next = rejected
    ? Array.from(new Set([...current, claimId]))
    : current.filter((id) => id !== claimId);
  await upsertPrivate(companyId, { rejected_claim_ids: next });
  return next;
}

export async function savePriorities(companyId: string, priorities: string[]): Promise<void> {
  const clean = Array.from(new Set(priorities.map((p) => p.trim()).filter(Boolean)));
  await upsertPrivate(companyId, { priorities: clean });
}

/** Member adds a fact the agent missed. Stored as origin='user', verified=false (RLS requires both). */
export async function addUserClaim(companyId: string, field: ClaimField, value: string): Promise<ProfileClaim> {
  const row = {
    company_id: companyId, field, value: value.trim(), type: 'stated' as const,
    origin: 'user' as const, verified: false, confidence: 'high' as const,
  };
  if (USE_MOCK || !supabase) {
    const c: ProfileClaim = {
      ...row, id: crypto.randomUUID(), quote: null, source_url: null, retrieved_at: null,
      is_simulated: false, created_at: new Date().toISOString(),
    };
    mockClaims.push(c);
    return c;
  }
  const { data, error } = await supabase.from('profile_claims').insert(row).select(CLAIM_COLS).single();
  if (error) throw new Error(`profile_claims: ${error.message}`);
  return data as ProfileClaim;
}
