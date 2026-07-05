# CLAUDE.md — Project Guidelines

## Privacy & PII

This tool processes personal data submitted by NGOs (org name, contact name, email, beneficiary descriptions, assessment answers). Apply these rules on every change:

- **Never add PII to URLs or query parameters.** Use POST with a JSON/form body. URL parameters appear in server access logs, browser history, and referrer headers.
- **Never log PII to the browser console.** Console messages must be generic stage markers only (e.g. `[dpdp] storing assessment`) — no data values, no URLs, no response bodies.
- **Never include org names or contact details in LLM prompts** unless strictly required for the output. The Anthropic API currently receives: sector, org size, beneficiaries description, section scores, and gap question text. `org_name` must not be included.
- **Audit any new external call** (fetch, API, analytics, third-party SDK) before adding it. Confirm what data is sent and where it goes. No analytics or tracking SDKs are used by design.
- **API keys** must be stored in Frappe site config (`frappe.conf.get(...)`), never hardcoded in source files.

## Page Structure & Shared Components

Pages are being migrated to a base template in a **strangler fig pattern** — new pages use the base template first; `index.html` and `assess.html` remain self-contained until the approach is validated on Frappe Cloud.

**Base template:** `dpdp_tool/templates/dpdp_base.html`
Owns the `<html>`, `<head>`, nav, footer, and font loading.

**Frappe template path:** Frappe's Jinja2 loader uses `PackageLoader(app, ".")` with the app module root (`dpdp_tool/dpdp_tool/`) as the search base. The correct extends path is:
```
{% extends "templates/dpdp_base.html" %}
```
Not `"dpdp_base.html"` — that looks for the file at the package root, not inside `templates/`.

**Adding a new page:**
1. Create `www/<page>.html` with `{% extends "templates/dpdp_base.html" %}` and `www/<page>.py` setting `context.asset_v`
2. Set `context.nav_mode = "minimal"` only for focused task flows (e.g. assess)
3. Add the page to the nav in `dpdp_base.html` if it should appear in navigation

Nav links use absolute paths (`/`, `/#why`, `/#dashboard`) so they resolve correctly from every page.

**Migrating `index.html` / `assess.html`:** Only do this after the new pages are confirmed working on Frappe Cloud. Follow the same extends pattern.

## CSS — Reuse First

Before adding any CSS class, search `dpdp.css` for an existing class that covers the need. **Never use inline `style` attributes** — always create or reuse a CSS class. If a pattern appears on more than one element, promote it to a class and check with the user first. The design token variables in `:root` must be used for all colours — no raw hex or rgba values outside the token definitions themselves.

## End-to-End Verification

For any significant change, verify with Playwright before reporting complete:

```bash
pip3 install jinja2 playwright --break-system-packages
python3 -m playwright install chromium
```

Strip Frappe front matter, render with Jinja2 `FileSystemLoader` over `templates/` and `www/`, inline `dpdp.css`, then screenshot with Playwright. Pass `asset_v` and `nav_mode` explicitly as context.

**Always verify when:** nav/footer/base template changes, new pages added, JS flow changes (assessment submit → polling → results), CSS layout changes, backend changes affecting rendered output.

Do not mark a frontend or full-stack change complete without a screenshot.

## Asset Cache-Busting

Whenever any static file is changed — **JS, CSS, JSON, images, or any file under `public/`** — bump the `asset_version` in:

```
dpdp_tool/public/dpdp-config.json
```

Use the format `YYYYMMDD[letter]`, e.g. `20260626a`, `20260626b` for multiple changes on the same day.

Both page templates (`www/assess.html`, `www/index.html`) append `?v={{ asset_v }}` to every asset URL. The version is read at request time from the config by `assess.py` and `index.py`, so updating the config is the only step required.

**Do not skip this step** — unchanged version strings cause browsers to serve stale JS/CSS after a deploy.
