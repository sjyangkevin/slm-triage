<div align="center">
  <img src="assets/logo.svg" width="300" alt="SLM Triage Logo" />
</div>

# SLM Triage

[![CI](https://github.com/sjyangkevin/slm-triage/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/sjyangkevin/slm-triage/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/sjyangkevin/slm-triage/graph/badge.svg)](https://codecov.io/gh/sjyangkevin/slm-triage)

A GitHub Action that runs a small language model (SLM) locally on a GitHub runner to triage incoming issues and pull requests.

SLM Triage is designed for repositories that want a self-contained, automated first-pass review of new contributions. It focuses on a practical question: does this issue or pull request contain enough relevant, actionable context for maintainers to review efficiently?

## The Problem

Open-source maintainers can spend significant time sorting through issues and pull requests before they can get to the work that needs deeper review. Some contributions are thoughtful and actionable. Others may be incomplete, loosely connected to the repository, or missing the context needed for someone else to make progress.

That problem has become more visible as Generative AI tools make it easier to draft issues, bug reports, and code changes quickly. This is useful for contributors, but it also means maintainers can receive more contributions with uneven quality, unclear reproduction steps, or changes that are only weakly related to the stated problem.

This challenge is being discussed openly across the community, including in GitHub's community discussion on [low-quality contributions on GitHub](https://github.com/orgs/community/discussions/185387) and broader maintainer conversations such as the OSSF issue on [best current practices for handling AI-assisted low-quality submissions](https://github.com/ossf/wg-vulnerability-disclosures/issues/178).

## How This Relates to Generative AI

Generative AI is part of the context for this project in two ways:

- It can increase the volume of incoming contributions by making it easier to draft issues and pull requests quickly.
- It can also help maintainers by automating repetitive triage work.

SLM Triage takes the second approach. It uses a model to evaluate whether a contribution is ready for human review based on its content, context, and relevance. The goal is to reduce time spent on contributions that need more detail before a maintainer can act.

## What It Evaluates

SLM Triage runs a small language model directly on the GitHub Actions runner using [Ollama](https://ollama.com). When a new issue or pull request is opened, the action can inspect:

- The title
- The body content
- The author
- The pull request diff, if enabled

It then scores the contribution against a rubric oriented around actionable context and relevance. If the result is `Needs Details`, the action can comment, apply a label, and optionally close the issue or pull request.

## Why Use a Small Language Model?

This project is not based on the idea that small models are better than large models in general. In many cases, large hosted models are better at reasoning, following complex instructions, and working with broad repository context.

For issue and pull request triage, though, a small local model offers a different operational tradeoff. The advantage is less about raw intelligence and more about running reliably as repository automation.

| Aspect | Small local model in GitHub Actions | Large hosted model or coding agent |
| --- | --- | --- |
| Cost model | Uses runner time and storage cache, with no per-contribution token billing | Often depends on API billing, seats, premium requests, or usage allowances |
| Distribution | Can be packaged directly into a workflow and reused across repositories | Usually requires external service access, account setup, or organization-level approval |
| Automation fit | Runs directly on GitHub events as unattended workflow automation | Can automate triage too, but many tools are optimized around interactive maintainer workflows |
| Credentials | Can run with the repository's GitHub token plus local model execution | Commonly needs external credentials, billing, or service entitlements in addition to GitHub access |
| Control | Model execution happens on the runner that already executes the workflow | Repository content is sent to an external model provider |
| Scalability | Can process contributions whenever GitHub runners are available | Also scales well, but may be gated by quotas, rate limits, budgets, or seat availability |
| Quality ceiling | Lower reasoning ability and weaker repository understanding | Stronger reasoning, longer context, and often better coding performance |

For maintainers who want basic automated triage without adding external model infrastructure, this can be a practical option.

## Advantages

- Runs on a standard GitHub-hosted runner and can complete on CPU in around 3 to 5 minutes.
- Does not require external model API keys, billing setup, or per-request model usage fees.
- Works directly on GitHub events such as newly opened issues and pull requests.
- Can be distributed as a reusable GitHub Action without additional service infrastructure.
- Can take follow-up actions through the GitHub API, such as commenting, labeling, or closing a contribution.

## Current Limitations

- The model does not have deep project-specific knowledge, so triage is based on high-level repository context and the relevance of the contribution itself.
- Small models have limited reasoning capability compared with larger hosted models.
- Context windows are limited, so very large pull requests or long issue threads may be harder to evaluate well.
- Local CPU inference is slower than calling a hosted model API.
- False positives are possible, which is why the default behavior is to comment and label rather than close.

## When It Works Best

SLM Triage is a good fit when:

- You want to filter for issues and pull requests that need more detail before a maintainer spends time on them.
- Your repository receives enough inbound volume that first-pass triage is repetitive.
- You prefer a workflow that can run entirely inside GitHub Actions without depending on an external model service.
- You are comfortable keeping a human in the loop for final decisions.

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
        uses: sjyangkevin/slm-triage@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

## Inputs

| Input | Description | Default |
| --- | --- | --- |
| `github-token` | **Required.** GitHub token for API calls. |  |
| `ollama-model` | Ollama model for inference. | `qwen3.5:2b` |
| `ollama-think` | Enables reasoning tags for models that support it. | `false` |
| `actions` | Comma-separated list of actions (`comment`,`label`,`close`). | `comment,label` |
| `review-label` | Label applied to contributions that need more info. | `needs-details` |
| `include-pr-diff` | Include the pull request diff in the evaluation. | `true` |

## Workflow

1. A new Issue or PR is opened in your repository.
2. The action installs Ollama and pulls a small language model (2 to 3 GB) on the runner. The model weight is cached between runs.
3. The model evaluates the contribution's title, body, and optionally code changes against a rubric to determine whether it contains actionable and relevant context.
4. If the contribution needs more detail, the action can comment, apply a label, and optionally close it based on your configuration.

## Local Testing

You can use the provided simulation script to test the triage logic locally against real, public GitHub issues or PRs without posting any automated replies:

```bash
# Basic test against an issue using the default model
uv run scripts/simulate_triage.py <owner>/<repo> <issue-number>

# Test using a specific model with reasoning/thinking enabled
uv run scripts/simulate_triage.py <owner>/<repo> <issue-number> --model qwen3.5:2b --think
```

*Note: If you run into strict rate limits, you can export `GITHUB_TOKEN` locally to authenticate the read-only fetch.*

## Examples

An example of automated triage output:

<div align="center">
  <img src="assets/tests/actions_on_test_issue.png" width="600" alt="Example Triage Comment" />
</div>

## Configuration Examples

**Default configuration**

```yaml
- uses: sjyangkevin/slm-triage@v1
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
```

**Comment and label only**

```yaml
- uses: sjyangkevin/slm-triage@v1
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    actions: "comment,label"
    review-label: "needs-details"
```

**Optional auto-close configuration**

```yaml
- uses: sjyangkevin/slm-triage@v1
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    ollama-model: "deepseek-r1:1.5b"
    ollama-think: "true"
    actions: "comment,label,close"
    review-label: "needs-follow-up"
```

## License

Apache License 2.0. See [LICENSE](LICENSE) for details.
