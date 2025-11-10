#!/usr/bin/env python3
import sys

from src.constants import (
    DYNAMIC_PLUGINS_CONFIG_YAML_FILE_PATH,
    GITHUB_REF,
    GITHUB_REPOSITORY,
    GITHUB_TOKEN,
    PR_CREATION_LIMIT,
    UPDATE_PR_STRATEGY,
    logger,
)
from src.exceptions import GithubPRFailedException
from src.github_api_client import GithubAPIClient
from src.loader import RHDHPluginsConfigLoader
from src.types import (
    GithubPullRequestStrategy,
    RHDHPluginUpdate,
    RHDHPluginUpdaterConfig,
)
from src.updater import RHDHPluginConfigUpdater
from src.utils import rhdh_plugin_needs_update


def main():
    if not GITHUB_REPOSITORY:
        logger.error("Error: GITHUB_REPOSITORY environment variable is required")
        return

    if not GITHUB_TOKEN:
        logger.error("Error: GITHUB_TOKEN environment variable is required")
        return

    gh_api_client = GithubAPIClient(token=GITHUB_TOKEN)
    rhdh_config_loader = RHDHPluginsConfigLoader()
    rhdh_config_updater = RHDHPluginConfigUpdater()
    rhdh_plugins = rhdh_config_loader.load_rhdh_plugins()
    trimmed_file_path = DYNAMIC_PLUGINS_CONFIG_YAML_FILE_PATH.replace(
        RHDHPluginUpdaterConfig.GH_RUNNER_PREFIX, ""
    )

    logger.info(f"found {len(rhdh_plugins)} RHDH plugins to check for updates")

    # list to cache all updates in case of joint strategy
    plugin_updates: "list[RHDHPluginUpdate]" = []
    prs_created = 0

    for plugin in rhdh_plugins:
        logger.info(f"Processing plugin: {plugin.plugin_name}")

        package = gh_api_client.fetch_package(
            plugin.package_name, tag_prefix_filter=plugin.current_tag_prefix
        )
        if not package.versions:
            logger.warning(
                f"no versions found for package {plugin.package_name}, skipping..."
            )
            continue

        # sort by version, considering dual versions
        latest_package_version = sorted(
            package.versions, key=lambda v: (v.version, v.second_version or "")
        )[-1]
        latest_version = latest_package_version.version
        latest_second_version = latest_package_version.second_version

        if not rhdh_plugin_needs_update(
            latest_version,
            plugin.current_version,
            latest_second_version,
            plugin.current_second_version,
        ):
            logger.info(
                f"plugin {plugin.plugin_name} is up-to-date "
                f"(version: {plugin.current_version})"
            )
            continue

        logger.info(
            f"newer version found for plugin {plugin.plugin_name}: "
            f"{latest_version} (current: {plugin.current_version})"
        )

        if UPDATE_PR_STRATEGY == GithubPullRequestStrategy.JOINT:
            logger.debug("caching plugin update for joint PR...")
            plugin_updates.append(
                RHDHPluginUpdate(
                    rhdh_plugin=plugin,
                    new_version=latest_version,
                    new_second_version=latest_second_version,
                )
            )
            continue

        if PR_CREATION_LIMIT > 0 and prs_created >= PR_CREATION_LIMIT:
            logger.warning(
                f"reached the PR creation limit of {PR_CREATION_LIMIT}, stopping..."
            )
            break

        try:
            updated_yaml = rhdh_config_updater.update_rhdh_plugin(
                plugin, latest_version, latest_second_version
            )

            pr_url = gh_api_client.create_pull_request(
                repo_full_name=GITHUB_REPOSITORY,
                file_path=trimmed_file_path,
                new_content=updated_yaml,
                branch_name=RHDHPluginUpdaterConfig.GH_PR_BRANCH_NAME_BASE.format(
                    plugin_name=plugin.plugin_name, latest_version=latest_version
                ),
                pr_title=RHDHPluginUpdaterConfig.GH_PR_TITLE_BASE.format(
                    plugin_name=plugin.plugin_name, latest_version=latest_version
                ),
                pr_body=RHDHPluginUpdaterConfig.GH_PR_BODY_BASE.format(
                    plugin_name=plugin.plugin_name,
                    current_version=plugin.current_version,
                    latest_version=latest_version,
                ),
                base_branch=GITHUB_REF,
            )
            logger.info(f"✓ Created PR: {pr_url}")
            prs_created += 1

        except GithubPRFailedException as e:
            logger.warning(f"✗ Failed to create PR for {plugin.plugin_name}: {e}")

    if plugin_updates:
        logger.info(f"creating joint PR for {len(plugin_updates)} plugin updates...")
        try:
            updated_yaml = rhdh_config_updater.bulk_update_rhdh_plugins(plugin_updates)

            pr_body = RHDHPluginUpdaterConfig.GH_BULK_PR_BODY_BASE.format(
                plugin_updates_count=len(plugin_updates)
            )
            for update in plugin_updates:
                pr_body += (
                    f"- **{update.rhdh_plugin.plugin_name}**: "
                    f"`{update.rhdh_plugin.current_version}` → "
                    f"`{update.new_version}`\n"
                )

            pr_body += (
                "\n🤖 Generated with [RHDH Plugin GitOps Updater]"
                "(https://github.com/thepetk/rhdh-plugin-gitops-updater)\n"
            )

            pr_url = gh_api_client.create_pull_request(
                repo_full_name=GITHUB_REPOSITORY,
                file_path=trimmed_file_path,
                new_content=updated_yaml,
                branch_name=RHDHPluginUpdaterConfig.GH_BULK_PR_BRANCH_NAME_BASE,
                pr_title=RHDHPluginUpdaterConfig.GH_BULK_PR_TITLE_BASE.format(
                    plugin_updates_count=len(plugin_updates)
                ),
                pr_body=pr_body,
                base_branch=GITHUB_REF,
            )
            prs_created += 1
            logger.info(f"✓ Created joint PR: {pr_url}")

        except GithubPRFailedException as e:
            logger.error(f"✗ Failed to create joint PR: {e}")
            sys.exit(1)

    logger.info(f"done! Created {prs_created} pull request(s)")


if __name__ == "__main__":
    main()
