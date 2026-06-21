---
name: tailored-resume-cover-letter
description: Generate a job-tailored resume and cover letter from the candidate's materials; researches the company for motivation, assumes MS Office, and always upsells skills (quantitative or qualitative).
---

## Tailored Resume + Cover Letter Generator

Produce a **job-specific tailored resume** and a **cover letter** for ONE target job, grounded in the candidate's real documents (existing resume, transcript, syllabi) and/or a grill-me interview.

### Standing rules (apply throughout)
- **Never ask "why do you want to work for this company?"** — do a background check on the company (website, recent projects/products, mission, news) and write a compelling, company-specific motivation yourself. Only ask the user about genuinely personal facts you can't research.
- **Assume MS Office proficiency by default** — include Microsoft Office (Word, Excel, PowerPoint) in the skills section without asking.
- **Always UPSELL the candidate's skills** in their strongest truthful light: **quantitative** when a real metric exists (e.g. "led a team of 8"), **qualitative** when not measurable (e.g. "clear, persuasive communicator"). Never fabricate; never undersell.

### Inputs
- **Target job** (REQUIRED): a job from the ranked list or a pasted JD. Always fetch/read the full description.
- **Candidate context** — at least ONE of: existing resume, transcript, course syllabi, or a grill-me interview.
- **MANDATORY: real email AND phone.** Never output placeholders — ask the user if missing.

### Workflow
1. **Read source documents** (resume/transcript/syllabi). For PDFs use `pdftotext` or a Python fallback. If syllabi missing but transcript present, look up public course descriptions online. Build a structured `candidate` object.
2. **Analyze the target job** → extract `jobSpec` (required/preferred skills, responsibilities, ATS keywords, seniority).
2.5. **Grill the candidate** — interview ONE question at a time, each with a recommended answer; stop after the high-value unknowns (5–8 Qs). Do not ask "why this company" (research it) or confirm MS Office (assumed).
3. **Match & plan** — map evidence to each requirement; surface gaps honestly (never fabricate).
4. **Generate the tailored RESUME** — truthful reorg/re-emphasis, action-verb bullets, role-targeted summary, JD-aligned Skills, optional Relevant Coursework. ~1 page for students/entry-level.
5. **Generate the COVER LETTER** — header → greeting → company-specific hook (from research) → 2 evidence-mapped body paragraphs → closing CTA. ~250–400 words.
6. **Output & save (ALWAYS MD + DOCX + PDF)** to `SimularFiles/artifacts/`. MD first, then DOCX (python-docx), then PDF (reportlab). Verify non-zero sizes.

### Rules & cautions
- Truthfulness is non-negotiable — tailor by selection/emphasis/phrasing, never fabrication.
- Email and phone required; ATS-friendly formatting; present draft for review before sending.

### Handoff
- After approval, offer to apply with `linkedin-easy-apply` (per-application approval before submitting).
