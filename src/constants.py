import logging
import os

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

# GITHUB_REPOSITORY: is the Github repository where PRs will be
# created (format: owner/repo)
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY", "")

# GITHUB_REF: is the base branch for PRs
GITHUB_REF = os.getenv("GITHUB_REF", "main")

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
