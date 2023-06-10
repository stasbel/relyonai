CFLAGS := relyonai tests

.PHONY: format lint test upload

format:
	python -m black $(CFLAGS)
	python -m isort $(CFLAGS)

lint:
	python -m flake8 $(CFLAGS)
	python -m mypy $(CFLAGS)

test:
	python -m pytest

upload:
	python -m build
	twine upload dist/*
