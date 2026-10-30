from dpdp_tool.api import _get_config, get_tagged_articles

# Posts tagged with this on projecttech4dev.org appear in "Read more"
ARTICLES_TAG = "dpdp-ngo-cohort-1"


def get_context(context):
    context.asset_v = _get_config().get("asset_version", "1")
    context.nav_active = "cohorts-events"
    context.articles = get_tagged_articles(ARTICLES_TAG)
