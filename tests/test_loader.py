import tempfile
from pathlib import Path
from typing import Any

import pytest
import yaml
from packaging.version import Version

from src.exceptions import InvalidRHDHPluginPackageDefinitionException
from src.loader import RHDHPluginsConfigLoader


class TestRHDHPluginsConfigLoader:
    """
    handles all tests for RHDHPluginsConfigLoader class.
    """

    def test_init_with_defaults(self) -> "None":
        loader = RHDHPluginsConfigLoader()
        assert loader.config_path == "dynamic-plugins.yaml"
        assert loader.config_location == "global.dynamic.plugins"

    def test_init_with_custom_values(self) -> "None":
        loader = RHDHPluginsConfigLoader(
            config_path="/custom/path.yaml", config_location="custom.location"
        )
        assert loader.config_path == "/custom/path.yaml"
        assert loader.config_location == "custom.location"

    def test_fetch_plugins_by_location(
        self, sample_config_data: "dict[str, Any]"
    ) -> "None":
        loader = RHDHPluginsConfigLoader()
        plugins = loader._fetch_plugins_by_location(sample_config_data)

        assert isinstance(plugins, list)
        assert len(plugins) == 4

    def test_fetch_plugins_by_location_empty_when_not_list(self) -> "None":
        loader = RHDHPluginsConfigLoader()
        data = {"global": {"dynamic": {"plugins": "not_a_list"}}}
        plugins = loader._fetch_plugins_by_location(data)

        assert plugins == []

    def test_parse_package_string_valid(self) -> "None":
        loader = RHDHPluginsConfigLoader()
        package = "oci://ghcr.io/redhat-developer/rhdh-plugin-export-overlays/backstage-plugin-mcp-actions-backend:next__0.1.2!backstage-plugin-mcp-actions-backend"

        result = loader._parse_package_string(package)

        assert (
            result["package_name"]
            == "rhdh-plugin-export-overlays/backstage-plugin-mcp-actions-backend"
        )
        assert result["version"] == Version("0.1.2")
        assert result["plugin_name"] == "backstage-plugin-mcp-actions-backend"

    def test_parse_package_string_invalid_no_oci_prefix(self) -> "None":
        loader = RHDHPluginsConfigLoader()
        package = "ghcr.io/redhat-developer/plugin:next__1.0.0!plugin"

        with pytest.raises(InvalidRHDHPluginPackageDefinitionException) as exc_info:
            loader._parse_package_string(package)

        assert "Invalid RHDH plugin package definition" in str(exc_info.value)

    def test_parse_package_string_invalid_no_exclamation(self) -> "None":
        loader = RHDHPluginsConfigLoader()
        package = "oci://ghcr.io/redhat-developer/plugin:next__1.0.0"

        with pytest.raises(InvalidRHDHPluginPackageDefinitionException) as exc_info:
            loader._parse_package_string(package)

        assert "Missing !" in str(exc_info.value)

    def test_parse_package_string_invalid_no_colon(self) -> "None":
        loader = RHDHPluginsConfigLoader()
        package = "oci://ghcr.io/redhat-developer/rhdh-plugin-export-overlays/plugin!plugin-name"

        with pytest.raises(InvalidRHDHPluginPackageDefinitionException) as exc_info:
            loader._parse_package_string(package)

        assert "Tag not found" in str(exc_info.value)

    def test_parse_package_string_invalid_wrong_tag_prefix(self) -> "None":
        loader = RHDHPluginsConfigLoader()
        package = "oci://ghcr.io/redhat-developer/rhdh-plugin-export-overlays/plugin:v1.0.0!plugin-name"

        with pytest.raises(InvalidRHDHPluginPackageDefinitionException) as exc_info:
            loader._parse_package_string(package)

        assert "not valid for package" in str(exc_info.value)

    def test_parse_package_string_handles_complex_plugin_names(self) -> "None":
        loader = RHDHPluginsConfigLoader()
        package = "oci://ghcr.io/redhat-developer/rhdh-plugin-export-overlays/red-hat-developer-hub-backstage-plugin-software-catalog-mcp-tool:next__0.2.0!red-hat-developer-hub-backstage-plugin-software-catalog-mcp-tool"

        result = loader._parse_package_string(package)

        assert (
            result["plugin_name"]
            == "red-hat-developer-hub-backstage-plugin-software-catalog-mcp-tool"
        )
        assert result["version"] == Version("0.2.0")

    def test_convert_rhdhplugin_list_filters_non_rhdh_plugins(
        self, sample_config_data: "dict[str, Any]"
    ) -> "None":
        loader = RHDHPluginsConfigLoader()
        plugins_list = sample_config_data["global"]["dynamic"]["plugins"]

        result = loader._convert_rhdhplugin_list(plugins_list)

        # should only get RHDH-specific plugins
        assert len(result) == 2
        assert all(
            plugin.package_name.startswith("rhdh-plugin-export-overlays/")
            for plugin in result
        )

    def test_convert_rhdhplugin_list_filters_disabled_plugins(
        self, sample_config_data: "dict[str, Any]"
    ) -> "None":
        loader = RHDHPluginsConfigLoader()
        plugins_list = sample_config_data["global"]["dynamic"]["plugins"]

        result = loader._convert_rhdhplugin_list(plugins_list)

        # disabled plugin should be filtered out
        assert all(not plugin.disabled for plugin in result)

    def test_convert_rhdhplugin_list_handles_invalid_packages(self) -> "None":
        loader = RHDHPluginsConfigLoader()
        plugins_list = [
            {
                "disabled": False,
                "package": "oci://ghcr.io/redhat-developer/rhdh-plugin-export-overlays/invalid!missing-version",
            }
        ]

        # should handle exception gracefully and return empty list
        result = loader._convert_rhdhplugin_list(plugins_list)
        assert result == []

    def test_load_rhdh_plugins(self, temp_config_file: "str") -> "None":
        loader = RHDHPluginsConfigLoader(config_path=temp_config_file)

        plugins = loader.load_rhdh_plugins()

        assert isinstance(plugins, list)
        # again only non-disabled RHDH-specific plugins
        assert len(plugins) == 2
        assert all(hasattr(plugin, "plugin_name") for plugin in plugins)
        assert all(hasattr(plugin, "current_version") for plugin in plugins)

    def test_load_rhdh_plugins_file_not_found(self) -> "None":
        loader = RHDHPluginsConfigLoader(config_path="/non/existent/file.yaml")

        with pytest.raises(FileNotFoundError):
            loader.load_rhdh_plugins()

    def test_load_rhdh_plugins_invalid_yaml(self) -> "None":
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name

        loader = RHDHPluginsConfigLoader(config_path=temp_path)

        with pytest.raises(yaml.YAMLError):
            loader.load_rhdh_plugins()

        # clean everything
        Path(temp_path).unlink()
