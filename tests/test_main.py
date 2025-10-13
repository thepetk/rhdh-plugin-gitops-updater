from typing import Any
from unittest.mock import Mock, patch

import pytest
from packaging.version import Version

from main import main
from src.exceptions import GithubPRFailedException
from src.types import (
    GithubPullRequestStrategy,
    RHDHPlugin,
    RHDHPluginPackage,
    RHDHPluginPackageVersion,
)


class TestMain:
    """
    handles all tests for main.
    """

    @patch("main.GITHUB_REPOSITORY", None)
    @patch("main.GITHUB_TOKEN", "test_token")
    def test_main_no_GITHUB_REPOSITORY(self, capsys: "Any") -> "None":
        # should log error and return without raising exception
        main()

    @patch("main.GITHUB_REPOSITORY", "owner/repo")
    @patch("main.GITHUB_TOKEN", None)
    def test_main_no_github_token(self, capsys: "Any") -> "None":
        # should log error and return without raising exception
        main()

    @patch("main.GITHUB_REPOSITORY", "owner/repo")
    @patch("main.GITHUB_TOKEN", "test_token")
    @patch("main.GithubAPIClient")
    @patch("main.RHDHPluginsConfigLoader")
    @patch("main.RHDHPluginConfigUpdater")
    def test_main_no_plugins_found(
        self, mock_updater_class: "Any", mock_loader_class: "Any", mock_api_class: "Any"
    ) -> "None":
        mock_loader = Mock()
        mock_loader.load_rhdh_plugins.return_value = []
        mock_loader_class.return_value = mock_loader

        main()

        mock_loader.load_rhdh_plugins.assert_called_once()

    @patch("main.GITHUB_REPOSITORY", "owner/repo")
    @patch("main.GITHUB_TOKEN", "test_token")
    @patch("main.UPDATE_PR_STRATEGY", GithubPullRequestStrategy.SEPARATE)
    @patch("main.PR_CREATION_LIMIT", 0)
    @patch("main.GithubAPIClient")
    @patch("main.RHDHPluginsConfigLoader")
    @patch("main.RHDHPluginConfigUpdater")
    def test_main_with_plugins_up_to_date(
        self, mock_updater_class: "Any", mock_loader_class: "Any", mock_api_class: "Any"
    ) -> "None":
        mock_plugin = RHDHPlugin(
            package_name="test-package",
            current_version=Version("1.0.0"),
            plugin_name="test-plugin",
            disabled=False,
        )

        mock_loader = Mock()
        mock_loader.load_rhdh_plugins.return_value = [mock_plugin]
        mock_loader_class.return_value = mock_loader

        mock_api = Mock()
        mock_package = RHDHPluginPackage(
            name="test-package",
            versions=[
                RHDHPluginPackageVersion(
                    name="12345",
                    version=Version("1.0.0"),
                    created_at="2024-01-15T10:00:00Z",
                )
            ],
        )
        mock_api.fetch_package.return_value = mock_package
        mock_api_class.return_value = mock_api

        main()

        mock_loader.load_rhdh_plugins.assert_called_once()
        mock_api.fetch_package.assert_called_once_with("test-package")
        # no pr should be created
        mock_api.create_pull_request.assert_not_called()

    @patch("main.GITHUB_REPOSITORY", "owner/repo")
    @patch("main.GITHUB_TOKEN", "test_token")
    @patch("main.GITHUB_REF", "main")
    @patch(
        "main.DYNAMIC_PLUGINS_CONFIG_YAML_FILE_PATH",
        "dynamic-plugins.yaml",
    )
    @patch("main.UPDATE_PR_STRATEGY", GithubPullRequestStrategy.SEPARATE)
    @patch("main.PR_CREATION_LIMIT", 0)
    @patch("main.GithubAPIClient")
    @patch("main.RHDHPluginsConfigLoader")
    @patch("main.RHDHPluginConfigUpdater")
    def test_main_with_plugin_update_separate_strategy(
        self, mock_updater_class: "Any", mock_loader_class: "Any", mock_api_class: "Any"
    ) -> "None":
        mock_plugin = RHDHPlugin(
            package_name="test-package",
            current_version=Version("1.0.0"),
            plugin_name="test-plugin",
            disabled=False,
        )

        mock_loader = Mock()
        mock_loader.load_rhdh_plugins.return_value = [mock_plugin]
        mock_loader_class.return_value = mock_loader

        mock_api = Mock()
        mock_package = RHDHPluginPackage(
            name="test-package",
            versions=[
                RHDHPluginPackageVersion(
                    name="12345",
                    version=Version("1.0.0"),
                    created_at="2024-01-15T10:00:00Z",
                ),
                RHDHPluginPackageVersion(
                    name="12346",
                    version=Version("1.1.0"),
                    created_at="2024-01-20T10:00:00Z",
                ),
            ],
        )
        mock_api.fetch_package.return_value = mock_package
        mock_api.create_pull_request.return_value = (
            "https://github.com/owner/repo/pull/1"
        )
        mock_api_class.return_value = mock_api

        mock_updater = Mock()
        mock_updater.update_rhdh_plugin.return_value = "updated yaml content"
        mock_updater_class.return_value = mock_updater

        main()

        mock_loader.load_rhdh_plugins.assert_called_once()
        mock_api.fetch_package.assert_called_once_with("test-package")
        mock_updater.update_rhdh_plugin.assert_called_once_with(
            mock_plugin, Version("1.1.0")
        )
        mock_api.create_pull_request.assert_called_once()

    @patch("main.GITHUB_REPOSITORY", "owner/repo")
    @patch("main.GITHUB_TOKEN", "test_token")
    @patch("main.GITHUB_REF", "main")
    @patch("main.UPDATE_PR_STRATEGY", GithubPullRequestStrategy.JOINT)
    @patch("main.PR_CREATION_LIMIT", 0)
    @patch("main.GithubAPIClient")
    @patch("main.RHDHPluginsConfigLoader")
    @patch("main.RHDHPluginConfigUpdater")
    def test_main_with_plugin_update_joint_strategy(
        self, mock_updater_class: "Any", mock_loader_class: "Any", mock_api_class: "Any"
    ) -> "None":
        mock_plugin1 = RHDHPlugin(
            package_name="test-package-1",
            current_version=Version("1.0.0"),
            plugin_name="test-plugin-1",
            disabled=False,
        )
        mock_plugin2 = RHDHPlugin(
            package_name="test-package-2",
            current_version=Version("2.0.0"),
            plugin_name="test-plugin-2",
            disabled=False,
        )

        mock_loader = Mock()
        mock_loader.load_rhdh_plugins.return_value = [mock_plugin1, mock_plugin2]
        mock_loader_class.return_value = mock_loader

        mock_api = Mock()

        def fetch_package_side_effect(package_name: "str") -> "RHDHPluginPackage":
            if package_name == "test-package-1":
                return RHDHPluginPackage(
                    name="test-package-1",
                    versions=[
                        RHDHPluginPackageVersion(
                            name="12345",
                            version=Version("1.0.0"),
                            created_at="2024-01-15T10:00:00Z",
                        ),
                        RHDHPluginPackageVersion(
                            name="12346",
                            version=Version("1.1.0"),
                            created_at="2024-01-20T10:00:00Z",
                        ),
                    ],
                )
            return RHDHPluginPackage(
                name="test-package-2",
                versions=[
                    RHDHPluginPackageVersion(
                        name="22345",
                        version=Version("2.0.0"),
                        created_at="2024-01-15T10:00:00Z",
                    ),
                    RHDHPluginPackageVersion(
                        name="22346",
                        version=Version("2.1.0"),
                        created_at="2024-01-20T10:00:00Z",
                    ),
                ],
            )

        mock_api.fetch_package.side_effect = fetch_package_side_effect
        mock_api.create_pull_request.return_value = (
            "https://github.com/owner/repo/pull/1"
        )
        mock_api_class.return_value = mock_api

        mock_updater = Mock()
        mock_updater.bulk_update_rhdh_plugins.return_value = "updated yaml content"
        mock_updater_class.return_value = mock_updater

        main()

        mock_loader.load_rhdh_plugins.assert_called_once()
        assert mock_api.fetch_package.call_count == 2
        # Should create a single joint PR
        mock_updater.bulk_update_rhdh_plugins.assert_called_once()
        mock_api.create_pull_request.assert_called_once()

    @patch("main.GITHUB_REPOSITORY", "owner/repo")
    @patch("main.GITHUB_TOKEN", "test_token")
    @patch("main.UPDATE_PR_STRATEGY", GithubPullRequestStrategy.SEPARATE)
    @patch("main.PR_CREATION_LIMIT", 1)
    @patch("main.GithubAPIClient")
    @patch("main.RHDHPluginsConfigLoader")
    @patch("main.RHDHPluginConfigUpdater")
    def test_main_respects_pr_creation_limit(
        self, mock_updater_class: "Any", mock_loader_class: "Any", mock_api_class: "Any"
    ) -> "None":
        mock_plugin1 = RHDHPlugin(
            package_name="test-package-1",
            current_version=Version("1.0.0"),
            plugin_name="test-plugin-1",
            disabled=False,
        )
        mock_plugin2 = RHDHPlugin(
            package_name="test-package-2",
            current_version=Version("2.0.0"),
            plugin_name="test-plugin-2",
            disabled=False,
        )

        mock_loader = Mock()
        mock_loader.load_rhdh_plugins.return_value = [mock_plugin1, mock_plugin2]
        mock_loader_class.return_value = mock_loader

        mock_api = Mock()

        def fetch_package_side_effect(package_name: "str") -> "RHDHPluginPackage":
            if package_name == "test-package-1":
                return RHDHPluginPackage(
                    name="test-package-1",
                    versions=[
                        RHDHPluginPackageVersion(
                            name="12346",
                            version=Version("1.1.0"),
                            created_at="2024-01-20T10:00:00Z",
                        ),
                    ],
                )
            return RHDHPluginPackage(
                name="test-package-2",
                versions=[
                    RHDHPluginPackageVersion(
                        name="22346",
                        version=Version("2.1.0"),
                        created_at="2024-01-20T10:00:00Z",
                    ),
                ],
            )

        mock_api.fetch_package.side_effect = fetch_package_side_effect
        mock_api.create_pull_request.return_value = (
            "https://github.com/owner/repo/pull/1"
        )
        mock_api_class.return_value = mock_api

        mock_updater = Mock()
        mock_updater.update_rhdh_plugin.return_value = "updated yaml content"
        mock_updater_class.return_value = mock_updater

        main()

        # should only create 1 PR due to limit
        assert mock_api.create_pull_request.call_count == 1

    @patch("main.GITHUB_REPOSITORY", "owner/repo")
    @patch("main.GITHUB_TOKEN", "test_token")
    @patch("main.UPDATE_PR_STRATEGY", GithubPullRequestStrategy.SEPARATE)
    @patch("main.PR_CREATION_LIMIT", 0)
    @patch("main.GithubAPIClient")
    @patch("main.RHDHPluginsConfigLoader")
    @patch("main.RHDHPluginConfigUpdater")
    def test_main_handles_pr_creation_failure(
        self, mock_updater_class: "Any", mock_loader_class: "Any", mock_api_class: "Any"
    ) -> "None":
        mock_plugin = RHDHPlugin(
            package_name="test-package",
            current_version=Version("1.0.0"),
            plugin_name="test-plugin",
            disabled=False,
        )

        mock_loader = Mock()
        mock_loader.load_rhdh_plugins.return_value = [mock_plugin]
        mock_loader_class.return_value = mock_loader

        mock_api = Mock()
        mock_package = RHDHPluginPackage(
            name="test-package",
            versions=[
                RHDHPluginPackageVersion(
                    name="12346",
                    version=Version("1.1.0"),
                    created_at="2024-01-20T10:00:00Z",
                ),
            ],
        )
        mock_api.fetch_package.return_value = mock_package
        mock_api.create_pull_request.side_effect = GithubPRFailedException(
            "Branch already exists"
        )
        mock_api_class.return_value = mock_api

        mock_updater = Mock()
        mock_updater.update_rhdh_plugin.return_value = "updated yaml content"
        mock_updater_class.return_value = mock_updater

        # should not raise exception
        main()

        mock_api.create_pull_request.assert_called_once()

    @patch("main.GITHUB_REPOSITORY", "owner/repo")
    @patch("main.GITHUB_TOKEN", "test_token")
    @patch("main.UPDATE_PR_STRATEGY", GithubPullRequestStrategy.JOINT)
    @patch("main.PR_CREATION_LIMIT", 0)
    @patch("main.GithubAPIClient")
    @patch("main.RHDHPluginsConfigLoader")
    @patch("main.RHDHPluginConfigUpdater")
    def test_main_exits_on_joint_pr_failure(
        self, mock_updater_class: "Any", mock_loader_class: "Any", mock_api_class: "Any"
    ) -> "None":
        mock_plugin = RHDHPlugin(
            package_name="test-package",
            current_version=Version("1.0.0"),
            plugin_name="test-plugin",
            disabled=False,
        )

        mock_loader = Mock()
        mock_loader.load_rhdh_plugins.return_value = [mock_plugin]
        mock_loader_class.return_value = mock_loader

        mock_api = Mock()
        mock_package = RHDHPluginPackage(
            name="test-package",
            versions=[
                RHDHPluginPackageVersion(
                    name="12346",
                    version=Version("1.1.0"),
                    created_at="2024-01-20T10:00:00Z",
                ),
            ],
        )
        mock_api.fetch_package.return_value = mock_package
        mock_api.create_pull_request.side_effect = GithubPRFailedException(
            "Failed to create PR"
        )
        mock_api_class.return_value = mock_api

        mock_updater = Mock()
        mock_updater.bulk_update_rhdh_plugins.return_value = "updated yaml content"
        mock_updater_class.return_value = mock_updater

        # should exit with code 1
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch("main.GITHUB_REPOSITORY", "owner/repo")
    @patch("main.GITHUB_TOKEN", "test_token")
    @patch("main.UPDATE_PR_STRATEGY", GithubPullRequestStrategy.SEPARATE)
    @patch("main.PR_CREATION_LIMIT", 0)
    @patch("main.GithubAPIClient")
    @patch("main.RHDHPluginsConfigLoader")
    @patch("main.RHDHPluginConfigUpdater")
    def test_main_skips_packages_without_versions(
        self, mock_updater_class: "Any", mock_loader_class: "Any", mock_api_class: "Any"
    ) -> "None":
        mock_plugin = RHDHPlugin(
            package_name="test-package",
            current_version=Version("1.0.0"),
            plugin_name="test-plugin",
            disabled=False,
        )

        mock_loader = Mock()
        mock_loader.load_rhdh_plugins.return_value = [mock_plugin]
        mock_loader_class.return_value = mock_loader

        mock_api = Mock()
        mock_package = RHDHPluginPackage(
            # no versions
            name="test-package",
            versions=[],
        )
        mock_api.fetch_package.return_value = mock_package
        mock_api_class.return_value = mock_api

        mock_updater = Mock()
        mock_updater_class.return_value = mock_updater

        main()

        mock_loader.load_rhdh_plugins.assert_called_once()
        mock_api.fetch_package.assert_called_once()

        # no updates should be attempted
        mock_updater.update_rhdh_plugin.assert_not_called()
        mock_api.create_pull_request.assert_not_called()
