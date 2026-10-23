.DEFAULT_GOAL := help
SHELL         := /bin/zsh

PKG_NAME     := xsearch
PKG_DIR_NAME := xsearch
PKG_DIR      := src/$(PKG_DIR_NAME)
VERSION      := $(shell grep -m 1 version pyproject.toml | tr -s ' ' | tr -d '"' | tr -d "'" | cut -d= -f2 | xargs)

UV     := $(shell command -v uv 2>/dev/null || echo uv)
PYTHON := $(UV) run python

PY_FILES := $(shell $(UV) run python -c 'from pathlib import Path; print(" ".join(map(str, Path("$(PKG_DIR)").rglob("*.py"))))')

.PHONY: help check smoke uv-link uv-unlink status log test-table test-json test-onion

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

test-table:  ## Run test query with Rich table output
	@$(UV) run xsearch "privacy tools" -s -f table -n 3

test-json:  ## Run test query with JSON output
	@$(UV) run xsearch "cryptography" -s -f json -n 2

test-onion:  ## Run test query on dark web (.onion)
	@$(UV) run xsearch "bitcoin" --no-surface -o -f table -n 3

# ── Install / Dev link (uv tool) ─────────────────────────────────────────────

uv-link:  ## Link globally into PATH via uv tool
	@$(UV) tool install --editable . --force
	@echo "✅ $(PKG_NAME) linked globally in ~/.local/bin/xsearch"

uv-unlink:  ## Uninstall global uv tool
	@$(UV) tool uninstall $(PKG_NAME) 2>/dev/null || true
	@echo "✅ $(PKG_NAME) uninstalled from tools"

# ── Git ───────────────────────────────────────────────────────────────────────

status:  ## git status --short
	@git status --short

log:  ## Last 10 commits oneline
	@git log --oneline -10
