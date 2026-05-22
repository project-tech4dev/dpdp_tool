"""
dpdp_tool/pdf_generator.py
Server-side PDF generation using WeasyPrint + Jinja2.
Called by api.generate_and_attach_pdf().
"""

import json
import frappe
from frappe.utils.jinja import get_jinja_hooks


LOGO_URL = (
    'https://projecttech4dev.org/wp-content/uploads'
    '/2024/05/13b5fab9b3d478788afed54141951357.png'
)

PDF_CSS = """
@page {
  size: A4;
  margin: 18mm 18mm 20mm 18mm;
  @bottom-left  { content: "Tech4Dev · DPDP Readiness Navigator · dpdp.projecttech4dev.org"; font-size: 7pt; color: #4A5568; font-family: Helvetica, sans-serif; }
  @bottom-right { content: "Page " counter(page) " of " counter(pages); font-size: 7pt; color: #4A5568; font-family: Helvetica, sans-serif; }
}
@page cover { margin: 0; }

* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: Helvetica, Arial, sans-serif; font-size: 9pt; color: #1A2B4A; line-height: 1.55; }

/* COVER */
.cover { page: cover; background: #1A2B4A; width: 210mm; height: 297mm; padding: 0; position: relative; page-break-after: always; }
.cover-stripe { position: absolute; left: 0; top: 0; bottom: 0; width: 5mm; background: #1D6FB8; }
.cover-body { padding: 40mm 18mm 18mm 24mm; }
.cover-eyebrow { color: #7EB8F0; font-size: 7.5pt; letter-spacing: .12em; text-transform: uppercase; margin-bottom: 32mm; }
.cover-logo { height: 28px; filter: brightness(0) invert(1); opacity: .85; margin-bottom: 6mm; }
.cover-title { color: #fff; font-size: 24pt; font-weight: 300; line-height: 1.2; margin-bottom: 28mm; }
.cover-score { color: #7EB8F0; font-size: 44pt; font-weight: 700; line-height: 1; margin-bottom: 4mm; }
.cover-score-lbl { color: #A0B9D2; font-size: 9pt; margin-bottom: 14mm; }
.cover-org { color: #fff; font-size: 13pt; margin-bottom: 3mm; }
.cover-meta { color: #8CA5C8; font-size: 8.5pt; margin-bottom: 3mm; }
.cover-band { color: #7EB8F0; font-size: 9pt; margin-top: 6mm; }

/* PAGE HEADER */
.page-hdr { background: #1A2B4A; padding: 3mm 18mm; margin: -18mm -18mm 10mm -18mm; }
.page-hdr span { color: #fff; font-size: 6.5pt; letter-spacing: .06em; text-transform: uppercase; }

/* SECTION HEADING */
h1.section { font-size: 14pt; font-weight: 700; color: #1A2B4A; margin-bottom: 6mm; border-bottom: 1px solid #DCE0E8; padding-bottom: 2mm; }
h2.subsection { font-size: 10pt; font-weight: 700; color: #1D6FB8; margin: 5mm 0 2mm; }
h3.item { font-size: 9pt; font-weight: 700; color: #1A2B4A; margin: 3mm 0 1mm; }

/* SCORE CARDS GRID */
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

/* PRIORITY BAND */
.pb-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 4mm; margin: 6mm 0; }
.pb-col { border-radius: 4px; padding: 4mm; border: 1px solid #DCE0E8; }
.pb-now     { background: #FEF2F2; border-color: rgba(185,28,28,.2); }
.pb-plan    { background: #FEF3CD; border-color: rgba(146,64,14,.2); }
.pb-monitor { background: rgba(22,101,52,.07); border-color: rgba(22,101,52,.2); }
.pb-label { font-size: 7pt; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 2mm; }
.pb-now .pb-label { color: #B91C1C; }
.pb-plan .pb-label { color: #92400E; }
.pb-monitor .pb-label { color: #166534; }
.pb-item { font-size: 8pt; color: #1A2B4A; padding: 1px 0; }
.pb-empty { font-size: 8pt; color: #4A5568; font-style: italic; }

/* AI CONTENT */
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

/* Q&A BREAKDOWN */
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

/* GLOSSARY */
.gloss-item { margin-bottom: 4mm; padding-bottom: 3mm; border-bottom: 1px solid #F0F0F0; }
.gloss-term { font-size: 8.5pt; font-weight: 700; color: #1A2B4A; }
.gloss-ref  { font-size: 7pt; color: #4A5568; margin-left: 2mm; }
.gloss-def  { font-size: 8pt; color: #4A5568; margin-top: 1mm; line-height: 1.5; }

/* REFERENCES */
.ref-item { margin-bottom: 3mm; }
.ref-title { font-size: 8.5pt; font-weight: 700; color: #1D6FB8; }
.ref-url   { font-size: 7.5pt; color: #4A5568; }
.ref-note  { font-size: 7.5pt; color: #4A5568; font-style: italic; }

/* PAGE BREAKS */
.page-break { page-break-before: always; }
"""


def generate_assessment_pdf(doc, cfg):
    """
    Build a comprehensive HTML report and convert to PDF via WeasyPrint.
    Returns PDF bytes.
    """
    from weasyprint import HTML, CSS

    answers_raw    = json.loads(doc.answers_json or '[]')
    # Build section scores from individual DocType fields (not JSON blob)
    section_scores = {
        'consent':    doc.score_consent    or 0,
        'storage':    doc.score_storage    or 0,
        'usage':      doc.score_usage      or 0,
        'rights':     doc.score_rights     or 0,
        'governance': doc.score_governance or 0,
    }
    questions     = cfg['questions']
    sections      = cfg['sections']
    sec_ids       = [s['id'] for s in sections]

    # Compute per-section data
    sec_keys = ['consent', 'storage', 'usage', 'rights', 'governance']
    sec_data = []
    for i, sec in enumerate(sections):
        sid  = sec_keys[i] if i < len(sec_keys) else sec['id']
        raw  = section_scores.get(sid, 0)
        qs   = [q for q in questions if q['section'] == i]
        maxi = len(qs) * cfg['scoring']['maxPerQuestion']
        pct  = round(raw / maxi * 100) if maxi else 0
        band = 'high' if pct >= 70 else ('mid' if pct >= 40 else 'low')
        lbl  = 'Strong' if pct >= 70 else ('Developing' if pct >= 40 else 'Priority gap')
        sec_data.append({
            'label': sec['label'], 'raw': raw, 'max': maxi,
            'pct': pct, 'band': band, 'lbl': lbl
        })

    # Priority band
    pb = {'now': [], 'plan': [], 'monitor': []}
    for i, sd in enumerate(sec_data):
        if sd['pct'] < 40:    pb['now'].append(sections[i]['label'])
        elif sd['pct'] < 70:  pb['plan'].append(sections[i]['label'])
        else:                  pb['monitor'].append(sections[i]['label'])

    # Q&A rows
    qa_rows = []
    for i, a_obj in enumerate(answers_raw):
        if i >= len(questions): break
        pts  = a_obj.get('points', 0) if isinstance(a_obj, dict) else 0
        q    = questions[i]
        lbl  = 'Yes' if pts == 2 else ('Partially' if pts == 1 else 'No')
        cls  = 'yes' if pts == 2 else ('part' if pts == 1 else 'no')
        qa_rows.append({
            'num':     i + 1,
            'section': sections[q['section']]['label'],
            'sec_idx': q['section'],
            'text':    q['text'],
            'why':     q.get('why', ''),
            'answer':  lbl,
            'cls':     cls,
        })

    # Band
    band_obj = next(
        (b for b in cfg['scoring']['bands'] if doc.total_score >= b['min']),
        cfg['scoring']['bands'][-1]
    )

    date_str = frappe.utils.formatdate(frappe.utils.today(), 'dd MMMM yyyy')

    # Markdown → simple HTML (same logic as JS but in Python)
    def md_to_html(text):
        if not text: return ''
        import re
        t = text
        # Tables
        def fmt_table(m):
            rows = [r.strip() for r in m.group(0).strip().split('\n') if '|' in r and not re.match(r'\|[-| :]+\|', r)]
            if not rows: return m.group(0)
            header = rows[0]
            body   = rows[1:]
            ths = ''.join(f'<th>{c.strip()}</th>' for c in header.split('|') if c.strip())
            trs = ''.join(
                '<tr>' + ''.join(f'<td>{c.strip()}</td>' for c in r.split('|') if c.strip()) + '</tr>'
                for r in body
            )
            return f'<table><thead><tr>{ths}</tr></thead><tbody>{trs}</tbody></table>'
        t = re.sub(r'(\|.+\|\n){2,}', fmt_table, t)
        t = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', t, flags=re.M)
        t = re.sub(r'^### (.+)$',  r'<h3>\1</h3>', t, flags=re.M)
        t = re.sub(r'^## (.+)$',   r'<h2>\1</h2>', t, flags=re.M)
        t = re.sub(r'^# (.+)$',    r'<h2>\1</h2>', t, flags=re.M)
        t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
        t = re.sub(r'^[-*] (.+)$', r'<li>\1</li>', t, flags=re.M)
        t = re.sub(r'(<li>.*</li>\n?)+', r'<ul>\g<0></ul>', t)
        t = re.sub(r'\n\n+', '</p><p>', t)
        return f'<div class="ai-content"><p>{t}</p></div>'

    summary_html = md_to_html(doc.executive_summary or '')
    roadmap_html = md_to_html(doc.action_roadmap or '')

    # Build HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>{PDF_CSS}</style>
</head>
<body>

<!-- ── COVER ── -->
<div class="cover">
  <div class="cover-stripe"></div>
  <div class="cover-body">
    <div class="cover-eyebrow">Tech4Dev · DPDP Readiness Navigator</div>
    <img class="cover-logo" src="{LOGO_URL}" alt="Tech4Dev">
    <div class="cover-title">DPDP Compliance<br>Readiness Report</div>
    <div class="cover-score">{doc.total_score}/50</div>
    <div class="cover-score-lbl">Overall readiness score</div>
    <div class="cover-org">{doc.org_name}</div>
    <div class="cover-meta">{doc.sector} · {doc.org_size}</div>
    <div class="cover-meta">Prepared for: {doc.contact_name or doc.org_name}</div>
    <div class="cover-meta">Assessed: {date_str}</div>
    <div class="cover-band">{band_obj['emoji']} {band_obj['label']}</div>
  </div>
</div>

<!-- ── SECTION SCORES ── -->
<div class="page-break">
<div class="page-hdr"><span>DPDP Readiness Report · {doc.org_name.upper()}</span></div>
<h1 class="section">Section Score Summary</h1>
<div class="sgrid">
{"".join(f'''
  <div class="scard {sd['band']}">
    <div class="sc-name">Section {i+1} · {sd['label']}</div>
    <div class="sc-score">{sd['raw']}/{sd['max']}</div>
    <div class="sc-bar"><div class="sc-bar-fill fill-{sd['band']}" style="width:{sd['pct']}%"></div></div>
    <div class="sc-lbl">{sd['lbl']} · {sd['pct']}%</div>
  </div>''' for i, sd in enumerate(sec_data))}
</div>

<h2 class="subsection">Priority Areas</h2>
<div class="pb-grid">
  <div class="pb-col pb-now">
    <div class="pb-label">Address Now</div>
    {"".join(f'<div class="pb-item">{s}</div>' for s in pb['now']) or '<div class="pb-empty">None</div>'}
  </div>
  <div class="pb-col pb-plan">
    <div class="pb-label">Plan &amp; Improve</div>
    {"".join(f'<div class="pb-item">{s}</div>' for s in pb['plan']) or '<div class="pb-empty">None</div>'}
  </div>
  <div class="pb-col pb-monitor">
    <div class="pb-label">Monitor</div>
    {"".join(f'<div class="pb-item">{s}</div>' for s in pb['monitor']) or '<div class="pb-empty">None</div>'}
  </div>
</div>
</div>

<!-- ── EXECUTIVE SUMMARY ── -->
<div class="page-break">
<div class="page-hdr"><span>DPDP Readiness Report · {doc.org_name.upper()}</span></div>
<h1 class="section">Executive Summary</h1>
{summary_html if summary_html else '<p style="color:#4A5568">Summary not yet generated.</p>'}
</div>

<!-- ── ACTION ROADMAP ── -->
<div class="page-break">
<div class="page-hdr"><span>DPDP Readiness Report · {doc.org_name.upper()}</span></div>
<h1 class="section">30 / 90 / 365-Day Action Roadmap</h1>
{roadmap_html if roadmap_html else '<p style="color:#4A5568">Roadmap not yet generated.</p>'}
</div>

<!-- ── Q&A BREAKDOWN ── -->
<div class="page-break">
<div class="page-hdr"><span>DPDP Readiness Report · {doc.org_name.upper()}</span></div>
<h1 class="section">Question-by-Question Breakdown</h1>
"""

    # Group Q&A by section
    for si, sec in enumerate(sections):
        rows = [r for r in qa_rows if r['sec_idx'] == si]
        if not rows: continue
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

    # Appendix A: Glossary
    html += f"""</div>

<!-- ── APPENDIX A: GLOSSARY ── -->
<div class="page-break">
<div class="page-hdr"><span>DPDP Readiness Report · {doc.org_name.upper()}</span></div>
<h1 class="section">Appendix A — Key Terms</h1>
"""
    for g in cfg['glossary']:
        html += f"""<div class="gloss-item">
  <span class="gloss-term">{g['term']}</span>
  <span class="gloss-ref">{g['reference']}</span>
  <div class="gloss-def">{g['definition']}</div>
</div>\n"""

    # Appendix B: References
    html += f"""</div>

<!-- ── APPENDIX B: REFERENCES ── -->
<div class="page-break">
<div class="page-hdr"><span>DPDP Readiness Report · {doc.org_name.upper()}</span></div>
<h1 class="section">Appendix B — Further Reading</h1>
"""
    for r in cfg['references']:
        html += f"""<div class="ref-item">
  <div class="ref-title">{r['title']}</div>
  <div class="ref-url">{r['url']}</div>
  {'<div class="ref-note">' + r['note'] + '</div>' if r.get('note') else ''}
</div>\n"""

    html += '</div>\n</body>\n</html>'

    # Render to PDF
    pdf = HTML(
        string=html,
        base_url=frappe.utils.get_url()
    ).write_pdf(
        stylesheets=[CSS(string=PDF_CSS)]
    )

    return pdf
