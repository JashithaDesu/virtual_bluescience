// The ONLY place that talks to Supabase. Pages call these functions, never supabase directly.
// Every function has a mock branch so the UI works before the database is ready.
import { supabase, USE_MOCK } from './supabase';
import { mockCompanies, mockUsers } from './mock';
import type { Company, Membership } from './types';

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
