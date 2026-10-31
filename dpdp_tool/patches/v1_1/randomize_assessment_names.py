"""
Rename existing DPDP Assessments from sequential DPDP-ASSESS-#### to random
names, keeping the old number in Legacy ID, and give their PDFs random file
names. Sequential names let anyone poll other organisations' reports.
"""

import frappe

from dpdp_tool.report_privacy import random_assessment_name, rename_report_files


def execute():
    # Fixtures sync after patches; Legacy ID must exist before we fill it
    if not frappe.db.has_column("DPDP Assessment", "legacy_id"):
        from frappe.utils.fixtures import sync_fixtures
        sync_fixtures("dpdp_tool")

    # A record that fails is logged and left as is (poll_status no longer serves
    # assessments older than a few days), so one bad row can't block a deploy.
    for old in frappe.get_all("DPDP Assessment", filters={"name": ["like", "DPDP-ASSESS-%"]}, pluck="name"):
        try:
            frappe.db.set_value("DPDP Assessment", old, "legacy_id", old, update_modified=False)
            frappe.rename_doc(
                "DPDP Assessment", old, random_assessment_name(),
                force=True, ignore_permissions=True, show_alert=False, rebuild_search=False,
            )
            frappe.db.commit()
        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(f"[DPDP] could not rename assessment {old}: {e}", "DPDP Report Privacy")

    rename_report_files()
    frappe.db.commit()
