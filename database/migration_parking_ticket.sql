-- Migration: Parking ticket action templates
-- Run this SQL in your Supabase SQL Editor

-- ============================================
-- VIC: Challenge a Council Parking Fine
-- ============================================
INSERT INTO action_templates (id, state, category, title, description, keywords, steps, estimated_time) VALUES
('vic_parking_fine_challenge', 'VIC', 'parking_ticket', 'Challenge a Parking Fine in Victoria',
 'Step-by-step guide to dispute a council or private parking infringement notice',
 ARRAY['parking', 'fine', 'ticket', 'infringement', 'challenge', 'council', 'parking fine', 'dispute'],
 '[
   {"order": 1, "title": "Check the Notice Details", "description": "Review the infringement notice for errors: incorrect registration, wrong date/time, wrong location, or missing information.", "details": "Any factual error on the notice may be grounds for withdrawal. Take photos of the notice and the location."},
   {"order": 2, "title": "Gather Evidence", "description": "Collect supporting evidence: photos of signage (or lack of), receipts, medical certificates, dashcam footage, or witness statements.", "details": "Visit the location and photograph signs from the driver''s perspective. Note if signs were obscured, missing, or confusing."},
   {"order": 3, "title": "Request Internal Review", "description": "Write to the issuing authority (council or Fines Victoria) requesting a review within 28 days of the notice date.", "details": "This is FREE. Clearly state your grounds for challenge and attach evidence. Send via email and keep a copy. Use the official review form if one is provided."},
   {"order": 4, "title": "Await Review Decision", "description": "The issuing authority will review your request and respond in writing.", "details": "If upheld, you can either pay or elect to have the matter heard in court. If withdrawn, no further action needed."},
   {"order": 5, "title": "Elect Court Hearing (if review fails)", "description": "If the internal review is unsuccessful, you can elect to have the matter heard at the Magistrates'' Court.", "details": "You must elect within 28 days of the review decision. The court will hear your case fresh — you are not bound by the internal review outcome. Consider if the fine amount justifies the effort."}
 ]'::jsonb,
 '28-60 days')
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- VIC: Challenge a Speeding Fine
-- ============================================
INSERT INTO action_templates (id, state, category, title, description, keywords, steps, estimated_time) VALUES
('vic_speeding_fine_challenge', 'VIC', 'parking_ticket', 'Challenge a Speeding Fine in Victoria',
 'Step-by-step guide to dispute a speed camera or police-issued speeding fine',
 ARRAY['speeding', 'speed', 'camera', 'fine', 'ticket', 'infringement', 'challenge', 'traffic'],
 '[
   {"order": 1, "title": "Request Camera Photos", "description": "If the fine is from a speed camera, request the camera images from Fines Victoria (free of charge).", "details": "Check the photos for: is it your vehicle? Is the speed reading clear? Is the location correct? You can request photos online at fines.vic.gov.au."},
   {"order": 2, "title": "Check for Technical Issues", "description": "Review the notice for errors and assess potential defences: speedometer calibration, emergency situation, camera accuracy.", "details": "Common grounds: recently serviced speedometer showing different reading, driving someone to hospital, incorrect speed zone signage, road works with unclear limits."},
   {"order": 3, "title": "Consider Official Warning (First Offence)", "description": "If this is your first speeding offence in Victoria, you may request an official warning instead of a fine.", "details": "Write to Fines Victoria explaining it is your first offence and requesting an official warning. This is discretionary but often granted for minor infringements (1-9 km/h over)."},
   {"order": 4, "title": "Apply for Internal Review", "description": "Submit a formal review request to Fines Victoria within 28 days, stating your grounds and attaching evidence.", "details": "Grounds can include: special circumstances, honest and reasonable mistake, incorrect signage, or that enforcement was conducted contrary to guidelines."},
   {"order": 5, "title": "Elect Magistrates'' Court (if needed)", "description": "If the review is rejected, elect to have the matter heard in the Magistrates'' Court within 28 days.", "details": "At court you can present your case, call witnesses, and challenge the evidence. Seek free legal advice from a community legal centre before attending."}
 ]'::jsonb,
 '28-90 days')
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- NSW: Challenge a Parking Fine
-- ============================================
INSERT INTO action_templates (id, state, category, title, description, keywords, steps, estimated_time) VALUES
('nsw_parking_fine_challenge', 'NSW', 'parking_ticket', 'Challenge a Parking Fine in NSW',
 'Step-by-step guide to dispute a council or state-issued parking fine in NSW',
 ARRAY['parking', 'fine', 'ticket', 'infringement', 'challenge', 'council', 'parking fine', 'dispute'],
 '[
   {"order": 1, "title": "Check the Penalty Notice", "description": "Review the penalty notice for errors: wrong registration number, incorrect date/time/location, or missing required information.", "details": "Under the Fines Act 1996 (NSW), a penalty notice must contain specific information. Errors may be grounds for review."},
   {"order": 2, "title": "Gather Evidence", "description": "Collect evidence supporting your case: photographs of signage, receipts showing you paid for parking, medical records if applicable.", "details": "Photograph the exact parking spot and all nearby signs. Note distances, visibility, and any obstructions to signs."},
   {"order": 3, "title": "Request a Review with Revenue NSW", "description": "Submit a review request to Revenue NSW online or by mail. You must do this before the due date on the notice.", "details": "Go to revenue.nsw.gov.au and select ''Request a review''. Provide your penalty notice number, grounds for review, and upload evidence. This is FREE."},
   {"order": 4, "title": "Await the Review Outcome", "description": "Revenue NSW will assess your review and notify you of the outcome.", "details": "Possible outcomes: penalty cancelled, official caution issued, penalty confirmed, or payment plan offered. Review typically takes 4-6 weeks."},
   {"order": 5, "title": "Elect Court Hearing (if review fails)", "description": "If your review is unsuccessful, you can elect to have the matter heard in the Local Court.", "details": "You must elect within 28 days of the review decision. A court election means the matter starts fresh. Consider whether the fine amount justifies attending court."}
 ]'::jsonb,
 '28-60 days')
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- NSW: Challenge a Speeding Fine
-- ============================================
INSERT INTO action_templates (id, state, category, title, description, keywords, steps, estimated_time) VALUES
('nsw_speeding_fine_challenge', 'NSW', 'parking_ticket', 'Challenge a Speeding Fine in NSW',
 'Step-by-step guide to dispute a speed camera or police-issued speeding fine in NSW',
 ARRAY['speeding', 'speed', 'camera', 'fine', 'ticket', 'infringement', 'challenge', 'traffic'],
 '[
   {"order": 1, "title": "Request Speed Camera Images", "description": "If the fine is from a fixed or mobile speed camera, request the camera images from Revenue NSW (free).", "details": "Visit revenue.nsw.gov.au or call 1300 138 118. Check: is it your vehicle? Is the speed reading visible? Is the location correct?"},
   {"order": 2, "title": "Assess Your Grounds", "description": "Determine if you have valid grounds: incorrect signage, emergency situation, vehicle was stolen, someone else was driving, or camera/radar error.", "details": "If someone else was driving, you can submit a statutory declaration nominating the actual driver. You must do this within 28 days."},
   {"order": 3, "title": "Request Review with Revenue NSW", "description": "Submit a formal review request online at revenue.nsw.gov.au before the due date on the notice.", "details": "State your grounds clearly, attach all evidence, and request the penalty be withdrawn or an official caution issued. First offenders with a clean record have a better chance."},
   {"order": 4, "title": "Consider Hardship Application", "description": "If you cannot afford to pay, apply for a Work and Development Order (WDO) or payment plan through Revenue NSW.", "details": "A WDO lets you work off fines through community service, counselling, or medical treatment. You need a WDO sponsor (e.g., community legal centre)."},
   {"order": 5, "title": "Elect Local Court (if needed)", "description": "If the review is rejected, you can elect to have the matter heard in the Local Court within 28 days.", "details": "At court, the prosecution must prove the offence. You can challenge the evidence, call witnesses, and present your defence. Get free legal advice from LawAccess NSW (1300 888 529) first."}
 ]'::jsonb,
 '28-90 days')
ON CONFLICT (id) DO NOTHING;
