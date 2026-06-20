.PHONY: help venv install test coverage lint typecheck security ci-local precommit-install clean build

env_name ?= venv
VENV_DETECT := $(shell \
	if [ -n "$$VIRTUAL_ENV" ]; then basename "$$VIRTUAL_ENV"; \
	elif [ -d "$(env_name)" ] && [ -f "$(env_name)/bin/activate" ]; then echo "$(env_name)"; \
	elif [ -d "venv" ] && [ -f "venv/bin/activate" ]; then echo "venv"; \
	else echo ""; fi)
PYTHON := $(if $(VENV_DETECT),./$(VENV_DETECT)/bin/python,python3.12)

help:
	@echo "axiom-aal Makefile"
	@echo "  make venv install test coverage lint typecheck security ci-local"

venv:
	$(PYTHON) -m venv $(env_name)
	./$(env_name)/bin/pip install -U pip
	./$(env_name)/bin/pip install -e ".[dev]"
	./$(env_name)/bin/pre-commit install || true

install:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest tests/ -v

coverage:
	$(PYTHON) -m pytest tests/ --cov=aal --cov-report=term --cov-report=xml --cov-fail-under=80

lint:
	ruff check . --config pyproject.toml
	ruff format --check . --config pyproject.toml

typecheck:
	mypy src/aal/ --config-file pyproject.toml

security:
	bandit -c pyproject.toml -r src/aal/ -ll
	pip-audit

ci-local:
	@set -e; VP=./$(VENV_DETECT)/bin; \
	if [ ! -x "$$VP/python" ]; then echo "Run: make venv"; exit 1; fi; \
	echo "== Ruff =="; $$VP/ruff check . --config pyproject.toml; $$VP/ruff format --check . --config pyproject.toml; \
	echo "== Mypy =="; $$VP/mypy src/aal/ --config-file pyproject.toml; \
	echo "== Pre-commit =="; $$VP/pre-commit run --all-files; \
	echo "== Pytest + coverage =="; $$VP/pytest tests/ --cov=aal --cov-report=xml --cov-report=term --cov-fail-under=80; \
	echo "== Security =="; $$VP/bandit -c pyproject.toml -r src/aal/ -ll; $$VP/pip-audit; \
	echo "ci-local: all checks passed."

precommit-install:
	pre-commit install

clean:
	rm -rf build dist *.egg-info .pytest_cache .coverage htmlcov coverage.xml .ruff_cache .mypy_cache

build: clean
	poetry build
