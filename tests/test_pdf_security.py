"""
PDF generator must not let report text inject HTML or make WeasyPrint load
local files. Report text comes from guests (org name, beneficiaries…) and from
the LLM, which can be steered to echo guest text.
"""

import importlib.util
import json
import pathlib
import types

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent / "dpdp_tool"


@pytest.fixture()
def gen(frappe):
    spec = importlib.util.spec_from_file_location("pdf_generator", ROOT / "pdf_generator.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _weasyprint():
    try:
        import weasyprint
        return weasyprint
    except (ImportError, OSError):  # OSError: pango/cairo libraries missing
        pytest.skip("WeasyPrint not available")


def _fetch(gen, url):
    """WeasyPrint 68+ returns a URLFetcher instance; older versions a plain function."""
    fetcher = gen._url_fetcher()
    return getattr(fetcher, "fetch", fetcher)(url)


# ─────────────────────────────────────────────────────────────────
# Markdown → HTML
# ─────────────────────────────────────────────────────────────────

def test_md_escapes_raw_html(gen):
    out = gen._md_to_html('<script>x</script> <img src="file:///etc/passwd"> **bold**')
    assert "<script>" not in out and "<img" not in out
    assert "&lt;script&gt;" in out and "<strong>bold</strong>" in out


def test_md_links_http_only_and_cannot_break_out_of_href(gen):
    out = gen._md_to_html(
        '[ok](https://example.org/a?x=1&y=2) '
        '[f](file:///site_config.json" rel="attachment) '
        '[j](javascript:alert(1))'
    )
    assert '<a href="https://example.org/a?x=1&amp;y=2">ok</a>' in out
    assert out.count("<a ") == 1
    assert 'href="file' not in out and 'href="javascript' not in out and 'rel="' not in out
    assert "j (javascript:alert(1)" in out          # non-http link shown as text, URL kept


def test_md_link_title_and_entities(gen):
    out = gen._md_to_html('[Act](https://meity.gov.in "DPDP") R&amp;D&nbsp;team')
    assert '<a href="https://meity.gov.in">Act</a>' in out
    assert "R&amp;D" in out and "&amp;amp;" not in out and "&amp;nbsp;" not in out


def test_md_keeps_tables_headings_bullets(gen):
    out = gen._md_to_html("## Plan\n- step one\n\n| A | B |\n|---|---|\n| 1 | 2 |\n")
    assert "<h2>Plan</h2>" in out and "<li>step one</li>" in out
    assert "<th>A</th>" in out and "<td>2</td>" in out


# ─────────────────────────────────────────────────────────────────
# Resource fetcher
# ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "http://169.254.169.254/latest/meta-data/",
    "https://evil.example/x.png",
    "https://projecttech4dev.org/wp-content/uploads/2024/05/13b5fab9b3d478788afed54141951357.png",
    "data:image/png;base64,AAAA",
])
def test_fetcher_refuses_anything_but_the_logo(gen, url):
    _weasyprint()
    with pytest.raises(ValueError):
        _fetch(gen, url)


def test_fetcher_lets_the_embedded_logo_through(gen):
    _weasyprint()
    response = _fetch(gen, gen._logo_data_uri())   # served from the data: URI, no network
    if isinstance(response, dict):   # WeasyPrint < 68: {"string": …} or {"file_obj": …}
        body = response.get("string") or response["file_obj"].read()
    else:
        body = response.read()
    assert body == gen.LOGO_PATH.read_bytes()


def test_cover_embeds_the_bundled_logo(gen):
    assert gen.LOGO_PATH.read_bytes().startswith(b"\x89PNG")
    assert gen._logo_data_uri().startswith("data:image/png;base64,iVBOR")


# ─────────────────────────────────────────────────────────────────
# End to end with real WeasyPrint
# ─────────────────────────────────────────────────────────────────

def test_report_cannot_embed_local_files(gen, frappe, tmp_path, monkeypatch):
    _weasyprint()
    secret = tmp_path / "site_config.json"
    secret.write_text("TOP-SECRET-db_password")
    f = secret.as_uri()
    frappe.utils.formatdate = lambda d, fmt: "31 October 2026"
    cfg = json.load(open(ROOT / "public" / "dpdp-config.json"))
    doc = types.SimpleNamespace(
        org_name='Acme <b>NGO</b>', contact_name=f'<img src="{f}">Ann', sector="Health", org_size="1-20",
        beneficiaries=f'Kids <link rel="attachment" href="{f}">', total_score=20,
        score_consent=4, score_storage=4, score_usage=4, score_rights=4, score_governance=4,
        answers_json="[]",
        executive_summary=f'## Summary\nSee [policy]({f}" rel="attachment) and <img src="{f}">.',
        action_roadmap="## 30-Day\n- step\n",
    )

    pdf = gen.generate_assessment_pdf(doc, cfg)

    assert pdf.startswith(b"%PDF")
    assert b"/EmbeddedFile" not in pdf and b"TOP-SECRET" not in pdf
