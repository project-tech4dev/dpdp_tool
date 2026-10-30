"""Patch that adds child-table columns to DPDP Event Speaker — mock frappe, loaded by path."""

import importlib.util
import pathlib
import sys
import types

import pytest

PATCH_PATH = (pathlib.Path(__file__).resolve().parent.parent / "dpdp_tool" / "patches" / "v1_0"
              / "add_child_columns_to_dpdp_event_speaker.py")


def _load(monkeypatch, *, table=True, columns=(), index=False):
    ddl = []
    db = types.SimpleNamespace(
        VARCHAR_LEN=140,
        table_exists=lambda doctype: table,
        has_column=lambda doctype, col: col in columns,
        has_index=lambda tbl, name: index,
        sql_ddl=ddl.append,
    )
    monkeypatch.setitem(sys.modules, "frappe", types.SimpleNamespace(db=db))
    spec = importlib.util.spec_from_file_location("patch_event_speaker", PATCH_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, ddl


def test_adds_missing_parent_columns_and_index(monkeypatch):
    module, ddl = _load(monkeypatch)
    module.execute()
    assert ddl == [
        "alter table `tabDPDP Event Speaker` add column `parent` varchar(140)",
        "alter table `tabDPDP Event Speaker` add column `parentfield` varchar(140)",
        "alter table `tabDPDP Event Speaker` add column `parenttype` varchar(140)",
        "alter table `tabDPDP Event Speaker` add index parent(parent)",
    ]


@pytest.mark.parametrize("kwargs", [
    {"table": False},
    {"columns": ("parent", "parentfield", "parenttype"), "index": True},
])
def test_no_op_when_table_missing_or_already_a_child_table(monkeypatch, kwargs):
    module, ddl = _load(monkeypatch, **kwargs)
    module.execute()
    assert ddl == []
