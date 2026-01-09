-- Migration v2: Add action_templates and expand legal_docs
-- Run this SQL in your Supabase SQL Editor

-- ============================================
-- 1. Create action_templates table
-- ============================================
CREATE TABLE IF NOT EXISTS action_templates (
    id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    keywords TEXT[],
    steps JSONB NOT NULL,
    estimated_time TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_templates_state ON action_templates(state);
CREATE INDEX IF NOT EXISTS idx_templates_keywords ON action_templates USING GIN(keywords);

-- ============================================
-- 2. Insert action templates
-- ============================================

-- VIC: Bond Refund
INSERT INTO action_templates (id, state, category, title, description, keywords, steps, estimated_time) VALUES
('vic_bond_refund', 'VIC', 'tenancy', 'Get Your Bond Back in Victoria',
 'Step-by-step guide to reclaim your rental bond after moving out',
 ARRAY['bond', 'deposit', 'refund', 'moving out', 'end of lease', 'bond back'],
 '[
   {"order": 1, "title": "Schedule Final Inspection", "description": "Contact your landlord or agent at least 7 days before moving out to arrange a final inspection.", "details": "Take timestamped photos of every room as evidence of the property condition."},
   {"order": 2, "title": "Complete Condition Report", "description": "Fill in the outgoing condition report and have both parties sign it.", "details": "Compare with your ingoing report. Note any pre-existing damage."},
   {"order": 3, "title": "Return All Keys", "description": "Return all keys, remotes, and access devices to the landlord/agent.", "details": "Get written confirmation (email or text) as proof of return."},
   {"order": 4, "title": "Lodge Bond Claim with RTBA", "description": "Submit your bond claim online at rentalbonds.vic.gov.au", "details": "You will need your bond reference number from your original receipt."},
   {"order": 5, "title": "Wait for Response", "description": "The landlord has 14 days to respond to your claim.", "details": "If they do not respond within 14 days, RTBA will release the bond to you."}
 ]'::jsonb,
 '14-21 days')
ON CONFLICT (id) DO NOTHING;

-- VIC: Break Lease
INSERT INTO action_templates (id, state, category, title, description, keywords, steps, estimated_time) VALUES
('vic_lease_break', 'VIC', 'tenancy', 'Break Your Lease Early in Victoria',
 'Guide to ending your tenancy before the lease expires',
 ARRAY['break lease', 'early termination', 'end tenancy early', 'leave early', 'terminate lease'],
 '[
   {"order": 1, "title": "Check Your Lease Terms", "description": "Review your lease agreement for break lease clauses and notice periods.", "details": "Fixed-term leases typically require minimum 28 days notice."},
   {"order": 2, "title": "Give Written Notice", "description": "Provide formal written notice using the official Notice of Intention to Vacate form.", "details": "Send via email AND registered post. Keep copies of everything."},
   {"order": 3, "title": "Understand Your Costs", "description": "Calculate potential costs: rent until new tenant found, re-letting fee (max 1 week rent), advertising costs.", "details": "The landlord must take reasonable steps to minimise these costs."},
   {"order": 4, "title": "Help Find a New Tenant", "description": "You can advertise and help find a replacement tenant to reduce your liability.", "details": "If you find a suitable tenant, your liability may end when they move in."},
   {"order": 5, "title": "Complete Final Inspection", "description": "Arrange final inspection and complete the outgoing condition report.", "details": "Follow the same process as a normal end of lease."}
 ]'::jsonb,
 '28+ days')
ON CONFLICT (id) DO NOTHING;

-- VIC: Rent Increase Dispute
INSERT INTO action_templates (id, state, category, title, description, keywords, steps, estimated_time) VALUES
('vic_rent_dispute', 'VIC', 'tenancy', 'Challenge a Rent Increase in Victoria',
 'Steps to dispute an unfair or invalid rent increase',
 ARRAY['rent increase', 'rent rise', 'dispute rent', 'unfair rent', 'challenge rent'],
 '[
   {"order": 1, "title": "Check Notice Validity", "description": "Verify the landlord gave at least 60 days written notice.", "details": "The notice must be in the prescribed form and state the new rent amount."},
   {"order": 2, "title": "Check Timing", "description": "Confirm at least 12 months have passed since the last increase or start of tenancy.", "details": "Rent cannot be increased more than once every 12 months."},
   {"order": 3, "title": "Research Market Rates", "description": "Compare similar properties in your area to assess if the increase is excessive.", "details": "Check realestate.com.au and domain.com.au for comparable rentals."},
   {"order": 4, "title": "Negotiate with Landlord", "description": "Contact your landlord to discuss the increase and try to negotiate.", "details": "Put your concerns in writing and keep records of all communications."},
   {"order": 5, "title": "Apply to VCAT if Needed", "description": "If negotiation fails, apply to VCAT within 30 days of receiving the notice.", "details": "VCAT can determine a fair rent increase. Fee is approximately $65."}
 ]'::jsonb,
 '30-60 days')
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- 3. Add state column to legal_docs (for filtering)
-- ============================================
ALTER TABLE legal_docs ADD COLUMN IF NOT EXISTS state TEXT DEFAULT 'VIC';

-- ============================================
-- 4. Insert more legal_docs mock data
-- ============================================

-- VIC Tenancy Laws
INSERT INTO legal_docs (content, metadata, state) VALUES
(
    'A landlord must not enter rented premises without the tenant''s consent, except in specific circumstances such as emergency, or with at least 24 hours notice for inspections, repairs, or to show the property to prospective tenants or buyers.',
    '{"source": "Residential Tenancies Act 1997 (Vic)", "section": "s 85-86", "url": "https://www.legislation.vic.gov.au/"}',
    'VIC'
),
(
    'A rental bond must not exceed one month''s rent. The bond must be lodged with the Residential Tenancies Bond Authority (RTBA) within 10 business days of receipt.',
    '{"source": "Residential Tenancies Act 1997 (Vic)", "section": "s 406-410", "url": "https://www.legislation.vic.gov.au/"}',
    'VIC'
),
(
    'A tenant may terminate a fixed-term rental agreement early by giving at least 28 days notice. The tenant may be liable for costs including rent until a new tenant is found, re-letting costs, and advertising costs.',
    '{"source": "Residential Tenancies Act 1997 (Vic)", "section": "s 234-235", "url": "https://www.legislation.vic.gov.au/"}',
    'VIC'
),
(
    'Urgent repairs must be carried out by the landlord within 24 hours of being notified. Urgent repairs include burst water pipes, blocked toilets, dangerous electrical faults, gas leaks, and flooding.',
    '{"source": "Residential Tenancies Act 1997 (Vic)", "section": "s 72-73", "url": "https://www.legislation.vic.gov.au/"}',
    'VIC'
),
(
    'A landlord cannot unreasonably refuse consent for a tenant to keep a pet. If refused, the tenant can apply to VCAT for an order allowing the pet.',
    '{"source": "Residential Tenancies Act 1997 (Vic)", "section": "s 71A", "url": "https://www.legislation.vic.gov.au/"}',
    'VIC'
);

-- NSW Tenancy Laws (for multi-state demo)
INSERT INTO legal_docs (content, metadata, state) VALUES
(
    'A landlord must give the tenant at least 60 days written notice of a rent increase. Rent cannot be increased during a fixed-term agreement unless the agreement allows it.',
    '{"source": "Residential Tenancies Act 2010 (NSW)", "section": "s 41-42", "url": "https://legislation.nsw.gov.au/"}',
    'NSW'
),
(
    'A rental bond in NSW must not exceed 4 weeks rent. The bond must be deposited with NSW Fair Trading within 10 days.',
    '{"source": "Residential Tenancies Act 2010 (NSW)", "section": "s 157-159", "url": "https://legislation.nsw.gov.au/"}',
    'NSW'
),
(
    'A landlord must give at least 2 days notice before entering the premises for routine inspections. No more than 4 inspections are allowed in any 12-month period.',
    '{"source": "Residential Tenancies Act 2010 (NSW)", "section": "s 55", "url": "https://legislation.nsw.gov.au/"}',
    'NSW'
);

-- ============================================
-- 5. Add more lawyers
-- ============================================
INSERT INTO lawyers (name, specialty, location, rate) VALUES
('David Chen', 'Tenancy', 'Melbourne', '$280/hr'),
('Emma Wilson', 'Tenancy', 'Sydney', '$320/hr'),
('Michael Brown', 'Property', 'Melbourne', '$400/hr'),
('Sophie Lee', 'Employment', 'Melbourne', '$350/hr'),
('Robert Taylor', 'Tenancy', 'Brisbane', '$290/hr');
