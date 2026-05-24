# DPDP Readiness Navigator

DPDP Act 2023 self-assessment tool for Indian NGOs. Built on Frappe Framework, deployed on Frappe Cloud.

**Live site:** https://dpdp.projecttech4dev.org  
**Deployment:** Frappe Cloud — auto-deploys on push to `main`

---

## What it does

A guided 25-question self-assessment across 5 sections of the DPDP Act 2023. On completion:
- Section scores rendered instantly (client-side)
- Call 1: Claude generates an executive summary with sector and beneficiary-specific risks
- Call 2: Claude generates a 30/90/365-day action roadmap using only gap questions
- WeasyPrint generates a PDF report and emails it to the assessor
- All outputs stored in Frappe as a `DPDP Assessment` document

---

## Repository structure

```
dpdp_tool/                              ← repo root (Frappe app)
├── setup.py
├── pyproject.toml
├── requirements.txt                    ← anthropic>=0.20.0, weasyprint
├── MANIFEST.in
└── dpdp_tool/                          ← Python package
    ├── hooks.py                        ← fixtures, CSS include
    ├── api.py                          ← all API endpoints and background jobs
    ├── pdf_generator.py                ← WeasyPrint PDF generation
    ├── modules.txt
    ├── fixtures/
    │   ├── dpdp_assessment.json        ← DPDP Assessment DocType definition
    │   ├── dpdp_consult_request.json   ← DPDP Consult Request DocType definition
    │   ├── email_template_assessment_report.json
    │   └── client_script_dpdp_assessment.json
    ├── dpdp_tool/
    │   └── doctype/
    │       ├── dpdp_assessment/
    │       │   ├── dpdp_assessment.py  ← DocType controller
    │       │   └── dpdp_assessment.json
    │       └── dpdp_consult_request/
    │           ├── dpdp_consult_request.py
    │           └── dpdp_consult_request.json
    ├── public/
    │   ├── css/dpdp.css                ← all styles (Public Sans + Outfit)
    │   ├── js/
    │   │   ├── dpdp-assess.js          ← assessment page logic
    │   │   └── dpdp-index.js           ← landing page / dashboard
    │   └── dpdp-config.json            ← single source of truth: questions,
    │                                      sections, scoring bands, glossary,
    │                                      references, sectors
    └── www/
        ├── assess.html                 ← assessment page (served at /assess)
        └── index.html                  ← landing page (served at /)
```

---

## API methods in `api.py`

| Method | Type | Purpose |
|---|---|---|
| `store_assessment` | Whitelisted | Saves assessment, enqueues AI background jobs |
| `poll_status` | Whitelisted | JS polls this for summary/roadmap/PDF readiness |
| `get_recommendations` | Whitelisted | Legacy single-call Claude (fallback) |
| `check_reco` | Whitelisted | Legacy poll for recommendations field |
| `patch_assessment_reco` | Whitelisted | Patches recommendations onto existing doc |
| `get_sector_insights` | Whitelisted | Aggregates scores by sector for dashboard |
| `submit_consult_request` | Whitelisted | Saves consult enquiry |
| `rerun_ai_calls` | Whitelisted | Desk button: re-enqueue both AI calls |
| `regenerate_pdf` | Whitelisted | Desk button: re-generate PDF only |
| `run_summary_call` | Background job | Call 1 — executive summary via Claude |
| `run_roadmap_call` | Background job | Call 2 — roadmap via Claude, triggers PDF |
| `generate_and_attach_pdf` | Background job | WeasyPrint PDF, attaches to doc, emails |

---

## Site config keys

Set these in Frappe Cloud → your site → Config:

| Key | Required | Purpose |
|---|---|---|
| `anthropic_api_key` | Yes | Claude API key |
| `dpdp_report_cc_email` | No | CC address for assessment report emails |
| `dpdp_site_url` | No | Override public URL (defaults to Frappe Cloud URL) |

---

## Deployment

Push to `main` → Frappe Cloud auto-deploys (2–4 minutes). The deploy runs `bench migrate` (applies fixture changes) and rebuilds assets (CSS/JS/config from `public/`).

```bash
git add .
git commit -m "your change"
git push origin main
```

See `frappe-setup-guide.md` for first-time setup instructions.

---

## Local PDF testing

```bash
pip install weasyprint
# Place test_pdf.py, pdf_generator.py, dpdp-config.json in same folder
/opt/homebrew/Cellar/weasyprint/68.1/libexec/bin/python test_pdf.py
open output_test.pdf
```

---

## Consult notifications

Internal team notifications for new consult requests are handled by a **Frappe Notification** configured in Desk (Document Type: DPDP Consult Request, Event: New) — not via code. This avoids SMTP quirks with `frappe.sendmail()` called from a web request thread.
