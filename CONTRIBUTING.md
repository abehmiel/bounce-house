# Contributing to Bounce House

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

```bash
git clone https://github.com/abehmiel/bounce-house.git
cd bounce-house
uv sync --extra dev
uv run pre-commit install
```

## Running Tests

```bash
uv run pytest              # Run all tests
uv run pytest -q           # Quiet output
uv run pytest tests/test_loudness.py  # Single file
```

## Code Quality

All of these must pass before merging:

```bash
uv run ruff check src/ tests/   # Lint
uv run ruff format src/ tests/  # Format (or --check to verify)
uv run mypy src/                # Type checking
```

Pre-commit hooks run ruff and mypy automatically on each commit.

## Making Changes

1. **Fork and branch** — create a feature branch from `main`
2. **Write tests first** — we follow TDD. Add failing tests, then implement
3. **Keep commits focused** — one logical change per commit, using [conventional commit](https://www.conventionalcommits.org/) messages (e.g., `feat:`, `fix:`, `test:`, `docs:`)
4. **Run the full suite** — `uv run pytest && uv run ruff check src/ tests/ && uv run mypy src/`
5. **Open a PR** — describe what you changed and why

## Architecture Notes

- **Analyzers are stateless** — each takes `AudioData`, returns `AnalysisResult` with a metrics dict
- **Rules are data, not code** — add threshold rules in `profiles.py`, not logic in analyzers
- **Every metric needs docs** — add a `MetricDoc` entry in `metric_docs.py` for any new metric
- **Diagnostics combine metrics** — multi-metric patterns live in `profiles.py` as data

## What to Work On

- Check [open issues](https://github.com/abehmiel/bounce-house/issues) for bugs and feature requests
- New analyzer modules, diagnostic patterns, and genre-specific profiles are all welcome
- Documentation improvements and typo fixes are always appreciated

## Questions?

Open an issue or start a discussion. We're happy to help you get oriented.
