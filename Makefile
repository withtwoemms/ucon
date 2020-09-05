SYSTEM_PYTHON = $(shell which python3.8)
PROJECT_NAME = $(shell basename $(CURDIR))
VENV = $(PROJECT_NAME)-venv
VENV_PYTHON = $(VENV)/bin/python
TESTDIR = tests


.PHONY: all
all: venv install clean

.PHONY: clean
clean: clean-install clean-venv clean-pyc

.PHONY: clean-install ## removes all install artifacts
clean-install:
	@rm -rf .eggs
	@rm -rf *.egg-info
	@rm -rf build
	@rm -rf dist

.PHONY: clean-pyc ## removes python bytecode
clean-pyc:
	@find . -name '*.pyc' -exec rm -f {} +
	@find . -name '*.pyo' -exec rm -f {} +
	@find . -name '*~' -exec rm -f {} +
	@find . -name '__pycache__' -exec rm -fr {} +

.PHONY: clean-venv ## removes the virtualenv directory
clean-venv:
	@rm -rf $(VENV)

.PHONY: commands ## lists all commands available
commands:
	@echo
	@tput bold setaf 2; echo $(shell basename $(CURDIR)); echo
	@$(MAKE) -pRrq -f $(lastword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/^# File/,/^# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | egrep -v -e '^[^[:alnum:]]' -e '^$@$$' | sed 's/^/  ->  /'
	@tput sgr0
	@echo

.PHONY: git-tag
git-tag:
	@echo $(shell git describe --tags)

.PHONY: install ## installs dependencies in a virtualenv
install: $(VENV) $(VENV_PYTHON)
	@$(VENV_PYTHON) -m pip install -r requirements.txt

.PHONY: system-install ## installs dependencies via SYSTEM_PYTHON
system-install:
	@pip install -r requirements.txt

.PHONY: test ## runs specific TestCase in TESTDIR
test: $(VENV_PYTHON)
ifeq ($(TESTCASE),)
	$(error TESTCASE not specified)
endif
	@$(VENV_PYTHON) -m unittest $(TESTDIR)$(if $(TESTCASE),.$(TESTCASE),)

.PHONY: tests ## runs all tests in TESTDIR
tests: $(VENV_PYTHON)
	@$(VENV_PYTHON) -m unittest discover $(TESTDIR)

.PHONY: tree ## outputs a file system diagram
tree:
	@tree -C $(CURDIR) -I '$(VENV)|__pycache__|*.egg-info|build|dist'

.PHONY: venv ## generates a virtualenv in the likeness of SYSTEM_PYTHON
venv:
	@if [ ! -d $(VENV) ]; then \
		$(SYSTEM_PYTHON) -m pip install virtualenv; \
		$(SYSTEM_PYTHON) -m virtualenv $(VENV) >/dev/null; \
	fi
