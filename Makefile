.PHONY: build serve test

build:
	uv run python -m mkdocs build --strict

serve:
	uv run python -m mkdocs serve --dev-addr localhost:8797

test:
	uv run --extra openai --extra telemetry python -m unittest discover -s tests -v
