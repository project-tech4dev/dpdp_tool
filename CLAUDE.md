# CLAUDE.md — Project Guidelines

## Privacy & PII

This tool processes personal data submitted by NGOs (org name, contact name, email, beneficiary descriptions, assessment answers). Apply these rules on every change:

- **Never add PII to URLs or query parameters.** Use POST with a JSON/form body. URL parameters appear in server access logs, browser history, and referrer headers.
- **Never log PII to the browser console.** Console messages must be generic stage markers only (e.g. `[dpdp] storing assessment`) — no data values, no URLs, no response bodies.
- **Never include org names or contact details in LLM prompts** unless strictly required for the output. The Anthropic API currently receives: sector, org size, beneficiaries description, section scores, and gap question text. `org_name` must not be included.
- **Audit any new external call** (fetch, API, analytics, third-party SDK) before adding it. Confirm what data is sent and where it goes. No analytics or tracking SDKs are used by design.
- **API keys** must be stored in Frappe site config (`frappe.conf.get(...)`), never hardcoded in source files.

## Asset Cache-Busting

Whenever any static file is changed — **JS, CSS, JSON, images, or any file under `public/`** — bump the `asset_version` in:

```
dpdp_tool/public/dpdp-config.json
```

Use the format `YYYYMMDD[letter]`, e.g. `20260626a`, `20260626b` for multiple changes on the same day.

Both page templates (`www/assess.html`, `www/index.html`) append `?v={{ asset_v }}` to every asset URL. The version is read at request time from the config by `assess.py` and `index.py`, so updating the config is the only step required.

**Do not skip this step** — unchanged version strings cause browsers to serve stale JS/CSS after a deploy.
