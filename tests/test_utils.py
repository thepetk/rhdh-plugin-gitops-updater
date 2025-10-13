from typing import Any

import pytest
from packaging.version import Version

from src.utils import get_plugins_list_from_dict, rhdh_plugin_needs_update


class TestGetPluginsListFromDict:
    """
    handles all tests for get_plugins_list_from_dict function.
    """

    def test_returns_list_at_nested_location(self) -> "None":
        data = {
            "level1": {
                "level2": {"plugins": [{"name": "plugin1"}, {"name": "plugin2"}]}
            }
        }
        keys = ["level1", "level2", "plugins"]
        result = get_plugins_list_from_dict(keys, data)
        assert result == [{"name": "plugin1"}, {"name": "plugin2"}]

    def test_returns_empty_list_when_value_not_list(self) -> "None":
        data = {"level1": {"plugins": "not_a_list"}}
        keys = ["level1", "plugins"]
        result = get_plugins_list_from_dict(keys, data)
        assert result == []

    def test_exits_when_key_not_found(self, capsys: "Any") -> "None":
        data = {"level1": {"other": "value"}}
        keys = ["level1", "missing_key"]

        with pytest.raises(SystemExit) as exc_info:
            get_plugins_list_from_dict(keys, data)

        assert exc_info.value.code == 1

    def test_exits_when_intermediate_value_not_dict(self, capsys: "Any") -> "None":
        data = {"level1": "not_a_dict"}
        keys = ["level1", "nested"]

        with pytest.raises(SystemExit) as exc_info:
            get_plugins_list_from_dict(keys, data)

        assert exc_info.value.code == 1

    def test_handles_single_level_navigation(self) -> "None":
        data = {"plugins": [{"name": "plugin1"}]}
        keys = ["plugins"]
        result = get_plugins_list_from_dict(keys, data)
        assert result == [{"name": "plugin1"}]


class TestRHDHPluginNeedsUpdate:
    """
    handles all tests for rhdh_plugin_needs_update function.
    """

    def test_returns_true_when_latest_greater(self) -> "None":
        latest = Version("1.2.0")
        current = Version("1.1.0")
        assert rhdh_plugin_needs_update(latest, current) is True

    def test_returns_false_when_versions_equal(self) -> "None":
        latest = Version("1.1.0")
        current = Version("1.1.0")
        assert rhdh_plugin_needs_update(latest, current) is False

    def test_returns_false_when_current_greater(self) -> "None":
        latest = Version("1.0.0")
        current = Version("1.1.0")
        assert rhdh_plugin_needs_update(latest, current) is False

    def test_handles_semantic_versioning(self) -> "None":
        assert rhdh_plugin_needs_update(Version("2.0.0"), Version("1.9.9")) is True
        assert rhdh_plugin_needs_update(Version("1.0.1"), Version("1.0.0")) is True
        assert rhdh_plugin_needs_update(Version("1.10.0"), Version("1.9.0")) is True

    def test_handles_prerelease_versions(self) -> "None":
        assert rhdh_plugin_needs_update(Version("1.0.0"), Version("1.0.0rc1")) is True
        assert (
            rhdh_plugin_needs_update(Version("1.0.0rc2"), Version("1.0.0rc1")) is True
        )
