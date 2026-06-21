---
name: linkedin-easy-apply
description: Find and complete LinkedIn Easy Apply job applications with fresh login via secure portal each attempt, autonomous company research for screening questions, and a mandatory final confirmation before submitting.
---

## LinkedIn Easy Apply Automation

Automates applying to jobs on LinkedIn via the **Easy Apply** flow (LinkedIn's in-platform multi-step modal). Use this when the user asks to apply to jobs on LinkedIn.

### Prerequisites & safety
- **STEP ZERO — fresh login every attempt (MANDATORY):** Before each new application attempt, WIPE any previous LinkedIn login/session first (clear cookies/session for linkedin.com, e.g. open a fresh/cleared context or log out), THEN prompt the user for their LinkedIn credentials through the secure input portal as the FIRST step — `requestApproval({ type:'user-input', title:'LinkedIn Login', domain:'linkedin.com', fields:[{key:'username',inputType:'email',label:'Email'},{key:'password',inputType:'password',label:'Password'}], evaluateFn: ... })`. Never read or store credentials yourself. Do NOT assume a pre-existing logged-in session — always re-authenticate through the portal.
- **NEVER submit an application without explicit user approval.** As the LAST step before submitting, ALWAYS show a final confirmation via `requestApproval({ reason: ... })` listing the job title, company, and a full summary of the application contents (name, email, phone, resume file, screening answers), and only click the final Submit after the user approves. This confirmation gate is mandatory on every single application.
- **Screening questions — answer autonomously, don't interrogate the user:** Do NOT ask the user open-ended questions like "why do you want to work for this company?". Instead, do a quick background check on the company (their website, recent projects/products, mission) and craft a strong, truthful answer yourself. Only pause for the user when a question requires personal data you genuinely don't have (and can't research).
- Only apply to jobs that have the **Easy Apply** button (in-platform). Skip jobs that redirect to an external company site unless the user explicitly asks to handle those.
- Confirm key applicant details with the user up front and store them in a profile object: full name, email, phone, location, years of experience, work authorization / visa status, willingness to relocate, desired salary, and the **resume file path** to upload.

### Workflow

**1. Gather criteria & profile**
- Ask the user (once) for: search keywords, location, filters (date posted, experience level, remote), how many to apply to, and confirm the profile/answers object above.

**2. Search for jobs** — use `https://www.linkedin.com/jobs/search/?keywords=...&f_AL=true&location=...` (f_AL=true filters to Easy Apply only). Collect job cards (title, company, ref); iterate one at a time.

**3. Open a job & start Easy Apply** — Click a job card, snapshot the detail pane, find the **Easy Apply** button, and click it.

**4. Fill the multi-step modal** (Contact info → Resume → Screening questions → Review). Snapshot each step, fill from the profile, answer screening questions from profile/company research, upload the resume file, click Next until Review. Do NOT check "Follow company" unless desired.

**5. Final confirmation & submit** — Show the mandatory `requestApproval` confirmation, then click Submit only after approval. Capture the confirmation.

**6. Loop & report** — Track applied/skipped/failed and report a summary table.

### Edge cases
- Unanswerable screening question needing personal data → pause and ask the user.
- External (non-Easy-Apply) → skip and note.
- Rate limiting / CAPTCHA → stop and inform the user.
- Already applied → skip.

### Tips
- Store the profile object in a REPL variable across applications.
- Batch one approval per submission so the user stays in control.
