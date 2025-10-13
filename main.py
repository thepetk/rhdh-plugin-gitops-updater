#!/usr/bin/env python3
from dataclasses import dataclass
import logging
import os
import re
import sys
from typing import Any
from urllib.parse import quote, urlparse

import requests
import yaml
from github import Auth, Github
from github.Repository import Repository
from packaging.version import Version
from requests import Response

# DYNAMIC_PLUGINS_CONFIG_YAML_FILE_PATH: is the path of the dynamic
# plugins config yaml file
DYNAMIC_PLUGINS_CONFIG_YAML_FILE_PATH = os.getenv(
    "DYNAMIC_PLUGINS_CONFIG_YAML_FILE_PATH", "dynamic-plugins.yaml"
)

# DYNAMIC_PLUGINS_CONFIG_YAML_LOCATION: is the location of the dynamic
# plugins config inside the yaml file.
DYNAMIC_PLUGINS_CONFIG_YAML_LOCATION = os.getenv(
    "DYNAMIC_PLUGINS_CONFIG_YAML_LOCATION", "global.dynamic.plugins"
)

# GITHUB_TOKEN: is the GitHub token to use for authentication
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# UPDATE_PR_STRATEGY: is the strategy to use when creating
# the github pull requests. It can be either "separate" or "joint".
UPDATE_PR_STRATEGY = os.getenv("UPDATE_PR_STRATEGY", "separate")

# PR_CREATION_LIMIT: is the maximum number of pull requests to create.
PR_CREATION_LIMIT = int(os.getenv("PR_CREATION_LIMIT", "0"))

# GITOPS_REPO: is the GitOps repository where PRs will be created (format: owner/repo)
GITOPS_REPO = os.getenv("GITOPS_REPO", "")

# GITOPS_BASE_BRANCH: is the base branch for PRs
GITOPS_BASE_BRANCH = os.getenv("GITOPS_BASE_BRANCH", "main")

# VERBOSE: is the verbosity level (0 = normal, 1 = verbose)
VERBOSE = int(os.getenv("VERBOSE", 0))

# LOGGING_LEVEL: is the logging level based on verbosity
LOGGING_LEVEL = "DEBUG" if VERBOSE > 0 else "INFO"

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOGGING_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


class GithubPRFailedException(Exception):
    """Exception raised when a GitHub pull request operation fails."""

    pass


class InvalidRHDHPluginPackageDefinitionException(Exception):
    """Exception raised when an RHDH plugin package definition is invalid."""

    pass


class RHDHPluginUpdaterConfig:
    GH_ORG_NAME = "redhat-developer"
    GH_REPO_NAME = "rhdh-plugin-export-overlays"
    GH_PACKAGE_TAG_PREFIX = "next__"
    GH_PACKAGES_BASE_URL = "https://api.github.com/orgs/{org}/packages"
    GH_PACKAGES_VERSION_BASE_URL = "https://api.github.com/orgs/{org}/packages/{package_type}/{package_name}/versions"
    GH_CR_REGISTRY_PREFIX = (
        "oci://ghcr.io/redhat-developer/rhdh-plugin-export-overlays/"
    )
    GH_PR_BRANCH_NAME_BASE = "update-{plugin_name}-{latest_version}"
    GH_PR_TITLE_BASE = "[rhdh-plugin-gitops-updater] Update `{plugin_name}` to version {latest_version}"
    GH_PR_BODY_BASE = """## Plugin Update

**Plugin**: `{plugin_name}`
**Current Version**: `{current_version}`
**New Version**: `{latest_version}`

This PR updates the RHDH plugin to the latest version.

🤖 Generated with [RHDH Plugin GitOps Updater](https://github.com/thepetk/rhdh-plugin-gitops-updater)
"""
    GH_BULK_PR_BRANCH_NAME_BASE = "update-rhdh-plugins-batch"
    GH_BULK_PR_TITLE_BASE = (
        "[rhdh-plugin-gitops-updater] Update {plugin_updates_count} RHDH plugins"
    )
    GH_BULK_PR_BODY_BASE = """## Batch Plugin Update

This PR updates {plugin_updates_count} RHDH plugins to their latest versions:

"""


class GithubPullRequestStrategy:
    SEPARATE = "separate"
    JOINT = "joint"


@dataclass
class RHDHPluginPackageVersion:
    name: "str"
    version: "Version"
    created_at: "str"


@dataclass
class RHDHPluginPackage:
    """
    Represents the RHDH plugin github package with its versions.
    """

    name: "str"
    versions: "list[RHDHPluginPackageVersion]"


@dataclass
class RHDHPlugin:
    """
    Represents an RHDH plugin from the dynamic plugins configuration.
    """

    package_name: "str"
    current_version: "Version"
    plugin_name: "str"
    disabled: "bool"


@dataclass
class RHDHPluginUpdate:
    """
    Represents an update for an RHDH plugin.
    """

    rhdh_plugin: "RHDHPlugin"
    new_version: "Version"


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


class GithubAPIClient:
    """
    Handles all GitHub-related operations.
    """

    def __init__(self, token: "str", per_page=100) -> "None":
        self.token = token
        self.per_page = per_page

        self.client = Github(auth=Auth.Token(token))

        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def _fetch_next(
        self, response: "Response", url: "str", params: "dict[str, int]"
    ) -> "tuple[str | None, dict[str, int]]":
        """
        extracts the next URL from the response links if available
        """
        if "next" not in response.links:
            return None, params

        # params unset as the next URL already contains query params
        params = {}
        url = response.links["next"]["url"]

        return url, params

    def _paginate(
        self, url: "str", extra_params: "dict[str, str] | None" = None
    ) -> "list[dict[str, Any]]":
        """
        handles pagination for GitHub API requests

        ::raises:: requests.HTTPError If the API request fails
        """
        items: "list[dict[str, Any]]" = []
        params = {
            "per_page": self.per_page,
        }

        if extra_params:
            params.update(extra_params)

        while url:
            logger.debug(f"fetching (GET) {url}")
            response = self._session.get(url, params=params)
            response.raise_for_status()

            resp_items = response.json()
            items.extend(resp_items)

            # handle pagination case
            url, params = self._fetch_next(response, url, params)
        return items

    def _convert_to_rhdh_plugin_package(
        self, package_name: "str", raw_versions: "list[dict[str, Any]]"
    ) -> "RHDHPluginPackage":
        """
        converts a list of package versions into an RHDHPluginPackage
        """
        versions = []
        for v in raw_versions:
            metadata = v.get("metadata")
            if not isinstance(metadata, dict):
                continue

            container = metadata.get("container")
            if not isinstance(container, dict):
                continue

            tags = container.get("tags")
            if not isinstance(tags, list) or not tags:
                continue

            tag = str(tags[0])
            if not tag.startswith(RHDHPluginUpdaterConfig.GH_PACKAGE_TAG_PREFIX):
                continue

            created_at = v.get("created_at")
            if not isinstance(created_at, str):
                continue

            logger.debug(f"found version {tag} for package {package_name}")
            versions.append(
                RHDHPluginPackageVersion(
                    name=str(v.get("name", "")),
                    version=Version(
                        tag.replace(RHDHPluginUpdaterConfig.GH_PACKAGE_TAG_PREFIX, "")
                    ),
                    created_at=created_at,
                )
            )

        return RHDHPluginPackage(name=package_name, versions=versions)

    def fetch_package(
        self,
        package_name: "str",
        org=RHDHPluginUpdaterConfig.GH_ORG_NAME,
    ) -> "RHDHPluginPackage":
        """
        fetch the RHDHPluginPackage for the given package name
        """
        # URL-encode the package name to handle slashes
        logger.debug(f"fetching package {package_name}")
        encoded_package_name = quote(package_name, safe="")
        raw_versions = self._paginate(
            url=RHDHPluginUpdaterConfig.GH_PACKAGES_VERSION_BASE_URL.format(
                org=org, package_type="container", package_name=encoded_package_name
            )
        )

        # fallback to package without versions
        if not raw_versions:
            logger.warning(f"no versions found for package {package_name}")
            return RHDHPluginPackage(name=package_name, versions=[])

        return self._convert_to_rhdh_plugin_package(package_name, raw_versions)

    def _branch_exists(self, repo: "Repository", branch_name: "str") -> "bool":
        """
        checks if a branch exists in the given repository
        """
        try:
            repo.get_git_ref(f"heads/{branch_name}")
            logger.debug(f"branch {branch_name} already exists")
            return True
        except Exception:
            logger.debug(f"branch {branch_name} does not exist, will create it")
            return False

    def _handle_new_endline(self, original_content: "str", new_content: "str") -> "str":
        """
        handles the new_endline formating issue
        """
        original_ends_with_newline = original_content.endswith("\n")

        if original_ends_with_newline and not new_content.endswith("\n"):
            new_content += "\n"
        elif not original_ends_with_newline and new_content.endswith("\n"):
            new_content = new_content.rstrip("\n")

        return new_content

    def create_pull_request(
        self,
        repo_full_name: "str",
        file_path: "str",
        new_content: "str",
        branch_name: "str",
        pr_title: "str",
        pr_body: "str",
        base_branch=GITOPS_BASE_BRANCH,
    ) -> str:
        """
        creates a pull request with file changes.

        ::raises:: GithubPRFailedException: If PR creation fails
        """
        logger.debug(f"creating PR in {repo_full_name} on branch {branch_name}")
        repo = self.client.get_repo(repo_full_name)
        base_ref = repo.get_git_ref(f"heads/{base_branch}")
        base_sha = base_ref.object.sha

        if self._branch_exists(repo, branch_name):
            # skip for separate pr strategy
            if UPDATE_PR_STRATEGY == GithubPullRequestStrategy.SEPARATE:
                logger.debug(f"checking for existing open PR for branch {branch_name}")
                raise GithubPRFailedException(f"Branch {branch_name} already exists")

            # if branch exists, check if there's an open PR for it
            try:
                pulls = repo.get_pulls(
                    state="open",
                    head=f"{repo.owner.login}:{branch_name}",
                    base=base_branch,
                )
            except Exception as e:
                logger.debug(f"no open PR found for branch {branch_name}: {e}")

            for pr in pulls:
                raise GithubPRFailedException(
                    f"Open PR already exists for branch {branch_name}: {pr.html_url}"
                )
        else:
            try:
                repo.create_git_ref(f"refs/heads/{branch_name}", base_sha)
                logger.debug(f"created branch {branch_name}")
            except Exception as e:
                raise GithubPRFailedException(
                    f"Failed to create branch {branch_name}: {e}"
                ) from e

        try:
            contents = repo.get_contents(file_path, ref=branch_name)
            logger.debug(f"updating file {file_path} in branch {branch_name}")
            repo.update_file(
                path=file_path,
                message=f"Update {file_path}",
                content=self._handle_new_endline(
                    original_content=contents.decoded_content.decode("utf-8"),
                    new_content=new_content,
                ),
                sha=contents.sha,
                branch=branch_name,
            )
        except Exception as update_error:
            raise GithubPRFailedException(
                f"Failed to update file {file_path}: {update_error}"
            ) from update_error

        try:
            logger.debug(f"opening pull request {pr_title}")
            pr = repo.create_pull(
                title=pr_title, body=pr_body, head=branch_name, base=base_branch
            )
            return pr.html_url
        except Exception as pr_error:
            raise GithubPRFailedException(
                f"Failed to create PR: {pr_error}"
            ) from pr_error


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
    ) -> "list[dict[str, str | bool]]":
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
                f"Too few image ref parts ({len(image_ref_parts)}) for package: {package}"
            )

        # get name and version
        name_and_version = image_ref_parts[-1]

        if ":" not in name_and_version:
            raise InvalidRHDHPluginPackageDefinitionException(
                f"Tag not found for package {package}"
            )

        name, raw_version = name_and_version.rsplit(":", 1)

        if RHDHPluginUpdaterConfig.GH_PACKAGE_TAG_PREFIX not in raw_version:
            raise InvalidRHDHPluginPackageDefinitionException(
                f"Tag {raw_version} not valid for package {package}"
            )

        version = Version(
            version=raw_version.replace(
                RHDHPluginUpdaterConfig.GH_PACKAGE_TAG_PREFIX, ""
            )
        )

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
                    package_name=parsed["package_name"],
                    current_version=parsed["version"],
                    plugin_name=parsed["plugin_name"],
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
                f"updated config for {plugin.plugin_name} from {plugin.current_version} to {new_version}"
            )
        else:
            logger.warning(
                f"no match found for plugin {plugin.plugin_name} with version {plugin.current_version}"
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


def rhdh_plugin_needs_update(
    latest_version: "Version", current_version: "Version"
) -> "bool":
    """
    checks if the latest version is greater than the current version
    """
    return latest_version > current_version


def main():
    if not GITOPS_REPO:
        logger.error("Error: GITOPS_REPO environment variable is required")
        return

    if not GITHUB_TOKEN:
        logger.error("Error: GITHUB_TOKEN environment variable is required")
        return

    gh_api_client = GithubAPIClient(token=GITHUB_TOKEN)
    rhdh_config_loader = RHDHPluginsConfigLoader()
    rhdh_config_updater = RHDHPluginConfigUpdater()
    rhdh_plugins = rhdh_config_loader.load_rhdh_plugins()

    logger.info(f"found {len(rhdh_plugins)} RHDH plugins to check for updates")

    # list to cache all updates in case of joint strategy
    plugin_updates: "list[RHDHPluginUpdate]" = []
    prs_created = 0

    for plugin in rhdh_plugins:
        logger.info(f"Processing plugin: {plugin.plugin_name}")

        package = gh_api_client.fetch_package(plugin.package_name)
        if not package.versions:
            logger.warning(
                f"no versions found for package {plugin.package_name}, skipping..."
            )
            continue

        latest_version = sorted(package.versions, key=lambda v: v.version)[-1].version

        if not rhdh_plugin_needs_update(latest_version, plugin.current_version):
            logger.info(
                f"plugin {plugin.plugin_name} is up-to-date (version: {plugin.current_version})"
            )
            continue

        logger.info(
            f"newer version found for plugin {plugin.plugin_name}: {latest_version} (current: {plugin.current_version})"
        )

        if UPDATE_PR_STRATEGY == GithubPullRequestStrategy.JOINT:
            logger.debug("caching plugin update for joint PR...")
            plugin_updates.append(
                RHDHPluginUpdate(rhdh_plugin=plugin, new_version=latest_version)
            )
            continue

        if PR_CREATION_LIMIT > 0 and prs_created >= PR_CREATION_LIMIT:
            logger.warning(
                f"reached the PR creation limit of {PR_CREATION_LIMIT}, stopping..."
            )
            break

        try:
            updated_yaml = rhdh_config_updater.update_rhdh_plugin(
                plugin, latest_version
            )

            pr_url = gh_api_client.create_pull_request(
                repo_full_name=GITOPS_REPO,
                file_path=DYNAMIC_PLUGINS_CONFIG_YAML_FILE_PATH,
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
                base_branch=GITOPS_BASE_BRANCH,
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
                pr_body += f"- **{update.rhdh_plugin.plugin_name}**: `{update.rhdh_plugin.current_version}` → `{update.new_version}`\n"

            pr_body += "\n🤖 Generated with [RHDH Plugin GitOps Updater](https://github.com/thepetk/rhdh-plugin-gitops-updater)\n"

            pr_url = gh_api_client.create_pull_request(
                repo_full_name=GITOPS_REPO,
                file_path=DYNAMIC_PLUGINS_CONFIG_YAML_FILE_PATH,
                new_content=updated_yaml,
                branch_name=RHDHPluginUpdaterConfig.GH_BULK_PR_BRANCH_NAME_BASE,
                pr_title=RHDHPluginUpdaterConfig.GH_BULK_PR_TITLE_BASE.format(
                    plugin_updates_count=len(plugin_updates)
                ),
                pr_body=pr_body,
                base_branch=GITOPS_BASE_BRANCH,
            )
            prs_created += 1
            logger.info(f"✓ Created joint PR: {pr_url}")

        except GithubPRFailedException as e:
            logger.error(f"✗ Failed to create joint PR: {e}")
            sys.exit(1)

    logger.info(f"done! Created {prs_created} pull request(s)")


if __name__ == "__main__":
    main()
