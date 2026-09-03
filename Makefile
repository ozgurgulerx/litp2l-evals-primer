.PHONY: build serve test

build:
	uv run mkdocs build --strict

serve:
	uv run mkdocs serve

test:
	uv run python -m unittest discover -s tests -v

