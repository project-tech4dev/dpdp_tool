"""Business-logic tests for dpdp_tool.api. See conftest.py for the harness."""

import datetime
import json


# ─────────────────────────────────────────────────────────────────
# _parse_sectors
# ─────────────────────────────────────────────────────────────────

import sys
import types

import pytest


def test_parse_sectors_list(api):
    assert api._parse_sectors(["Health", "Education"]) == "Health, Education"


def test_parse_sectors_list_strips_and_drops_blanks(api):
    assert api._parse_sectors(["Health ", "", "  "]) == "Health"


def test_parse_sectors_json_string_list(api):
    assert api._parse_sectors('["Health", "Education"]') == "Health, Education"


def test_parse_sectors_plain_string_is_stripped(api):
    assert api._parse_sectors("  Health  ") == "Health"


def test_parse_sectors_empty_and_none(api):
    assert api._parse_sectors("") == ""
    assert api._parse_sectors(None) == ""


def test_parse_sectors_non_string_coerced(api):
    assert api._parse_sectors(5) == "5"


# ─────────────────────────────────────────────────────────────────
# _section_scores_from_doc
# ─────────────────────────────────────────────────────────────────

def _doc(**overrides):
    base = dict(
        org_name="SENTINEL_ORG", org_email="sentinel@pii.example",
        contact_name="SENTINEL_CONTACT",
        sector="Education", org_size="20-100 staff",
        beneficiaries="Children in rural communities", total_score=24,
        score_consent=4, score_storage=6, score_usage=5,
        score_rights=4, score_governance=5, answers_json="[]",
    )
    base.update(overrides)
    return types.SimpleNamespace(**base)


def test_section_scores_from_doc_maps_fields(api):
    scores = api._section_scores_from_doc(_doc())
    assert scores == {
        "consent": 4, "storage": 6, "usage": 5,
        "rights": 4, "governance": 5,
    }


def test_section_scores_from_doc_none_becomes_zero(api):
    scores = api._section_scores_from_doc(_doc(score_consent=None, score_rights=None))
    assert scores["consent"] == 0
    assert scores["rights"] == 0


# ─────────────────────────────────────────────────────────────────
# _build_gap_answers  — only No(0)/Partially(1) kept; Yes(>=2) dropped
# ─────────────────────────────────────────────────────────────────

def test_gap_answers_keeps_only_gaps(api):
    answers = json.dumps([
        {"q": 1, "section": "Consent", "text": "Q1", "why": "w1", "points": 2},
        {"q": 2, "section": "Consent", "text": "Q2", "why": "w2", "points": 1},
        {"q": 3, "section": "Storage", "text": "Q3", "why": "w3", "points": 0},
    ])
    out = api._build_gap_answers(answers)
    assert "Q1" not in out          # Yes dropped
    assert "Q2" in out and "Partially" in out
    assert "Q3" in out and "No" in out


def test_gap_answers_all_yes_message(api):
    answers = json.dumps([{"q": 1, "section": "C", "text": "Q1", "points": 2}])
    assert api._build_gap_answers(answers) == "All questions answered Yes — no gaps."


def test_gap_answers_bad_json(api):
    assert api._build_gap_answers("{not json") == "Answers not available."


def test_gap_answers_empty(api):
    assert api._build_gap_answers("") == "All questions answered Yes — no gaps."
    assert api._build_gap_answers(None) == "All questions answered Yes — no gaps."


def test_gap_answers_skips_non_dict_entries(api):
    answers = json.dumps(["a string", 42, {"q": 1, "section": "C", "text": "Q1", "points": 0}])
    out = api._build_gap_answers(answers)
    assert "Q1" in out
    assert out.count("\n") == 0     # only the one valid gap line


def test_gap_answers_truncates_text_and_why(api):
    answers = json.dumps([{
        "q": 1, "section": "C",
        "text": "T" * 200, "why": "W" * 200, "points": 0,
    }])
    out = api._build_gap_answers(answers)
    assert "T" * 120 in out and "T" * 121 not in out
    assert "W" * 100 in out and "W" * 101 not in out


# ─────────────────────────────────────────────────────────────────
# _fallback  — deterministic offline recommendation
# ─────────────────────────────────────────────────────────────────

def test_fallback_has_expected_headings(api):
    out = api._fallback({"score_consent": 4}, 24)
    for heading in ("## 30-Day Priority Actions",
                    "## 90-Day Compliance Foundation",
                    "## 1-Year Compliance Habits",
                    "## Summary Table"):
        assert heading in out


def test_fallback_accepts_json_string_scores(api):
    out = api._fallback(json.dumps({"score_consent": 4}), 24)
    assert "## 30-Day Priority Actions" in out


def test_fallback_bad_string_does_not_crash(api):
    out = api._fallback("{not json", 24)
    assert "## 30-Day Priority Actions" in out


def test_fallback_is_static_regardless_of_scores(api):
    """Characterization: output does not vary with the scores passed.
    _fallback computes lowest-2 sections (gap_names) but never uses them —
    see note flagged to maintainer. Locks current behavior."""
    low_consent = api._fallback({"consent": 0, "storage": 10}, 10)
    low_storage = api._fallback({"consent": 10, "storage": 0}, 10)
    assert low_consent == low_storage


# ─────────────────────────────────────────────────────────────────
# Prompt builders — PII must never reach the LLM.
# CLAUDE.md: org_name/contact/email excluded from Claude calls.
# ─────────────────────────────────────────────────────────────────

PII_SENTINELS = ("SENTINEL_ORG", "SENTINEL_CONTACT", "sentinel@pii.example")


def _assert_no_pii(text):
    for sentinel in PII_SENTINELS:
        assert sentinel not in text, f"PII leaked into prompt: {sentinel!r}"


def test_summary_prompt_excludes_pii(api):
    scores = api._section_scores_from_doc(_doc())
    _assert_no_pii(api._build_summary_prompt(_doc(), scores))


def test_summary_prompt_includes_allowed_context(api):
    scores = api._section_scores_from_doc(_doc())
    out = api._build_summary_prompt(_doc(), scores)
    assert "Education" in out                       # sector
    assert "20-100 staff" in out                    # org_size
    assert "Children in rural communities" in out   # beneficiaries


def test_roadmap_prompt_excludes_pii(api):
    scores = api._section_scores_from_doc(_doc())
    gaps = api._build_gap_answers(_doc().answers_json)
    _assert_no_pii(api._build_roadmap_prompt(_doc(), scores, gaps))


def test_roadmap_prompt_embeds_gap_summary(api):
    scores = api._section_scores_from_doc(_doc())
    out = api._build_roadmap_prompt(_doc(), scores, "MY_GAP_MARKER")
    assert "MY_GAP_MARKER" in out


def test_build_prompt_excludes_pii_and_embeds_answers(api):
    out = api._build_prompt(
        sector="Education", org_size="20-100 staff",
        beneficiaries="Children", total_score=24, max_score=50,
        section_scores={"consent": 4}, answers="MY_GAP_MARKER",
    )
    _assert_no_pii(out)
    assert "MY_GAP_MARKER" in out
    assert "Education" in out


# ─────────────────────────────────────────────────────────────────
# _validate_origin — security control on whitelisted guest endpoints
# ─────────────────────────────────────────────────────────────────

def test_validate_origin_allows_live_site(api, frappe):
    frappe.request.headers = {"Origin": "https://dpdp.projecttech4dev.org"}
    api._validate_origin()  # no raise


def test_validate_origin_rejects_foreign_origin(api, frappe):
    frappe.request.headers = {"Origin": "https://evil.example.com"}
    with pytest.raises(frappe.PermissionError):
        api._validate_origin()


def test_validate_origin_falls_back_to_referer(api, frappe):
    frappe.request.headers = {"Referer": "https://evil.example.com/x"}
    with pytest.raises(frappe.PermissionError):
        api._validate_origin()


def test_validate_origin_allows_missing_headers(api, frappe):
    frappe.request.headers = {}
    api._validate_origin()  # empty source → guest allowed, no raise


# ─────────────────────────────────────────────────────────────────
# Scoring bands — config integrity + boundary selection.
# Mirrors the selection expression used in _send_report_email / pdf_generator.
# ─────────────────────────────────────────────────────────────────

def _band_label(cfg, score):
    bands = cfg["scoring"]["bands"]
    return next((b for b in bands if score >= b["min"]), bands[-1])["label"]


def test_bands_cover_zero_and_are_descending(config):
    bands = config["scoring"]["bands"]
    mins = [b["min"] for b in bands]
    assert mins == sorted(mins, reverse=True)   # highest-min first
    assert bands[-1]["min"] == 0                # a band catches score 0


@pytest.mark.parametrize("score,expected", [
    (50, "Strong Readiness"),
    (46, "Strong Readiness"),
    (45, "Moderate Readiness"),
    (36, "Moderate Readiness"),
    (35, "Basic Readiness — Needs Work"),
    (21, "Basic Readiness — Needs Work"),
    (20, "High Risk — Not Ready"),
    (0,  "High Risk — Not Ready"),
])
def test_band_boundaries(config, score, expected):
    assert _band_label(config, score) == expected


# ─────────────────────────────────────────────────────────────────
# get_sector_insights — dashboard aggregation
# ─────────────────────────────────────────────────────────────────

class _Row(dict):
    """Mimics frappe._dict: supports both row.field and row['field']."""
    def __getattr__(self, k):
        return self[k]


def _insight_row(sector, total):
    return _Row(
        sector=sector, total_score=total,
        score_consent=total // 5, score_storage=total // 5,
        score_usage=total // 5, score_rights=total // 5,
        score_governance=total // 5,
    )


def _wire_insights(api, frappe, monkeypatch, rows, sectors):
    monkeypatch.setattr(api, "_get_config", lambda: {"sectors": sectors})
    frappe.db.sql = lambda *a, **k: rows


def test_insights_suppresses_sectors_under_three(api, frappe, monkeypatch):
    rows = [_insight_row("Education", 40) for _ in range(3)]
    rows += [_insight_row("Health & Nutrition", 30)]   # only 1 → suppressed
    _wire_insights(api, frappe, monkeypatch, rows, ["Education", "Health & Nutrition"])

    results = api.get_sector_insights()
    sectors = {r["sector"] for r in results}
    assert "Education" in sectors
    assert "Health & Nutrition" not in sectors


def test_insights_all_sectors_row_first(api, frappe, monkeypatch):
    rows = [_insight_row("Education", 40) for _ in range(3)]
    _wire_insights(api, frappe, monkeypatch, rows, ["Education"])

    results = api.get_sector_insights()
    assert results[0]["sector"] == "All Sectors"
    assert results[0]["submission_count"] == 3


def test_insights_averages_are_correct(api, frappe, monkeypatch):
    rows = [_insight_row("Education", s) for s in (30, 40, 50)]
    _wire_insights(api, frappe, monkeypatch, rows, ["Education"])

    edu = next(r for r in api.get_sector_insights() if r["sector"] == "Education")
    assert edu["avg_overall"] == 40.0
    assert edu["submission_count"] == 3


def test_insights_ignores_unknown_sectors(api, frappe, monkeypatch):
    rows = [_insight_row("NotARealSector", 40) for _ in range(3)]
    _wire_insights(api, frappe, monkeypatch, rows, ["Education"])

    results = api.get_sector_insights()
    # unknown sector never bucketed; only the All-Sectors summary (rows>=3) remains
    assert all(r["sector"] in ("All Sectors",) for r in results)


def test_insights_empty_when_too_few_rows(api, frappe, monkeypatch):
    rows = [_insight_row("Education", 40) for _ in range(2)]
    _wire_insights(api, frappe, monkeypatch, rows, ["Education"])
    assert api.get_sector_insights() == []


def test_insights_multi_sector_row_counts_in_each(api, frappe, monkeypatch):
    rows = [_insight_row("Education, Health & Nutrition", 40) for _ in range(3)]
    _wire_insights(api, frappe, monkeypatch, rows, ["Education", "Health & Nutrition"])

    counts = {r["sector"]: r["submission_count"] for r in api.get_sector_insights()}
    assert counts["Education"] == 3
    assert counts["Health & Nutrition"] == 3


# ─────────────────────────────────────────────────────────────────
# get_events
# ─────────────────────────────────────────────────────────────────

def test_event_status_future_today_past_and_undated(api):
    assert api._event_status("2026-08-01", "2026-07-13") == "Upcoming"
    assert api._event_status("2026-07-13", "2026-07-13") == "Upcoming"
    assert api._event_status("2026-07-12", "2026-07-13") == "Past"
    assert api._event_status(None, "2026-07-13") == "Upcoming"


def _wire_events(frappe, events, links=(), people=()):
    calls = []
    rows = {"DPDP Event": events, "DPDP Event Speaker": links, "DPDP Speaker": people}
    def _get_all(doctype, **kw):
        calls.append((doctype, kw))
        return [dict(r) for r in rows[doctype]]
    frappe.get_all = _get_all
    return calls


def test_get_events_status_order_and_date_serialised(api, frappe):
    _wire_events(frappe, [
        {"name": "EVT-1", "title": "Old", "event_date": datetime.date(2026, 6, 1)},
        {"name": "EVT-2", "title": "TBC", "event_date": None},
        {"name": "EVT-3", "title": "Soon", "event_date": datetime.date(2026, 9, 1)},
    ])
    events = api.get_events()
    assert [e["title"] for e in events] == ["TBC", "Soon", "Old"]
    assert [e["status"] for e in events] == ["Upcoming", "Upcoming", "Past"]
    assert events[1]["event_date"] == "2026-09-01"


def test_get_events_only_requests_published(api, frappe):
    seen = {}
    def _get_all(doctype, **kw):
        seen.update(doctype=doctype, **kw)
        return []
    frappe.get_all = _get_all
    assert api.get_events() == []
    assert seen["doctype"] == "DPDP Event"
    assert seen["filters"] == {"published": 1}


def test_get_events_attaches_speakers_in_order(api, frappe):
    calls = _wire_events(
        frappe,
        [{"name": "EVT-1", "title": "A", "event_date": None},
         {"name": "EVT-2", "title": "B", "event_date": None}],
        links=[{"parent": "EVT-1", "speaker": "SPK-2"},
               {"parent": "EVT-1", "speaker": "SPK-1"},
               {"parent": "EVT-2", "speaker": "SPK-1"}],
        people=[{"name": "SPK-1", "speaker_name": "One", "role": "R1", "linkedin_url": "u1"},
                {"name": "SPK-2", "speaker_name": "Two", "role": None, "linkedin_url": None}],
    )
    by_name = {e["name"]: e for e in api.get_events()}
    assert [s["speaker_name"] for s in by_name["EVT-1"]["speakers"]] == ["Two", "One"]
    assert [s["speaker_name"] for s in by_name["EVT-2"]["speakers"]] == ["One"]
    assert "name" not in by_name["EVT-1"]["speakers"][0]
    assert calls[1][1]["filters"]["parent"] == ["in", ["EVT-1", "EVT-2"]]
    assert calls[2][0] == "DPDP Speaker"


def test_get_events_skips_links_to_missing_speakers(api, frappe):
    _wire_events(
        frappe,
        [{"name": "EVT-1", "title": "A", "event_date": None}],
        links=[{"parent": "EVT-1", "speaker": "SPK-9"}],
        people=[],
    )
    assert api.get_events()[0]["speakers"] == []


def test_get_events_skips_speaker_query_when_no_events(api, frappe):
    calls = _wire_events(frappe, [])
    assert api.get_events() == []
    assert [c[0] for c in calls] == ["DPDP Event"]


def test_get_events_returns_empty_on_error(api, frappe):
    def _boom(*a, **k):
        raise RuntimeError("db down")
    frappe.get_all = _boom
    assert api.get_events() == []


# ─────────────────────────────────────────────────────────────────
# get_tagged_articles (Tech4Dev blog via WordPress REST)
# ─────────────────────────────────────────────────────────────────

def _wp_post(**kw):
    post = {
        "date": "2026-10-13T09:30:00",
        "link": "https://projecttech4dev.org/helping-ngos/",
        "title": {"rendered": "Helping NGOs &#8211; DPDP"},
        "excerpt": {"rendered": "<p>At a roundtable &amp; more [&hellip;]</p>\n"},
        "author": 42,
        "jetpack_featured_media_url": "https://projecttech4dev.org/wp-content/uploads/2026/10/cohort.jpg",
    }
    post.update(kw)
    return post


def _wire_wp(monkeypatch, responses):
    calls = []

    def _get(url, params=None, timeout=None):
        calls.append(url)
        body = responses[url.rsplit("/", 1)[-1]]
        if isinstance(body, Exception):
            raise body
        return types.SimpleNamespace(json=lambda: body)

    monkeypatch.setitem(sys.modules, "requests", types.SimpleNamespace(get=_get))
    return calls


def test_wp_post_to_article_cleans_text_and_formats_date(api):
    a = api._wp_post_to_article(_wp_post(), {42: "Shweta Chaudhury"})
    assert a == {
        "title": "Helping NGOs – DPDP",
        "summary": "At a roundtable & more…",
        "date": "13 Oct 2026",
        "author": "Shweta Chaudhury",
        "image": "https://projecttech4dev.org/wp-content/uploads/2026/10/cohort.jpg",
        "link": "https://projecttech4dev.org/helping-ngos/",
    }


def test_wp_post_to_article_drops_offsite_link_and_trims_summary(api):
    long = "<p>" + "word " * 100 + "</p>"
    a = api._wp_post_to_article(_wp_post(link="https://evil.example/x", excerpt={"rendered": long},
                                         jetpack_featured_media_url="https://evil.example/x.png"))
    assert a["link"] == "" and a["image"] == "" and a["author"] == ""
    assert len(a["summary"]) <= 181 and a["summary"].endswith("…")


def test_get_tagged_articles_fetches_tag_then_posts(api, monkeypatch):
    calls = _wire_wp(monkeypatch, {"tags": [{"id": 7}], "posts": [_wp_post()],
                                   "users": [{"id": 42, "name": "Shweta Chaudhury"}]})
    articles = api.get_tagged_articles("dpdp-ngo-cohort-1")
    assert [(a["title"], a["author"]) for a in articles] == [("Helping NGOs – DPDP", "Shweta Chaudhury")]
    assert [c.rsplit("/", 1)[-1] for c in calls] == ["tags", "posts", "users"]


def test_get_tagged_articles_keeps_posts_if_author_lookup_fails(api, monkeypatch):
    _wire_wp(monkeypatch, {"tags": [{"id": 7}], "posts": [_wp_post()], "users": RuntimeError("403")})
    articles = api.get_tagged_articles("dpdp")
    assert [(a["title"], a["author"]) for a in articles] == [("Helping NGOs – DPDP", "")]


def test_get_tagged_articles_unknown_tag_is_empty(api, monkeypatch):
    calls = _wire_wp(monkeypatch, {"tags": []})
    assert api.get_tagged_articles("nope") == []
    assert len(calls) == 1


def test_get_tagged_articles_network_error_returns_empty(api, monkeypatch):
    _wire_wp(monkeypatch, {"tags": RuntimeError("timeout")})
    assert api.get_tagged_articles("dpdp-ngo-cohort-1") == []
