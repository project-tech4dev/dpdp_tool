from dpdp_tool.api import _get_config


def get_context(context):
    context.asset_v = _get_config().get("asset_version", "1")
