PYTHON ?= python
PIP ?= $(PYTHON) -m pip

.PHONY: install install-dev test run

install:
	$(PIP) install -r requirements.txt

install-dev:
	$(PIP) install -r requirements-dev.txt

test:
	$(PYTHON) -m unittest discover

run:
	$(PYTHON) -m streamlit run app.py
