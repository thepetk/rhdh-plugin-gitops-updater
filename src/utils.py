import sys
from typing import Any

from packaging.version import Version

from src.constants import logger


def get_plugins_list_from_dict(
    keys: "list[str]", data: "dict[str, Any]"
) -> "list[dict[str, Any]]":
    """
    navigates through a nested dictionary using a list of keys.
    """
    current: "dict[str, Any]" = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            logger.error("invalid config location, cannot find plugins list")
            sys.exit(1)

        current = current[key]

    return [] if not isinstance(current, list) else current


def rhdh_plugin_needs_update(
    latest_version: "Version", current_version: "Version"
) -> "bool":
    """
    checks if the latest version is greater than the current version
    """
    return latest_version > current_version
