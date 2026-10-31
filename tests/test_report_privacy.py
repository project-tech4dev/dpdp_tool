"""
Report privacy: random assessment/PDF names, the 3-day public window on
poll_status / check_reco, and the daily privatise job.
Loaded by path against the conftest frappe mock (no bench needed).
"""

import ast
import datetime as dt
import importlib.util
import json
import pathlib
import re
import sys
import types

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent / "dpdp_tool"
NOW = dt.datetime(2026, 10, 31, 12, 0)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def rp(frappe, monkeypatch):
    frappe.utils.now_datetime = lambda: NOW
    frappe.utils.get_datetime = lambda v: v if isinstance(v, dt.datetime) else dt.datetime.fromisoformat(str(v))
    module = _load("dpdp_tool.report_privacy", ROOT / "report_privacy.py")
    # api.py imports it lazily as dpdp_tool.report_privacy
    monkeypatch.setitem(sys.modules, "dpdp_tool", types.ModuleType("dpdp_tool"))
    monkeypatch.setitem(sys.modules, "dpdp_tool.report_privacy", module)
    return module


# ─────────────────────────────────────────────────────────────────
# Names
# ─────────────────────────────────────────────────────────────────

def test_random_names_are_unguessable_and_unique(rp):
    names = {rp.random_assessment_name() for _ in range(500)}
    assert len(names) == 500
    assert all(re.fullmatch(r"DPDP-[0-9a-f]{16}", n) for n in names)
    assert re.fullmatch(r"DPDP_Report_[0-9a-f]{16}\.pdf", rp.random_report_filename())


def test_autoname_hook_sets_random_name(rp):
    doc = types.SimpleNamespace(name=None)
    rp.set_random_name(doc, "autoname")
    assert re.fullmatch(r"DPDP-[0-9a-f]{16}", doc.name)


def test_hooks_wire_autoname_and_daily_job(rp):
    tree = ast.parse((ROOT / "hooks.py").read_text())
    hooks = {t.id: ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
             for t in n.targets if t.id in ("doc_events", "scheduler_events")}
    autoname = hooks["doc_events"]["DPDP Assessment"]["autoname"]
    daily = hooks["scheduler_events"]["daily"]
    assert autoname == "dpdp_tool.report_privacy.set_random_name" and hasattr(rp, "set_random_name")
    assert "dpdp_tool.report_privacy.make_old_report_pdfs_private" in daily


def test_fixture_autoname_is_not_sequential():
    doctype = json.load(open(ROOT / "fixtures" / "dpdp_assessment.json"))[0]
    assert "#" not in doctype["autoname"]


# ─────────────────────────────────────────────────────────────────
# Public window (poll_status / check_reco)
# ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("age, ok", [
    (dt.timedelta(minutes=5), True),
    (dt.timedelta(days=2, hours=23), True),
    (dt.timedelta(days=3, minutes=1), False),
])
def test_public_window(rp, age, ok):
    assert rp.is_within_public_window(NOW - age) is ok
    assert rp.is_within_public_window(str(NOW - age)) is ok   # DB may hand back a string
    assert rp.is_within_public_window(None) is False


def _assessment(age, **kw):
    row = {"status": "Processed", "executive_summary": "S", "action_roadmap": "R",
           "pdf_file": "/files/DPDP_Report_x.pdf", "failed_reason": None,
           "recommendations": "reco", "creation": NOW - age}
    row.update(kw)
    return types.SimpleNamespace(**row)


def test_poll_status_answers_recent_assessment(api, frappe, rp):
    frappe.db.get_value = lambda *a, **k: _assessment(dt.timedelta(minutes=3))
    out = api.poll_status("DPDP-0123456789abcdef")
    assert out["executive_summary"] == "S" and out["pdf_file"] == "/files/DPDP_Report_x.pdf"


def test_poll_status_hides_old_and_missing_assessments(api, frappe, rp):
    frappe.db.get_value = lambda *a, **k: _assessment(dt.timedelta(days=4))
    assert api.poll_status("DPDP-0123456789abcdef") == {"status": "not_found"}
    frappe.db.get_value = lambda *a, **k: None
    assert api.poll_status("DPDP-ASSESS-0042") == {"status": "not_found"}


def test_check_reco_hides_old_and_missing_assessments(api, frappe, rp):
    frappe.db.get_value = lambda *a, **k: _assessment(dt.timedelta(days=10))
    assert api.check_reco("DPDP-0123456789abcdef") == {"status": "not_found"}
    frappe.db.get_value = lambda *a, **k: None          # unknown name: same answer, no error
    assert api.check_reco("DPDP-0123456789abcdef") == {"status": "not_found"}
    frappe.db.get_value = lambda *a, **k: _assessment(dt.timedelta(hours=1))
    assert api.check_reco("DPDP-0123456789abcdef")["recommendations"] == "reco"


# ─────────────────────────────────────────────────────────────────
# Daily job
# ─────────────────────────────────────────────────────────────────

def test_daily_job_privatises_old_report_pdfs(rp, frappe):
    calls = {"filters": None, "saved": [], "flag_fixed": [], "rolled_back": 0}
    rows = [types.SimpleNamespace(name="F1", file_url="/files/a.pdf"),          # save fails
            types.SimpleNamespace(name="F2", file_url="/files/b.pdf"),          # moved
            types.SimpleNamespace(name="F3", file_url="/private/files/c.pdf")]  # shares a private file

    def get_all(doctype, filters=None, **kw):
        calls["filters"] = filters
        return rows

    def get_doc(doctype, name):
        doc = types.SimpleNamespace(name=name, is_private=0)
        def save(ignore_permissions=False):
            if name == "F1":
                raise FileNotFoundError("gone")
            calls["saved"].append((name, doc.is_private))
        doc.save = save
        return doc

    frappe.get_all, frappe.get_doc = get_all, get_doc
    frappe.db.set_value = lambda doctype, name, field, value, **kw: calls["flag_fixed"].append((name, field, value))
    frappe.db.rollback = lambda: calls.__setitem__("rolled_back", calls["rolled_back"] + 1)
    rp.make_old_report_pdfs_private()

    assert calls["filters"] == {"attached_to_doctype": "DPDP Assessment", "is_private": 0,
                                "creation": ["<", NOW - dt.timedelta(days=3)]}
    assert calls["saved"] == [("F2", 1)]                 # F1 failed, was rolled back; others still done
    assert calls["flag_fixed"] == [("F3", "is_private", 1)]
    assert calls["rolled_back"] == 1
