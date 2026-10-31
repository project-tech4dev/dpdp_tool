"""
Report privacy: random assessment/PDF names, the 3-day public window on
poll_status / check_reco, the daily privatise job, and the one-time rename patch.
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


def test_fixture_is_not_sequential_and_has_legacy_id():
    doctype = json.load(open(ROOT / "fixtures" / "dpdp_assessment.json"))[0]
    assert "#" not in doctype["autoname"]
    assert any(f["fieldname"] == "legacy_id" and f.get("read_only") for f in doctype["fields"])


def test_patch_is_registered():
    assert "dpdp_tool.patches.v1_1.randomize_assessment_names" in (ROOT / "patches.txt").read_text()


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


def test_check_reco_hides_old_assessments(api, frappe, rp):
    frappe.get_doc = lambda *a: _assessment(dt.timedelta(days=10))
    assert api.check_reco("DPDP-0123456789abcdef") == {"status": "not_found"}
    frappe.get_doc = lambda *a: _assessment(dt.timedelta(hours=1))
    assert api.check_reco("DPDP-0123456789abcdef")["recommendations"] == "reco"


# ─────────────────────────────────────────────────────────────────
# Daily job
# ─────────────────────────────────────────────────────────────────

def test_daily_job_privatises_old_report_pdfs(rp, frappe):
    calls = {"filters": None, "saved": [], "rolled_back": 0}

    def get_all(doctype, filters=None, **kw):
        calls["filters"] = filters
        return ["F1", "F2"]

    def get_doc(doctype, name):
        doc = types.SimpleNamespace(name=name, is_private=0)
        def save(ignore_permissions=False):
            if name == "F1":
                raise FileNotFoundError("gone")
            calls["saved"].append((name, doc.is_private))
        doc.save = save
        return doc

    frappe.get_all, frappe.get_doc = get_all, get_doc
    frappe.db.rollback = lambda: calls.__setitem__("rolled_back", calls["rolled_back"] + 1)
    rp.make_old_report_pdfs_private()

    assert calls["filters"] == {"attached_to_doctype": "DPDP Assessment", "is_private": 0,
                                "creation": ["<", NOW - dt.timedelta(days=3)]}
    assert calls["saved"] == [("F2", 1)]          # F1 failed, was rolled back, F2 still done
    assert calls["rolled_back"] == 1


# ─────────────────────────────────────────────────────────────────
# One-time rename of existing data
# ─────────────────────────────────────────────────────────────────

def _file_row(name, url, attached, private=0):
    return types.SimpleNamespace(name=name, file_url=url, is_private=private, attached_to_name=attached)


def test_rename_report_files_moves_files_and_updates_links(rp, frappe, tmp_path):
    public = tmp_path / "public" / "files"
    public.mkdir(parents=True)
    (public / "DPDP_Acme_NGO_2026-06-01.pdf").write_bytes(b"pdf")
    (public / "shared.pdf").write_bytes(b"pdf")
    rows = [
        _file_row("F1", "/files/DPDP_Acme_NGO_2026-06-01.pdf", "DPDP-a"),
        _file_row("F2", "/files/DPDP_Report_0123456789abcdef.pdf", "DPDP-b"),   # already random
        _file_row("F3", "/files/shared.pdf", "DPDP-c"),                          # shared on disk
        _file_row("F4", "/files/missing.pdf", "DPDP-d"),                          # not on disk
    ]
    sets = []
    frappe.get_all = lambda *a, **k: rows
    frappe.get_doc = lambda doctype, name: types.SimpleNamespace(
        get_full_path=lambda: str(public / next(r for r in rows if r.name == name).file_url.rsplit("/", 1)[-1]))
    frappe.db.count = lambda doctype, filters: 2 if filters["file_url"] == "/files/shared.pdf" else 1
    frappe.db.get_value = lambda doctype, name, field: "/files/DPDP_Acme_NGO_2026-06-01.pdf"
    frappe.db.set_value = lambda *a, **k: sets.append(a)
    frappe.db.commit = lambda: None

    rp.rename_report_files()

    remaining = sorted(p.name for p in public.iterdir())
    assert "DPDP_Acme_NGO_2026-06-01.pdf" not in remaining and "shared.pdf" in remaining
    new_name = next(n for n in remaining if n.startswith("DPDP_Report_"))
    assert sets == [
        ("File", "F1", {"file_name": new_name, "file_url": f"/files/{new_name}"}),
        ("DPDP Assessment", "DPDP-a", "pdf_file", f"/files/{new_name}"),
    ]


def test_patch_renames_assessments_and_keeps_legacy_id(rp, frappe, monkeypatch):
    calls = {"legacy": [], "renamed": [], "synced": 0, "files": 0}
    frappe.db.has_column = lambda doctype, col: False
    frappe.get_all = lambda doctype, filters=None, **kw: ["DPDP-ASSESS-0001", "DPDP-ASSESS-0003", "DPDP-ASSESS-0002"]
    frappe.db.set_value = lambda doctype, name, field, value, **kw: calls["legacy"].append((name, field, value))
    def rename_doc(doctype, old, new, **kw):
        if old == "DPDP-ASSESS-0003":
            raise RuntimeError("locked")
        calls["renamed"].append((old, new, kw))
    frappe.rename_doc = rename_doc
    frappe.db.rollback = lambda: calls.__setitem__("rolled_back", True)
    fixtures = types.ModuleType("frappe.utils.fixtures")
    fixtures.sync_fixtures = lambda app: calls.__setitem__("synced", calls["synced"] + 1)
    monkeypatch.setitem(sys.modules, "frappe.utils", types.ModuleType("frappe.utils"))
    monkeypatch.setitem(sys.modules, "frappe.utils.fixtures", fixtures)
    monkeypatch.setattr(rp, "rename_report_files", lambda: calls.__setitem__("files", 1))

    patch = _load("randomize_assessment_names", ROOT / "patches" / "v1_1" / "randomize_assessment_names.py")
    patch.execute()

    assert calls["synced"] == 1 and calls["files"] == 1
    assert ("DPDP-ASSESS-0002", "legacy_id", "DPDP-ASSESS-0002") in calls["legacy"]
    # 0003 failed and was rolled back; the others still went through
    assert [o for o, _, _ in calls["renamed"]] == ["DPDP-ASSESS-0001", "DPDP-ASSESS-0002"]
    assert calls["rolled_back"] is True
    assert all(re.fullmatch(r"DPDP-[0-9a-f]{16}", n) for _, n, _ in calls["renamed"])
    assert all(kw["force"] and kw["ignore_permissions"] for _, _, kw in calls["renamed"])
