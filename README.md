# Evals Primer

A practical, evolving book about evaluating AI systems—from test-set design to production monitoring.

## Write locally

All book chapters live in [`docs/`](docs). Edit the Markdown files, then preview the book:

```bash
uv sync
uv run mkdocs serve
```

Open <http://127.0.0.1:8000> while the preview server is running. Changes appear automatically.

## Check the book

```bash
make test
make build
```

The strict build catches broken navigation and configuration problems. Every push to `main` publishes the latest book through GitHub Pages.

## Add a chapter

1. Create a Markdown file in `docs/`.
2. Add it to `nav` in [`mkdocs.yml`](mkdocs.yml).
3. Run `make build` before pushing.

