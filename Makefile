VENV        := .venv
PYTHON      := $(VENV)/bin/python
PIP         := $(VENV)/bin/pip
FLAKE8      := $(VENV)/bin/flake8
MYPY        := $(VENV)/bin/mypy
MAIN        := pac-man.py
CONFIG      := config.json
WHEEL       := mazegenerator-00001-py3-none-any.whl

MYPY_FLAGS  := --warn-return-any --warn-unused-ignores --ignore-missing-imports \
               --disallow-untyped-defs --check-untyped-defs

.DEFAULT_GOAL := run

$(VENV):
	python3 -m venv $(VENV)

install: $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install $(WHEEL)

run:
	$(PYTHON) $(MAIN) $(CONFIG)

debug:
	$(PYTHON) -m pdb $(MAIN) $(CONFIG)

lint:
	$(FLAKE8) .
	$(MYPY) . $(MYPY_FLAGS)

lint-strict:
	$(FLAKE8) .
	$(MYPY) . --strict

test:
	$(PYTHON) -m pytest tests/ -v

package: $(VENV)
	$(PIP) install pyinstaller
	$(VENV)/bin/pyinstaller pacman.spec --noconfirm

deploy:
	ITCH_GAME=$${ITCH_GAME:-pacman} ./scripts/deploy_itch.sh

clean:
	find . -type d -name '__pycache__' -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache .ruff_cache
	rm -rf build dist *.egg-info
	find . -type f -name '*.py[cod]' -delete

.PHONY: install run debug lint lint-strict test package deploy clean
