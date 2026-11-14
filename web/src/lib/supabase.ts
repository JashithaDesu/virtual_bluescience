import { createClient, type SupabaseClient } from '@supabase/supabase-js';

// The anon key is designed to be public (RLS protects the data). The service role key must NEVER be here.
const url = (import.meta.env.VITE_SUPABASE_URL as string | undefined) ?? '';
const anonKey = (import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined) ?? '';
export const ASK_URL = (import.meta.env.VITE_ASK_URL as string | undefined) ?? '';

export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true' || !url || !anonKey;

const SERVICE_KEY_MSG = 'Refusing to start: a SERVICE ROLE key is configured in the browser. Use the anon key.';
function assertNotServiceRole(key: string) {
  if (key.startsWith('sb_secret_')) throw new Error(SERVICE_KEY_MSG);
  const parts = key.split('.');
  if (parts.length !== 3) return;
  let role: unknown;
  try {
    role = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/'))).role;
  } catch {
    return;
  }
  if (role === 'service_role') throw new Error(SERVICE_KEY_MSG);
}

if (!USE_MOCK) assertNotServiceRole(anonKey);

export const supabase: SupabaseClient | null = USE_MOCK ? null : createClient(url, anonKey);
