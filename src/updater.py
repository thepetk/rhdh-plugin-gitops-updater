import re

from packaging.version import Version

from src.constants import (
    DYNAMIC_PLUGINS_CONFIG_YAML_FILE_PATH,
    DYNAMIC_PLUGINS_CONFIG_YAML_LOCATION,
    logger,
)
from src.types import RHDHPlugin, RHDHPluginUpdate, RHDHPluginUpdaterConfig


class RHDHPluginConfigUpdater:
    """
    Handles updating RHDH plugin versions in the YAML configuration file.
    """

    def __init__(
        self,
        config_path=DYNAMIC_PLUGINS_CONFIG_YAML_FILE_PATH,
        config_location=DYNAMIC_PLUGINS_CONFIG_YAML_LOCATION,
    ) -> "None":
        self.config_path = config_path
        self.config_location = config_location

    def _update_plugin_version_in_content(
        self,
        content: "str",
        plugin: "RHDHPlugin",
        new_version: "Version",
    ) -> "str":
        """
        update a single plugin version in the YAML content using string replacement.
        This preserves the original YAML formatting.
        """
        logger.debug(
            f"updating config for plugin {plugin.plugin_name} to version {new_version}"
        )

        old_tag = (
            f"{RHDHPluginUpdaterConfig.GH_PACKAGE_TAG_PREFIX}{plugin.current_version}"
        )
        new_tag = f"{RHDHPluginUpdaterConfig.GH_PACKAGE_TAG_PREFIX}{new_version}"

        # pattern to find the specific plugin's package line with the old version
        pattern = re.compile(
            rf"(package:\s+(?:oci://)?[^\s]*{re.escape(plugin.plugin_name)}[^\s]*:){re.escape(old_tag)}(![^\s]*)",
            re.MULTILINE,
        )

        # Replace the old tag with the new tag
        updated_content = pattern.sub(rf"\g<1>{new_tag}\g<2>", content)

        if updated_content != content:
            logger.debug(
                f"updated config for {plugin.plugin_name} from "
                f"{plugin.current_version} to {new_version}"
            )
        else:
            logger.warning(
                f"no match found for plugin {plugin.plugin_name} with version "
                f"{plugin.current_version}"
            )

        return updated_content

    def update_rhdh_plugin(
        self,
        rhdh_plugin: "RHDHPlugin",
        new_version: "Version",
    ) -> "str":
        """
        updates a single plugin and return the updated YAML content.
        """
        with open(self.config_path, "r") as f:
            content = f.read()

        updated_content = self._update_plugin_version_in_content(
            content, rhdh_plugin, new_version
        )

        return updated_content

    def bulk_update_rhdh_plugins(
        self,
        updates: "list[RHDHPluginUpdate]",
    ) -> str:
        """
        updates multiple plugins and returns the updated YAML content.
        """
        with open(self.config_path, "r") as f:
            content = f.read()

        for update in updates:
            content = self._update_plugin_version_in_content(
                content, update.rhdh_plugin, update.new_version
            )

        return content
