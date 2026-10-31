"""
Keep assessment reports unguessable and only briefly reachable without login.

- New DPDP Assessments get a random name. The report page polls with this
  name, so it must not be guessable (it used to be DPDP-ASSESS-0001, 0002…).
- Report PDFs get a random file name, without the org name.
- poll_status and check_reco only answer for assessments created in the last
  REPORT_PUBLIC_DAYS days.
- A daily job makes report PDFs older than that private.
"""

import os
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
    return bool(creation) and frappe.utils.now_datetime() - creation < timedelta(days=REPORT_PUBLIC_DAYS)


def make_old_report_pdfs_private():
    """Daily: report PDFs older than REPORT_PUBLIC_DAYS become private. Saving
    the File moves it to private/files and updates the assessment's pdf_file."""
    cutoff = frappe.utils.now_datetime() - timedelta(days=REPORT_PUBLIC_DAYS)
    names = frappe.get_all(
        "File",
        filters={"attached_to_doctype": "DPDP Assessment", "is_private": 0, "creation": ["<", cutoff]},
        pluck="name",
    )
    for name in names:
        try:
            file_doc = frappe.get_doc("File", name)
            file_doc.is_private = 1
            file_doc.save(ignore_permissions=True)
            frappe.db.commit()
        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(f"[DPDP] could not make report PDF private ({name}): {e}", "DPDP Report Privacy")


def rename_report_files():
    """Give existing report PDFs a random file name (they used to carry the org name)."""
    files = frappe.get_all(
        "File",
        filters={"attached_to_doctype": "DPDP Assessment", "is_folder": 0},
        fields=["name", "file_url", "is_private", "attached_to_name"],
    )
    for f in files:
        if not f.file_url or f.file_url.rsplit("/", 1)[-1].startswith("DPDP_Report_"):
            continue
        # Frappe de-duplicates identical uploads; don't move a file another record still uses
        if frappe.db.count("File", {"file_url": f.file_url}) > 1:
            continue
        old_path = frappe.get_doc("File", f.name).get_full_path()
        if not os.path.exists(old_path):
            continue
        new_name = random_report_filename()
        new_path = os.path.join(os.path.dirname(old_path), new_name)
        new_url = ("/private/files/" if f.is_private else "/files/") + new_name
        os.rename(old_path, new_path)
        try:
            frappe.db.set_value("File", f.name, {"file_name": new_name, "file_url": new_url}, update_modified=False)
            if frappe.db.get_value("DPDP Assessment", f.attached_to_name, "pdf_file") == f.file_url:
                frappe.db.set_value("DPDP Assessment", f.attached_to_name, "pdf_file", new_url, update_modified=False)
            frappe.db.commit()
        except Exception as e:
            os.rename(new_path, old_path)
            frappe.db.rollback()
            frappe.log_error(f"[DPDP] could not rename report PDF ({f.name}): {e}", "DPDP Report Privacy")
