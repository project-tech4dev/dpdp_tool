"""Legacy recommendation endpoints refuse every call unless dpdp_legacy_reco_enabled is set."""

import pytest


# ─────────────────────────────────────────────────────────────────
# Legacy recommendation endpoints — off unless dpdp_legacy_reco_enabled
# ─────────────────────────────────────────────────────────────────

LEGACY_CALLS = {
    "get_recommendations": dict(docname="DPDP-0123456789abcdef", sector="Health", org_size="1-20",
                                beneficiaries="x", total_score=10, max_score=50,
                                section_scores="{}", answers="[]"),
    "check_reco": dict(docname="DPDP-0123456789abcdef"),
    "patch_assessment_reco": dict(docname="DPDP-ASSESS-0042", recommendations="junk"),
}


@pytest.mark.parametrize("endpoint", sorted(LEGACY_CALLS))
def test_legacy_endpoints_refuse_when_disabled(api, frappe, endpoint):
    side_effects, logged = [], []
    frappe.enqueue = lambda *a, **k: side_effects.append("enqueue")
    frappe.get_doc = lambda *a, **k: side_effects.append("get_doc")
    frappe.db.get_value = lambda *a, **k: side_effects.append("get_value")
    frappe.log_error = lambda msg, title=None: logged.append((msg, title))

    with pytest.raises(frappe.PermissionError):
        getattr(api, endpoint)(**LEGACY_CALLS[endpoint])

    assert side_effects == []                      # nothing ran: no Claude job, no read, no write
    assert logged == [(f"Disabled legacy endpoint called: {endpoint}", "DPDP Legacy Endpoint")]


def test_legacy_endpoint_works_when_switched_on(api, frappe):
    queued = []
    frappe.conf.get = lambda key, default=None: 1 if key == "dpdp_legacy_reco_enabled" else default
    frappe.enqueue = lambda *a, **k: queued.append(k["docname"])
    out = api.get_recommendations(**LEGACY_CALLS["get_recommendations"])
    assert out["status"] == "queued" and queued == ["DPDP-0123456789abcdef"]
