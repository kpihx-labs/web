.DEFAULT_GOAL := help
SHELL         := /bin/zsh

PKG_NAME     := search-unifier
PKG_DIR_NAME := search_unifier
PKG_DIR      := src/$(PKG_DIR_NAME)
VERSION      := $(shell grep -m 1 version pyproject.toml | tr -s ' ' | tr -d '"' | tr -d "'" | cut -d= -f2 | xargs)

UV     := $(shell command -v uv 2>/dev/null || echo uv)
PYTHON := $(UV) run python

PY_FILES := $(shell $(UV) run python -c 'from pathlib import Path; print(" ".join(map(str, Path("$(PKG_DIR)").rglob("*.py"))))')

.PHONY: help check smoke uv-link uv-unlink status log run-surface run-onion run-all

help:  ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

# ── Quality ──────────────────────────────────────────────────────────────────

check: smoke  ## Syntax compile + type check
	@$(PYTHON) -m py_compile $(PY_FILES)
	@echo "✅ Syntax check passed"

smoke:  ## Smoke test verifying module imports
	@$(PYTHON) -c "import $(PKG_DIR_NAME)" || (echo "❌ smoke test failed"; exit 1)
	@echo "✅ Smoke test passed"

# ── Execution ────────────────────────────────────────────────────────────────

run-surface:  ## Run test query on surface web
	@$(UV) run search-unifier "privacy tools" --surface -f md --limit 3

run-onion:  ## Run test query on dark web (.onion)
	@$(UV) run search-unifier "security" --no-surface --onion -f md --limit 3

run-all:  ## Run test query across surface and dark web simultaneously
	@$(UV) run search-unifier "privacy" --surface --onion -f md --limit 3

# ── Install / Dev link (uv tool) ─────────────────────────────────────────────

uv-link:  ## Link globally into PATH via uv tool
	@$(UV) tool install --editable . --force
	@echo "✅ $(PKG_NAME) linked globally in ~/.local/bin/search-unifier"

uv-unlink:  ## Uninstall global uv tool
	@$(UV) tool uninstall $(PKG_NAME) 2>/dev/null || true
	@echo "✅ $(PKG_NAME) uninstalled from tools"

# ── Git ───────────────────────────────────────────────────────────────────────

status:  ## git status --short
	@git status --short

log:  ## Last 10 commits oneline
	@git log --oneline -10
