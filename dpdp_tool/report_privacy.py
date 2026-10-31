"""
Keep assessment reports unguessable and only briefly reachable without login.

- New DPDP Assessments get a random name. The report page polls with this
  name, so it must not be guessable (it used to be DPDP-ASSESS-0001, 0002…).
- Report PDFs get a random file name, without the org name.
- poll_status and check_reco only answer for assessments created in the last
  REPORT_PUBLIC_DAYS days.
- A daily job makes report PDFs older than that private.
"""

import secrets
from datetime import timedelta

import frappe

REPORT_PUBLIC_DAYS = 3


def random_assessment_name():
    return f"DPDP-{secrets.token_hex(8)}"


def random_report_filename():
    return f"DPDP_Report_{secrets.token_hex(8)}.pdf"


def set_random_name(doc, method=None):
    """doc_events autoname hook. DPDP Assessment is a custom DocType, so a
    controller autoname() would never run."""
    doc.name = random_assessment_name()


def is_within_public_window(creation):
    if not creation:
        return False
    return frappe.utils.now_datetime() - frappe.utils.get_datetime(creation) < timedelta(days=REPORT_PUBLIC_DAYS)


def make_old_report_pdfs_private():
    """Daily: report PDFs older than REPORT_PUBLIC_DAYS become private. Saving
    the File moves it to private/files and updates the assessment's pdf_file."""
    cutoff = frappe.utils.now_datetime() - timedelta(days=REPORT_PUBLIC_DAYS)
    files = frappe.get_all(
        "File",
        filters={"attached_to_doctype": "DPDP Assessment", "is_private": 0, "creation": ["<", cutoff]},
        fields=["name", "file_url"],
    )
    for f in files:
        try:
            if (f.file_url or "").startswith("/private/"):
                # Already in private/files (a record sharing the file was moved); just fix the flag
                frappe.db.set_value("File", f.name, "is_private", 1, update_modified=False)
            else:
                file_doc = frappe.get_doc("File", f.name)
                file_doc.is_private = 1
                file_doc.save(ignore_permissions=True)
            frappe.db.commit()
        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(f"[DPDP] could not make report PDF private ({f.name}): {e}", "DPDP Report Privacy")
