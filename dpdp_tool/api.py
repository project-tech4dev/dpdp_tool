"""
DPDP Navigator — Frappe API
Tech4Dev · dpdp.projecttech4dev.org
File: dpdp_tool/api.py

Methods:
  Existing (unchanged):
    get_recommendations   — single-call Claude roadmap (legacy/fallback)
    check_reco            — polls for recommendations field
    store_assessment      — saves assessment; NOW also enqueues 2-call AI jobs
    patch_assessment_reco — patches recommendations onto existing doc
    get_sector_insights   — aggregates scores by sector for dashboard
    submit_consult_request — saves consult enquiry

  New (2-call architecture):
    poll_status           — polls executive_summary, action_roadmap, pdf_file
    run_summary_call      — background job: Call 1, executive summary
    run_roadmap_call      — background job: Call 2, action roadmap
    generate_and_attach_pdf — background job: PDF + email
"""

import frappe
import json
from datetime import datetime


# ─────────────────────────────────────────────────────────────────
# HELPERS
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


def _validate_origin():
    """Reject requests not originating from the DPDP site."""
    allowed = [
        "https://dpdp-assessment.m.frappe.cloud",
        "https://dpdp.projecttech4dev.org",
    ]
    origin  = frappe.request.headers.get("Origin", "")
    referer = frappe.request.headers.get("Referer", "")
    source  = origin or referer
    if source and not any(source.startswith(a) for a in allowed):
        frappe.throw("Unauthorized", frappe.PermissionError)


# Module-level config cache — cleared on bench restart
_config_cache = None

def _get_config():
    global _config_cache
    if _config_cache is None:
        import os
        path = os.path.join(
            frappe.get_app_path('dpdp_tool'), 'public', 'dpdp-config.json'
        )
        with open(path, 'r') as f:
            _config_cache = json.load(f)
    return _config_cache


def _section_scores_from_doc(doc):
    """Return section scores dict from individual DocType fields."""
    return {
        'consent':    doc.score_consent    or 0,
        'storage':    doc.score_storage    or 0,
        'usage':      doc.score_usage      or 0,
        'rights':     doc.score_rights     or 0,
        'governance': doc.score_governance or 0,
    }


# ─────────────────────────────────────────────────────────────────
# METHOD 1 — get_recommendations  (legacy single-call, kept as fallback)
# ─────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def get_recommendations(docname, sector, org_size, beneficiaries,
                        total_score, max_score, section_scores, answers):
    """
    Legacy: enqueues the single-call Claude job and returns immediately.
    The new 2-call flow is triggered automatically from store_assessment.
    Kept for backward compatibility and as a manual retry mechanism.
    """
    try:
        _validate_origin()
        if not docname:
            frappe.throw("docname required")

        frappe.enqueue(
            "dpdp_tool.api._run_recommendation_job",
            queue="long",
            timeout=600,
            docname=docname,
            sector=sector,
            org_size=org_size,
            beneficiaries=beneficiaries,
            total_score=total_score,
            max_score=max_score,
            section_scores=section_scores,
            answers=answers,
        )
        frappe.logger("dpdp").info(f"[DPDP] queued recommendation job for {docname}")
        return {"status": "queued", "docname": docname}

    except Exception as e:
        frappe.log_error(f"DPDP queue error: {e}", "DPDP API")
        return {"status": "error", "message": str(e)}


def _run_recommendation_job(docname, sector, org_size, beneficiaries,
                            total_score, max_score, section_scores, answers):
    """Legacy background worker — writes to recommendations field."""
    try:
        import anthropic

        api_key = frappe.conf.get("anthropic_api_key")
        if not api_key:
            raise ValueError("anthropic_api_key not set in site config")

        if isinstance(section_scores, str):
            section_scores = json.loads(section_scores)

        sector_str = _parse_sectors(sector)
        client     = anthropic.Anthropic(api_key=api_key)
        response   = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=10000,
            messages=[{"role": "user", "content": _build_prompt(
                sector_str, org_size, beneficiaries,
                int(float(total_score)), int(float(max_score)),
                section_scores, answers
            )}]
        )
        reco = response.content[0].text
        frappe.logger("dpdp").info(f"[DPDP] legacy job complete for {docname}")

    except Exception as e:
        frappe.log_error(f"DPDP job error ({docname}): {e}", "DPDP API")
        reco = _fallback(section_scores, total_score)

    try:
        doc = frappe.get_doc("DPDP Assessment", docname)
        doc.recommendations = reco
        doc.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(f"DPDP job doc-save error ({docname}): {e}", "DPDP API")


# ─────────────────────────────────────────────────────────────────
# METHOD 1b — check_reco  (legacy poll, kept for backward compat)
# ─────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def check_reco(docname):
    """Legacy: polls recommendations field. New code uses poll_status instead."""
    try:
        _validate_origin()
        if not docname:
            return {"status": "error", "message": "docname required"}
        doc = frappe.get_doc("DPDP Assessment", docname)
        if doc.recommendations:
            return {"status": "ok", "recommendations": doc.recommendations}
        return {"status": "pending"}
    except Exception as e:
        frappe.log_error(f"DPDP check_reco error ({docname}): {e}", "DPDP API")
        return {"status": "error", "message": str(e)}


# ─────────────────────────────────────────────────────────────────
# METHOD 2 — store_assessment
# Field names match existing DocType exactly.
# Now also enqueues the 2-call AI background jobs.
# ─────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def store_assessment(org_name, org_email, contact_name, sector, org_size,
                     beneficiaries, total_score, score_consent, score_storage,
                     score_usage, score_rights, score_governance,
                     answers_json, recommendations=""):
    try:
        _validate_origin()
        if not org_name or not org_email:
            return {"status": "error", "message": "Missing required fields"}

        doc                  = frappe.new_doc("DPDP Assessment")
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
        doc.recommendations  = recommendations  # empty on new submissions
        doc.status           = "Submitted"       # background jobs will update
        doc.submitted_on     = datetime.now()
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        # Enqueue 2-call AI architecture in parallel
        frappe.enqueue(
            "dpdp_tool.api.run_summary_call",
            docname=doc.name,
            queue="short",
            timeout=180,
            is_async=True
        )
        frappe.enqueue(
            "dpdp_tool.api.run_roadmap_call",
            docname=doc.name,
            queue="long",
            timeout=360,
            is_async=True
        )

        frappe.logger("dpdp").info(f"[DPDP] stored {doc.name}, enqueued 2-call jobs")
        return {"status": "ok", "docname": doc.name}

    except Exception as e:
        frappe.log_error(f"DPDP store error: {e}", "DPDP API")
        return {"status": "error"}


# ─────────────────────────────────────────────────────────────────
# NEW — poll_status
# Single endpoint the JS polls every 5s to check all three outputs.
# ─────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def poll_status(docname):
    """
    Returns the current state of all three async outputs.
    JS uses has_summary / has_roadmap / pdf_file rather than status string
    so it's immune to status value changes.
    """
    try:
        _validate_origin()
        doc = frappe.db.get_value(
            "DPDP Assessment", docname,
            ["status", "executive_summary", "action_roadmap",
             "pdf_file", "failed_reason"],
            as_dict=True
        )
        if not doc:
            return {"status": "not_found"}
        return {
            "status":          doc.status,
            "executive_summary": doc.executive_summary or None,
            "action_roadmap":  doc.action_roadmap or None,
            "pdf_file":        doc.pdf_file or None,
            "failed_reason":   doc.failed_reason or None,
        }
    except Exception as e:
        frappe.log_error(f"DPDP poll_status error ({docname}): {e}", "DPDP API")
        return {"status": "error", "message": str(e)}


# ─────────────────────────────────────────────────────────────────
# METHOD 2b — patch_assessment_reco  (kept, unchanged)
# ─────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True, methods=["POST"])
def patch_assessment_reco(docname, recommendations):
    """Patch recommendations onto an existing DPDP Assessment doc."""
    try:
        _validate_origin()
        if not docname:
            return {"status": "error", "message": "docname required"}
        doc = frappe.get_doc("DPDP Assessment", docname)
        doc.recommendations = recommendations or ""
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        frappe.logger("dpdp").info(f"[DPDP] patch_assessment_reco: patched {docname}")
        return {"status": "ok", "docname": docname}
    except Exception as e:
        frappe.log_error(f"DPDP patch reco error ({docname}): {e}", "DPDP API")
        return {"status": "error", "message": str(e)}


# ─────────────────────────────────────────────────────────────────
# NEW BACKGROUND JOBS — 2-call architecture
# ─────────────────────────────────────────────────────────────────

def run_summary_call(docname):
    """
    Background job: Call 1 — fast executive summary.
    Input: section scores + org context only. No question detail needed.
    Streams results within ~10s. Updates status to 'Summary Ready'.
    """
    try:
        import anthropic

        api_key = frappe.conf.get("anthropic_api_key")
        if not api_key:
            raise ValueError("anthropic_api_key not set in site config")

        doc    = frappe.get_doc("DPDP Assessment", docname)
        scores = _section_scores_from_doc(doc)
        prompt = _build_summary_prompt(doc, scores)

        client  = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}]
        )
        summary = message.content[0].text

        frappe.db.set_value("DPDP Assessment", docname, {
            "executive_summary": summary,
            "status":            "Summary Ready",
        })
        frappe.db.commit()
        frappe.logger("dpdp").info(f"[DPDP] summary ready for {docname}")

    except Exception as e:
        frappe.log_error(f"[DPDP] summary call failed for {docname}: {e}",
                         "DPDP Summary Error")
        # Don't update status to Failed — roadmap call may still succeed


def run_roadmap_call(docname):
    """
    Background job: Call 2 — comprehensive action roadmap.
    Uses the existing well-tested _build_prompt with gap questions only.
    On success, triggers PDF generation + email.
    Updates status to 'Roadmap Ready' then 'Processed' after PDF.
    """
    try:
        import anthropic

        api_key = frappe.conf.get("anthropic_api_key")
        if not api_key:
            raise ValueError("anthropic_api_key not set in site config")

        doc    = frappe.get_doc("DPDP Assessment", docname)
        scores = _section_scores_from_doc(doc)

        # Parse answers to build gap-only context (reduces tokens)
        answers_raw  = doc.answers_json or "[]"
        gap_summary  = _build_gap_answers(answers_raw)

        prompt = _build_roadmap_prompt(doc, scores, gap_summary)

        client  = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}]
        )
        roadmap = message.content[0].text

        frappe.db.set_value("DPDP Assessment", docname, {
            "action_roadmap": roadmap,
            "status":         "Roadmap Ready",
        })
        frappe.db.commit()
        frappe.logger("dpdp").info(f"[DPDP] roadmap ready for {docname}")

        # Trigger PDF generation (waits for both AI outputs)
        frappe.enqueue(
            "dpdp_tool.api.generate_and_attach_pdf",
            docname=docname,
            queue="short",
            timeout=180,
            is_async=True
        )

    except Exception as e:
        frappe.log_error(f"[DPDP] roadmap call failed for {docname}: {e}",
                         "DPDP Roadmap Error")
        existing = frappe.db.get_value("DPDP Assessment", docname, "failed_reason") or ""
        frappe.db.set_value("DPDP Assessment", docname, {
            "failed_reason": (existing + f"\nRoadmap: {e}").strip()
        })
        frappe.db.commit()


def generate_and_attach_pdf(docname):
    """
    Background job: generate PDF, attach to doc, email to assessor.
    Sets status to 'Processed' on completion (keeps get_sector_insights working).
    """
    try:
        from dpdp_tool.pdf_generator import generate_assessment_pdf

        doc = frappe.get_doc("DPDP Assessment", docname)
        cfg = _get_config()

        pdf_bytes = generate_assessment_pdf(doc, cfg)

        filename = (
            f"DPDP_{doc.org_name.replace(' ', '_')}"
            f"_{frappe.utils.today()}.pdf"
        )

        file_doc = frappe.get_doc({
            "doctype":             "File",
            "file_name":           filename,
            "content":             pdf_bytes,
            "is_private":          0,
            "attached_to_doctype": "DPDP Assessment",
            "attached_to_name":    docname,
        })
        file_doc.insert(ignore_permissions=True)

        frappe.db.set_value("DPDP Assessment", docname, {
            "pdf_file":   file_doc.file_url,
            "status":     "Processed",   # keeps get_sector_insights query working
        })
        frappe.db.commit()
        frappe.logger("dpdp").info(f"[DPDP] PDF attached for {docname}")

        # Email the report
        _send_report_email(doc, file_doc)

        frappe.db.set_value("DPDP Assessment", docname, "pdf_emailed", 1)
        frappe.db.commit()

    except Exception as e:
        frappe.log_error(f"[DPDP] PDF generation failed for {docname}: {e}",
                         "DPDP PDF Error")


# ─────────────────────────────────────────────────────────────────
# EMAIL
# ─────────────────────────────────────────────────────────────────

def _render_email_template(template_name, args):
    """
    Fetch an Email Template from the doctype and render it with Jinja.
    Bypasses Frappe's sendmail template= file-path lookup entirely.
    Returns rendered HTML string, or None if the template does not exist.
    """
    try:
        tmpl = frappe.get_doc("Email Template", template_name)
        from frappe.utils.jinja import render_template
        return render_template(tmpl.response_html or tmpl.response or "", args)
    except Exception:
        return None


def _send_report_email(doc, file_doc):
    """
    Email the completed report with PDF attached.
    Renders Email Template from doctype (not file path).
    """
    cfg  = _get_config()
    band = next(
        (b for b in cfg["scoring"]["bands"] if doc.total_score >= b["min"]),
        cfg["scoring"]["bands"][-1]
    )

    # Read PDF bytes directly from disk
    try:
        file_path = frappe.get_doc("File", file_doc.name).get_full_path()
        with open(file_path, "rb") as f:
            pdf_bytes = f.read()
        attachments = [{"fname": file_doc.file_name, "fcontent": pdf_bytes}]
        frappe.logger("dpdp").info(f"[DPDP] PDF read OK: {len(pdf_bytes)} bytes for {doc.name}")
    except Exception as e:
        frappe.log_error(f"[DPDP] PDF read failed, falling back to fid: {e}", "DPDP Email")
        attachments = [{"fname": file_doc.file_name, "fid": file_doc.name}]

    args = {
        "doc":        doc,
        "band_label": band["label"],
        "band_emoji": band["emoji"],
        "site_url":   frappe.utils.get_url(),
    }

    # Render from doctype — no file path lookup
    html = _render_email_template("DPDP Assessment Report", args)
    if not html:
        html = (
            f"Dear {doc.contact_name or doc.org_name},<br><br>"
            f"Your DPDP Readiness Report is attached.<br><br>"
            f"Score: {doc.total_score}/50 - {band['emoji']} {band['label']}<br><br>"
            f"Tech4Dev DPDP Navigator"
        )

    cc_raw = frappe.conf.get("dpdp_report_cc_email") or ""
    cc     = [e.strip() for e in cc_raw.split(",") if e.strip()]

    frappe.sendmail(
        recipients=[doc.org_email],
        cc=cc or None,
        subject=f"Your DPDP Readiness Report - {doc.org_name}",
        message=html,
        attachments=attachments,
        now=True,
    )


# ─────────────────────────────────────────────────────────────────
# METHOD 3 — get_sector_insights  (unchanged)
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
            if len(entries) < 1:
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
# METHOD 4 — submit_consult_request  (unchanged)
# ─────────────────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def submit_consult_request(org_name, contact_name, email,
                           sector="", org_size="", service_interest="",
                           message="", phone=""):
    try:
        _validate_origin()
        if not org_name or not contact_name or not email:
            frappe.throw("Organisation name, contact name, and email are required.")

        doc                  = frappe.new_doc("DPDP Consult Request")
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

        # Notify internal team
        _send_consult_notification(doc)

        return {"status": "ok"}

    except Exception as e:
        frappe.log_error(f"DPDP consult error: {e}", "DPDP API")
        return {"status": "error", "message": str(e)}


def _send_consult_notification(doc):
    try:
        notify_email = (
            frappe.conf.get("dpdp_consult_notify_email")
            or "dpdp@projecttech4dev.org"
        )

        args = {"doc": doc, "site_url": frappe.utils.get_url()}

        html = _render_email_template("DPDP Consult Request Internal", args)

        if not html:
            html = (
                f"<b>New DPDP Consult Request</b><br><br>"
                f"<b>Organisation:</b> {doc.org_name}<br>"
                f"<b>Contact:</b> {doc.contact_name}<br>"
                f"<b>Email:</b> {doc.email}<br>"
                f"<b>Phone:</b> {doc.phone or chr(8212)}<br>"
                f"<b>Sector:</b> {doc.sector or chr(8212)}<br>"
                f"<b>Size:</b> {doc.org_size or chr(8212)}<br>"
                f"<b>Service Interest:</b> {doc.service_interest or chr(8212)}<br><br>"
                f"<b>Message:</b><br>{doc.message or '(none)'}<br><br>"
                f"<a href='{frappe.utils.get_url()}/app/dpdp-consult-request/{doc.name}'>"
                f"View in Frappe Desk</a>"
            )

        frappe.log_error(f"STEP 3 — calling sendmail to {notify_email}", "DPDP Debug")
        try:
            frappe.sendmail(
                recipients=["vinod@projecttech4dev.org"],
                cc=None,
                subject=f"New DPDP Consult Request - {doc.org_name}",
                message=f"New consult request from {doc.org_name} - {doc.contact_name} - {doc.email}",
                now=True,
            )
                
        except Exception:
            frappe.log_error(frappe.get_traceback(), "DPDP Email Failure")
            raise

    except Exception as e:
        frappe.log_error(
            f"[DPDP] consult notification failed for {doc.name}: {e}",
            "DPDP Consult Notification"
        )

# ─────────────────────────────────────────────────────────────────
# PROMPTS
# ─────────────────────────────────────────────────────────────────

def _build_summary_prompt(doc, section_scores):
    """
    Call 1 — concise executive summary + sector risks + priority band.
    Fast, focused, no question detail needed.
    """
    sec_lines = "\n".join([
        f"- Data Collection & Consent:  {section_scores.get('consent', 0)}/10",
        f"- Data Storage & Security:    {section_scores.get('storage', 0)}/10",
        f"- Data Usage & Sharing:       {section_scores.get('usage', 0)}/10",
        f"- Rights of Individuals:      {section_scores.get('rights', 0)}/10",
        f"- Governance & Processes:     {section_scores.get('governance', 0)}/10",
    ])

    return f"""You are a senior DPDP Act 2023 compliance advisor for Indian NGOs.

Organisation: {doc.org_name}
Sector: {doc.sector}
Size: {doc.org_size}
Beneficiaries: {doc.beneficiaries or 'Not specified'}
Overall score: {doc.total_score}/50

Section scores:
{sec_lines}

Produce a focused executive brief with exactly these four sections:

## What Your Score Tells You
3-4 sentences plain language for a non-technical NGO leader. Interpret the overall score honestly. Reference the two lowest-scoring sections by name.

## Sector and Beneficiary Risks
Bullet list of exactly 3 risks specific to {doc.sector} work and beneficiaries ({doc.beneficiaries or 'not specified'}). For each risk name the DPDP Act provision and phrase any penalty as "up to ₹X crore". Be concrete — name the programme activity or data type at risk, not a generic statement.

## Priority Areas
A table classifying each section:

| Address Now | Plan & Improve | Monitor |
|---|---|---|

Place each section name in the column matching its score: under 40% = Address Now, 40-70% = Plan & Improve, over 70% = Monitor.

## One Action This Week
One sentence. Name a specific, concrete action the organisation can take in the next 7 days. Not generic advice — something achievable by a {doc.org_size} NGO.

Rules: bullet points only, no prose paragraphs in risks section, penalties as "up to ₹X crore", refer to dpdpa.com for further reading, do not cite iSPIRT or SECO."""


def _build_gap_answers(answers_json):
    """
    Parse answers_json and return a formatted string of gap questions only
    (No + Partially) to reduce tokens sent to Call 2.
    """
    try:
        answers = json.loads(answers_json or "[]")
    except Exception:
        return "Answers not available."

    lines = []
    for a in answers:
        if not isinstance(a, dict):
            continue
        pts = a.get("points", 0)
        if pts >= 2:
            continue  # Skip Yes answers
        lbl     = "Partially" if pts == 1 else "No"
        section = a.get("section", "")
        q_text  = a.get("text", "")[:120]
        why     = a.get("why", "")[:100]
        lines.append(f"[{section}] Q{a.get('q','?')}: {q_text} → {lbl}. Why it matters: {why}")

    return "\n".join(lines) if lines else "All questions answered Yes — no gaps."


def _build_roadmap_prompt(doc, section_scores, gap_summary):
    """
    Call 2 — comprehensive action roadmap using existing well-tested prompt structure.
    Only receives gap questions to reduce token input.
    """
    sec_lines = "\n".join([
        f"- Data Collection & Consent:  {section_scores.get('consent', 0)}/10",
        f"- Data Storage & Security:    {section_scores.get('storage', 0)}/10",
        f"- Data Usage & Sharing:       {section_scores.get('usage', 0)}/10",
        f"- Rights of Individuals:      {section_scores.get('rights', 0)}/10",
        f"- Governance & Processes:     {section_scores.get('governance', 0)}/10",
    ])

    return _build_prompt(
        sector=doc.sector,
        org_size=doc.org_size,
        beneficiaries=doc.beneficiaries or "Not specified",
        total_score=int(doc.total_score or 0),
        max_score=50,
        section_scores=section_scores,
        answers=gap_summary,  # gap questions only
    )


def _build_prompt(sector, org_size, beneficiaries,
                  total_score, max_score, section_scores, answers):
    """
    Existing comprehensive prompt — unchanged. Used by both legacy
    _run_recommendation_job and the new run_roadmap_call.
    """
    sec_lines = "\n".join([
        f"- Data Collection & Consent:  {section_scores.get('consent', 0)}/10",
        f"- Data Storage & Security:    {section_scores.get('storage', 0)}/10",
        f"- Data Usage & Sharing:       {section_scores.get('usage', 0)}/10",
        f"- Rights of Individuals:      {section_scores.get('rights', 0)}/10",
        f"- Governance & Processes:     {section_scores.get('governance', 0)}/10",
    ])

    prompt = f"""You are a senior DPDP Act 2023 compliance advisor specialising exclusively in Indian NGOs and social sector organisations. You have deep knowledge of:
- The Digital Personal Data Protection Act 2023 and DPDP Rules 2025
- How NGOs actually operate in India — stretched staff, multiple funders, field programmes, government partnerships
- The specific data risks that arise in each social sector (health, education, livelihoods, gender/SRHR, humanitarian, disability)
- The Data Protection Board of India's enforcement priorities and penalty schedule
 
You are reviewing a self-assessment submitted by a {org_size} organisation working in **{sector}**, with primary beneficiaries: **{beneficiaries}**.
 
━━━ ASSESSMENT RESULTS ━━━
 
Overall score:  {total_score}/{max_score} points
Readiness bands: 0–20 High Risk · 21–35 Basic · 36–45 Moderate · 46–50 Strong
 
Section scores (each out of 10):
{sec_lines}
  
━━━ GAP AREAS (No or Partially answered) ━━━
{answers}
 
━━━ YOUR TASK ━━━
 
Produce a substantive, personalised compliance roadmap that this organisation's leadership can act on without additional guidance.
Target length: 1,200–1,800 words. Be specific; be direct; be useful.
 
━━━ CRITICAL INSTRUCTIONS ━━━
 
1. CITE ONLY REAL DPDP ACT SECTIONS AND RULE NUMBERS.
2. Be specific to THIS organisation — reference their sector(s), {org_size} size, and beneficiary profile throughout.
3. Use the gap areas above to ground your advice. Address each gap directly.
4. If beneficiaries include anyone under 18, address Section 9 obligations in every relevant action.
5. Where the organisation works across multiple sectors, name the specific data risk for each sector separately.
6. Use realistic role titles for a {org_size} NGO.
7. Every action must state: (a) WHY — cite DPDP section and penalty range. (b) HOW — concrete enough to start tomorrow.
8. Calibrate urgency to the score band.
9. Prioritise the two lowest-scoring sections.
10. Phrase all penalties as "up to ₹X crore" — never as fixed amounts.
11. Refer users only to dpdpa.com for further reading. Do not reference iSPIRT or SECO.
 
━━━ FORMAT — use exactly these headings ━━━
 
## 30-Day Priority Actions
Start with the two lowest-scoring sections. 4–5 items.

**[Specific task name]**
- **Who:** [Role appropriate for {org_size} NGO]
- **Why this cannot wait:** [DPDP Act section + penalty + specific consequence for {beneficiaries}]
- **How:** [3–4 sentences of practical guidance. Name tools, templates, or processes.]
- **Covers multiple gaps:** [Only include when genuinely true]

## 90-Day Compliance Foundation
5 items building on 30-day actions.

**[Specific task name]**
- **Who leads:** [Role]
- **Why this matters:** [DPDP Act section + consequence for {sector} work]
- **How:** [3–4 sentences]
- **Done when:** [Specific, tangible deliverable]

## 1-Year Compliance Habits
4 items attached to existing organisational moments.

**[Task name]**
- **When:** [Specific existing moment — board meeting, staff retreat, funder report]
- **Who:** [Role]
- **Why:** [One sentence on what degrades if this lapses]
- **What to do:** [2–3 sentences]

## Summary Table
| Action | Timeline | Owner | Why It Matters |
|---|---|---|---|
(top 6 actions from above)

Further reading: https://www.dpdpa.com/blogs/DPDPA_Implementation_Timeline.html"""

    frappe.logger("dpdp").info(
        "\n" + "=" * 60 + "\n[DPDP] prompt built for " + str(sector) + "\n" + "=" * 60
    )
    return prompt


def _fallback(section_scores, total_score):
    """Fallback recommendations when Claude call fails — unchanged."""
    if isinstance(section_scores, str):
        try:
            section_scores = json.loads(section_scores)
        except Exception:
            section_scores = {}

    gaps      = sorted(section_scores.items(), key=lambda x: x[1] or 0)[:2]
    gap_names = [g[0].replace("_", " ").title() for g in gaps]

    return f"""## Standard Recommendations (AI unavailable)

## 30-Day Priority Actions

**Designate a data protection owner**
- Who: Executive Director or Senior Programme Manager
- Why: The DPDP Act holds Data Fiduciaries accountable (Section 8). Without a named owner no compliance work can proceed.
- How: Name a person, document their mandate in a one-page terms of reference, share with the board.

**Audit your consent forms**
- Who: Programme Manager
- Why: Invalid consent is a direct DPDP violation (Section 6). Penalties up to ₹250 crore apply.
- How: Check every form for four elements: purpose, retention period, rights, contact details.

**Create a basic data inventory**
- Who: Programme Manager and IT person
- Why: You cannot protect data you have not mapped.
- How: One spreadsheet row per data type: what it is, where stored, who can access, how long kept.

## 90-Day Compliance Foundation

**Draft a Data Protection Policy** — ED. Done when: approved policy shared with all staff.

**Train staff on DPDP basics** — Programme Head. Done when: session held and documented.

**Sign Data Processing Agreements with vendors** — ED/Finance. Done when: agreements filed for top 3 processors.

**Establish a grievance mechanism** — Programme Manager. Done when: named email and response protocol documented.

**Document a breach response procedure** — ED/Programme Manager. Done when: one-page checklist exists.

## 1-Year Compliance Habits

**Annual compliance review** — AGM · ED

**Consent form refresh** — New programme launch · Programme Manager

**Staff DPDP refresher** — Annual staff retreat · HR/Programme Head

**Vendor DPA check** — Contract renewals · Finance/ED

## Summary Table
| Action | Timeline | Owner | Why It Matters |
|---|---|---|---|
| Designate data protection owner | 30 days | ED | Accountability under Section 8 |
| Audit consent forms | 30 days | Programme Manager | Section 6 compliance |
| Data inventory | 30 days | PM + IT | Foundation of all compliance |
| Data Protection Policy | 90 days | ED | Accountability and trust |
| Staff training | 90 days | Programme Head | Reduces accidental breach risk |
| Breach response plan | 90 days | ED | Mandatory notification under DPDP |

Further reading: https://www.dpdpa.com/blogs/DPDPA_Implementation_Timeline.html"""
