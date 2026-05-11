# DPDP Navigator — Complete Setup Guide
**Site:** `dpdp.projecttech4dev.org` | **App:** `dpdp_tool` | **Frappe Cloud**

---

## Overview

The DPDP Navigator runs as a custom Frappe app on a dedicated Frappe Cloud site. This guide covers everything from creating the GitHub repository through to a live, CI/CD-deployed site — so every code change pushed to `main` deploys automatically without manual file copying.

```
GitHub repo (dpdp_tool)
       │
       │  git push to main
       ▼
Frappe Cloud (auto-deploys)
       │
       ├── www/index.html         → dpdp.projecttech4dev.org/
       ├── www/assess.html        → dpdp.projecttech4dev.org/assess
       ├── public/css/dpdp.css    → /assets/dpdp_tool/css/dpdp.css
       ├── public/js/dpdp-index.js
       ├── public/js/dpdp-assess.js
       └── dpdp_tool/api.py       → /api/method/dpdp_tool.api.*
```

---

## PART 1 — GitHub Repository

### 1.1 Create the repo

Go to github.com → New repository:
- **Name:** `dpdp_tool`
- **Visibility:** Private (recommended — keeps your API integration private)
- **Initialise with:** README

### 1.2 Exact folder structure

The repo must match Frappe's expected app structure precisely. Create it as follows:

```
dpdp_tool/                          ← repo root
├── README.md
├── requirements.txt                ← Python dependencies
├── setup.py                        ← Frappe app manifest
├── MANIFEST.in
└── dpdp_tool/                      ← Python package (same name)
    ├── __init__.py
    ├── hooks.py                    ← App hooks
    ├── api.py                      ← All API methods
    ├── modules.txt
    ├── dpdp_tool/                  ← Module folder
    │   └── __init__.py
    ├── public/                     ← Static assets (auto-served by Frappe)
    │   ├── css/
    │   │   └── dpdp.css
    │   └── js/
    │       ├── dpdp-index.js
    │       └── dpdp-assess.js
    ├── www/                        ← Web pages (auto-routed by Frappe)
    │   ├── index.html              → served at /
    │   └── assess.html             → served at /assess
    └── fixtures/                   ← DocType definitions (exported JSON)
        ├── dpdp_assessment.json
        └── dpdp_consult_request.json
```

### 1.3 Required boilerplate files

**`setup.py`**
```python
from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

setup(
    name="dpdp_tool",
    version="1.0.0",
    description="DPDP Readiness Navigator — Tech4Dev",
    author="Tech4Dev",
    author_email="dpdp@projecttech4dev.org",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires
)
```

**`requirements.txt`**
```
anthropic>=0.20.0
```

**`MANIFEST.in`**
```
recursive-include dpdp_tool/public *
recursive-include dpdp_tool/www *
recursive-include dpdp_tool/fixtures *
```

**`dpdp_tool/__init__.py`**
```python
__version__ = "1.0.0"
```

**`dpdp_tool/modules.txt`**
```
DPDP Tool
```

**`dpdp_tool/hooks.py`**
```python
app_name      = "dpdp_tool"
app_title     = "DPDP Tool"
app_publisher = "Tech4Dev"
app_description = "DPDP Readiness Navigator"
app_version   = "1.0.0"
app_icon      = "octicon octicon-file-directory"
app_color     = "#1D6FB8"
app_email     = "dpdp@projecttech4dev.org"
app_license   = "MIT"

# Fixtures — DocType definitions exported as JSON
# Run `bench export-fixtures` to regenerate after DocType changes
fixtures = [
    {"dt": "DocType", "filters": [["name", "in", [
        "DPDP Assessment",
        "DPDP Consult Request"
    ]]]},
    {"dt": "Module Def", "filters": [["name", "in", ["DPDP Tool"]]]}
]
```

**`dpdp_tool/dpdp_tool/__init__.py`**
```python
# Module init
```

### 1.4 Place your working files

Copy the five project files into the repo at the exact paths below:

| File | Destination in repo |
|---|---|
| `api.py` | `dpdp_tool/api.py` |
| `dpdp.css` | `dpdp_tool/public/css/dpdp.css` |
| `dpdp-index.js` | `dpdp_tool/public/js/dpdp-index.js` |
| `dpdp-assess.js` | `dpdp_tool/public/js/dpdp-assess.js` |
| `index.html` | `dpdp_tool/www/index.html` |
| `assess.html` | `dpdp_tool/www/assess.html` |

### 1.5 Initial commit

```bash
git add .
git commit -m "Initial DPDP Navigator app"
git push origin main
```

---

## PART 2 — Frappe Cloud Site

### 2.1 Create the site

1. Log into [frappecloud.com](https://frappecloud.com)
2. **New Site** →
   - Region: **India (Mumbai)** — mandatory for DPDP data residency
   - Plan: Start with the smallest available (Micro or Basic)
   - Apps to install: **Frappe Framework only** — do not add ERPNext

### 2.2 Connect the GitHub repo

1. In Frappe Cloud → **Apps** tab → **Add App**
2. Select **GitHub** as the source
3. Authorise Frappe Cloud to access your GitHub account if prompted
4. Select the `dpdp_tool` repository
5. Branch: `main`
6. Click **Add App**

Frappe Cloud will now:
- Clone the repo
- Install it on your site automatically
- Install Python dependencies from `requirements.txt` (including `anthropic`)

### 2.3 Add the Claude API key

In Frappe Cloud → your site → **Site Config** tab → **Add Key**:

```
Key:   anthropic_api_key
Value: sk-ant-YOUR-ACTUAL-KEY-HERE
```

This is the **only** place the API key lives. It is read server-side via `frappe.conf.get("anthropic_api_key")` and never reaches the browser.

### 2.4 Add custom domain

1. Site → **Domains** tab → **Add Domain**
2. Enter: `dpdp.projecttech4dev.org`
3. Frappe Cloud shows you a CNAME record to add
4. Add it at your DNS provider (wherever `projecttech4dev.org` is registered)
5. Click **Verify** — SSL certificate issues automatically

---

## PART 3 — CI/CD with Frappe Cloud

### How it works

Once your GitHub repo is connected, Frappe Cloud listens for pushes to `main`. Every merge to `main` triggers an automatic deployment:

```
Developer pushes to main
         ↓
Frappe Cloud detects the push (via GitHub webhook)
         ↓
Pulls latest code from the repo
         ↓
Runs bench migrate (applies any DocType changes from fixtures)
         ↓
Rebuilds assets (CSS, JS from public/)
         ↓
Restarts the site
         ↓
Changes are live — typically 2–4 minutes
```

### Recommended branch strategy

```
main        ← production, auto-deploys to dpdp.projecttech4dev.org
develop     ← integration branch, test here before merging to main
feature/*   ← individual feature branches
```

A typical change workflow:
```bash
git checkout -b feature/update-question-3
# make changes
git add . && git commit -m "Update Q3 wording"
git push origin feature/update-question-3
# open a pull request to develop
# test on develop
# merge develop → main to deploy
```

### What auto-deploys vs what does not

| Change | Auto-deployed | Notes |
|---|---|---|
| HTML pages (`www/`) | ✓ Yes | Immediately on push |
| CSS/JS (`public/`) | ✓ Yes | Assets rebuilt automatically |
| `api.py` | ✓ Yes | Python reloaded on restart |
| DocType fields (via fixtures) | ✓ Yes | `bench migrate` runs automatically |
| New DocType (first time) | Manual once | Export fixture JSON first (see Part 5) |
| Site config (API key) | Manual | Set once in Frappe Cloud dashboard |
| Python dependencies (`requirements.txt`) | ✓ Yes | Reinstalled on deploy |

---

## PART 4 — DocTypes

DocTypes define the database tables where assessment data is stored. Create them once via the Frappe Desk UI, then export as JSON fixtures so future deploys apply them automatically.

### 4.1 Create DocType: `DPDP Assessment`

Frappe Desk → Search "DocType" → New

**Settings:**
- Name: `DPDP Assessment`
- Module: `DPDP Tool`
- Is Submittable: No
- Allow Guest to Create: No

**Fields — add in this exact order:**

| Label | Fieldname | Type | Notes |
|---|---|---|---|
| Organisation Name | org_name | Data | Required |
| Email | org_email | Data | Required |
| Contact Name | contact_name | Data | |
| Sector(s) | sector | Small Text | Multi-sector stored as comma-separated |
| Organisation Size | org_size | Select | |
| Beneficiary Groups | beneficiaries | Small Text | |
| Total Score | total_score | Float | |
| Score — Consent | score_consent | Float | |
| Score — Storage | score_storage | Float | |
| Score — Usage | score_usage | Float | |
| Score — Rights | score_rights | Float | |
| Score — Governance | score_governance | Float | |
| Raw Answers (JSON) | answers_json | Long Text | |
| AI Recommendations | recommendations | Long Text | |
| Status | status | Select | |
| Submitted On | submitted_on | Datetime | |

> **Why Small Text for Sector?** The sector field uses `Small Text` (not `Select`) because organisations can belong to multiple sectors simultaneously. The field stores comma-separated values like `"Education, Health & Nutrition"`. The API expands these when computing sector insights.

**Organisation Size options** (paste into Select field options, one per line):
```
Under 20 staff
20–100 staff
100–500 staff
500+ staff
```

**Status options:**
```
Submitted
Processed
Failed
```

Click **Save**.

---

### 4.2 Create DocType: `DPDP Consult Request`

Frappe Desk → DocType → New

**Settings:**
- Name: `DPDP Consult Request`
- Module: `DPDP Tool`
- Is Submittable: No

**Fields:**

| Label | Fieldname | Type | Notes |
|---|---|---|---|
| Organisation Name | org_name | Data | Required |
| Contact Name | contact_name | Data | Required |
| Email | email | Data | Required |
| Phone | phone | Data | |
| Sector(s) | sector | Small Text | Multi-sector |
| Organisation Size | org_size | Select | |
| Service Interest | service_interest | Select | |
| Message | message | Text | |
| Status | status | Select | |
| Submitted On | submitted_on | Datetime | |

**Service Interest options:**
```
Tier 1 — Self Assessment
Tier 2 — Light Advisory
Tier 3 — Deep Advisory
Not sure yet
```

**Status options:**
```
New
Contacted
Converted
```

Click **Save**.

---

### 4.3 Export DocTypes as fixtures (critical for CI/CD)

Once both DocTypes are created and saved, export them as JSON so they deploy automatically via `bench migrate` on every future push:

In the Frappe Desk console (Desk → Developer → Console):

```python
# Export both DocTypes as fixture JSON files
frappe.flags.in_install = True

import frappe.utils.fixtures as fu

# Export DPDP Assessment
with open('/home/frappe/frappe-bench/apps/dpdp_tool/dpdp_tool/fixtures/dpdp_assessment.json', 'w') as f:
    import json
    data = frappe.get_doc("DocType", "DPDP Assessment").as_dict()
    json.dump(data, f, indent=2, default=str)

print("Done")
```

Then from the bench terminal:

```bash
cd /home/frappe/frappe-bench
bench --site dpdp.projecttech4dev.org export-fixtures
```

This generates JSON files in `dpdp_tool/fixtures/`. Commit these to the repo:

```bash
git add dpdp_tool/fixtures/
git commit -m "Add DocType fixtures for DPDP Assessment and Consult Request"
git push origin main
```

From this point, any new site or fresh deploy will have the DocTypes automatically — no manual Desk setup needed.

---

## PART 5 — Multi-Sector Implementation

### How it works end-to-end

**In the browser (assess.html / index.html):**

The sector field renders as a multi-select checkbox group. The user can pick more than one:

```html
<!-- Replace the single <select> in the org-form with this -->
<div class="if-group">
  <label>Sector(s) *</label>
  <div class="sector-checkboxes" id="sector-checkboxes">
    <label class="sector-cb"><input type="checkbox" value="Health &amp; Nutrition"> Health &amp; Nutrition</label>
    <label class="sector-cb"><input type="checkbox" value="Education"> Education</label>
    <label class="sector-cb"><input type="checkbox" value="Livelihoods"> Livelihoods</label>
    <label class="sector-cb"><input type="checkbox" value="Gender &amp; SRHR"> Gender &amp; SRHR</label>
    <label class="sector-cb"><input type="checkbox" value="Environment"> Environment</label>
    <label class="sector-cb"><input type="checkbox" value="Disability"> Disability</label>
    <label class="sector-cb"><input type="checkbox" value="Humanitarian"> Humanitarian</label>
    <label class="sector-cb"><input type="checkbox" value="Governance"> Governance</label>
    <label class="sector-cb"><input type="checkbox" value="Other"> Other</label>
  </div>
</div>
```

Add this CSS to `dpdp.css`:
```css
.sector-checkboxes{display:grid;grid-template-columns:1fr 1fr;gap:.4rem .75rem;margin-top:.25rem}
.sector-cb{display:flex;align-items:center;gap:7px;font-size:.84rem;color:var(--ink);cursor:pointer;padding:4px 0}
.sector-cb input[type=checkbox]{width:15px;height:15px;accent-color:var(--blue);flex-shrink:0;cursor:pointer}
```

**In `dpdp-assess.js` — update `startAssessment()`:**

```javascript
// Replace the single select read with:
function getSelectedSectors() {
  const checked = document.querySelectorAll('#sector-checkboxes input:checked');
  return Array.from(checked).map(cb => cb.value);
}

function startAssessment() {
  const o   = document.getElementById('i-org').value.trim();
  const n   = document.getElementById('i-name').value.trim();
  const e   = document.getElementById('i-email').value.trim();
  const sc  = getSelectedSectors();
  const sz  = document.getElementById('i-size').value;

  if (!o || !n || !e || sc.length === 0 || !sz) {
    alert('Please fill in all required fields and select at least one sector.');
    return;
  }
  org = { org: o, name: n, email: e, sector: sc, size: sz,
          bene: document.getElementById('i-bene').value.trim() };
  // ... rest of startAssessment unchanged
}
```

**Sending to Frappe API — sectors as JSON array:**

```javascript
// In storeInFrappe() — sector sent as JSON-stringified array:
body: JSON.stringify({
  org_name:  org.org,
  sector:    JSON.stringify(org.sector),  // ["Education","Health & Nutrition"]
  // ... other fields
})

// In fetchReco() — same:
section_scores: { consent: secScores[0], ... },
sector: JSON.stringify(org.sector),
```

**In Frappe `api.py` — `_parse_sectors()` handles the array:**

The helper function already handles JSON arrays, comma-separated strings, and plain strings:

```python
def _parse_sectors(sector_raw):
    # ["Education", "Health & Nutrition"]  →  "Education, Health & Nutrition"
    # "Education, Health & Nutrition"      →  "Education, Health & Nutrition"
    # "Education"                          →  "Education"
```

**In the database:**

Stored as `"Education, Health & Nutrition"` in the `sector` field.

**In `get_sector_insights()`:**

Each assessment is expanded to contribute to every sector it lists:

```python
for row in rows:
    # "Education, Health & Nutrition" → ["Education", "Health & Nutrition"]
    for sec in [s.strip() for s in (row.sector or "").split(",")]:
        if sec in KNOWN_SECTORS:
            buckets[sec].append(row)
```

So an organisation working in both Education and Health appears in both sectors' averages — which is the correct behaviour for cross-sector NGOs.

---

## PART 6 — Verify After Deployment

### 6.1 Test API methods in Frappe console

Desk → Developer → Bench Console:

```python
# Test 1: Store assessment with multi-sector input
result = frappe.call("dpdp_tool.api.store_assessment",
    org_name="Test NGO",
    org_email="test@test.org",
    contact_name="Test User",
    sector='["Education", "Health & Nutrition"]',   # JSON array
    org_size="20-100 staff",
    beneficiaries="children, women",
    total_score=32,
    score_consent=5, score_storage=6, score_usage=7,
    score_rights=8, score_governance=6,
    answers_json="[]"
)
print(result)
# Expected: {"status": "ok", "docname": "DPDP-ASSESS-00001"}

# Verify sector was stored correctly
doc = frappe.get_doc("DPDP Assessment", result["docname"])
print(doc.sector)
# Expected: "Education, Health & Nutrition"
```

```python
# Test 2: Claude call (uses your API key)
result = frappe.call("dpdp_tool.api.get_recommendations",
    org_name="Test NGO",
    sector='["Education", "Health & Nutrition"]',
    org_size="20-100 staff",
    beneficiaries="children",
    total_score=32, max_score=50,
    section_scores={"consent":5,"storage":6,"usage":7,"rights":8,"governance":6},
    answers="Q1: Yes\nQ2: Partially\nQ3: No"
)
print(result["status"])            # "ok" or "fallback"
print(result["recommendations"][:400])
```

```python
# Test 3: Sector insights (empty until 3+ submissions per sector)
data = frappe.call("dpdp_tool.api.get_sector_insights")
print(data)
# After 3+ test submissions to "Education": shows Education stats
```

```python
# Test 4: Consult request
result = frappe.call("dpdp_tool.api.submit_consult_request",
    org_name="Test NGO",
    contact_name="Test User",
    email="test@test.org",
    sector='["Education"]',
    service_interest="Tier 2 - Light Advisory"
)
print(result)
# Expected: {"status": "ok"}
```

### 6.2 Full user journey test

1. Visit `https://dpdp.projecttech4dev.org` — landing page loads
2. Dashboard shows demo data (real data appears after 3+ submissions per sector)
3. Click "Begin Self-Assessment" → `/assess` opens
4. Fill org profile — select **multiple sectors** using checkboxes
5. Answer all 25 questions
6. Click Submit → section score cards render **instantly** (client-side)
7. Loading animation appears (~8–15 seconds) while Frappe calls Claude
8. Recommendations render on screen
9. "Download PDF Report" activates → PDF downloads in browser
10. Frappe Desk → DPDP Tool → DPDP Assessment → record shows `sector` as comma-separated values
11. Submit consult form → record appears in DPDP Consult Request with status "New"

### 6.3 Verify CI/CD is working

Make a small, visible change — for example, update the hero sub-copy in `index.html`:

```bash
# On your machine
git checkout -b test/cicd-check
# Edit dpdp_tool/www/index.html — change one word
git add dpdp_tool/www/index.html
git commit -m "Test CI/CD deployment"
git push origin test/cicd-check
# Open a PR to main and merge it
```

Go to Frappe Cloud → your site → **Deployments** tab. You should see a new deployment triggered within seconds. When it completes (2–4 minutes), visit the site and confirm your change is live.

---

## PART 7 — Scoring Reference

| Answer | Points |
|---|---|
| Yes | 2 |
| Partially | 1 |
| No / Not Sure | 0 |

**Maximum score: 50** (25 questions × 2 pts, 5 questions × 2 pts per section)

| Score | Band |
|---|---|
| 0–20 | High Risk — Not Ready |
| 21–35 | Basic Readiness — Needs Work |
| 36–45 | Moderate Readiness |
| 46–50 | Strong Readiness |

**5 sections, 10 pts each:**

| # | Section | Questions |
|---|---|---|
| 1 | Data Collection & Consent | Q1–5 |
| 2 | Data Storage & Security | Q6–10 |
| 3 | Data Usage & Sharing | Q11–15 |
| 4 | Rights of Individuals | Q16–20 |
| 5 | Governance & Processes | Q21–25 |

---

## PART 8 — Rate Limiting

| Method | Limit | Window | Reason |
|---|---|---|---|
| `get_recommendations` | 10/IP | 1 hour | Prevents Claude API cost abuse |
| `store_assessment` | 10/IP | 1 hour | Matches recommendation limit |
| `submit_consult_request` | 5/IP | 1 hour | Prevents form spam |
| `get_sector_insights` | Unlimited | — | Read-only, low cost |

---

## PART 9 — Making Changes After Go-Live

### Updating questions or copy
Edit the relevant file → commit to a feature branch → PR to `main` → auto-deploys.

```bash
# Example: update Q3 wording
git checkout -b fix/q3-wording
# Edit dpdp_tool/public/js/dpdp-assess.js
git add . && git commit -m "Clarify Q3 wording"
git push origin fix/q3-wording
# PR → main → auto-deploy
```

### Adding a DocType field
1. Add the field via Frappe Desk on the live site
2. Run `bench --site dpdp.projecttech4dev.org export-fixtures`
3. Commit the updated fixture JSON to the repo
4. All future deploys will include the new field automatically

### Updating the API key
Frappe Cloud → Site → Site Config → edit `anthropic_api_key`. No deploy needed.

### Monitoring errors
Frappe Desk → Error Log — all `frappe.log_error()` calls from `api.py` appear here. Filter by title "DPDP API" to see only DPDP-related errors.

---

## PART 10 — Go-Live Checklist

**GitHub**
- [ ] `dpdp_tool` repo created (private)
- [ ] All boilerplate files in place (`setup.py`, `hooks.py`, `requirements.txt`, `MANIFEST.in`)
- [ ] All 5 project files placed at correct paths
- [ ] Initial commit pushed to `main`

**Frappe Cloud**
- [ ] New site created — region: India (Mumbai)
- [ ] GitHub repo connected via Apps tab
- [ ] `dpdp_tool` app installed and showing as active
- [ ] `anthropic_api_key` added to Site Config
- [ ] Custom domain `dpdp.projecttech4dev.org` verified with SSL

**DocTypes**
- [ ] `DPDP Assessment` created with all fields (sector as Small Text)
- [ ] `DPDP Consult Request` created with all fields
- [ ] Both exported as fixtures and committed to repo
- [ ] `bench migrate` confirmed fixtures apply on deploy

**Multi-sector**
- [ ] Sector checkboxes rendering in org profile form
- [ ] Multi-sector selection sends JSON array to API
- [ ] `_parse_sectors()` correctly converts array to comma-separated string
- [ ] Stored records show comma-separated sectors in Frappe Desk
- [ ] `get_sector_insights()` correctly expands multi-sector records into per-sector buckets

**Testing**
- [ ] All 4 API methods tested via Frappe console
- [ ] Full 25-question flow completed end-to-end
- [ ] Multi-sector selection tested — org appears in multiple sector dashboard tabs
- [ ] PDF generated and checked
- [ ] Consult form submits successfully

**CI/CD**
- [ ] Test change pushed → deployment triggered in Frappe Cloud
- [ ] Change visible on site within 5 minutes of merge to `main`

**Final**
- [ ] `projecttech4dev.org` WordPress page updated to link to `dpdp.projecttech4dev.org`
- [ ] Team briefed on Frappe Desk for viewing submissions and consult requests
