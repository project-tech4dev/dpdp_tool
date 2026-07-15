"""
Test harness for dpdp_tool.api — no Frappe/bench required.

Injects a mock `frappe` module into sys.modules, then loads api.py by file
path (there is no installed dpdp_tool package outside bench). Mirrors the
frappe-mocking approach in test_pdf.py, extended for the surface api.py touches:
logger, request.headers, throw/PermissionError, db.sql, conf.get.
"""

import sys
import json
import types
import importlib.util
import pathlib

import pytest

API_PATH = pathlib.Path(__file__).resolve().parent.parent / "dpdp_tool" / "api.py"
CONFIG_PATH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "dpdp_tool" / "public" / "dpdp-config.json"
)


@pytest.fixture(scope="session")
def config():
    """The real dpdp-config.json — single source of truth for bands/sectors."""
    with open(CONFIG_PATH) as f:
        return json.load(f)


class _PermissionError(Exception):
    pass


def _make_frappe():
    frappe = types.ModuleType("frappe")

    frappe.PermissionError = _PermissionError

    # whitelist is a decorator applied at import time; pass functions through
    def _whitelist(*d_args, **d_kwargs):
        def deco(fn):
            return fn
        return deco

    frappe.whitelist = _whitelist

    def _throw(msg, exc=None):
        raise (exc or Exception)(msg)

    frappe.throw = _throw
    frappe.log_error = lambda *a, **k: None
    frappe.logger = lambda *a, **k: types.SimpleNamespace(
        info=lambda *x, **y: None,
        warning=lambda *x, **y: None,
        error=lambda *x, **y: None,
    )

    # request/headers — overridden per-test for _validate_origin
    frappe.request = types.SimpleNamespace(headers={})

    # db — overridden per-test for get_sector_insights
    frappe.db = types.SimpleNamespace(
        sql=lambda *a, **k: [],
        get_value=lambda *a, **k: None,
        set_value=lambda *a, **k: None,
        commit=lambda *a, **k: None,
    )

    # conf — anthropic key etc.
    frappe.conf = types.SimpleNamespace(get=lambda *a, **k: None)

    frappe.utils = types.SimpleNamespace(
        today=lambda: "2026-07-13",
        get_url=lambda: "https://dpdp.projecttech4dev.org",
    )

    return frappe


@pytest.fixture()
def frappe(monkeypatch):
    """Fresh frappe mock per test; also exposed on the loaded api module."""
    fake = _make_frappe()
    monkeypatch.setitem(sys.modules, "frappe", fake)
    return fake


@pytest.fixture()
def api(frappe):
    """The loaded api.py module, wired to the per-test frappe mock."""
    spec = importlib.util.spec_from_file_location("dpdp_api", API_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
