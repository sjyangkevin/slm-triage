# SLM Triage

A GitHub Action that automatically triages incoming Issues and Pull Requests by running a small local LLM to score submissions against your project's contribution guidelines.

## Why?

Open-source maintainers are increasingly overwhelmed by low-quality, AI-generated issues and PRs that look polished on the surface but don't follow project guidelines. SLM Triage fights AI with AI — running a Small Language Model **locally on the GitHub runner** (no API keys, no costs) to evaluate each submission against your project's own guidelines.

## Quick Start

Add this to `.github/workflows/slm-triage.yml` in your repository:

```yaml
name: SLM Triage

on:
  issues:
    types: [opened]
  pull_request:
    types: [opened]

jobs:
  triage:
    runs-on: ubuntu-24.04
    permissions:
      issues: write
      pull-requests: write
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Run SLM Triage
        uses: your-username/slm-triage@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

Then create an `AGENTS.md` file **in your repository** with your contribution guidelines. The action will automatically fetch and use it as the scoring criteria.

## Inputs

| Input | Description | Default |
| --- | --- | --- |
| `github-token` | **Required.** GitHub token for API calls. | — |
| `ollama-model` | Ollama model for inference. | `phi3` |
| `guidelines-file` | Path to the guidelines file **in your repository**. | `AGENTS.md` |
| `test-file-pattern` | Glob to detect test files (language-agnostic). | `test_*` |
| `score-threshold` | Score at or below which the action acts. | `2` |
| `low-quality-label` | Label applied to low-scoring submissions. | `needs-review/low-quality` |

## How It Works

1. A new Issue or PR is opened in **your** repository.
2. The action installs Ollama and pulls a small LLM (~2 GB) on the runner. The model is cached between runs.
3. Your guidelines file (e.g. `AGENTS.md`) is fetched from **your repository** via the GitHub REST API.
4. The LLM scores the submission's title and description against the guidelines (1–5 scale).
5. If the score is at or below the threshold, the action posts a comment and applies a label.

## Examples

**Python project** (pytest conventions):
```yaml
- uses: your-username/slm-triage@v1
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    test-file-pattern: "test_*"
```

**JavaScript project** (Jest conventions):
```yaml
- uses: your-username/slm-triage@v1
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    test-file-pattern: "*.test.js"
    guidelines-file: "CONTRIBUTING.md"
```

**Go project:**
```yaml
- uses: your-username/slm-triage@v1
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    test-file-pattern: "*_test.go"
```

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.
