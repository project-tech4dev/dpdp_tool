# CLAUDE.md — Project Guidelines

## Privacy & PII

This tool processes personal data submitted by NGOs (org name, contact name, email, beneficiary descriptions, assessment answers). Apply these rules on every change:

- **Never add PII to URLs or query parameters.** Use POST with a JSON/form body. URL parameters appear in server access logs, browser history, and referrer headers.
- **Never log PII to the browser console.** Console messages must be generic stage markers only (e.g. `[dpdp] storing assessment`) — no data values, no URLs, no response bodies.
- **Never include org names or contact details in LLM prompts** unless strictly required for the output. The Anthropic API currently receives: sector, org size, beneficiaries description, section scores, and gap question text. `org_name` must not be included.
- **Audit any new external call** (fetch, API, analytics, third-party SDK) before adding it. Confirm what data is sent and where it goes. No analytics or tracking SDKs are used by design.
- **API keys** must be stored in Frappe site config (`frappe.conf.get(...)`), never hardcoded in source files.

## Page Structure & Shared Components

All pages extend `dpdp_tool/templates/dpdp_base.html` using Jinja2 `{% extends "dpdp_base.html" %}`. The base template owns the `<html>`, `<head>`, nav, footer, and font loading. **Never duplicate the nav or footer in individual pages.**

Two nav modes are supported via `context.nav_mode` set in each page's `.py` file:
- `full` (default) — full nav with dropdown and hamburger. Used by index, resources, privacy-policy.
- `minimal` — logo + back link only. Used by assess (focused task flow).

When adding a new page:
1. Create `www/<page>.html` extending the base and `www/<page>.py` setting `context.asset_v`
2. Set `context.nav_mode = "minimal"` only if the page is a focused task flow
3. Add the page to the nav in `dpdp_base.html` if it should appear in navigation

Nav links use absolute paths (`/`, `/#why`, `/#dashboard`) so they work correctly from every page.

## CSS — Reuse First

Before adding any CSS class, search `dpdp.css` for existing classes that cover the need. Do not add new classes for one-off layout values — use inline `style` for truly isolated cases. If a pattern appears on more than one element, promote it to a class and check with the user first. The design token variables in `:root` must be used for all colours — no raw hex or rgba values outside of the token definitions themselves.

## End-to-End Verification

For any significant change, verify with Playwright before reporting complete. Use the inline rendering approach already established in this project (Jinja2 renders templates with inlined CSS, Playwright drives Chromium headless):

```bash
pip3 install jinja2 playwright --break-system-packages
python3 -m playwright install chromium
```

**Always verify with Playwright when:**
- Any frontend change touches the nav, footer, or base template
- A new page is added
- JS logic changes that affect the assessment flow (form submission, polling, results rendering)
- CSS changes that affect layout or component visibility
- Any backend change that affects what the page renders (new context variables, API response shape)

**Minimum evidence required:**
- Screenshot of the affected UI state (nav, form, results panel, etc.)
- If a flow is involved (e.g. assessment submit → polling → results), screenshot each stage

The rendering setup: strip Frappe front matter, render with Jinja2 using `FileSystemLoader` over `templates/` and `www/`, inline `dpdp.css`, then drive with Playwright. The `asset_v` and `nav_mode` context variables must be passed explicitly.

Do not mark a task complete on a frontend or full-stack change without a screenshot showing the actual rendered output.

## Asset Cache-Busting

Whenever any static file is changed — **JS, CSS, JSON, images, or any file under `public/`** — bump the `asset_version` in:

```
dpdp_tool/public/dpdp-config.json
```

Use the format `YYYYMMDD[letter]`, e.g. `20260626a`, `20260626b` for multiple changes on the same day.

Both page templates (`www/assess.html`, `www/index.html`) append `?v={{ asset_v }}` to every asset URL. The version is read at request time from the config by `assess.py` and `index.py`, so updating the config is the only step required.

**Do not skip this step** — unchanged version strings cause browsers to serve stale JS/CSS after a deploy.
