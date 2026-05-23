import frappe
from frappe.model.document import Document


class DpdpAssessment(Document):
    """
    DPDP Assessment DocType controller.
    AI generation and PDF email are handled by background jobs in api.py.
    """

    def before_insert(self):
        self.submitted_on = frappe.utils.now()

    def validate(self):
        if not self.org_email:
            frappe.throw("Work email is required.")
        if not self.org_name:
            frappe.throw("Organisation name is required.")
