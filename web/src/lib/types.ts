// Shapes copied from TEAM CONTRACT v1.5. Do not rename anything.
export type ClaimField =
  | 'offering' | 'technology' | 'expertise' | 'application_area' | 'market'
  | 'customer_group' | 'geography' | 'priority' | 'collaboration' | 'domain'
  | 'relevant_topic' | 'size' | 'founded' | 'location';
export type ClaimType = 'stated' | 'inferred' | 'missing';
export type Confidence = 'high' | 'medium' | 'low';
export type Origin = 'agent' | 'user';
export type OpportunityType = 'funding' | 'event' | 'testbed' | 'support';
export type Role = 'member' | 'staff';
export type AskRoute = 'in_scope' | 'unrelated' | 'unclear' | 'refused' | 'refer_to_staff';

// profile_embedding is never selected in the browser
export interface Company {
  id: string; name: string; website: string | null; bsp_url: string | null;
  domains: string[]; is_simulated: boolean; created_at: string;
}

export interface ProfileClaim {
  id: string; company_id: string; field: ClaimField; value: string | null; type: ClaimType;
  quote: string | null; source_url: string | null; retrieved_at: string | null;
  confidence: Confidence; origin: Origin; verified: boolean; is_simulated: boolean; created_at: string;
}

export interface CompanyPrivate {
  company_id: string; priorities: string[]; rejected_claim_ids: string[];
  notes: string | null; updated_at: string;
}

// embedding is never selected in the browser
export interface Opportunity {
  id: string; source: string; type: OpportunityType; title: string; url: string;
  summary: string | null; date_or_deadline: string | null; format: 'online' | 'in_person' | null;
  audience: string | null; eligibility: string; eligibility_note: string | null;
  next_step: string; domains: string[]; retrieved_at: string; content_hash: string | null;
  is_simulated: boolean;
}

export interface Match {
  company_id: string; opportunity_id: string; score: number | null; rank: number | null;
  reason: string | null; created_at: string;
}
export interface MatchWithOpportunity extends Match { opportunities: Opportunity }

export interface Feedback {
  id: string; company_id: string; opportunity_id: string; user_id: string;
  saved: boolean; rating: -1 | 0 | 1; created_at: string;
}

export interface Membership { user_id: string; company_id: string | null; role: Role }

export interface AskSource { title: string; url: string; date: string | null }
export interface AskResponse { answer: string; route: AskRoute; sources: AskSource[] }

// Feed row as returned by: matches.select('rank, score, reason, opportunity:opportunities(...)')
export type FeedOpportunity = Pick<Opportunity,
  'id' | 'title' | 'type' | 'url' | 'source' | 'date_or_deadline' | 'format' | 'audience'
  | 'eligibility' | 'eligibility_note' | 'next_step' | 'is_simulated'>;
export interface FeedItem {
  rank: number | null; score: number | null; reason: string | null;
  opportunity: FeedOpportunity | null;
}
