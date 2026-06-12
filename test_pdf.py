"""
Standalone PDF test script — no Frappe required.
Run from the same folder as pdf_generator.py and dpdp-config.json.

Install deps:
    pip install weasyprint

Run:
    python test_pdf.py
    open output_test.pdf
"""

import sys, json, types, datetime

# ── Mock Frappe ────────────────────────────────────────────────────
frappe = types.ModuleType('frappe')
frappe.utils = types.SimpleNamespace(
    formatdate = lambda d, fmt: datetime.date.today().strftime('%d %B %Y'),
    today      = lambda: str(datetime.date.today()),
    get_url    = lambda: 'https://dpdp.projecttech4dev.org',
)
frappe.log_error = lambda *a, **k: print('[frappe.log_error]', a[0][:80] if a else '')
frappe.logger    = lambda *a: types.SimpleNamespace(info=lambda *x: None, warning=lambda *x: None)
sys.modules['frappe'] = frappe

# ── Mock doc ───────────────────────────────────────────────────────
doc = types.SimpleNamespace(
    org_name         = 'Test Organisation',
    org_email        = 'test@example.org',
    contact_name     = 'Test User',
    sector           = 'Education, Health & Nutrition',
    org_size         = '20-100 staff',
    beneficiaries    = 'Children and women in rural communities',
    total_score      = 24,
    score_consent    = 4,
    score_storage    = 6,
    score_usage      = 5,
    score_rights     = 4,
    score_governance = 5,
    executive_summary = """## What Your Score Tells You
Your score of 24/50 indicates Basic Readiness. Data Collection & Consent and Rights of Individuals are your two lowest-scoring sections and require immediate attention.

## Sector and Beneficiary Risks
- **Children's data** under Section 9 requires verifiable guardian consent before collection
- **Health data** collected during programme delivery is sensitive personal data under Draft DPDP Rules — heightened protection required
- **Rural beneficiaries** may lack awareness of their data rights — grievance mechanisms must be accessible in local languages

## Priority Areas
| Address Now | Plan & Improve | Monitor |
|---|---|---|
| Data Collection & Consent | Data Usage & Sharing | Data Storage & Security |
| Rights of Individuals | Governance & Processes | |

## One Action This Week
Appoint a named data protection contact and document their mandate in a one-page terms of reference — share with the board by Friday.""",

    action_roadmap = """## 30-Day Priority Actions

**Designate a data protection owner**
- Who: Executive Director or Senior Programme Manager
- Why: Section 8 accountability for repeated violations
- How: One-page terms of reference, share with board

**Audit all consent forms used in field programmes**
- Who: Programme Manager
- Why: Section 6 — invalid consent is a direct DPDP violation
- How: Check each form for purpose, retention, rights, and contact details

## 90-Day Compliance Foundation

**Draft a Data Protection Policy**
- Who leads: Executive Director
- Why: Section 8 accountability and funder trust
- Done when: Board-approved policy shared with all staff

**Train field staff on DPDP basics**
- Who leads: Programme Head
- Done when: Session held and attendance documented

## 365-Day / 1-Year Actions

**Annual compliance review**
- When: Annual board meeting
- Who: ED + data protection owner

**Consent form refresh on each new programme launch**
- When: Programme design phase
- Who: Programme Manager

## Summary Table
| Action | Timeline | Owner | Why It Matters |
|---|---|---|---|
| Designate data protection owner | 30 days | ED | Section 8 accountability |
| Audit consent forms | 30 days | Programme Manager | Section 6 compliance |
| Data Protection Policy | 90 days | ED | Accountability and funder trust |
| Staff training | 90 days | Programme Head | Reduces breach risk |
| Annual compliance review | 365 days | ED | Sustained compliance |

Further reading: https://www.dpdpa.com/blogs/DPDPA_Implementation_Timeline.html""",

    answers_json = json.dumps([
        {"q": i+1, "section": ["Data Collection & Consent","Data Storage & Security","Data Usage & Sharing","Rights of Individuals","Governance & Processes"][i//5],
         "text": f"Test question {i+1}", "why": f"Why this matters for question {i+1}.",
         "answer_idx": [0,1,2][i%3], "answer_label": ["Yes","Partially","No"][i%3], "points": [2,1,0][i%3]}
        for i in range(25)
    ]),
)

# ── Load config ────────────────────────────────────────────────────
try:
    with open('dpdp-config.json') as f:
        cfg = json.load(f)
    print('✓ Config loaded')
except FileNotFoundError:
    print('✗ dpdp-config.json not found — place it in the same folder as this script')
    sys.exit(1)

# ── Import pdf_generator ───────────────────────────────────────────
try:
    import importlib.util, pathlib
    spec = importlib.util.spec_from_file_location('pdf_generator', 'pdf_generator.py')
    pg   = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pg)
    print('✓ pdf_generator imported')
except Exception as e:
    print(f'✗ Failed to import pdf_generator: {e}')
    sys.exit(1)

# ── Generate PDF ───────────────────────────────────────────────────
try:
    print('Generating PDF...')
    pdf_bytes = pg.generate_assessment_pdf(doc, cfg)
    out = 'output_test.pdf'
    with open(out, 'wb') as f:
        f.write(pdf_bytes)
    print(f'✓ PDF written: {out} ({len(pdf_bytes):,} bytes)')
    print(f'  Open with: open {out}')
except Exception as e:
    import traceback
    print(f'✗ PDF generation failed:')
    traceback.print_exc()
