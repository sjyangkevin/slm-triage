# Contributing to SLM Triage

Thank you for your interest in contributing! This guide covers how to set up your development environment, run tests, and submit changes.

For issue and pull request guidelines used by the LLM triage process, see [`AGENTS.md`](AGENTS.md).

## Prerequisites

- Python 3.10 or later
- [uv](https://docs.astral.sh/uv/) (Python package manager)

## Development Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/sjyangkevin/slm-triage.git
   cd slm-triage
   ```

2. Install all dependencies (including dev tools):

   ```bash
   uv sync
   ```

3. Set up pre-commit hooks to enforce code style automatically:

   ```bash
   pre-commit install
   ```

## Running Tests

Run the full test suite:

```bash
uv run pytest
```

Run tests with coverage:

```bash
uv run pytest --cov=src
```

## Code Style

Code style is enforced by [Ruff](https://docs.astral.sh/ruff/) via pre-commit hooks. If you prefer to run checks manually:

```bash
# Lint
uv run ruff check src/ tests/

# Format
uv run ruff format src/ tests/
```

All code must pass both linting and formatting checks before merging.

## Submitting Changes

1. **Open an issue first.** Describe the bug or feature request. Wait for approval before starting work.
2. **Create a branch** from `main` for your changes.
3. **Write or update tests** for any code changes.
4. **Ensure CI passes.** Run `uv run pytest` and `uv run ruff check src/ tests/` locally before pushing.
5. **Open a pull request** that references the approved issue. Include a clear title and a description of what changed and why.

See [`AGENTS.md`](AGENTS.md) for an example PR quality guidelines.

## Extending the Action

To add a new triage action (e.g., a new response when a submission scores below the threshold):

1. **Add the action logic** in `src/main.py` inside the `_apply_actions` method, following the existing pattern for `comment`, `label`, and `close`.
2. **Add a corresponding API method** in `src/github_client.py` if the action requires a new GitHub API call.
3. **Update `action.yml`** to document the new action in the `actions` input description.
4. **Add tests** in `tests/test_main.py` covering the new behavior.
