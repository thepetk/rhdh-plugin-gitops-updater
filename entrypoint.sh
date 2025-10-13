#!/bin/bash
set -e

echo "Starting RHDH Plugin GitOps Updater..."
echo "Config path: $DYNAMIC_PLUGINS_CONFIG_YAML_FILE_PATH"
echo "Config location: $DYNAMIC_PLUGINS_CONFIG_YAML_LOCATION"
echo "GitOps repo: $GITOPS_REPO"
echo "PR strategy: $UPDATE_PR_STRATEGY"
echo "PR creation limit: $PR_CREATION_LIMIT"
echo "Verbose: $VERBOSE"

# Environment variables are already set by action.yml
# They will be picked up by main.py automatically
uv run python main.py
