.PHONY: help
help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {sub("\\\\n",sprintf("\n%22c"," "), $$2);printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: install
install: ## Installs rhdh-plugin-gitops-updater
	 pip install -e .

.PHONY: ruff
ruff: ## Run ruff for formatting and linting
	uv run ruff check --fix
	uv run ruff format

.PHONY: ty
ty: ## Run type check with ty
	uvx ty check

.PHONY: test
test: ## Run tests with pytest
	uv run pytest

.PHONY: pre-commit-install
pre-commit-install: ## Install pre-commit hooks
	uv run pre-commit install