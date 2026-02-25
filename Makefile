# © 2026 The Radiativity Company
# Licensed under the Apache License, Version 2.0
# See the LICENSE file for details.

# --- Configuration ---
PROJECTNAME := ucon
PYTHON ?= 3.12
SUPPORTED_PYTHONS := 3.7 3.8 3.9 3.10 3.11 3.12 3.13 3.14
UV_VENV ?= .${PROJECTNAME}-${PYTHON}
UV_INSTALLED := .uv-installed
DEPS_INSTALLED := ${UV_VENV}/.deps-installed
TESTDIR := tests/
TESTNAME ?=
COVERAGE ?= true

# --- Color Setup ---
GREEN := \033[0;32m
CYAN := \033[0;36m
YELLOW := \033[1;33m
RESET := \033[0m

# --- Help Command ---
.PHONY: help
help:
	@echo "\n${YELLOW}ucon Development Commands${RESET}\n"
	@echo "  ${CYAN}install${RESET}       - Install package with all extras"
	@echo "  ${CYAN}install-test${RESET}  - Install with test dependencies only"
	@echo "  ${CYAN}test${RESET}          - Run tests (PYTHON=X.Y for specific version)"
	@echo "  ${CYAN}test-all${RESET}      - Run tests across all supported Python versions"
	@echo "  ${CYAN}coverage${RESET}      - Generate coverage report"
	@echo "  ${CYAN}build${RESET}         - Build source and wheel distributions"
	@echo "  ${CYAN}docs${RESET}          - Build documentation (output in site/)"
	@echo "  ${CYAN}docs-serve${RESET}    - Start documentation dev server"
	@echo "  ${CYAN}venv${RESET}          - Create virtual environment"
	@echo "  ${CYAN}clean${RESET}         - Remove build artifacts and caches"
	@echo "  ${CYAN}stubs${RESET}         - Generate dimension.pyi type stubs"
	@echo "  ${CYAN}stubs-check${RESET}   - Verify stubs are current (for CI)"
	@echo ""
	@echo "${YELLOW}Variables:${RESET}\n"
	@echo "  PYTHON=${PYTHON}		- Python version for test target"
	@echo "  UV_VENV=${UV_VENV}	- Path to virtual environment"
	@echo "  TESTNAME=		- Specific test to run (e.g., tests.ucon.test_core)"
	@echo "  COVERAGE=${COVERAGE}		- Enable coverage (true/false)"
	@echo ""

# --- uv Installation ---
${UV_INSTALLED}:
	@command -v uv >/dev/null 2>&1 || { \
		echo "${GREEN}Installing uv...${RESET}"; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	}
	@touch ${UV_INSTALLED}

# --- Virtual Environment ---
${UV_VENV}: ${UV_INSTALLED}
	@echo "${GREEN}Creating virtual environment at ${UV_VENV}...${RESET}"
	@uv venv --python ${PYTHON} ${UV_VENV}

${DEPS_INSTALLED}: pyproject.toml uv.lock | ${UV_VENV}
	@echo "${GREEN}Syncing dependencies into ${UV_VENV}...${RESET}"
	@UV_PROJECT_ENVIRONMENT=${UV_VENV} uv sync --python ${PYTHON} --extra test --extra pydantic --extra mcp
	@touch ${DEPS_INSTALLED}

.PHONY: venv
venv: ${DEPS_INSTALLED}
	@echo "${CYAN}Virtual environment ready at ${UV_VENV}${RESET}"
	@echo "${CYAN}Activate with:${RESET} source ${UV_VENV}/bin/activate"

# --- Installation ---
.PHONY: install-test
install-test: ${UV_VENV}
	@UV_PROJECT_ENVIRONMENT=${UV_VENV} uv sync --python ${PYTHON} --extra test

.PHONY: install
install: ${UV_VENV}
	@echo "${GREEN}Installing with all extras into ${UV_VENV}...${RESET}"
	@UV_PROJECT_ENVIRONMENT=${UV_VENV} uv sync --python ${PYTHON} --extra test --extra pydantic --extra mcp

# --- Testing ---
.PHONY: test
test: ${DEPS_INSTALLED}
	@echo "${GREEN}Running tests with Python ${PYTHON}...${RESET}"
ifeq ($(COVERAGE),true)
	@UV_PROJECT_ENVIRONMENT=${UV_VENV} uv run --python ${PYTHON} coverage run --source=ucon --branch \
		--omit="**/tests/*,**/site-packages/*.py,setup.py" \
		-m pytest $(if $(TESTNAME),$(TESTNAME),${TESTDIR}) -q
	@UV_PROJECT_ENVIRONMENT=${UV_VENV} uv run --python ${PYTHON} coverage report -m
	@UV_PROJECT_ENVIRONMENT=${UV_VENV} uv run --python ${PYTHON} coverage xml
else
	@UV_PROJECT_ENVIRONMENT=${UV_VENV} uv run --python ${PYTHON} -m pytest \
		$(if $(TESTNAME),$(TESTNAME),${TESTDIR}) -q
endif

.PHONY: test-all
test-all: ${UV_INSTALLED}
	@echo "${GREEN}Running tests across all supported Python versions...${RESET}"
	@for pyver in $(SUPPORTED_PYTHONS); do \
		echo "\n${CYAN}=== Python $$pyver ===${RESET}"; \
		uv run --python $$pyver -m pytest ${TESTDIR} -q \
		|| echo "${YELLOW}Python $$pyver: FAILED or not available${RESET}"; \
	done

# --- Coverage ---
.PHONY: coverage
coverage: ${DEPS_INSTALLED}
	@echo "${GREEN}Generating coverage report...${RESET}"
	@UV_PROJECT_ENVIRONMENT=${UV_VENV} uv run --python ${PYTHON} coverage report -m
	@UV_PROJECT_ENVIRONMENT=${UV_VENV} uv run --python ${PYTHON} coverage html
	@echo "${CYAN}HTML report at htmlcov/index.html${RESET}"

# --- Documentation ---
DOCS_DEPS_INSTALLED := ${UV_VENV}/.docs-deps-installed

${DOCS_DEPS_INSTALLED}: pyproject.toml | ${UV_VENV}
	@echo "${GREEN}Installing docs dependencies...${RESET}"
	@UV_PROJECT_ENVIRONMENT=${UV_VENV} uv sync --python ${PYTHON} --extra docs
	@touch ${DOCS_DEPS_INSTALLED}

.PHONY: docs
docs: ${DOCS_DEPS_INSTALLED}
	@echo "${GREEN}Building documentation...${RESET}"
	@UV_PROJECT_ENVIRONMENT=${UV_VENV} uv run --python ${PYTHON} mkdocs build
	@echo "${CYAN}Documentation at site/${RESET}"

.PHONY: docs-serve
docs-serve: ${DOCS_DEPS_INSTALLED}
	@echo "${GREEN}Starting documentation server...${RESET}"
	@UV_PROJECT_ENVIRONMENT=${UV_VENV} uv run --python ${PYTHON} mkdocs serve

# --- Building ---
.PHONY: build
build: ${UV_INSTALLED}
	@echo "${GREEN}Building distributions...${RESET}"
	@uv build
	@echo "${CYAN}Distributions at dist/${RESET}"

# --- Cleaning ---
.PHONY: clean
clean:
	@echo "${GREEN}Cleaning build artifacts...${RESET}"
	@rm -rf dist/ build/ *.egg-info/
	@rm -rf ${UV_VENV} ${DEPS_INSTALLED} ${UV_INSTALLED}
	@rm -rf .uv_cache .pytest_cache htmlcov/
	@rm -f coverage.xml .coverage
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "${CYAN}Clean complete.${RESET}"

.PHONY: clean-all
clean-all: clean
	@echo "${YELLOW}Removing uv.lock...${RESET}"
	@rm -f uv.lock

# --- Stubs ---
.PHONY: stubs
stubs: ${DEPS_INSTALLED}
	@echo "${GREEN}Generating dimension stubs...${RESET}"
	@UV_PROJECT_ENVIRONMENT=${UV_VENV} uv run --python ${PYTHON} \
		python scripts/generate_dimension_stubs.py -o ucon/dimension.pyi
	@echo "${CYAN}Wrote ucon/dimension.pyi${RESET}"

.PHONY: check-stubs
stubs-check: ${DEPS_INSTALLED}
	@echo "${GREEN}Verifying dimension stubs are current...${RESET}"
	@UV_PROJECT_ENVIRONMENT=${UV_VENV} uv run --python ${PYTHON} \
		python scripts/generate_dimension_stubs.py --check
