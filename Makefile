SHELL := /bin/zsh
.DEFAULT_GOAL := help
UV := uv
BACKEND ?= $(abspath ../searxng)
HOST ?= github

.PHONY: help deps install uv-link uninstall purge purge-all check build publish push backend-clone backend-up backend-down backend-health backend-purge backend-onion-up backend-onion-down
help: ## Show operations; no dependency installation on help
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST)
deps: ## Show system dependencies and upstream installation paths
	@$(UV) run web capabilities --format json
	@printf '%s\n' 'System: ffmpeg; SongRec (cargo install songrec --no-default-features --features ffmpeg); optional poppler-utils/tesseract-ocr/fonts-dejavu-core. See README for native build prerequisites.'
install: ## Install editable CLI and create user config without overwriting
	@$(UV) sync
	@$(UV) tool install --editable . --force
	@web setup
uv-link: install ## Standard compatibility target
uninstall: ## Remove only the executable/environment; retain user evidence
	@$(UV) tool uninstall k-web
purge: backend-down ## Trash owned runtime data; retain source/shared native tools
	@$(UV) run web purge --yes
	@$(UV) tool uninstall k-web
purge-all: ## Confirmed backend backup/removal followed by app state/tool purge
	@$(MAKE) backend-purge CONFIRM="$(CONFIRM)"
	@$(MAKE) purge
check: ## Full active-package lint, types and offline regression tests
	@ruff check src tests
	@ruff format --check src tests
	@pyright --pythonpath .venv/bin/python src
	@$(UV) run pytest -q
build: ## Build only current k-web artifacts with uv_build
	@test ! -d dist || rm -r dist
	@$(UV) build
publish: build ## Explicit publish; use with-env in an interactive tmux ops pane
	@$(UV) publish dist/k_web-*.whl dist/k_web-*.tar.gz
push: ## Push current branch to both SSH remotes
	@for remote in github gitlab; do git push $$remote "$$(git branch --show-current)" || exit; done
backend-clone: ## Fetch sibling backend repo from HOST=github or gitlab
	@test ! -e "$(BACKEND)" || { printf '%s\n' 'Backend directory already exists; retained'; exit 1; }
	@git clone "git@$(HOST).com:kpihx-labs/searxng.git" "$(BACKEND)"
backend-up: ## Validate/start the sibling deployment
	@$(MAKE) -C "$(BACKEND)" up
backend-down: ## Stop only the sibling deployment, retaining volumes
	@$(MAKE) -C "$(BACKEND)" down
backend-health: ## Verify local API and real upstream canary
	@$(MAKE) -C "$(BACKEND)" live
backend-onion-up: ## Enable isolated optional onion search
	@$(MAKE) -C "$(BACKEND)" onion-up
backend-onion-down: ## Disable only optional onion search
	@$(MAKE) -C "$(BACKEND)" onion-down
backend-purge: ## Explicit backend volume removal, after private /tmp backup
	@$(MAKE) -C "$(BACKEND)" purge CONFIRM="$(CONFIRM)"
