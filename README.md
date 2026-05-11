# dpdp_tool — DPDP Readiness Navigator

DPDP Act 2023 readiness assessment for NGOs. Built on Frappe Framework.

**Live site:** https://dpdp.projecttech4dev.org  
**Deployment:** Frappe Cloud — auto-deploys on push to `main`

## Push to your GitHub and connect

```bash
git remote add origin https://github.com/YOUR-ORG/dpdp_tool.git
git push -u origin main
```

Then in Frappe Cloud → Apps → Add App → GitHub → `dpdp_tool` → branch `main`.

Add your Claude API key in Site Config:
```
anthropic_api_key = sk-ant-YOUR-KEY
```

## Structure

```
dpdp/             ← repo root = Frappe app root
├── setup.py
├── requirements.txt   anthropic>=0.20.0
├── MANIFEST.in
└── dpdp_tool/         ← Python package
    ├── __init__.py
    ├── hooks.py
    ├── modules.txt
    ├── api.py         4 whitelisted API methods
    ├── fixtures/      DocTypes (auto-applied on bench migrate)
    ├── doctype/       Controller stubs
    ├── public/css/    dpdp.css
    ├── public/js/     dpdp-index.js, dpdp-assess.js
    └── www/           index.html, assess.html
```

See [frappe-setup-guide.md](frappe-setup-guide.md) for full instructions.
