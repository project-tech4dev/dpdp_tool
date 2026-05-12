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

@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
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
            model="claude-sonnet-4-6",
            max_tokens=10000,
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

    return f"""You are a senior DPDP Act 2023 compliance advisor specialising exclusively in Indian NGOs and social sector organisations. You have deep knowledge of:
- The Digital Personal Data Protection Act 2023 and DPDP Rules 2025
- How small and mid-sized NGOs actually operate in India — stretched staff, multiple funders, field programmes, government partnerships
- The specific data risks that arise in each social sector (health, education, livelihoods, gender/SRHR, humanitarian, disability)
- The Data Protection Board of India's enforcement priorities and penalty schedule
 
You are reviewing a self-assessment submitted by a {org_size} organisation working in **{sector}**, with primary beneficiaries: **{beneficiaries or "not specified"}**.
 
ASSESSMENT RESULTS
Overall score: {total_score}/{max_score} points
 
Section scores (each out of 10, scored across 5 questions at 2 pts each):
{sec_lines}
 
Priority order for this organisation: (lowest scores first)
 
INDIVIDUAL QUESTION RESPONSES
{answers}
 
YOUR TASK
Produce a substantive, personalised compliance roadmap. This document will be read by the organisation's leadership — it must be specific enough to act on without any additional guidance.
 
CRITICAL INSTRUCTIONS
1. Be specific to THIS organisation — reference their sector(s), size, and beneficiary profile throughout. Generic advice is not acceptable.
2. For beneficiaries involving children (under 18), explicitly address Section 9 obligations in every relevant action.
3. Where the organisation works across multiple sectors, name the specific data risk for each sector separately — do not bundle them.
4. Name realistic roles for a {org_size} NGO (e.g. for under 20 staff: ED, Programme Lead, Admin/Finance Officer, Field Coordinator — not abstract titles like "DPO").
5. Every action must explain WHY it matters with a specific DPDP Act section or Rule number and the exact penalty range.
6. The HOW must be detailed enough that someone with no legal background can start tomorrow — include what to write, who to call, what tool to use, what the output looks like.
7. Flag explicitly where completing one action satisfies multiple DPDP obligations.
8. Prioritise the two lowest-scoring sections.
9. Tone: direct, supportive, non-judgmental. These organisations are trying to do right by their communities.
 
FORMAT — use exactly these headings, in this order:
 
## Executive Summary
4–5 sentences. State the overall score and what it means in plain language. Name the two most critical gaps specific to their sector and beneficiary profile. Explain what the real-world risk is if these gaps are not addressed (not just the legal penalty — the actual harm to beneficiaries). Close with an honest, realistic sentence on the effort required.
 
## What Your Scores Tell Us
A short paragraph (4–6 sentences) interpreting the pattern of scores — what the combination of high and low scores reveals about this organisation's current state. Be analytical: what did they get right, what has been neglected, and why might that be given their sector and size? This gives leadership a diagnostic frame before the action list.
 
## 30-Day Priority Actions
Start with the two lowest-scoring sections. 4–5 items total. For each:
 
**[Specific task name — not generic]**
- **Who:** [Specific role for a {org_size} NGO]
- **Why this cannot wait:** [Exact DPDP Act section + penalty amount + specific real-world consequence for their beneficiaries if this fails]
- **How:** [3–4 sentences of step-by-step practical guidance. Name specific tools, documents, or processes. Include what the finished output looks like.]
- **Covers multiple gaps:** [Only include this line if true — name which other obligations this action satisfies]
 
## 90-Day Compliance Foundation
5 items that build on the 30-day actions. For each:
 
**[Specific task name]**
- **Who leads:** [Role]
- **Why this matters:** [DPDP Act section + consequence specific to their sector]
- **How:** [3–4 sentences of practical guidance with concrete steps]
- **Done when:** [Specific, tangible deliverable — a signed document, a completed spreadsheet, a trained staff group, not vague milestones]
 
## 1-Year Compliance Habits
4 items — each must be attached to an existing organisational moment (annual board meeting, staff retreat, programme review, funder report, contract renewal). These are recurring practices, not one-time tasks.
 
**[Task name]**
- **When:** [Specific existing moment in the organisation's calendar]
- **Who:** [Role]
- **Why:** [One sentence on what degrades if this lapses]
- **What to do:** [2–3 sentences of specific annual action]
 
## Key Data Risks for {sector} Organisations
Three risks specific to this organisation's sector(s) and beneficiary profile. For each, go beyond naming the risk — explain the realistic scenario in which it manifests for an organisation like this one.
 
**[Risk name]**
- **The scenario:** [2–3 sentences describing exactly how this risk arises in practice for a {org_size} {sector} organisation — name the specific programme activity, tool, or process where the breach could occur]
- **DPDP Act provision:** [Section and Rule number]
- **Penalty:** [Exact penalty range]
- **What makes this sector particularly exposed:** [One sentence on why {sector} organisations face heightened risk on this specific issue compared to other NGOs]"""


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
- Why urgent: The DPDP Act holds Data Fiduciaries accountable (Section 8). Without a named owner no compliance work can proceed.
- How: Name a person, document their mandate in a one-page terms of reference, share with the board at the next meeting.

**Audit your consent forms**
- Who: Programme Manager
- Why urgent: Invalid consent is a direct DPDP violation (Section 6). Penalties up to Rs.250 crore apply.
- How: Check every form against four elements: purpose, retention period, rights explained, contact details. Update the three most-used forms first.

**Create a basic data inventory**
- Who: Programme Manager + IT person
- Why urgent: You cannot protect data you have not mapped.
- How: One spreadsheet row per data type: what it is, where stored, who has access, how long kept.

## 90-Day Compliance Foundation

**Draft a Data Protection Policy** -- ED .  Done when: approved 1-page policy shared with all staff

**Train staff on DPDP basics** -- Programme Head .  Done when: session held and documented

**Sign DPAs with key vendors** -- ED/Finance Head .  Done when: signed agreements filed for top 3 processors

**Establish a grievance mechanism** -- Programme Manager .  Done when: named email and response protocol documented

**Document a breach response procedure** -- ED/Programme Manager . Done when: one-page checklist exists

## 1-Year Habits

**Annual compliance review** -- When: AGM . Who: ED . 

**Consent form refresh** -- When: New programme launch . Who: Programme Manager . 

**Staff DPDP refresher** -- When: Annual staff retreat . Who: HR/Programme Head . 

**Vendor DPA check** -- When: Contract renewals . Who: Finance/ED . 

## Key Risk Areas

Connect with a Tech4Dev DPDP Advisor for a sector-specific implementation plan."""


# ─────────────────────────────────────────────────────────────────
# METHOD 2 — store_assessment
# ─────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
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

@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
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

@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
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
