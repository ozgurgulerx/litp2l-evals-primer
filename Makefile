.PHONY: build serve test

build:
	uv run mkdocs build --strict

serve:
	uv run mkdocs serve --dev-addr localhost:8797

test:
	uv run python -m unittest discover -s tests -v
