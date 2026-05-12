"""
DPDP Navigator — Frappe API
Tech4Dev · dpdp.projecttech4dev.org
File: dpdp_tool/dpdp_tool/api.py

Four whitelisted methods:
  1. get_recommendations  — calls Claude, returns roadmap
  2. store_assessment     — saves completed assessment to DocType
  3. get_sector_insights  — aggregates scores by sector for dashboard
  4. submit_consult_request — saves consult enquiry to DocType
"""

import frappe
import json
from datetime import datetime


# ─────────────────────────────────────────────────────────────────
# HELPER — normalise sector input (single string or JSON array)
# Browser sends sectors as JSON array: ["Education","Health & Nutrition"]
# We store as comma-separated string for Frappe compatibility.
# ─────────────────────────────────────────────────────────────────

def _parse_sectors(sector_raw):
    """Return a clean comma-separated sector string from any input format."""
    if not sector_raw:
        return ""
    if isinstance(sector_raw, list):
        return ", ".join(s.strip() for s in sector_raw if s.strip())
    if isinstance(sector_raw, str):
        try:
            parsed = json.loads(sector_raw)
            if isinstance(parsed, list):
                return ", ".join(s.strip() for s in parsed if s.strip())
        except (json.JSONDecodeError, ValueError):
            pass
        return sector_raw.strip()
    return str(sector_raw).strip()


# ─────────────────────────────────────────────────────────────────
# METHOD 1 — get_recommendations
# ─────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
@frappe.rate_limit(key="ip", limit=10, seconds=3600)
def get_recommendations(org_name, sector, org_size, beneficiaries,
                        total_score, max_score, section_scores, answers):
    try:
        import anthropic

        api_key = frappe.conf.get("anthropic_api_key")
        if not api_key:
            frappe.throw("API configuration missing. Contact administrator.")

        if isinstance(section_scores, str):
            section_scores = json.loads(section_scores)

        sector_str = _parse_sectors(sector)

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            messages=[{"role": "user", "content": _build_prompt(
                org_name, sector_str, org_size, beneficiaries,
                int(float(total_score)), int(float(max_score)),
                section_scores, answers
            )}]
        )
        recommendations = response.content[0].text
        return {"recommendations": recommendations, "status": "ok"}

    except Exception as e:
        frappe.log_error(f"DPDP recommendation error: {e}", "DPDP API")
        return {
            "recommendations": _fallback(section_scores, total_score),
            "status": "fallback"
        }


def _build_prompt(org_name, sector, org_size, beneficiaries,
                  total_score, max_score, section_scores, answers):

    sec_lines = "\n".join([
        f"- Data Collection & Consent:  {section_scores.get('consent', 0)}/10",
        f"- Data Storage & Security:    {section_scores.get('storage', 0)}/10",
        f"- Data Usage & Sharing:       {section_scores.get('usage', 0)}/10",
        f"- Rights of Individuals:      {section_scores.get('rights', 0)}/10",
        f"- Governance & Processes:     {section_scores.get('governance', 0)}/10",
    ])

    return f"""You are a DPDP Act 2023 compliance advisor for Indian NGOs and social sector organisations.

ORGANISATION
- Sector(s): {sector}
- Size: {org_size}
- Beneficiaries: {beneficiaries or "Not specified"}
- Overall score: {total_score}/{max_score}

SECTION SCORES (each out of 10 — 5 questions x 2 pts)
{sec_lines}

ASSESSMENT RESPONSES
{answers}

INSTRUCTIONS
- Staff are stretched. Every action must be concrete and time-boxed.
- Name who in the NGO would own each task based on the size and sector.
- Reference specific DPDP Act sections and penalties to convey urgency.
- Where the organisation works across multiple sectors, note sector-specific data risks for each.
- Where the organisation works across beneficiaries (e.g. children), note sector-specific data risks for each.
- Flag where one action covers multiple compliance gaps.
- Prioritise the lowest-scoring sections first.

FORMAT (use exactly these headings):

## Executive Summary
3-4 sentences. State score, name the two biggest risks given their sector(s) and beneficiary profile, honest sentence on realistic effort.

## 30-Day Priority Actions
4-5 items. For each:
**[Task name]**
- Who: [Role in small/mid NGO]
- Time: [Realistic hours]
- Why urgent: [DPDP section + penalty]
- How: [2-3 sentences of specific, actionable guidance]

## 90-Day Compliance Foundation
5 items. For each:
**[Task name]**
- Who leads: [Role]
- Effort: [Hours]
- Done when: [Concrete deliverable]

## 1-Year Habits
4 items attached to existing calendar moments.
**[Task name]** -- When: [Existing moment] . Who: [Role] . Time: [e.g. 1 hour/year]

## Key Risk Areas for {sector} Organisations
Three specific data risks for these sector(s), each with DPDP Act provision and realistic consequence."""


def _fallback(section_scores, total_score):
    if isinstance(section_scores, str):
        try:
            section_scores = json.loads(section_scores)
        except Exception:
            section_scores = {}

    gaps = sorted(section_scores.items(), key=lambda x: x[1] or 0)[:2]
    gap_names = [g[0].replace("_", " ").title() for g in gaps]

    return f"""(Note: Fallback sumamry due to Ai failure) 
    
## Executive Summary

Your organisation scored **{total_score}/50** on the DPDP Act 2023 readiness assessment. The most significant gaps are in **{", ".join(gap_names)}**. With structured effort of roughly one half-day per month, meaningful compliance progress is achievable within 90 days.

## 30-Day Priority Actions

**Designate a data protection owner**
- Who: Executive Director or Senior Programme Manager
- Time: 2 hours
- Why urgent: The DPDP Act holds Data Fiduciaries accountable (Section 8). Without a named owner no compliance work can proceed.
- How: Name a person, document their mandate in a one-page terms of reference, share with the board at the next meeting.

**Audit your consent forms**
- Who: Programme Manager
- Time: 3 hours
- Why urgent: Invalid consent is a direct DPDP violation (Section 6). Penalties up to Rs.250 crore apply.
- How: Check every form against four elements: purpose, retention period, rights explained, contact details. Update the three most-used forms first.

**Create a basic data inventory**
- Who: Programme Manager + IT person
- Time: 3-4 hours
- Why urgent: You cannot protect data you have not mapped.
- How: One spreadsheet row per data type: what it is, where stored, who has access, how long kept.

## 90-Day Compliance Foundation

**Draft a Data Protection Policy** -- ED . 4-6 hours . Done when: approved 1-page policy shared with all staff

**Train staff on DPDP basics** -- Programme Head . 2 hours . Done when: session held and documented

**Sign DPAs with key vendors** -- ED/Finance . 2 hours per vendor . Done when: signed agreements filed for top 3 processors

**Establish a grievance mechanism** -- Programme Manager . 1 hour . Done when: named email and response protocol documented

**Document a breach response procedure** -- ED . 2 hours . Done when: one-page checklist exists

## 1-Year Habits

**Annual compliance review** -- When: AGM . Who: ED . Time: 1 hour/year

**Consent form refresh** -- When: New programme launch . Who: Programme Manager . Time: 2 hours

**Staff DPDP refresher** -- When: Annual staff retreat . Who: HR/Programme Head . Time: 1 hour

**Vendor DPA check** -- When: Contract renewals . Who: Finance/ED . Time: 1 hour per vendor

## Key Risk Areas

Connect with a Tech4Dev DPDP Advisor for a sector-specific implementation plan."""


# ─────────────────────────────────────────────────────────────────
# METHOD 2 — store_assessment
# ─────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
@frappe.rate_limit(key="ip", limit=10, seconds=3600)
def store_assessment(org_name, org_email, contact_name, sector, org_size,
                     beneficiaries, total_score, score_consent, score_storage,
                     score_usage, score_rights, score_governance,
                     answers_json, recommendations=""):
    try:
        if not org_name or not org_email:
            return {"status": "error", "message": "Missing required fields"}

        doc = frappe.new_doc("DPDP Assessment")
        doc.org_name         = org_name
        doc.org_email        = org_email
        doc.contact_name     = contact_name
        doc.sector           = _parse_sectors(sector)
        doc.org_size         = org_size
        doc.beneficiaries    = beneficiaries
        doc.total_score      = float(total_score or 0)
        doc.score_consent    = float(score_consent or 0)
        doc.score_storage    = float(score_storage or 0)
        doc.score_usage      = float(score_usage or 0)
        doc.score_rights     = float(score_rights or 0)
        doc.score_governance = float(score_governance or 0)
        doc.answers_json     = answers_json
        doc.recommendations  = recommendations
        doc.status           = "Processed"
        doc.submitted_on     = datetime.now()
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        return {"status": "ok", "docname": doc.name}

    except Exception as e:
        frappe.log_error(f"DPDP store error: {e}", "DPDP API")
        return {"status": "error"}


# ─────────────────────────────────────────────────────────────────
# METHOD 3 — get_sector_insights
# Multi-sector orgs contribute to each sector they listed.
# ─────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def get_sector_insights():
    try:
        rows = frappe.db.sql("""
            SELECT sector, total_score, score_consent, score_storage,
                   score_usage, score_rights, score_governance
            FROM `tabDPDP Assessment`
            WHERE status = 'Processed'
              AND sector IS NOT NULL AND sector != ''
        """, as_dict=True)

        KNOWN_SECTORS = [
            "Health & Nutrition", "Education", "Livelihoods",
            "Gender & SRHR", "Environment", "Disability",
            "Humanitarian", "Governance", "Other"
        ]

        from collections import defaultdict
        buckets = defaultdict(list)

        for row in rows:
            for sec in [s.strip() for s in (row.sector or "").split(",")]:
                if sec in KNOWN_SECTORS:
                    buckets[sec].append(row)

        results = []
        for sector, entries in buckets.items():
            if len(entries) < 3:
                continue

            def avg(field):
                vals = [e[field] for e in entries if e.get(field) is not None]
                return round(sum(vals) / len(vals), 1) if vals else 0

            results.append({
                "sector":           sector,
                "submission_count": len(entries),
                "avg_overall":      avg("total_score"),
                "avg_consent":      avg("score_consent"),
                "avg_storage":      avg("score_storage"),
                "avg_usage":        avg("score_usage"),
                "avg_rights":       avg("score_rights"),
                "avg_governance":   avg("score_governance"),
            })

        results.sort(key=lambda x: x["submission_count"], reverse=True)
        return results

    except Exception as e:
        frappe.log_error(f"DPDP insights error: {e}", "DPDP API")
        return []


# ─────────────────────────────────────────────────────────────────
# METHOD 4 — submit_consult_request
# ─────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
@frappe.rate_limit(key="ip", limit=5, seconds=3600)
def submit_consult_request(org_name, contact_name, email,
                           sector="", org_size="", service_interest="",
                           message="", phone=""):
    try:
        if not org_name or not contact_name or not email:
            frappe.throw("Organisation name, contact name, and email are required.")

        doc = frappe.new_doc("DPDP Consult Request")
        doc.org_name         = org_name
        doc.contact_name     = contact_name
        doc.email            = email
        doc.phone            = phone
        doc.sector           = _parse_sectors(sector)
        doc.org_size         = org_size
        doc.service_interest = service_interest
        doc.message          = message
        doc.status           = "New"
        doc.submitted_on     = datetime.now()
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        # Uncomment to notify your team by email:
        # frappe.sendmail(
        #     recipients=["dpdp@projecttech4dev.org"],
        #     subject=f"New DPDP Consult -- {org_name}",
        #     message=(
        #         f"From: {contact_name} ({email})<br>"
        #         f"Sector(s): {_parse_sectors(sector)}<br>"
        #         f"Service: {service_interest}<br>"
        #         f"Message: {message}"
        #     )
        # )

        return {"status": "ok"}

    except Exception as e:
        frappe.log_error(f"DPDP consult error: {e}", "DPDP API")
        return {"status": "error", "message": str(e)}
