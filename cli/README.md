# fairguard-cli

> Command-line interface for the [FairGuard](https://github.com/fairguard/fairguard) AI Fairness Firewall.

## Installation

```bash
pip install fairguard-cli
```

## Quick Start

### 1. Initialize your project

```bash
fairguard init
```

You will be prompted for your API URL, Project ID, and API Key. The API URL and
Project ID are saved to `.fairguard.yml` in the current directory. **The API key
is never written to disk** — export it as an environment variable instead:

```bash
export FAIRGUARD_API_KEY=fgk_...
```

### 2. Run a fairness audit

```bash
fairguard test \
  --data predictions.csv \
  --target label \
  --prediction score \
  --sensitive gender,age_group
```

The command exits **0** on a passing audit and **1** on a failing audit or error,
making it easy to use as a CI gate.

### 3. Generate a report

```bash
fairguard report --output report.md
```

### 4. Check runtime status

```bash
fairguard status
```

## Configuration

Config is resolved in the following priority order (highest wins):

| Source | Example |
| ------ | ------- |
| Environment variables | `FAIRGUARD_API_URL`, `FAIRGUARD_API_KEY`, `FAIRGUARD_PROJECT_ID` |
| `.fairguard.yml` | nearest file walking up from cwd |
| Defaults | `api_url: https://api.fairguard.io` |

### `.fairguard.yml` format

```yaml
api_url: https://api.fairguard.io
project_id: proj_abc123
```

## Commands

### `fairguard init`

Interactive wizard that creates `.fairguard.yml`.

```
Options:
  --api-url TEXT       FairGuard API URL  [default: https://api.fairguard.io]
  --project-id TEXT    Project ID  [required]
  --api-key TEXT       API Key  [required]
```

### `fairguard test`

Upload a CSV and run an offline fairness audit.

```
Options:
  --data PATH             Path to CSV file  [required]
  --project-id TEXT       Project ID
  --target TEXT           Ground-truth column name
  --prediction TEXT       Prediction/score column name
  --sensitive TEXT        Comma-separated sensitive attribute columns
  --endpoint-id TEXT      Scope audit to a specific endpoint
```

### `fairguard report`

Fetch the latest (or a specific) audit result and write a Markdown report.

```
Options:
  --project-id TEXT    Project ID
  --audit-id TEXT      Specific audit ID  (defaults to latest)
  --output PATH        Output file  [default: fairguard-report.md]
```

### `fairguard status`

Display runtime monitoring status for a project.

```
Options:
  --project-id TEXT    Project ID
  --endpoint-id TEXT   Scope to a specific endpoint
```

## CI / CD Integration

See [docs/ci-examples.md](../docs/ci-examples.md) for GitHub Actions and
GitLab CI examples.

## License

MIT
