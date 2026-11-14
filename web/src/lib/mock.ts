// DEV-ONLY mock data shaped exactly like the contract tables. Every row is is_simulated=true
// so if it ever leaks into the demo it carries a SIMULATED badge.
import type { Company, CompanyPrivate, Match, Membership, Opportunity, ProfileClaim } from './types';

const T = '2026-11-13T20:00:00Z';

export const mockUsers: Record<string, Membership> = {
  'member-oht@demo': { user_id: '00000000-0000-4000-8000-000000000001', company_id: 'ocean-harvesting', role: 'member' },
  'member-addsecure@demo': { user_id: '00000000-0000-4000-8000-000000000002', company_id: 'addsecure', role: 'member' },
  'staff@demo': { user_id: '00000000-0000-4000-8000-000000000003', company_id: null, role: 'staff' },
};

export const mockCompanies: Company[] = [
  { id: 'ocean-harvesting', name: 'Ocean Harvesting', website: 'https://www.oceanharvesting.com/', bsp_url: 'https://www.bluesciencepark.se/medlem/ocean-harvesting/', domains: ['MOCK energy'], is_simulated: true, created_at: T },
  { id: 'addsecure', name: 'AddSecure', website: 'https://www.addsecure.se/elnatslosningar/', bsp_url: 'https://www.bluesciencepark.se/medlem/addsecure/', domains: ['MOCK security'], is_simulated: true, created_at: T },
  { id: 'malvacom', name: 'Malvacom', website: 'https://malvacom.com/', bsp_url: 'https://www.bluesciencepark.se/medlem/malvacom/', domains: ['MOCK software'], is_simulated: true, created_at: T },
];

const claim = (p: Partial<ProfileClaim> & Pick<ProfileClaim, 'id' | 'company_id' | 'field' | 'type'>): ProfileClaim => ({
  value: null, quote: null, source_url: null, retrieved_at: T, confidence: 'medium',
  origin: 'agent', verified: false, is_simulated: true, created_at: T, ...p,
});

export const mockClaims: ProfileClaim[] = [
  claim({ id: 'b0000000-0000-4000-8000-000000000001', company_id: 'ocean-harvesting', field: 'offering', type: 'stated', value: 'MOCK: wave energy converter', quote: 'MOCK-citat: Vi utvecklar teknik för vågkraft.', source_url: 'https://www.oceanharvesting.com/', confidence: 'high', verified: true }),
  claim({ id: 'b0000000-0000-4000-8000-000000000002', company_id: 'ocean-harvesting', field: 'technology', type: 'stated', value: 'MOCK: energy storage in the power take-off', quote: 'MOCK-citat: Lagring av energi i kraftuttaget.', source_url: 'https://www.oceanharvesting.com/', confidence: 'high', verified: true }),
  claim({ id: 'b0000000-0000-4000-8000-000000000003', company_id: 'ocean-harvesting', field: 'location', type: 'stated', value: 'MOCK: Karlskrona', quote: 'MOCK-citat: Medlem i Blue Science Park, Karlskrona.', source_url: 'https://www.bluesciencepark.se/medlem/ocean-harvesting/' }),
  claim({ id: 'b0000000-0000-4000-8000-000000000004', company_id: 'ocean-harvesting', field: 'application_area', type: 'inferred', value: 'MOCK: offshore renewable energy parks', source_url: 'https://www.oceanharvesting.com/', confidence: 'low' }),
  claim({ id: 'b0000000-0000-4000-8000-000000000005', company_id: 'ocean-harvesting', field: 'customer_group', type: 'missing', retrieved_at: null }),
  claim({ id: 'b0000000-0000-4000-8000-000000000006', company_id: 'addsecure', field: 'offering', type: 'stated', value: 'MOCK: secure communication for power grids', quote: 'MOCK-citat: Säker kommunikation för elnätet.', source_url: 'https://www.addsecure.se/elnatslosningar/', confidence: 'high', verified: true }),
  claim({ id: 'b0000000-0000-4000-8000-000000000007', company_id: 'addsecure', field: 'domain', type: 'inferred', value: 'MOCK: cybersecurity', source_url: 'https://www.addsecure.se/elnatslosningar/', confidence: 'medium' }),
];

export const mockPrivate: CompanyPrivate[] = [
  { company_id: 'ocean-harvesting', priorities: [], rejected_claim_ids: [], notes: null, updated_at: T },
  { company_id: 'addsecure', priorities: [], rejected_claim_ids: [], notes: null, updated_at: T },
];

const opp = (p: Partial<Opportunity> & Pick<Opportunity, 'id' | 'type' | 'title' | 'url' | 'next_step'>): Opportunity => ({
  source: 'MOCK', summary: null, date_or_deadline: null, format: null, audience: null,
  eligibility: 'potential', eligibility_note: null, domains: [], retrieved_at: T, content_hash: null,
  is_simulated: true, ...p,
});

export const mockOpportunities: Opportunity[] = [
  opp({ id: 'a0000000-0000-4000-8000-000000000001', type: 'testbed', title: 'MOCK: marine test environment', url: 'https://www.bluesciencepark.se/vara-tjanster/test-utveckling/', summary: 'MOCK summary of a test environment.', next_step: 'MOCK: contact the test coordinator' }),
  opp({ id: 'a0000000-0000-4000-8000-000000000002', type: 'funding', title: 'MOCK: innovation funding call', url: 'https://www.bluesciencepark.se/vara-tjanster/vagar-till-finansiering/', date_or_deadline: '2027-02-15', eligibility_note: 'MOCK: SMEs in Sweden', next_step: 'MOCK: book a funding advice meeting' }),
  opp({ id: 'a0000000-0000-4000-8000-000000000003', type: 'event', title: 'MOCK: energy networking breakfast', url: 'https://www.bluesciencepark.se/event/', date_or_deadline: '2026-12-03', format: 'in_person', audience: 'MOCK: member companies', next_step: 'MOCK: register on the event page' }),
  opp({ id: 'a0000000-0000-4000-8000-000000000004', type: 'support', title: 'MOCK: funded cybersecurity consultant hours', url: 'https://www.bluesciencepark.se/projekt-erbjudande/', next_step: 'MOCK: apply via the project page' }),
  opp({ id: 'a0000000-0000-4000-8000-000000000005', type: 'event', title: 'MOCK: webinar on digital security', url: 'https://www.bluesciencepark.se/event/', date_or_deadline: '2026-11-27', format: 'online', audience: 'MOCK: SMEs', next_step: 'MOCK: sign up for the webinar' }),
];

const m = (company_id: string, n: number, rank: number, reason: string): Match => ({
  company_id, opportunity_id: `a0000000-0000-4000-8000-00000000000${n}`, score: 1 - rank / 10, rank, reason, created_at: T,
});

export const mockMatches: Match[] = [
  m('ocean-harvesting', 1, 1, 'MOCK reason: offers a marine test site for wave energy hardware.'),
  m('ocean-harvesting', 2, 2, 'MOCK reason: call targets renewable energy SMEs.'),
  m('ocean-harvesting', 3, 3, 'MOCK reason: energy-sector networking.'),
  m('ocean-harvesting', 5, 4, 'MOCK reason: weak link, general SME webinar.'),
  m('ocean-harvesting', 4, 5, 'MOCK reason: weak link, digital support.'),
  m('addsecure', 4, 1, 'MOCK reason: funded cybersecurity support matches their security offering.'),
  m('addsecure', 5, 2, 'MOCK reason: webinar on digital security.'),
  m('addsecure', 2, 3, 'MOCK reason: call open to tech SMEs.'),
  m('addsecure', 3, 4, 'MOCK reason: grid customers attend energy events.'),
  m('addsecure', 1, 5, 'MOCK reason: weak link, marine testbed.'),
];
