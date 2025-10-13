# RHDH Plugin GitOps Updater

[![Tests](https://github.com/thepetk/rhdh-plugin-gitops-updater/actions/workflows/ci.yaml/badge.svg)](https://github.com/thepetk/rhdh-plugin-gitops-updater/actions/workflows/ci.yaml)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)

> [!IMPORTANT]
> This is a personal **Proof of Concept (PoC)** GitHub Action. Use at your own risk in production environments.

A GitHub Action that monitors and updates Red Hat Developer Hub (RHDH) dynamic plugins in your GitOps repository. This action checks for new plugin versions and creates pull requests to keep your RHDH installation up to date.

## Features

- 🔄 **Automatic Plugin Updates**: Monitors RHDH plugin versions from the GitHub Container Registry
- 🎯 **Flexible PR Strategies**: Create `separate` PRs per plugin or a single `joint` PR for all updates
- 🔒 **Safe Updates**: Preserves YAML formatting and validates plugin definitions
- 🚀 **GitOps Integration**: Works seamlessly with GitOps-based RHDH deployments
- ⚙️ **Configurable**: Customize PR limits, config paths, and update strategies
- 📝 **Detailed Logging**: Optional verbose mode for debugging

## Quick Start

Add this workflow to your GitOps repository at `.github/workflows/update-rhdh-plugins.yaml`:

```yaml
name: Update RHDH Plugins

on:
  schedule:
    # Run daily at 2 AM UTC
    - cron: "0 2 * * *"
  workflow_dispatch:

jobs:
  update-plugins:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Update RHDH plugins
        uses: thepetk/rhdh-plugin-gitops-updater@v1
        with:
          config-path: "charts/rhdh/values.yaml"
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

## Usage Examples

### Basic Usage with Separate PRs

Create individual pull requests for each plugin update:

```yaml
- name: Update RHDH plugins
  uses: thepetk/rhdh-plugin-gitops-updater@v1
  with:
    config-path: "charts/rhdh/values.yaml"
    github-token: ${{ secrets.GITHUB_TOKEN }}
    update-pr-strategy: "separate"
```

### Joint PR for All Updates

Create a single pull request containing all plugin updates:

```yaml
- name: Update RHDH plugins
  uses: thepetk/rhdh-plugin-gitops-updater@v1
  with:
    config-path: "charts/rhdh/values.yaml"
    github-token: ${{ secrets.GITHUB_TOKEN }}
    update-pr-strategy: "joint"
```

### Custom Configuration Location

If your dynamic plugins configuration is at a different YAML path:

```yaml
- name: Update RHDH plugins
  uses: thepetk/rhdh-plugin-gitops-updater@v1
  with:
    config-path: "dynamic-plugins.yaml"
    config-location: "plugins.dynamic"
    github-token: ${{ secrets.GITHUB_TOKEN }}
```

### Limit Number of PRs

Limit the number of pull requests created in a single run:

```yaml
- name: Update RHDH plugins
  uses: thepetk/rhdh-plugin-gitops-updater@v1
  with:
    config-path: "charts/rhdh/values.yaml"
    github-token: ${{ secrets.GITHUB_TOKEN }}
    update-pr-strategy: "separate"
    pr-creation-limit: "3"
```

### Enable Verbose Logging

For debugging or detailed information:

```yaml
- name: Update RHDH plugins
  uses: thepetk/rhdh-plugin-gitops-updater@v1
  with:
    config-path: "charts/rhdh/values.yaml"
    github-token: ${{ secrets.GITHUB_TOKEN }}
    verbose: "1"
```

## Inputs

| Input                | Description                                                                              | Required | Default                  |
| -------------------- | ---------------------------------------------------------------------------------------- | -------- | ------------------------ |
| `config-path`        | Path to the dynamic plugins config YAML file (e.g., `charts/rhdh/values.yaml`)           | Yes      | -                        |
| `config-location`    | Location of the dynamic plugins config inside the YAML file                              | No       | `global.dynamic.plugins` |
| `github-token`       | GitHub token for API access and PR creation                                              | Yes      | -                        |
| `update-pr-strategy` | PR creation strategy: `separate` or `joint`                                              | No       | `separate`               |
| `pr-creation-limit`  | Maximum number of PRs to create (0 for unlimited, only applies with `separate` strategy) | No       | `0`                      |
| `verbose`            | Enable verbose logging (0 = normal, 1 = debug)                                           | No       | `0`                      |

## How It Works

1. **Discovery**: The action reads your dynamic plugins configuration file and identifies all RHDH plugins
2. **Version Check**: For each plugin, it queries the GitHub Container Registry for the latest version
3. **Comparison**: Compares current versions with the latest available versions
4. **PR Creation**: Creates pull requests based on your chosen strategy:
   - **Separate**: One PR per plugin update
   - **Joint**: Single PR with all updates
5. **Formatting Preservation**: Updates are made via string replacement to preserve your YAML formatting

## Supported Plugin Format

The action works with RHDH dynamic plugins defined in the following format:

```yaml
global:
  dynamic:
    plugins:
      - disabled: false
        package: oci://ghcr.io/redhat-developer/rhdh-plugin-export-overlays/backstage-plugin-name:next__1.0.0!backstage-plugin-name
      - disabled: false
        package: oci://ghcr.io/redhat-developer/rhdh-plugin-export-overlays/another-plugin:next__2.0.0!another-plugin
```

## Permissions

The action requires the following permissions:

```yaml
jobs:
  update-plugins:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
      packages: read
    steps:
      # ...
```

## Development

### Local Testing

1. Clone the repository:

   ```bash
   git clone https://github.com/thepetk/rhdh-plugin-gitops-updater.git
   cd rhdh-plugin-gitops-updater
   ```

2. Install dependencies:

   ```bash
   make install
   ```

3. Run tests:

   ```bash
   make test
   ```

4. Run linting:

   ```bash
   make ruff
   ```

5. Run type checking:
   ```bash
   make ty
   ```

### Running Locally

You can run the updater script directly:

```bash
export GITHUB_TOKEN="your-token"
export GITOPS_REPO="owner/repo"
export DYNAMIC_PLUGINS_CONFIG_YAML_FILE_PATH="charts/rhdh/values.yaml"
export UPDATE_PR_STRATEGY="separate"

uv run main.py
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request or open an issue you may have noticed.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
