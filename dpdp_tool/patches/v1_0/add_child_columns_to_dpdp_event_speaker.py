"""
DPDP Event Speaker was first created from its bare doctype JSON, before the
fixture marked it as a child table, so its table has no parent columns.
Frappe only adds those when it creates a child table, so add them here.
"""

import frappe

DOCTYPE = "DPDP Event Speaker"


def execute():
    if not frappe.db.table_exists(DOCTYPE):
        return

    table = f"tab{DOCTYPE}"
    for column in ("parent", "parentfield", "parenttype"):
        if not frappe.db.has_column(DOCTYPE, column):
            frappe.db.sql_ddl(f"alter table `{table}` add column `{column}` varchar({frappe.db.VARCHAR_LEN})")

    if not frappe.db.has_index(table, "parent"):
        frappe.db.sql_ddl(f"alter table `{table}` add index parent(parent)")
