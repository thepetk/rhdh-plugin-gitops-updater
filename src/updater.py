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

    def _build_version_string(
        self, version: "Version", second_version: "Version | None" = None
    ) -> "str":
        """
        builds a version string, including second version if present
        """
        if second_version:
            return f"{version}__{second_version}"
        return str(version)

    def _find_current_tag_prefix(self, content: "str", plugin: "RHDHPlugin") -> "str":
        """
        finds which tag prefix is currently being used for the plugin
        by searching the content for the plugin with any of the configured prefixes
        """
        version_string = self._build_version_string(
            plugin.current_version, plugin.current_second_version
        )

        for prefix in RHDHPluginUpdaterConfig.GH_PACKAGE_TAG_PREFIX:
            test_tag = f"{prefix}{version_string}"
            pattern = re.compile(
                rf"package:\s+(?:oci://)?[^\s]*{re.escape(plugin.plugin_name)}[^\s]*:{re.escape(test_tag)}![^\s]*",
                re.MULTILINE,
            )
            if pattern.search(content):
                return prefix

        return RHDHPluginUpdaterConfig.GH_PACKAGE_TAG_PREFIX[0]

    def _update_plugin_version_in_content(
        self,
        content: "str",
        plugin: "RHDHPlugin",
        new_version: "Version",
        new_second_version: "Version | None" = None,
    ) -> "str":
        """
        update a single plugin version in the YAML content using string replacement.
        This preserves the original YAML formatting.
        """
        new_version_string = self._build_version_string(new_version, new_second_version)
        logger.debug(
            f"updating config for plugin {plugin.plugin_name} "
            f"to version {new_version_string}"
        )

        # Find which tag prefix is currently used for this plugin
        current_prefix = self._find_current_tag_prefix(content, plugin)

        old_version_string = self._build_version_string(
            plugin.current_version, plugin.current_second_version
        )
        old_tag = f"{current_prefix}{old_version_string}"
        new_tag = f"{current_prefix}{new_version_string}"

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
                f"{old_version_string} to {new_version_string}"
            )
        else:
            logger.warning(
                f"no match found for plugin {plugin.plugin_name} with version "
                f"{old_version_string}"
            )

        return updated_content

    def update_rhdh_plugin(
        self,
        rhdh_plugin: "RHDHPlugin",
        new_version: "Version",
        new_second_version: "Version | None" = None,
    ) -> "str":
        """
        updates a single plugin and return the updated YAML content.
        """
        with open(self.config_path, "r") as f:
            content = f.read()

        updated_content = self._update_plugin_version_in_content(
            content, rhdh_plugin, new_version, new_second_version
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
                content,
                update.rhdh_plugin,
                update.new_version,
                update.new_second_version,
            )

        return content
