#!/bin/bash
set -e

echo "Starting RHDH Plugin GitOps Updater..."
echo "Config path: $DYNAMIC_PLUGINS_CONFIG_YAML_FILE_PATH"
echo "Config location: $DYNAMIC_PLUGINS_CONFIG_YAML_LOCATION"
echo "GitOps repo: $GITHUB_REPOSITORY"
echo "GitOps branch: $GITHUB_REF"
echo "PR strategy: $UPDATE_PR_STRATEGY"
echo "PR creation limit: $PR_CREATION_LIMIT"
echo "Verbose: $VERBOSE"

cd /app
uv run python main.py