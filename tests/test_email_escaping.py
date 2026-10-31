"""
Guest-typed fields (org name, contact name, email) must not inject HTML into
emails: the report email goes to an address the guest chooses, so markup there
is a ready-made phishing link sent from our domain.
"""

import json
import pathlib
import sys
import types

import pytest
from jinja2.sandbox import SandboxedEnvironment

ROOT = pathlib.Path(__file__).resolve().parent.parent / "dpdp_tool"
EVIL = '<a href="https://evil.example/login">Download your report</a>'


def _doc(**kw):
    row = dict(name="DPDP-0123456789abcdef", org_name="Acme", contact_name=EVIL,
               org_email='x@y.org"><img src=x>', total_score=20)
    row.update(kw)
    return types.SimpleNamespace(**row)


def test_report_template_escapes_the_greeting():
    tmpl = json.load(open(ROOT / "fixtures" / "email_template_assessment_report.json"))[0]
    env = SandboxedEnvironment()          # like Frappe's: no autoescape
    for field in ("response_html", "response"):
        out = env.from_string(tmpl[field]).render(doc=_doc(), band_label="Basic", band_emoji="",
                                                  site_url="https://dpdp.projecttech4dev.org")
        assert EVIL not in out and "&lt;a href=&#34;https://evil.example/login&#34;&gt;" in out


def test_fallback_report_email_escapes_the_greeting(api, frappe, tmp_path, config):
    pdf = tmp_path / "r.pdf"
    pdf.write_bytes(b"%PDF")
    sent = []
    api._get_config = lambda: config
    api._render_email_template = lambda *a, **k: None          # template missing → fallback
    frappe.get_doc = lambda *a, **k: types.SimpleNamespace(get_full_path=lambda: str(pdf))
    frappe.sendmail = lambda **k: sent.append(k)

    api._send_report_email(_doc(), types.SimpleNamespace(name="F1", file_name="DPDP_Report_x.pdf"))

    assert EVIL not in sent[0]["message"] and "&lt;a href=" in sent[0]["message"]


@pytest.mark.parametrize("job", ["run_summary_call", "run_roadmap_call"])
def test_admin_failure_alerts_escape_guest_fields(api, frappe, job):
    sent = []
    frappe.conf.get = lambda key, default=None: None            # no API key → the job fails
    frappe.get_doc = lambda *a, **k: _doc()
    frappe.sendmail = lambda **k: sent.append(k)
    frappe.enqueue = lambda *a, **k: None
    sys.modules.setdefault("anthropic", types.ModuleType("anthropic"))

    getattr(api, job)("DPDP-0123456789abcdef")

    message = sent[0]["message"]
    assert EVIL not in message and "&lt;a href=" in message
    assert "<img" not in message                                  # email field escaped too


def test_unused_send_report_email_is_gone():
    assert "def send_report_email" not in (ROOT / "pdf_generator.py").read_text()
