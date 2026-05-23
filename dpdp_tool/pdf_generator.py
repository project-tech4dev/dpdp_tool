"""
dpdp_tool/pdf_generator.py
Server-side PDF generation using WeasyPrint.
Called by api.generate_and_attach_pdf().

Section order (agreed):
  1. Cover            — score, org, date, band
  2. Executive Summary — board-level read (Call 1)
  3. Section Scores    — visual quick read
  4. Action Roadmap    — org profile + summary table + 30/90/365 sections
  5. Q&A Breakdown     — audit trail, all 25 questions + why text
  Appendix A: Glossary
  Appendix B: References
"""

import json
import re
import frappe


LOGO_URL = (
    'https://projecttech4dev.org/wp-content/uploads'
    '/2024/05/13b5fab9b3d478788afed54141951357.png'
)

STATIC_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: Helvetica, Arial, sans-serif; font-size: 9pt; color: #1A2B4A; line-height: 1.55; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: Helvetica, Arial, sans-serif; font-size: 9pt; color: #1A2B4A; line-height: 1.55; }

/* ── COVER ── */
.cover { page: cover; background: #1A2B4A; width: 210mm; height: 297mm; padding: 0; position: relative; page-break-after: always; display: flex; flex-direction: column; }
.cover-stripe { position: absolute; left: 0; top: 0; bottom: 0; width: 5mm; background: #E8622A; }
.cover-topbar { background: #fff; padding: 14px 24px 14px 22mm; display: flex; align-items: center; gap: 12px; }
.cover-logo { height: 26px; display: block; }
.cover-logo-divider { width: 1px; height: 22px; background: #DCE0E8; flex-shrink: 0; }
.cover-nav-title { font-size: 11pt; font-weight: 700; color: #1A2B4A; letter-spacing: .04em; text-transform: uppercase; }
.cover-body { padding: 0 18mm 6mm 22mm; flex: 1; display: flex; flex-direction: column; }
.cover-title { color: #fff; font-size: 26pt; font-weight: 300; line-height: 1.2; margin-top: 28mm; margin-bottom: auto; }
.cover-bottom { margin-top: 8mm; }
.cover-org-row { display: flex; align-items: flex-end; justify-content: space-between; gap: 12mm; margin-bottom: 5mm; }
.cover-org { color: #fff; font-size: 15pt; font-weight: 500; line-height: 1.2; }
.cover-meta { color: rgba(255,255,255,.5); font-size: 8pt; margin-top: 3px; }
.cover-score-block { text-align: right; flex-shrink: 0; }
.cover-score { color: #7EB8F0; font-size: 40pt; font-weight: 700; line-height: 1; }
.cover-score-lbl { color: rgba(255,255,255,.4); font-size: 8pt; margin-top: 2px; }
.cover-divider { border: none; border-top: 1px solid rgba(255,255,255,.15); margin: 0 0 5mm; }
.cover-band { color: #fff; font-size: 12pt; font-weight: 500; display: flex; align-items: center; gap: 8px; }
.cover-date { color: rgba(255,255,255,.35); font-size: 8pt; margin-top: 4mm; }


/* ── HEADINGS ── */
h1.section { font-size: 14pt; font-weight: 700; color: #1A2B4A; margin-bottom: 6mm; border-bottom: 1px solid #DCE0E8; padding-bottom: 2mm; }
h2.subsection { font-size: 10pt; font-weight: 700; color: #1D6FB8; margin: 6mm 0 3mm; border-left: 3px solid #1D6FB8; padding-left: 3mm; }

/* ── SCORE CARDS ── */
.sgrid { display: grid; grid-template-columns: 1fr 1fr; gap: 5mm; margin-bottom: 8mm; }
.scard { border: 1px solid #DCE0E8; border-radius: 4px; padding: 5mm; border-top: 3px solid #DCE0E8; }
.scard.high { border-top-color: #1D6FB8; }
.scard.mid  { border-top-color: #D97706; }
.scard.low  { border-top-color: #B91C1C; }
.sc-name { font-size: 7.5pt; color: #4A5568; margin-bottom: 2mm; }
.sc-score { font-size: 16pt; font-weight: 300; color: #1A2B4A; line-height: 1; margin-bottom: 2mm; }
.scard.high .sc-score { color: #1D6FB8; }
.scard.mid  .sc-score { color: #D97706; }
.scard.low  .sc-score { color: #B91C1C; }
.sc-bar { height: 4px; background: #DCE0E8; border-radius: 2px; margin-bottom: 2mm; }
.sc-bar-fill { height: 4px; border-radius: 2px; }
.fill-high { background: #1D6FB8; } .fill-mid { background: #D97706; } .fill-low { background: #B91C1C; }
.sc-lbl { font-size: 7pt; color: #4A5568; }

/* ── ORG PROFILE (top of roadmap page) ── */
.org-profile-pdf { background: #1A2B4A; border-radius: 4px; padding: 5mm; margin-bottom: 6mm; }
.op-pdf-label { font-size: 7pt; color: rgba(255,255,255,.5); text-transform: uppercase; letter-spacing: .08em; margin-bottom: 3mm; }
.op-pdf-table { width: 100%; border-collapse: collapse; font-size: 8.5pt; }
.op-pdf-table td { padding: 2.5px 6px; vertical-align: top; color: #fff; }
.op-pdf-key { color: rgba(255,255,255,.5); font-weight: 500; white-space: nowrap; width: 22%; }

/* ── AI CONTENT ── */
.ai-content { font-size: 8.5pt; line-height: 1.65; }
.ai-content p { margin-bottom: 3mm; }
.ai-content ul { padding-left: 5mm; margin-bottom: 3mm; }
.ai-content ul li { margin-bottom: 1.5mm; }
.ai-content h2 { font-size: 10pt; font-weight: 700; color: #1D6FB8; margin: 5mm 0 2mm; }
.ai-content h3 { font-size: 9pt; font-weight: 700; color: #1A2B4A; margin: 3mm 0 1.5mm; }
.ai-content h4 { font-size: 8.5pt; font-weight: 700; color: #1A2B4A; margin: 2.5mm 0 1mm; }
.ai-content table { width: 100%; border-collapse: collapse; margin: 3mm 0; font-size: 8pt; }
.ai-content th { background: #E8ECF5; color: #1A2B4A; font-weight: 700; padding: 4px 6px; border: 1px solid #DCE0E8; text-align: left; }
.ai-content td { padding: 4px 6px; border: 1px solid #DCE0E8; vertical-align: top; }
.ai-content tr:nth-child(even) td { background: #F7F5F0; }
.ai-content a { color: #1D6FB8; text-decoration: underline; }
.ai-footnote { font-size: 7.5pt; color: #4A5568; font-style: italic; line-height: 1.5; margin: 1mm 0; }

/* ── Q&A BREAKDOWN ── */
.qa-section-hdr { font-size: 8pt; font-weight: 700; color: #1D6FB8; text-transform: uppercase; letter-spacing: .06em; margin: 5mm 0 2mm; }
.qa-row { display: flex; gap: 3mm; align-items: flex-start; padding: 2.5mm 0; border-bottom: 1px solid #F0F0F0; }
.qa-chip { min-width: 20px; height: 14px; border-radius: 2px; font-size: 6.5pt; font-weight: 700; color: #fff; text-align: center; line-height: 14px; flex-shrink: 0; padding: 0 2px; }
.chip-yes  { background: #16A34A; }
.chip-part { background: #D97706; }
.chip-no   { background: #B91C1C; }
.qa-text { flex: 1; }
.qa-q { font-size: 8pt; color: #1A2B4A; margin-bottom: 1mm; }
.qa-why { font-size: 7.5pt; color: #4A5568; font-style: italic; line-height: 1.5; }
.qa-ans { font-size: 7.5pt; font-weight: 700; flex-shrink: 0; min-width: 18mm; text-align: right; }
.ans-yes  { color: #16A34A; } .ans-part { color: #D97706; } .ans-no { color: #B91C1C; }

/* ── GLOSSARY ── */
.gloss-item { margin-bottom: 4mm; padding-bottom: 3mm; border-bottom: 1px solid #F0F0F0; }
.gloss-term { font-size: 8.5pt; font-weight: 700; color: #1A2B4A; }
.gloss-ref  { font-size: 7pt; color: #4A5568; margin-left: 2mm; }
.gloss-def  { font-size: 8pt; color: #4A5568; margin-top: 1mm; line-height: 1.5; }

/* ── REFERENCES ── */
.ref-item { margin-bottom: 3mm; }
.ref-title { font-size: 8.5pt; font-weight: 700; color: #1D6FB8; }
.ref-url   { font-size: 7.5pt; color: #4A5568; }
.ref-note  { font-size: 7.5pt; color: #4A5568; font-style: italic; }

/* ── PAGE BREAKS ── */
.page-break { page-break-before: always; }"""


def _get_pdf_css(org_name):
    """
    Build full PDF CSS. The @page rule is an f-string (needs org_name).
    Static CSS is a plain string — no brace escaping required.
    """
    hdr = f"DPDP READINESS REPORT \u00b7 {org_name.upper()[:40]}"
    page_css = (
        "@page {\n"
        "  size: A4;\n"
        "  margin: 26mm 18mm 20mm 18mm;\n"
        f'  @top-left   {{ content: \"\"; background: #1A2B4A; }}\n'
        f'  @top-center {{ content: \"{hdr}\"; background: #1A2B4A; color: #fff; font-size: 6.5pt; letter-spacing: .06em; font-family: Helvetica, sans-serif; vertical-align: middle; }}\n'
        f'  @top-right  {{ content: \"\"; background: #1A2B4A; }}\n'
        "  @bottom-left  { content: \"Tech4Dev \u00b7 DPDP Readiness Navigator \u00b7 dpdp.projecttech4dev.org\"; font-size: 7pt; color: #4A5568; font-family: Helvetica, sans-serif; }\n"
        "  @bottom-right { content: \"Page \" counter(page) \" of \" counter(pages); font-size: 7pt; color: #4A5568; font-family: Helvetica, sans-serif; }\n"
        "}\n"
        "@page cover {\n"
        "  margin: 0;\n"
        "  @top-left   { content: normal; background: transparent; }\n"
        "  @top-center { content: normal; background: transparent; }\n"
        "  @top-right  { content: normal; background: transparent; }\n"
        "  @bottom-left  { content: none; }\n"
        "  @bottom-right { content: none; }\n"
        "}\n"
    )
    return page_css + STATIC_CSS

# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────

def _md_to_html(text):
    """
    Convert Claude markdown output to PDF-safe HTML.
    Handles: links, tables, footnotes, headings, bold, bullets.
    Does NOT handle italic (Helvetica italic is indistinct in small PDF text).
    """
    if not text:
        return ''

    t = text

    # Links: [text](url) → <a>
    t = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', t)

    # Tables — find header|separator|rows blocks
    def fmt_table(m):
        lines = [l.strip() for l in m.group(0).strip().split('\n')
                 if '|' in l and not re.match(r'^\|[-| :]+\|$', l.strip())]
        if not lines:
            return m.group(0)
        header = lines[0]
        body   = lines[1:]
        ths = ''.join(f'<th>{c.strip()}</th>' for c in header.split('|') if c.strip())
        trs = ''.join(
            '<tr>' + ''.join(f'<td>{c.strip()}</td>' for c in r.split('|') if c.strip()) + '</tr>'
            for r in body
        )
        return f'<table><thead><tr>{ths}</tr></thead><tbody>{trs}</tbody></table>'

    t = re.sub(r'(\|.+\|\n){2,}', fmt_table, t)

    # Footnotes: line starting with * (not **bold**) → footnote paragraph
    t = re.sub(r'^\* ([^*\n].+)$', r'<p class="ai-footnote">* \1</p>', t, flags=re.M)

    # Headings
    t = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', t, flags=re.M)
    t = re.sub(r'^### (.+)$',  r'<h3>\1</h3>', t, flags=re.M)
    t = re.sub(r'^## (.+)$',   r'<h2>\1</h2>', t, flags=re.M)
    t = re.sub(r'^# (.+)$',    r'<h2>\1</h2>', t, flags=re.M)

    # Bold
    t = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', t)

    # Bullets — only - prefix (not * which is footnote)
    t = re.sub(r'^- (.+)$', r'<li>\1</li>', t, flags=re.M)
    t = re.sub(r'(<li>.*</li>\n?)+', r'<ul>\g<0></ul>', t)

    # Paragraphs
    t = re.sub(r'\n\n+', '</p><p>', t)
    t = t.strip()

    return f'<div class="ai-content"><p>{t}</p></div>'


def _parse_roadmap_sections(text):
    """
    Split roadmap markdown into named sections by ## heading.
    Returns dict with keys: 'table', '30', '90', '365'
    """
    sections = {}
    if not text:
        return sections
    parts = re.split(r'^## ', text, flags=re.M)
    for part in parts:
        if not part.strip():
            continue
        nl      = part.find('\n')
        heading = part[:nl].strip().lower() if nl != -1 else part.strip().lower()
        body    = part[nl + 1:].strip() if nl != -1 else ''
        if '30' in heading:
            sections['30']    = body
        elif '90' in heading:
            sections['90']    = body
        elif '365' in heading or 'year' in heading:
            sections['365']   = body
        elif 'summary' in heading or 'table' in heading:
            sections['table'] = body
    return sections


def _build_roadmap_html(action_roadmap):
    """
    Build structured roadmap HTML:
      1. Summary table (extracted and surfaced first)
      2. 30-day actions
      3. 90-day actions
      4. 365-day actions
    Falls back to full markdown-to-HTML if sections can't be parsed.
    """
    if not action_roadmap:
        return '<p style="color:#4A5568">Roadmap not yet generated.</p>'

    secs = _parse_roadmap_sections(action_roadmap)
    parts = []

    if secs.get('table'):
        parts.append(
            '<h2 class="subsection">Action Summary</h2>\n'
            + _md_to_html(secs['table'])
        )

    for key, label in [
        ('30',  '30-Day Priority Actions'),
        ('90',  '90-Day Compliance Foundation'),
        ('365', '365-Day / 1-Year Actions'),
    ]:
        if secs.get(key):
            parts.append(
                f'<h2 class="subsection">{label}</h2>\n'
                + _md_to_html(secs[key])
            )

    # If parsing found nothing, render the whole text
    if not parts:
        return _md_to_html(action_roadmap)

    return '\n'.join(parts)


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────

def generate_assessment_pdf(doc, cfg):
    """
    Build a comprehensive HTML report and convert to PDF via WeasyPrint.
    Returns PDF bytes.

    Section order:
      Cover → Executive Summary → Section Scores →
      Action Roadmap (org profile + summary table + 30/90/365) →
      Q&A Breakdown → Appendix A (Glossary) → Appendix B (References)
    """
    from weasyprint import HTML, CSS

    answers_raw    = json.loads(doc.answers_json or '[]')
    section_scores = {
        'consent':    doc.score_consent    or 0,
        'storage':    doc.score_storage    or 0,
        'usage':      doc.score_usage      or 0,
        'rights':     doc.score_rights     or 0,
        'governance': doc.score_governance or 0,
    }
    questions = cfg['questions']
    sections  = cfg['sections']
    sec_keys  = ['consent', 'storage', 'usage', 'rights', 'governance']

    # ── Per-section score data ──
    sec_data = []
    for i, sec in enumerate(sections):
        sid  = sec_keys[i] if i < len(sec_keys) else sec['id']
        raw  = section_scores.get(sid, 0)
        qs   = [q for q in questions if q['section'] == i]
        maxi = len(qs) * cfg['scoring']['maxPerQuestion']
        pct  = round(raw / maxi * 100) if maxi else 0
        band = 'high' if pct >= 70 else ('mid' if pct >= 40 else 'low')
        lbl  = 'Strong' if pct >= 70 else ('Developing' if pct >= 40 else 'Priority gap')
        sec_data.append({'label': sec['label'], 'raw': raw, 'max': maxi,
                         'pct': pct, 'band': band, 'lbl': lbl})

    # ── Q&A rows ──
    qa_rows = []
    for i, a_obj in enumerate(answers_raw):
        if i >= len(questions):
            break
        pts = a_obj.get('points', 0) if isinstance(a_obj, dict) else 0
        q   = questions[i]
        lbl = 'Yes' if pts == 2 else ('Partially' if pts == 1 else 'No')
        cls = 'yes' if pts == 2 else ('part' if pts == 1 else 'no')
        qa_rows.append({
            'num': i + 1, 'section': sections[q['section']]['label'],
            'sec_idx': q['section'], 'text': q['text'],
            'why': q.get('why', ''), 'answer': lbl, 'cls': cls,
        })

    # ── Band and dates ──
    band_obj = next(
        (b for b in cfg['scoring']['bands'] if doc.total_score >= b['min']),
        cfg['scoring']['bands'][-1]
    )
    date_str = frappe.utils.formatdate(frappe.utils.today(), 'dd MMMM yyyy')

    # ── Rendered AI content ──
    summary_html         = _md_to_html(doc.executive_summary or '')
    roadmap_body_html    = _build_roadmap_html(doc.action_roadmap or '')

    # ── Score cards HTML ──
    score_cards_html = ''.join(f'''
  <div class="scard {sd['band']}">
    <div class="sc-name">Section {i+1} · {sd['label']}</div>
    <div class="sc-score">{sd['raw']}/{sd['max']}</div>
    <div class="sc-bar"><div class="sc-bar-fill fill-{sd['band']}" style="width:{sd['pct']}%"></div></div>
    <div class="sc-lbl">{sd['lbl']} · {sd['pct']}%</div>
  </div>''' for i, sd in enumerate(sec_data))

    # ── Beneficiary row (conditional) ──
    bene_row = (
        f"<tr><td class='op-pdf-key'>Beneficiaries</td>"
        f"<td colspan='3'>{doc.beneficiaries}</td></tr>"
        if doc.beneficiaries else ''
    )

    # ═══════════════════════════════════════════════════════════════
    # HTML DOCUMENT
    # Order: Cover → Summary → Scores → Roadmap → Q&A → Appendices
    # ═══════════════════════════════════════════════════════════════
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>{_get_pdf_css(doc.org_name)}</style>
</head>
<body>

<!-- ══ 1. COVER ══════════════════════════════════════════════════ -->
<div class="cover">
  <div class="cover-stripe"></div>

  <!-- White top bar: logo + DPDP Navigator title -->
  <div class="cover-topbar">
    <img class="cover-logo" src="{LOGO_URL}" alt="Tech4Dev">
    <div class="cover-logo-divider"></div>
    <div class="cover-nav-title">DPDP Readiness Navigator</div>
  </div>

  <div class="cover-body">
    <!-- Report title — pushed down from top bar -->
    <div class="cover-title">DPDP Compliance<br>Readiness Report</div>

    <!-- Bottom block: org + score side by side, then band -->
    <div class="cover-bottom">
      <div class="cover-org-row">
        <div>
          <div class="cover-org">{doc.org_name}</div>
          <div class="cover-meta">{doc.sector} · {doc.org_size} · {doc.contact_name or doc.org_name}</div>
        </div>
        <div class="cover-score-block">
          <div class="cover-score">{int(doc.total_score)}/50</div>
          <div class="cover-score-lbl">overall score</div>
        </div>
      </div>
      <hr class="cover-divider">
      <div class="cover-band">{band_obj['emoji']} {band_obj['label']}</div>
      <div class="cover-date">Assessed: {date_str}</div>
    </div>
  </div>
</div>

<!-- ══ 2. EXECUTIVE SUMMARY ══════════════════════════════════════ -->
<div class="page-break">
<h1 class="section">Executive Summary</h1>
{summary_html if summary_html else '<p style="color:#4A5568">Summary not yet generated.</p>'}
</div>

<!-- ══ 3. SECTION SCORE SUMMARY ══════════════════════════════════ -->
<div class="page-break">
<h1 class="section">Section Score Summary</h1>
<div class="sgrid">
{score_cards_html}
</div>
</div>

<!-- ══ 4. ACTION ROADMAP ══════════════════════════════════════════ -->
<div class="page-break">
<h1 class="section">Action Roadmap</h1>

{roadmap_body_html}
</div>

<!-- ══ 5. Q&A BREAKDOWN ══════════════════════════════════════════ -->
<div class="page-break">
<h1 class="section">Question-by-Question Breakdown</h1>
<p style="font-size:8pt;color:#4A5568;margin-bottom:5mm">
  All 25 assessment questions, your response, and the compliance rationale for each.
  This section is the audit trail for your assessment.
</p>
"""

    # Q&A rows grouped by section
    for si, sec in enumerate(sections):
        rows = [r for r in qa_rows if r['sec_idx'] == si]
        if not rows:
            continue
        html += f'<div class="qa-section-hdr">Section {si+1} — {sec["label"]}</div>\n'
        for r in rows:
            html += f"""<div class="qa-row">
  <div class="qa-chip chip-{r['cls']}">Q{r['num']}</div>
  <div class="qa-text">
    <div class="qa-q">{r['text']}</div>
    {'<div class="qa-why">' + r['why'] + '</div>' if r['why'] else ''}
  </div>
  <div class="qa-ans ans-{r['cls']}">{r['answer']}</div>
</div>\n"""

    html += '</div>\n'

    # ══ APPENDIX A: GLOSSARY ══════════════════════════════════════
    html += f"""
<div class="page-break">
<h1 class="section">Appendix A — Key Terms</h1>
<p style="font-size:8pt;color:#4A5568;margin-bottom:5mm">
  Plain-language definitions of DPDP Act terminology used in this report.
</p>
"""
    for g in cfg['glossary']:
        html += f"""<div class="gloss-item">
  <span class="gloss-term">{g['term']}</span>
  <span class="gloss-ref"> · {g['reference']}</span>
  <div class="gloss-def">{g['definition']}</div>
</div>\n"""

    # ══ APPENDIX B: REFERENCES ════════════════════════════════════
    html += f"""</div>

<div class="page-break">
<h1 class="section">Appendix B — Further Reading</h1>
<p style="font-size:8pt;color:#4A5568;margin-bottom:5mm">
  Validated references for DPDP Act guidance. All links verified at time of publication.
</p>
"""
    for r in cfg['references']:
        html += f"""<div class="ref-item">
  <div class="ref-title">{r['title']}</div>
  <div class="ref-url">{r['url']}</div>
  {'<div class="ref-note">' + r['note'] + '</div>' if r.get('note') else ''}
</div>\n"""

    html += '</div>\n</body>\n</html>'

    # ── Render to PDF ──
    return HTML(
        string=html,
        base_url=frappe.utils.get_url()
    ).write_pdf(
        stylesheets=[CSS(string=_get_pdf_css(doc.org_name))]
    )


def send_report_email(doc, file_doc):
    """Email the completed report to the assessor."""
    cfg  = _get_config_cached()
    band = next(
        (b for b in cfg['scoring']['bands'] if doc.total_score >= b['min']),
        cfg['scoring']['bands'][-1]
    )
    frappe.sendmail(
        recipients=[doc.org_email],
        subject=f'Your DPDP Readiness Report — {doc.org_name}',
        template='DPDP Assessment Report',
        args={
            'doc':        doc,
            'band_label': band['label'],
            'band_emoji': band['emoji'],
            'site_url':   frappe.utils.get_url(),
        },
        attachments=[{'fname': file_doc.file_name, 'fid': file_doc.name}]
    )


def _get_config_cached():
    """Import config loader from api module to avoid duplication."""
    from dpdp_tool.api import _get_config
    return _get_config()
