from dpdp_tool.api import _get_config, get_tagged_articles

# Posts tagged with this on projecttech4dev.org are listed on /blog
ARTICLES_TAG = "dpdp"


def get_context(context):
    context.asset_v = _get_config().get("asset_version", "1")
    context.nav_active = "resources"
    context.articles = get_tagged_articles(ARTICLES_TAG, limit=12)
