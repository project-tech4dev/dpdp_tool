# DPDP Navigator — Setup Guide

**Site:** `dpdp.projecttech4dev.org` | **App:** `dpdp_tool` | **Frappe Cloud**

---

## Overview

The DPDP Navigator runs as a custom Frappe app. Every code change pushed to `main` on GitHub deploys automatically — no manual file copying or SSH.

```
GitHub (main branch)
    │  git push
    ▼
Frappe Cloud (auto-deploys)
    ├── bench migrate        → applies DocType fixture changes
    ├── bench build          → rebuilds CSS/JS/config from public/
    └── site restart         → new Python code active
```

---

## Part 1 — First-time GitHub setup

If you are setting up a new instance, create a private GitHub repository named `dpdp_tool`, push this codebase to it, then connect it in Frappe Cloud under Apps → Add App → GitHub.

```bash
git remote add origin https://github.com/YOUR-ORG/dpdp_tool.git
git push -u origin main
```

---

## Part 2 — Frappe Cloud site setup

### 2.1 Create the site

Frappe Cloud → New Site:
- **Region:** India (Mumbai) — required for DPDP data residency
- **Apps:** Frappe Framework only — do not add ERPNext

### 2.2 Connect the GitHub repo

Apps tab → Add App → GitHub → select `dpdp_tool` → branch `main`.

Frappe Cloud installs the app, runs `pip install -r requirements.txt` (installs `anthropic` and `weasyprint`), and runs `bench migrate` to apply all fixtures.

### 2.3 Add site config

Frappe Cloud → your site → Config → Add each key:

| Key | Value |
|---|---|
| `anthropic_api_key` | `sk-ant-YOUR-KEY` |
| `dpdp_report_cc_email` | `dpdp@projecttech4dev.org` |
| `dpdp_consult_notify_email` | `dpdp@projecttech4dev.org` |

### 2.4 Add custom domain

Site → Domains → Add Domain → `dpdp.projecttech4dev.org`. Add the CNAME record at your DNS provider. Frappe Cloud issues SSL automatically.

---

## Part 3 — DocTypes

DocTypes are defined in `fixtures/dpdp_assessment.json` and `fixtures/dpdp_consult_request.json` and applied automatically on every deploy via `bench migrate`. You do not need to create them manually.

### DPDP Assessment — key fields

| Field | Type | Purpose |
|---|---|---|
| `org_name` | Data | Organisation name |
| `org_email` | Data | Assessor email (report sent here) |
| `contact_name` | Data | Assessor name |
| `sector` | Small Text | Comma-separated sectors |
| `org_size` | Select | Under 20 / 20-100 / 100-500 / 500+ staff |
| `beneficiaries` | Small Text | Beneficiary groups |
| `total_score` | Float | Overall score out of 50 |
| `score_consent` | Float | Section 1 score |
| `score_storage` | Float | Section 2 score |
| `score_usage` | Float | Section 3 score |
| `score_rights` | Float | Section 4 score |
| `score_governance` | Float | Section 5 score |
| `answers_json` | Long Text | All 25 answers as JSON |
| `executive_summary` | Long Text | Call 1 AI output |
| `action_roadmap` | Long Text | Call 2 AI output |
| `pdf_file` | Attach | Generated PDF |
| `pdf_emailed` | Check | Set after email sent |
| `status` | Select | Submitted / Summary Ready / Roadmap Ready / Processed / Failed |
| `submitted_on` | Datetime | Auto-set on insert |
| `failed_reason` | Long Text | Error detail if AI calls fail |
| `recommendations` | Long Text | Legacy single-call output (kept for backward compat) |

### Status flow

```
Submitted → Summary Ready → Roadmap Ready → Processed
                                 ↘ (always) → PDF generated → pdf_emailed = 1
```

`Processed` is the terminal success state. `get_sector_insights()` queries `WHERE status = 'Processed'`.

### If you add a new field

1. Add it via Desk → DocType → DPDP Assessment
2. Run from bench: `bench --site dpdp.projecttech4dev.org export-fixtures`
3. Commit the updated `fixtures/dpdp_assessment.json` to the repo

---

## Part 4 — Email setup

### Assessment report email

Sent automatically by `generate_and_attach_pdf` background job when PDF is ready. Uses the `DPDP Assessment Report` Email Template (stored as a fixture and editable in Desk → Email Template).

To edit the email template without a code deploy: Desk → Email Template → DPDP Assessment Report → edit → save.

### Consult request notification

Handled by a **Frappe Notification** configured directly in Desk:

Desk → Notification → New:
- Document Type: `DPDP Consult Request`
- Event: `New`
- Channel: `Email`
- Recipients: your internal email address
- Subject: `New Consult Request — {{ doc.org_name }}`
- Message: paste the HTML from `email_template_consult_internal.html`

This approach avoids SMTP issues that arise when `frappe.sendmail()` is called from a web request thread.

### Outgoing email account

Desk → Email Account → ensure one account has **Default Outgoing** checked. Both emails send from this account.

---

## Part 5 — Desk actions

### Viewing submissions

Desk → DPDP Tool → DPDP Assessment. Each record shows the full assessment with AI outputs, PDF attachment, and status.

### Regenerating a PDF or re-running AI

Open any DPDP Assessment record → Actions dropdown:
- **Regenerate PDF** — re-renders the PDF from stored AI content and re-emails. No Claude calls.
- **Re-run AI Analysis** — re-queues both Claude calls and regenerates the PDF. Overwrites existing AI content.

### Sector insights

`get_sector_insights()` returns average scores by sector for the dashboard. Requires at least one completed (`Processed`) assessment per sector to show data.

---

## Part 6 — Configuration: questions, scoring, glossary

Everything about the assessment — all 25 questions, 5 sections, scoring bands, glossary terms, references, and sector options — lives in one file:

```
dpdp_tool/public/dpdp-config.json
```

The JS fetches this on page load (cached in sessionStorage). The Python `api.py` reads it via `_get_config()` with a module-level cache.

To change a question, add a sector, update a glossary term, or adjust scoring bands: edit `dpdp-config.json` and push to `main`. No Python or HTML changes needed.

---

## Part 7 — Scoring reference

Scoring is defined in `dpdp-config.json` under `scoring.bands`:

| Score | Band |
|---|---|
| 46–50 | Strong Readiness |
| 36–45 | Moderate Readiness |
| 21–35 | Basic Readiness — Needs Work |
| 0–20 | High Risk — Not Ready |

Each question has three options: Yes (2pts), Partially (1pt), No (0pts). Maximum 50 points across 25 questions, 5 sections of 5 questions each.

---

## Part 8 — CI/CD workflow

```
feature/* branch
    → PR to main
    → merge to main
    → Frappe Cloud detects push
    → deploys in 2–4 minutes
```

| Change type | Auto-deploys | Notes |
|---|---|---|
| HTML (`www/`) | ✓ | On push |
| CSS/JS/config (`public/`) | ✓ | Assets rebuilt |
| `api.py`, `pdf_generator.py` | ✓ | Python reloaded on restart |
| DocType fields (fixtures) | ✓ | `bench migrate` runs on deploy |
| Site config (API keys) | Manual | Set in Frappe Cloud dashboard |
| Email Template content | Manual | Edit in Desk — no deploy needed |

---

## Part 9 — Local PDF testing

WeasyPrint requires system libraries not available on Mac by default.

```bash
brew install weasyprint
```

Then place `test_pdf.py`, `pdf_generator.py`, and `dpdp-config.json` in the same folder:

```bash
/opt/homebrew/Cellar/weasyprint/68.1/libexec/bin/python test_pdf.py
open output_test.pdf
```

`test_pdf.py` mocks the entire `frappe` module — no Frappe installation needed.

---

## Part 10 — Go-live checklist

**GitHub**
- [ ] Repository is private
- [ ] All files committed and pushed to `main`

**Frappe Cloud**
- [ ] Site created in India (Mumbai) region
- [ ] GitHub repo connected and app installed
- [ ] `anthropic_api_key` set in Site Config
- [ ] `dpdp_report_cc_email` set in Site Config
- [ ] Custom domain `dpdp.projecttech4dev.org` added with SSL verified

**Email**
- [ ] Default outgoing email account configured in Desk
- [ ] Test email sent successfully from Desk
- [ ] `DPDP Assessment Report` Email Template present in Desk
- [ ] Consult Notification configured in Desk (Frappe Notification)

**DocTypes**
- [ ] DPDP Assessment has all required fields (check `fixtures/dpdp_assessment.json`)
- [ ] DPDP Consult Request has all required fields
- [ ] Client Script "DPDP Assessment Actions" showing Actions dropdown on records

**Testing**
- [ ] Full 25-question assessment completed end-to-end
- [ ] Executive summary appears in Summary tab (~15 seconds)
- [ ] Roadmap appears in Roadmap tab (~60 seconds)
- [ ] PDF received by email
- [ ] PDF download button works on results page
- [ ] Consult form submits and team receives notification
- [ ] CI/CD: push a small change and confirm it deploys within 5 minutes

**Monitoring**
- [ ] Desk → Error Log shows no unexpected DPDP errors
- [ ] Anthropic API key has sufficient credits
