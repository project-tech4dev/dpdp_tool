app_name        = "dpdp_tool"
app_title       = "DPDP Tool"
app_publisher   = "Tech4Dev"
app_description = "DPDP Readiness Navigator for NGOs"
app_version     = "1.0.0"
app_icon        = "octicon octicon-shield"
app_color       = "#1D6FB8"
app_email       = "dpdp@projecttech4dev.org"
app_license     = "MIT"

# Fixtures — DocType definitions and Email Templates auto-applied on bench migrate.
# After changing a DocType via Desk, run:
#   bench --site dpdp.projecttech4dev.org export-fixtures
# then commit the updated JSON files.
fixtures = [
    {
        "dt": "DocType",
        "filters": [["name", "in", [
            "DPDP Assessment",
            "DPDP Consult Request"
        ]]]
    },
    {
        "dt": "Email Template",
        "filters": [["name", "in", [
            "DPDP Assessment Report",
            "DPDP Consult Request Internal"
        ]]]
    }
]

web_include_css = ["/assets/dpdp_tool/css/dpdp.css"]
