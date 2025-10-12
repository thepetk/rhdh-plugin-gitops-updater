#!/bin/bash
set -e

# parse inputs from action.yml
DYNAMIC_PLUGINS_PATH="$1"
GITHUB_TOKEN="$2"
PLUGIN_FILTER="$3"
PR_MODE="$4"
MAX_PRS="$5"

echo "Starting RHDH Plugin GitOps Updater..."
echo "Dynamic plugins path: $DYNAMIC_PLUGINS_PATH"
echo "PR mode: $PR_MODE"
echo "Max PRs: $MAX_PRS"

uv run python main.py \
  --dynamic-plugins-path "$DYNAMIC_PLUGINS_PATH" \
  --github-token "$GITHUB_TOKEN" \
  --plugin-filter "$PLUGIN_FILTER" \
  --pr-mode "$PR_MODE" \
  --max-prs "$MAX_PRS"
