# CI/CD Integration Examples

This page shows how to integrate FairGuard fairness audits into your CI/CD pipelines.

---

## GitHub Actions

### Basic Fairness Gate

Add a fairness audit job that **blocks merges** when fairness thresholds are violated.

```yaml
name: FairGuard Audit
on:
  push:
    branches: [main]
  pull_request:

jobs:
  fairness-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install FairGuard CLI
        run: pip install fairguard-cli

      - name: Run Fairness Audit
        env:
          FAIRGUARD_API_URL: ${{ secrets.FAIRGUARD_API_URL }}
          FAIRGUARD_API_KEY: ${{ secrets.FAIRGUARD_API_KEY }}
          FAIRGUARD_PROJECT_ID: ${{ secrets.FAIRGUARD_PROJECT_ID }}
        run: |
          fairguard test \
            --data predictions.csv \
            --target label \
            --prediction score \
            --sensitive gender,age_group
```

### With Report Artifact

Save a Markdown report as a build artifact for every run.

```yaml
name: FairGuard Audit with Report
on:
  push:
    branches: [main]
  pull_request:

jobs:
  fairness-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install FairGuard CLI
        run: pip install fairguard-cli

      - name: Run Fairness Audit
        id: audit
        env:
          FAIRGUARD_API_URL: ${{ secrets.FAIRGUARD_API_URL }}
          FAIRGUARD_API_KEY: ${{ secrets.FAIRGUARD_API_KEY }}
          FAIRGUARD_PROJECT_ID: ${{ secrets.FAIRGUARD_PROJECT_ID }}
        run: |
          fairguard test \
            --data predictions.csv \
            --target label \
            --prediction score \
            --sensitive gender,age_group

      - name: Generate Report
        if: always()
        env:
          FAIRGUARD_API_URL: ${{ secrets.FAIRGUARD_API_URL }}
          FAIRGUARD_API_KEY: ${{ secrets.FAIRGUARD_API_KEY }}
          FAIRGUARD_PROJECT_ID: ${{ secrets.FAIRGUARD_PROJECT_ID }}
        run: |
          fairguard report --output fairguard-report.md

      - name: Upload Report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: fairguard-report
          path: fairguard-report.md
          retention-days: 90
```

### Matrix Strategy (Multiple Models)

Run audits across multiple model variants in parallel.

```yaml
name: FairGuard Multi-Model Audit
on:
  push:
    branches: [main]

jobs:
  fairness-audit:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        model: [baseline, v2, v3]
      fail-fast: false
    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install FairGuard CLI
        run: pip install fairguard-cli

      - name: Run Fairness Audit (${{ matrix.model }})
        env:
          FAIRGUARD_API_URL: ${{ secrets.FAIRGUARD_API_URL }}
          FAIRGUARD_API_KEY: ${{ secrets.FAIRGUARD_API_KEY }}
          FAIRGUARD_PROJECT_ID: ${{ secrets.FAIRGUARD_PROJECT_ID }}
        run: |
          fairguard test \
            --data predictions_${{ matrix.model }}.csv \
            --endpoint-id ${{ matrix.model }} \
            --target label \
            --prediction score \
            --sensitive gender,age_group
```

---

## GitLab CI

### Basic Fairness Gate

```yaml
stages:
  - test
  - fairness

fairness-audit:
  stage: fairness
  image: python:3.11-slim
  before_script:
    - pip install fairguard-cli
  script:
    - fairguard test
        --data predictions.csv
        --target label
        --prediction score
        --sensitive gender,age_group
  variables:
    FAIRGUARD_API_URL: $FAIRGUARD_API_URL
    FAIRGUARD_API_KEY: $FAIRGUARD_API_KEY
    FAIRGUARD_PROJECT_ID: $FAIRGUARD_PROJECT_ID
  only:
    - main
    - merge_requests
```

### With Report Artifact

```yaml
stages:
  - test
  - fairness

fairness-audit:
  stage: fairness
  image: python:3.11-slim
  before_script:
    - pip install fairguard-cli
  script:
    - |
      fairguard test \
        --data predictions.csv \
        --target label \
        --prediction score \
        --sensitive gender,age_group || AUDIT_FAILED=1
    - fairguard report --output fairguard-report.md
    - exit ${AUDIT_FAILED:-0}
  artifacts:
    when: always
    paths:
      - fairguard-report.md
    expire_in: 90 days
  variables:
    FAIRGUARD_API_URL: $FAIRGUARD_API_URL
    FAIRGUARD_API_KEY: $FAIRGUARD_API_KEY
    FAIRGUARD_PROJECT_ID: $FAIRGUARD_PROJECT_ID
  only:
    - main
    - merge_requests
```

---

## CircleCI

```yaml
version: 2.1

jobs:
  fairness-audit:
    docker:
      - image: cimg/python:3.11
    steps:
      - checkout
      - run:
          name: Install FairGuard CLI
          command: pip install fairguard-cli
      - run:
          name: Run Fairness Audit
          command: |
            fairguard test \
              --data predictions.csv \
              --target label \
              --prediction score \
              --sensitive gender,age_group
      - run:
          name: Generate Report
          when: always
          command: fairguard report --output fairguard-report.md
      - store_artifacts:
          path: fairguard-report.md

workflows:
  build-and-audit:
    jobs:
      - fairness-audit
```

---

## Setting Secrets

In all examples, configure the following secrets in your CI provider:

| Secret | Description |
| ------ | ----------- |
| `FAIRGUARD_API_URL` | Base URL of your FairGuard instance |
| `FAIRGUARD_API_KEY` | API key with audit permissions |
| `FAIRGUARD_PROJECT_ID` | The project to audit against |

### GitHub: Settings → Secrets and variables → Actions
### GitLab: Settings → CI/CD → Variables
### CircleCI: Project Settings → Environment Variables
