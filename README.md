<div align="center">
  <img src="assets/logo.svg" width="300" alt="SLM Triage Logo" />
</div>

# SLM Triage

[![CI](https://github.com/sjyangkevin/slm-triage/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/sjyangkevin/slm-triage/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/sjyangkevin/slm-triage/graph/badge.svg)](https://codecov.io/gh/sjyangkevin/slm-triage)

A GitHub Action that runs a small LLM to triage incoming issues and PRs, helping maintainers identify potential [AI-generated slop](https://github.com/ossf/wg-vulnerability-disclosures/issues/178).

## The Problem

Open-source maintainers face a growing flood of low-quality, AI-generated issues and pull requests, commonly called **"AI-slop."** These submissions are polished on the surface but fall apart under review: they may hallucinate APIs, ignore contribution guidelines, and add no real value. The effect is a [DDoS on human attention](https://www.reddit.com/r/opensource/comments/1q3f89b/open_source_is_being_ddosed_by_ai_slop_and_github/). Projects like [curl](https://daniel.haxx.se/blog/2025/07/14/death-by-a-thousand-slops/), [Node.js](https://nodejs.org/en/blog/announcements/hackerone-signal-requirement), and others have already been forced to change their contribution policies in response.

## Why a Small Language Model?

Identifying AI-slop requires **semantic understanding**: does this submission actually follow the project's guidelines, or does it just *look* like it does? Large cloud-hosted LLMs can do this, but they introduce real problems for open-source triage:

| Concern | Cloud LLM | SLM (Local) |
|---|---|---|
| **Cost** | Per-token API fees on *every* issue/PR | Free, runs on the GitHub runner |
| **Privacy** | Sends PRs and guidelines to a third-party | Everything stays on the runner |
| **Context Size** | Massive context limits that remain mostly unused | The right size for a task that requires minimal context |
| **Infrastructure** | Requires API keys and billing setup | Zero configuration beyond the action |

**SLM Triage** runs a Small Language Model directly on the GitHub Actions runner using [Ollama](https://ollama.com). By default, it uses `qwen3.5:2b`, leveraging its native reasoning/thinking capabilities to run a reliable evaluation while staying well within the constraints of the standard free GitHub-hosted runner.

## Trade-offs

- **Runner time:** Local inference on CPU adds roughly 1–3 minutes per run. Model weights are cached between runs to avoid redundant downloads.
- **False positives:** SLMs can misinterpret nuance. The default behavior is to *label and comment* rather than close, keeping a human in the loop for final decisions.
- **Depth of reasoning:** SLMs excel at procedural checks (e.g. is the reproduction context present? is the PR title descriptive?) but are not suited for deep code-level architectural review.

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

## Inputs

| Input | Description | Default |
| --- | --- | --- |
| `github-token` | **Required.** GitHub token for API calls. | - |
| `ollama-model` | Ollama model for inference. | `qwen3.5:2b` |
| `ollama-think` | Enables reasoning tags for models that support it (e.g. `deepseek-r1`). | `true` |
| `actions`      | Comma-separated list of actions (`comment`,`label`,`close`). | `comment,label` |
| `review-label` | Label applied to submissions that need more info. | `needs-details` |

## How It Works

1. A new Issue or PR is opened in **your** repository.
2. The action installs Ollama and pulls a small LLM (~2 GB) on the runner. The model is cached between runs.
3. The LLM evaluates the submission's Title, Body, and associated state against a static rubric determining whether it contains actionable context.
4. If the submission is lacking (returning `Needs Details`), the action executes user-defined configuration hooks (like dropping a comment and applying a label).

## Local Testing

You can use the provided simulation script to test the triage logic locally against real, public GitHub issues or PRs without posting any automated replies:

```bash
# Basic test against an issue using the default model
uv run scripts/simulate_triage.py apache/airflow 55351

# Test using a specific model with reasoning/thinking enabled
uv run scripts/simulate_triage.py apache/airflow 51059 --model qwen3.5:2b --think
```

*Note: If you run into strict rate limits, you can export `GITHUB_TOKEN` locally to authenticate the read-only fetch.*

## Examples

**Example Issue Triage Output**:
<div align="center">
  <img src="assets/tests/actions_on_test_issue.png" width="600" alt="Example Triage Comment" />
</div>

**Default Configuration**:
```yaml
- uses: your-username/slm-triage@v1
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
```

**Aggressive Auto-Close Configuration**
```yaml
- uses: your-username/slm-triage@v1
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    ollama-model: "deepseek-r1:1.5b"
    ollama-think: "true"
    actions: "comment,label,close"
    review-label: "auto-spam"
```

## License

Apache License 2.0. See [LICENSE](LICENSE) for details.
