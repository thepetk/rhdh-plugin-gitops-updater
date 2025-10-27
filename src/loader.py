from urllib.parse import urlparse

import yaml
from packaging.version import Version

from src.constants import (
    DYNAMIC_PLUGINS_CONFIG_YAML_FILE_PATH,
    DYNAMIC_PLUGINS_CONFIG_YAML_LOCATION,
    logger,
)
from src.exceptions import InvalidRHDHPluginPackageDefinitionException
from src.types import RHDHPlugin, RHDHPluginUpdaterConfig
from src.utils import get_plugins_list_from_dict, match_tag_prefix


class RHDHPluginsConfigLoader:
    """
    Handles RHDH app-config and dynamic plugins config parsing and updates
    """

    def __init__(
        self,
        config_path=DYNAMIC_PLUGINS_CONFIG_YAML_FILE_PATH,
        config_location=DYNAMIC_PLUGINS_CONFIG_YAML_LOCATION,
    ) -> "None":
        self.config_path = config_path
        self.config_location = config_location

    def _fetch_plugins_by_location(
        self, data: "dict[str, str | int | bool]"
    ) -> "list[dict[str, str | int | bool]]":
        """
        fetches the plugins from the config file based on the config location
        """
        keys = self.config_location.split(".")
        plugins_list = get_plugins_list_from_dict(keys, data)

        return plugins_list if isinstance(plugins_list, list) else []

    def _parse_package_string(self, package: "str") -> "dict[str, str | Version]":
        """
        parses the OCI package string to extract plugin info.

        ::raises:: InvalidRHDHPluginPackageDefinitionException
        If the package definition is invalid

        ::raises:: ImageTagNotFoundException if the image tag is not found
        """
        if not package.startswith("oci://"):
            raise InvalidRHDHPluginPackageDefinitionException(
                f"Invalid RHDH plugin package definition: {package}"
            )

        # remove the oci:// prefix
        package = package.replace("oci://", "", 1)

        # split image ref and plugin name
        if "!" not in package:
            raise InvalidRHDHPluginPackageDefinitionException(
                f"Missing ! in package {package} definition"
            )

        image_ref, plugin_name = package.split("!", 1)

        # parse the image ref
        parsed_url = urlparse(f"//{image_ref}")
        image_ref_parts = parsed_url.path.lstrip("/").split("/")

        # should have less than 4 parts (registry, org, repo, name:version)
        if not len(image_ref_parts) < 4:
            raise InvalidRHDHPluginPackageDefinitionException(
                f"Too few image ref parts ({len(image_ref_parts)}) "
                f"for package: {package}"
            )

        # get name and version
        name_and_version = image_ref_parts[-1]

        if ":" not in name_and_version:
            raise InvalidRHDHPluginPackageDefinitionException(
                f"Tag not found for package {package}"
            )

        name, raw_version = name_and_version.rsplit(":", 1)

        matched_prefix = match_tag_prefix(raw_version)
        if not matched_prefix:
            raise InvalidRHDHPluginPackageDefinitionException(
                f"Tag {raw_version} not valid for package {package}"
            )

        version = Version(version=raw_version.replace(matched_prefix, ""))

        package_name = f"rhdh-plugin-export-overlays/{name}"

        return {
            "package_name": package_name,
            "version": version,
            "plugin_name": plugin_name,
        }

    def _convert_rhdhplugin_list(
        self, plugins_list: "list[dict[str, str | int | bool]]"
    ) -> "list[RHDHPlugin]":
        """
        converts a list of plugin dicts into a list of RHDHPlugin objects
        """
        rhdh_plugins = []
        for plugin_entry in plugins_list:
            package = str(plugin_entry.get("package", ""))
            disabled = bool(plugin_entry.get("disabled", False))

            # continue if is not an RHDH plugin or is disabled
            if not package.startswith(RHDHPluginUpdaterConfig.GH_CR_REGISTRY_PREFIX):
                logger.info(f"skipping plugin {package} as it's not RHDH Plugin")
                continue

            if disabled is True:
                logger.info(f"skipping plugin {package} as it's disabled")
                continue

            try:
                parsed = self._parse_package_string(package)
            except InvalidRHDHPluginPackageDefinitionException as e:
                logger.warning(f"failed to parse package:: {e}")
                continue

            if len(parsed.keys()) == 0:
                continue

            rhdh_plugins.append(
                RHDHPlugin(
                    package_name=str(parsed["package_name"]),
                    current_version=parsed["version"],  # type: ignore
                    plugin_name=str(parsed["plugin_name"]),
                    disabled=disabled,
                )
            )
        return rhdh_plugins

    def load_rhdh_plugins(self) -> "list[RHDHPlugin]":
        """
        parses the config file and extracts RHDH plugins list.
        """
        logger.debug("loading RHDH plugins from config...")
        with open(self.config_path, "r") as f:
            data = yaml.safe_load(f)

        plugins_list = self._fetch_plugins_by_location(data)
        rhdh_plugins = self._convert_rhdhplugin_list(plugins_list)

        return rhdh_plugins
