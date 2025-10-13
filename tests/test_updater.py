from typing import Any

import pytest
from packaging.version import Version

from src.types import RHDHPlugin, RHDHPluginUpdate
from src.updater import RHDHPluginConfigUpdater


class TestRHDHPluginConfigUpdater:
    """
    handles all tests for RHDHPluginConfigUpdater class.
    """

    def test_init_with_defaults(self) -> "None":
        updater = RHDHPluginConfigUpdater()
        assert updater.config_path == "dynamic-plugins.yaml"
        assert updater.config_location == "global.dynamic.plugins"

    def test_init_with_custom_values(self) -> "None":
        updater = RHDHPluginConfigUpdater(
            config_path="/custom/path.yaml", config_location="custom.location"
        )
        assert updater.config_path == "/custom/path.yaml"
        assert updater.config_location == "custom.location"

    def test_update_plugin_version_in_content_success(
        self, sample_yaml_content: "str", sample_plugin: "RHDHPlugin"
    ) -> "None":
        updater = RHDHPluginConfigUpdater()
        new_version = Version("0.1.3")

        updated_content = updater._update_plugin_version_in_content(
            sample_yaml_content, sample_plugin, new_version
        )

        assert "next__0.1.3" in updated_content
        assert "next__0.1.2" not in updated_content
        assert updated_content != sample_yaml_content

    def test_update_plugin_version_in_content_preserves_formatting(
        self, sample_yaml_content: "str", sample_plugin: "RHDHPlugin"
    ) -> "None":
        updater = RHDHPluginConfigUpdater()
        new_version = Version("0.1.3")

        updated_content = updater._update_plugin_version_in_content(
            sample_yaml_content, sample_plugin, new_version
        )

        # check that structure is preserved
        assert "global:" in updated_content
        assert "dynamic:" in updated_content
        assert "plugins:" in updated_content
        assert "disabled: false" in updated_content

    def test_update_plugin_version_in_content_no_match(
        self, sample_yaml_content: "str"
    ) -> "None":
        updater = RHDHPluginConfigUpdater()
        non_existent_plugin = RHDHPlugin(
            package_name="rhdh-plugin-export-overlays/non-existent",
            current_version=Version("1.0.0"),
            plugin_name="non-existent-plugin",
            disabled=False,
        )
        new_version = Version("1.0.1")

        updated_content = updater._update_plugin_version_in_content(
            sample_yaml_content, non_existent_plugin, new_version
        )

        # content should be unchanged
        assert updated_content == sample_yaml_content

    def test_update_plugin_version_updates_correct_plugin_only(
        self, sample_yaml_content: "str"
    ) -> "None":
        updater = RHDHPluginConfigUpdater()
        plugin = RHDHPlugin(
            package_name="rhdh-plugin-export-overlays/red-hat-developer-hub-backstage-plugin-software-catalog-mcp-tool",
            current_version=Version("0.2.0"),
            plugin_name="red-hat-developer-hub-backstage-plugin-software-catalog-mcp-tool",
            disabled=False,
        )
        new_version = Version("0.2.1")

        updated_content = updater._update_plugin_version_in_content(
            sample_yaml_content, plugin, new_version
        )

        # check that the correct plugin was updated
        assert "software-catalog-mcp-tool:next__0.2.1" in updated_content
        # check that other plugin was not affected
        assert "mcp-actions-backend:next__0.1.2" in updated_content

    def test_update_rhdh_plugin(
        self, temp_yaml_file: "Any", sample_plugin: "RHDHPlugin"
    ) -> "None":
        updater = RHDHPluginConfigUpdater(config_path=temp_yaml_file)
        new_version = Version("0.1.3")

        updated_content = updater.update_rhdh_plugin(sample_plugin, new_version)

        assert "next__0.1.3" in updated_content
        assert "next__0.1.2" not in updated_content

    def test_bulk_update_rhdh_plugins(self, temp_yaml_file: "Any") -> "None":
        updater = RHDHPluginConfigUpdater(config_path=temp_yaml_file)

        plugin1 = RHDHPlugin(
            package_name="rhdh-plugin-export-overlays/backstage-plugin-mcp-actions-backend",
            current_version=Version("0.1.2"),
            plugin_name="backstage-plugin-mcp-actions-backend",
            disabled=False,
        )
        plugin2 = RHDHPlugin(
            package_name="rhdh-plugin-export-overlays/red-hat-developer-hub-backstage-plugin-software-catalog-mcp-tool",
            current_version=Version("0.2.0"),
            plugin_name="red-hat-developer-hub-backstage-plugin-software-catalog-mcp-tool",
            disabled=False,
        )

        updates = [
            RHDHPluginUpdate(rhdh_plugin=plugin1, new_version=Version("0.1.3")),
            RHDHPluginUpdate(rhdh_plugin=plugin2, new_version=Version("0.2.1")),
        ]

        updated_content = updater.bulk_update_rhdh_plugins(updates)

        assert "next__0.1.3" in updated_content
        assert "next__0.2.1" in updated_content
        assert "next__0.1.2" not in updated_content
        assert "next__0.2.0" not in updated_content

    def test_update_rhdh_plugin_file_not_found(self) -> "None":
        updater = RHDHPluginConfigUpdater(config_path="/non/existent/file.yaml")
        plugin = RHDHPlugin(
            package_name="test",
            current_version=Version("1.0.0"),
            plugin_name="test-plugin",
            disabled=False,
        )

        with pytest.raises(FileNotFoundError):
            updater.update_rhdh_plugin(plugin, Version("1.0.1"))
