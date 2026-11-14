
import { supabase, USE_MOCK } from './supabase';
import { mockClaims, mockCompanies, mockMatches, mockOpportunities, mockPrivate, mockUsers } from './mock';
import { ASK_URL } from './supabase';
import type { AskResponse, Company, CompanyPrivate, FeedItem, Membership, ProfileClaim } from './types';

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
  if (USE_MOCK || !ASK_URL) return mockAsk(question);
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
