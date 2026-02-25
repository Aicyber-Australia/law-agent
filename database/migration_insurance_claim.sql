-- Migration: Insurance claim action templates
-- Run this SQL in your Supabase SQL Editor

-- ============================================
-- VIC: Dispute a Denied/Underpaid Insurance Claim
-- ============================================
INSERT INTO action_templates (id, state, category, title, description, keywords, steps, estimated_time) VALUES
('vic_insurance_claim_dispute', 'VIC', 'insurance_claim', 'Dispute an Insurance Claim Decision in Victoria',
 'Step-by-step guide to challenge a denied or underpaid insurance claim through IDR and AFCA',
 ARRAY['insurance', 'claim', 'denied', 'dispute', 'underpaid', 'rejected', 'AFCA', 'complaint', 'general insurance'],
 '[
   {"order": 1, "title": "Review Your Policy & Decision Letter", "description": "Carefully read your insurance policy, Product Disclosure Statement (PDS), and the insurer''s decision letter.", "details": "Identify the exact reason for denial or underpayment. Check if the exclusion or limitation they cite actually applies to your situation. Note any policy clauses that support your claim."},
   {"order": 2, "title": "Gather Supporting Evidence", "description": "Collect all evidence that supports your claim: photos, receipts, repair quotes, medical reports, police reports, witness statements.", "details": "Get independent assessments if the insurer''s valuation seems low. For building claims, get your own builder''s quote. For car claims, get an independent assessment."},
   {"order": 3, "title": "Lodge a Formal Internal Complaint", "description": "Submit a written complaint to the insurer''s Internal Dispute Resolution (IDR) team. This is different from the claims team.", "details": "Clearly state why you disagree with their decision, reference specific policy clauses, and attach your evidence. The insurer must acknowledge within 1 business day and respond within 30 calendar days (General Insurance Code of Practice)."},
   {"order": 4, "title": "Escalate to AFCA if IDR Fails", "description": "If the insurer''s IDR response is unsatisfactory or they don''t respond within 30 days, lodge a complaint with AFCA (Australian Financial Complaints Authority).", "details": "AFCA is FREE. Lodge online at afca.org.au or call 1800 931 678. You need your policy number and the insurer''s IDR reference number. AFCA can award compensation up to $1,085,400 for general insurance disputes."},
   {"order": 5, "title": "Consider Further Options", "description": "If AFCA''s determination is not in your favour, consider other options: VCAT, legal action, or seeking legal advice.", "details": "AFCA decisions are binding on the insurer but not on you — you can still go to court. For smaller amounts, VCAT may be appropriate. For larger claims, consider a no-win-no-fee insurance lawyer. Contact the Insurance Law Service (free) on 1300 663 464."}
 ]'::jsonb,
 '30-120 days')
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- VIC: Motor Vehicle Insurance Claim Dispute
-- ============================================
INSERT INTO action_templates (id, state, category, title, description, keywords, steps, estimated_time) VALUES
('vic_car_insurance_claim', 'VIC', 'insurance_claim', 'Dispute a Car Insurance Claim in Victoria',
 'Step-by-step guide for motor vehicle insurance claim disputes including not-at-fault claims',
 ARRAY['car', 'motor', 'vehicle', 'accident', 'insurance', 'claim', 'not at fault', 'collision', 'damage'],
 '[
   {"order": 1, "title": "Document Everything", "description": "Gather all evidence from the accident: photos of damage, the other party''s details, police report number, dashcam footage, and witness contact details.", "details": "If you haven''t already, take photos of all damage from multiple angles. Get written repair quotes from at least two repairers. Keep records of any hire car costs or out-of-pocket expenses."},
   {"order": 2, "title": "Review Your Policy Coverage", "description": "Check your policy type (comprehensive, third party property, third party fire & theft) and understand what is covered.", "details": "For not-at-fault claims: even if you only have third party insurance, you may be able to claim against the at-fault driver''s insurer directly. For comprehensive: check your excess amount and any exclusions."},
   {"order": 3, "title": "Challenge the Insurer''s Assessment", "description": "If the insurer''s offer is too low or they''ve denied your claim, request a detailed written explanation and challenge it with your own evidence.", "details": "Common issues: insurer undervaluing the vehicle (get your own market valuation from RedBook or similar), insurer using cheap aftermarket parts (you may be entitled to genuine parts), or insurer disputing fault."},
   {"order": 4, "title": "Lodge Internal Complaint", "description": "If the claims team won''t budge, escalate to the insurer''s formal complaints/IDR team in writing.", "details": "Reference the General Insurance Code of Practice and the Insurance Contracts Act 1984. The insurer must respond within 30 days. Keep copies of all correspondence."},
   {"order": 5, "title": "Escalate to AFCA or VCAT", "description": "If IDR fails, lodge with AFCA (free) or apply to VCAT for a hearing.", "details": "AFCA handles most insurance disputes effectively. For not-at-fault claims against uninsured drivers, you may need to pursue through VCAT or Magistrates'' Court directly."}
 ]'::jsonb,
 '30-90 days')
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- NSW: Dispute a Denied/Underpaid Insurance Claim
-- ============================================
INSERT INTO action_templates (id, state, category, title, description, keywords, steps, estimated_time) VALUES
('nsw_insurance_claim_dispute', 'NSW', 'insurance_claim', 'Dispute an Insurance Claim Decision in NSW',
 'Step-by-step guide to challenge a denied or underpaid insurance claim in NSW',
 ARRAY['insurance', 'claim', 'denied', 'dispute', 'underpaid', 'rejected', 'AFCA', 'complaint', 'general insurance'],
 '[
   {"order": 1, "title": "Review Your Policy & Decision", "description": "Read your PDS, Certificate of Insurance, and the insurer''s decision letter carefully.", "details": "Identify the specific exclusion or reason cited. Check if it genuinely applies. Note the insurer''s obligations under the Insurance Contracts Act 1984 (Cth) — particularly the duty of utmost good faith (s 13)."},
   {"order": 2, "title": "Collect Evidence", "description": "Gather all supporting documentation: photos, receipts, quotes, expert reports, and any correspondence with the insurer.", "details": "For property claims, get independent repair/replacement quotes. For health claims, get supporting medical opinions. Keep a log of all phone calls (date, time, who you spoke to, what was said)."},
   {"order": 3, "title": "Lodge Formal Complaint with Insurer", "description": "Write to the insurer''s IDR team requesting a formal review of their decision.", "details": "This is FREE and required before going to AFCA. The insurer must respond within 30 calendar days. If they don''t respond, you can escalate to AFCA immediately. Reference the General Insurance Code of Practice 2020."},
   {"order": 4, "title": "Lodge AFCA Complaint", "description": "If IDR is unsuccessful or the insurer doesn''t respond in time, lodge a free complaint with AFCA.", "details": "Visit afca.org.au or call 1800 931 678. AFCA will contact the insurer and attempt to resolve the dispute. If no resolution, AFCA makes a binding determination. Time limit: within 2 years of the IDR response."},
   {"order": 5, "title": "Further Options if Needed", "description": "If AFCA cannot help or you disagree with their determination, consider NCAT or court action.", "details": "NCAT (NSW Civil and Administrative Tribunal) can hear consumer claims. For larger amounts, the Local Court or District Court may be appropriate. Contact the Insurance Law Service (1300 663 464) or LawAccess NSW (1300 888 529) for free advice."}
 ]'::jsonb,
 '30-120 days')
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- NSW: Motor Vehicle Insurance Claim Dispute
-- ============================================
INSERT INTO action_templates (id, state, category, title, description, keywords, steps, estimated_time) VALUES
('nsw_car_insurance_claim', 'NSW', 'insurance_claim', 'Dispute a Car Insurance Claim in NSW',
 'Step-by-step guide for motor vehicle insurance claim disputes in NSW',
 ARRAY['car', 'motor', 'vehicle', 'accident', 'insurance', 'claim', 'not at fault', 'collision', 'damage', 'CTP'],
 '[
   {"order": 1, "title": "Secure Your Evidence", "description": "Collect all accident evidence: photos, police event number, other party''s details, dashcam footage, and witness statements.", "details": "Important: NSW has separate CTP (green slip) insurance for personal injury and property insurance for vehicle damage. Make sure you''re claiming under the right policy. For property damage, claim under your comprehensive policy or the at-fault party''s insurer."},
   {"order": 2, "title": "Understand Your Coverage", "description": "Review your policy to confirm what''s covered and check the excess amount.", "details": "For not-at-fault claims: you can claim through your own insurer (who will recover from the at-fault party) or claim directly against the at-fault party''s insurer. Going through your own insurer is usually faster but may involve paying your excess first."},
   {"order": 3, "title": "Challenge Unfair Assessments", "description": "If the insurer''s valuation or repair assessment is inadequate, dispute it with independent evidence.", "details": "Get your own written quotes for repairs. For total loss disputes, provide evidence of market value (similar vehicles for sale, RedBook valuation). You can request the insurer''s assessor''s report."},
   {"order": 4, "title": "Escalate Through IDR", "description": "Lodge a formal written complaint with the insurer''s internal dispute resolution team.", "details": "State your case clearly with evidence. The insurer must respond within 30 days under the General Insurance Code of Practice. If they don''t, you can go straight to AFCA."},
   {"order": 5, "title": "AFCA or NCAT", "description": "Escalate to AFCA (free) if IDR fails. For disputes with uninsured drivers, consider NCAT.", "details": "AFCA is the primary path for insured disputes. For not-at-fault claims against uninsured drivers, you may need to pursue through NCAT or the Local Court. Contact LawAccess NSW (1300 888 529) for free guidance."}
 ]'::jsonb,
 '30-90 days')
ON CONFLICT (id) DO NOTHING;
