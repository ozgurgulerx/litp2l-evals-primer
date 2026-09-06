# Evals Primer

A practical, evolving book about evaluating AI systems—from test-set design to production monitoring.

## Write locally

All book chapters live in [`docs/`](docs). Edit the Markdown files, then preview the book:

```bash
uv sync
make serve
```

Open <http://localhost:8797/litp2l-evals-primer/> while the preview server is running. Changes appear automatically. The `localhost` hostname is intentional: Safari can reject an explicit `127.0.0.1` HTTP URL when HTTPS-Only mode is enabled.

## Check the book

```bash
make test
make build
```

`make test` includes the optional OpenAI SDK for offline transport-contract tests and the optional OpenTelemetry SDK/HTTP exporter for local telemetry tests. Provider tests use an in-memory HTTP transport and synthetic credentials. Telemetry tests use loopback-only HTTP, not a hosted collector. They do not make paid model calls or establish model quality. For coverage, install `uv sync --frozen --group dev --extra openai --extra telemetry` and run `uv run --extra openai --extra telemetry coverage run --branch --source=cx_eval_lab -m unittest discover -s tests`, then `uv run --extra openai --extra telemetry coverage report --fail-under=80`.

The strict build catches broken navigation and configuration problems. Every push to `main` publishes the latest book through GitHub Pages.

## Add a chapter

1. Create a Markdown file in `docs/`.
2. Add it to `nav` in [`mkdocs.yml`](mkdocs.yml).
3. Run `make build` before pushing.
