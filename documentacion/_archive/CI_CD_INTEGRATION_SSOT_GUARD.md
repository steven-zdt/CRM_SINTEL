# CI/CD Integration: SSoT Architecture Guard

**Purpose:** Instructions for integrating the SSoT Server Guard into CI/CD pipelines  
**Target:** GitHub Actions, GitLab CI, Jenkins, etc.

---

## 🔗 GitHub Actions Integration

### Option 1: Dedicated Architecture Check Job

Add to `.github/workflows/tests.yml`:

```yaml
name: Tests & Quality Checks

on:
  push:
    branches: [ main, develop ]
    paths:
      - 'apps/tenant/**'
      - 'apps/config/**'
      - '.github/workflows/tests.yml'
  pull_request:
    branches: [ main, develop ]

jobs:
  architecture-ssot-check:
    name: Architecture SSoT Guard
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: sintel_test
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: 🛡️ Run SSoT Architecture Guard
        env:
          DEBUG: 'False'
          DJANGO_SETTINGS_MODULE: config.settings
          DATABASE_URL: postgres://postgres:postgres@localhost:5432/sintel_test
        run: |
          python manage.py migrate
          python -m pytest apps/tenant/core/tests/test_architecture_ssot.py \
            -v --tb=short --strict-markers
      
      - name: 📊 Report Architecture Status
        if: always()
        run: |
          echo "## Architecture Guard Status" >> $GITHUB_STEP_SUMMARY
          grep -E "PASSED|FAILED|SKIPPED" .pytest_cache/v/log.txt >> $GITHUB_STEP_SUMMARY || true
```

### Option 2: Integrated into Existing Test Job

```yaml
  python-tests:
    name: Python Tests
    runs-on: ubuntu-latest
    
    steps:
      # ... existing setup steps ...
      
      - name: Run all tests (including Architecture Guard)
        run: |
          pytest \
            apps/tenant/core/tests/test_architecture_ssot.py \
            tests/ \
            -v --cov=apps --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          flags: architecture-ssot
```

---

## 🐳 Docker Integration

### Dockerfile Test Stage

```dockerfile
# Stage: Quality Assurance
FROM python:3.12.13 AS qa

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run SSoT Architecture Guard
RUN python manage.py migrate
RUN python -m pytest \
    apps/tenant/core/tests/test_architecture_ssot.py \
    -v --tb=short \
    || { echo "ARCHITECTURE GUARD FAILED"; exit 1; }

LABEL test.architecture="ssot-compliant"
```

### Docker Compose with Test Service

```yaml
services:
  web:
    build: .
    environment:
      DATABASE_URL: postgresql://postgres:postgres@db:5432/sintel
  
  tests:
    build:
      context: .
      target: qa
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://postgres:postgres@db:5432/sintel_test
    command: >
      sh -c "
        python manage.py migrate --database=test &&
        python -m pytest apps/tenant/core/tests/test_architecture_ssot.py -v
      "
```

---

## 🔄 GitLab CI Integration

### `.gitlab-ci.yml`

```yaml
stages:
  - test
  - build
  - deploy

architecture:ssot:
  stage: test
  image: python:3.12.13
  services:
    - postgres:16
  variables:
    POSTGRES_DB: sintel_test
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: postgres
    DJANGO_SETTINGS_MODULE: config.settings
  before_script:
    - pip install -r requirements.txt
    - python manage.py migrate
  script:
    - pytest apps/tenant/core/tests/test_architecture_ssot.py -v --tb=short
  artifacts:
    reports:
      junit: report.xml
    expire_in: 1 week
  allow_failure: false  # ← Architecture violations BLOCK the pipeline
```

---

## 🏗️ Jenkins Integration

### Jenkinsfile (Declarative)

```groovy
pipeline {
    agent any
    
    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
    }
    
    stages {
        stage('Setup') {
            steps {
                sh '''
                    python -m venv venv
                    . venv/bin/activate
                    pip install -r requirements.txt
                '''
            }
        }
        
        stage('Migrations') {
            steps {
                sh '''
                    . venv/bin/activate
                    python manage.py migrate
                '''
            }
        }
        
        stage('🛡️ Architecture Guard') {
            steps {
                sh '''
                    . venv/bin/activate
                    python -m pytest \
                        apps/tenant/core/tests/test_architecture_ssot.py \
                        -v \
                        --tb=short \
                        --junit-xml=test-results.xml
                '''
            }
        }
    }
    
    post {
        always {
            junit 'test-results.xml'
            archiveArtifacts artifacts: 'test-results.xml'
        }
        failure {
            emailext(
                subject: "Architecture SSoT Guard FAILED - ${env.BUILD_NUMBER}",
                body: "Commit introduced models without empresa_id FK.\n\nCheck: ${env.BUILD_URL}",
                to: '${DEFAULT_RECIPIENTS}'
            )
        }
    }
}
```

---

## 🔐 Pre-Commit Hook (Local Development)

### `.git/hooks/pre-commit`

```bash
#!/bin/bash

# Pre-commit hook: Architecture SSoT Guard

set -e

echo "[PRE-COMMIT] Running Architecture SSoT Guard..."

# Run Architecture test
python -m pytest \
    apps/tenant/core/tests/test_architecture_ssot.py::TestArchitectureSSoTIntegrity::test_all_tenant_models_have_empresa_fk \
    -xvs --tb=short

if [ $? -ne 0 ]; then
    echo ""
    echo "⚠️  ARCHITECTURE VIOLATION DETECTED!"
    echo "Your commit introduces models without empresa_id FK."
    echo "Run: pytest apps/tenant/core/tests/test_architecture_ssot.py -xvs"
    echo ""
    exit 1
fi

echo "✅ Architecture Guard passed"
exit 0
```

**Install:**
```bash
chmod +x .git/hooks/pre-commit
```

---

## 📋 Makefile Tasks

Add to `Makefile`:

```makefile
.PHONY: test-architecture test-all guard-check

# Check architecture SSoT compliance
test-architecture:
	@echo "🛡️  Running Architecture SSoT Guard..."
	docker exec crm_sintel-web-1 python -m pytest \
		apps/tenant/core/tests/test_architecture_ssot.py \
		-v --tb=short

# Test architecture + all tests
test-all: test-architecture
	@echo "🧪 Running full test suite..."
	docker exec crm_sintel-web-1 python -m pytest tests/ -v

# Quick guard check (local)
guard-check:
	@echo "⚡ Quick Architecture Guard check..."
	python -m pytest \
		apps/tenant/core/tests/test_architecture_ssot.py \
		-x --tb=line -q
```

**Usage:**
```bash
make test-architecture      # Run guard tests in Docker
make guard-check            # Quick local check
make test-all               # Guard + full suite
```

---

## 🎯 CI/CD Workflow Best Practices

### Block on Failure

**CRITICAL:** Set these checks to **BLOCK** pull requests:

| Platform | Setting |
|----------|---------|
| GitHub | Add to branch protection rules |
| GitLab | Add as required job (allow_failure: false) |
| Jenkins | Set "fail build on test failure" |

### Notification Strategy

```yaml
notifications:
  slack:
    on_failure: "#architecture-alerts"
    message: |
      🚨 @devs Architecture Guard FAILED
      PR: ${{ github.event.pull_request.html_url }}
      See: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
```

### Performance Optimization

**Cache dependencies:**
```yaml
cache:
  key: python-${{ hashFiles('requirements.txt') }}
  paths:
    - .venv/
    - .pytest_cache/
```

**Parallel test execution:**
```bash
pytest apps/tenant/core/tests/test_architecture_ssot.py \
  -n auto \
  --dist loadscope
```

---

## 🚨 Troubleshooting

### Test Fails in CI But Passes Locally

**Causes:**
1. Different Python versions
2. Different database states
3. Missing migration in CI

**Fix:**
```bash
# Ensure CI runs migrations
python manage.py migrate --database=test

# Force fresh test database
pytest --tb=short --create-db
```

### Timeout in Docker

**Increase timeout:**
```bash
pytest --timeout=30 apps/tenant/core/tests/test_architecture_ssot.py
```

### False Positives (Model Added After Scan)

**Solution:** Run test AFTER model discovery:
```bash
# Bad: Finds models before migration
python -m pytest test_file.py

# Good: Migration first, then test
python manage.py migrate
python -m pytest test_file.py
```

---

## 📊 Rollout Schedule

| Phase | Timeline | Action |
|-------|----------|--------|
| Phase 1 | Week 1 | Enable in develop branch only (warning mode) |
| Phase 2 | Week 2 | Enable in main branch + require pass |
| Phase 3 | Week 3 | Add to pre-commit hook for all devs |
| Phase 4 | Week 4 | Integrate into deployment gate |

---

## 🔍 Monitoring & Alerts

### Slack Integration

```yaml
# .github/workflows/tests.yml
- name: Notify Architecture Status
  if: always()
  uses: slackapi/slack-github-action@v1.25
  with:
    webhook-url: ${{ secrets.SLACK_WEBHOOK }}
    payload: |
      {
        "text": "Architecture SSoT Guard: ${{ job.status }}",
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "🛡️ *Architecture Guard*\n${{ job.status == 'success' ? '✅ PASS' : '❌ FAIL' }}"
            }
          }
        ]
      }
```

### Email Report

```bash
# After test completion
if [ $? -ne 0 ]; then
  echo "Architecture violation in PR #$PULL_REQUEST" | \
    mail -s "SSoT Guard Failed" architecture-team@company.com
fi
```

---

## ✅ Verification Checklist

- [ ] Test file deployed: `apps/tenant/core/tests/test_architecture_ssot.py`
- [ ] Fixtures available: `conftest.py`
- [ ] CI/CD config updated (.github/workflows, .gitlab-ci.yml, Jenkinsfile)
- [ ] Branch protection rules configured
- [ ] Notifications setup (Slack, email)
- [ ] Pre-commit hook installed
- [ ] Team notified
- [ ] Test executed successfully in CI/CD environment
- [ ] Failure scenario tested (create model without empresa FK, verify blocking)
- [ ] Documentation accessible to team

---

**Status:** Ready for CI/CD Integration  
**Responsibility:** DevOps / Architecture Team  
**Escalation:** dev-lead@team.com
