<div align="center">
  <img src="assets/logo.svg" height="60" alt="SLM Triage Logo" />
</div>

# SLM Triage

[![CI](https://github.com/sjyangkevin/slm-triage/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/sjyangkevin/slm-triage/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/sjyangkevin/slm-triage/graph/badge.svg)](https://codecov.io/gh/sjyangkevin/slm-triage)

A GitHub Action that triages incoming Issues and Pull Requests by running a small local LLM to evaluate submissions against your project's `AGENTS.md`, to help identify [AI-generated slop](https://github.com/ossf/wg-vulnerability-disclosures/issues/178).

## The Problem

Open-source maintainers face a growing flood of low-quality, AI-generated issues and pull requests, commonly called **"AI-slop."** These submissions are polished on the surface but fall apart under review: they may hallucinate APIs, ignore contribution guidelines, and add no real value. The effect is a [DDoS on human attention](https://www.reddit.com/r/opensource/comments/1q3f89b/open_source_is_being_ddosed_by_ai_slop_and_github/). Projects like [curl](https://daniel.haxx.se/blog/2025/07/14/death-by-a-thousand-slops/), [Node.js](https://nodejs.org/en/blog/announcements/hackerone-signal-requirement), and others have already been forced to change their contribution policies in response.

## Why a Small Language Model?

Identifying AI-slop requires **semantic understanding**: does this submission actually follow the project's guidelines, or does it just *look* like it does? Large cloud-hosted LLMs can do this, but they introduce real problems for open-source triage:

| Concern | Cloud LLM | SLM (Local) |
|---|---|---|
| **Cost** | Per-token API fees on *every* issue/PR | Free, runs on the GitHub runner |
| **Privacy** | Sends PRs and guidelines to a third-party | Everything stays on the runner |
| **Capability** | Overkill for checklist-style evaluation | Right-sized for scoring and classification |
| **Infrastructure** | Requires API keys and billing setup | Zero configuration beyond the action |

**SLM Triage** uses [Ollama](https://ollama.com) to run a Small Language Model directly on the GitHub Actions runner. The default model, [Phi-3 mini](https://ollama.com/library/phi3) (3.8B parameters, ~2.3GB download), fits comfortably on standard GitHub-hosted runners with a 2-core CPU and 8GB RAM, which are [free for public repositories](https://docs.github.com/en/actions/using-github-hosted-runners/using-github-hosted-runners/about-github-hosted-runners#standard-github-hosted-runners-for-public-repositories). A typical triage prompt consists of a guidelines file and an issue or PR body, which is well within the model's context window. This makes triage a task where a small, efficient model can be good enough.

## Trade-offs

- **Runner time:** Local inference on CPU adds roughly 1–3 minutes per run. Model weights are cached between runs to avoid redundant downloads.
- **False positives:** SLMs can misinterpret nuance. The default behavior is to *label and comment* rather than close, keeping a human in the loop for final decisions.
- **Depth of reasoning:** SLMs excel at procedural checks (test files included? issue template filled out?) but are not suited for deep architectural review.

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
| `ollama-model` | Ollama model for inference. | `phi3` |
| `guidelines-file` | Path to the guidelines file **in your repository**. | `AGENTS.md` |
| `test-file-pattern` | Glob to detect test files (language-agnostic). | `test_*` |
| `score-threshold` | Score at or below which the action acts. | `2` |
| `actions`         | Comma-separated list of actions (`comment`,`label`,`close`). | `comment,label` |
| `review-label` | Label applied to submissions that need more info. | `needs-details` |

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

Apache License 2.0. See [LICENSE](LICENSE) for details.
