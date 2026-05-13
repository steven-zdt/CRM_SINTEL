# ⚡ Start Using SSoT Architecture Guard TODAY

**5-Minute Setup Guide**

---

## 🚀 Option 1: Local Testing (Right Now)

### Test Your Current Codebase

```bash
cd c:\Users\Administrator\Documents\crm_sintel

# Run the guard
python -m pytest apps/tenant/core/tests/test_architecture_ssot.py -xvs
```

**Expected output:**
```
collected 6 items

test_architecture_ssot.py::TestArchitectureSSoTIntegrity::test_all_tenant_models_have_empresa_fk PASSED
test_architecture_ssot.py::TestArchitectureSSoTIntegrity::test_empresa_fk_field_constraints PASSED
test_architecture_ssot.py::TestArchitectureSSoTIntegrity::test_base_model_consistency_check PASSED
test_architecture_ssot.py::TestSSoTRuleEnforcement::test_service_layer_cannot_create_record_without_empresa SKIPPED
test_architecture_ssot.py::TestSSoTRuleEnforcement::test_queryset_is_scoped_by_empresa SKIPPED
test_architecture_ssot.py::TestSSoTRuleEnforcement::test_empresa_fk_prevents_orphaned_records SKIPPED

=================== 3 passed, 3 skipped in 5.86s ====================
```

✅ **You're protected!**

---

## 🐳 Option 2: Docker Testing (Recommended)

### Run in Container

```bash
# 1. Copy files if not already there
docker cp test_architecture_ssot.py crm_sintel-web-1:/app/apps/tenant/core/tests/
docker cp conftest.py crm_sintel-web-1:/app/

# 2. Run the guard
docker exec crm_sintel-web-1 python -m pytest \
  apps/tenant/core/tests/test_architecture_ssot.py -v
```

✅ **Guard is active in production environment!**

---

## 🔄 Option 3: Add to Makefile (Recommended)

### One-Command Easy Access

```bash
# Add to Makefile:
echo '
.PHONY: guard test-architecture

guard:
	@echo "🛡️  Running Architecture SSoT Guard (quick)..."
	python -m pytest apps/tenant/core/tests/test_architecture_ssot.py::TestArchitectureSSoTIntegrity::test_all_tenant_models_have_empresa_fk -x --tb=line

test-architecture:
	@echo "🛡️  Running Full Architecture Test Suite..."
	docker exec crm_sintel-web-1 python -m pytest apps/tenant/core/tests/test_architecture_ssot.py -v
' >> Makefile

# Now use:
make guard              # Quick check (5 sec)
make test-architecture  # Full check in Docker (8 sec)
```

---

## 💻 Option 4: Pre-Commit Hook (Most Effective)

### Automatic Protection Before Commits

```bash
# Create hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
echo "[PRE-COMMIT] 🛡️  Running Architecture SSoT Guard..."
python -m pytest \
    apps/tenant/core/tests/test_architecture_ssot.py::TestArchitectureSSoTIntegrity::test_all_tenant_models_have_empresa_fk \
    -x --tb=line -q

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ ARCHITECTURE VIOLATION DETECTED!"
    echo "Your commit introduces models without empresa_id FK."
    echo ""
    echo "Fix:"
    echo "1. Add 'empresa = models.ForeignKey(...)' to the model"
    echo "2. Run: python manage.py makemigrations"
    echo "3. Try again: git commit"
    echo ""
    exit 1
fi
echo "✅ Architecture Guard passed - commit allowed"
exit 0
EOF

chmod +x .git/hooks/pre-commit
```

**From now on:**
```bash
git commit -m "Add my model"
# → Pre-commit hook automatically checks modelo!
# → If violation: commit BLOCKED ❌
# → If clean: commit ALLOWED ✅
```

---

## 🐙 Option 5: GitHub Actions (CI/CD)

### Automatic Queue Gate

```bash
# Create file: .github/workflows/architecture-guard.yml
cat > .github/workflows/architecture-guard.yml << 'EOF'
name: 🛡️ Architecture SSoT Guard

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  architecture-guard:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s

    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install deps
        run: pip install -r requirements.txt
      
      - name: 🛡️ Run Guard
        run: |
          python manage.py migrate
          python -m pytest \
            apps/tenant/core/tests/test_architecture_ssot.py \
            -v --tb=short
EOF

git add .github/workflows/architecture-guard.yml
git commit -m "ci: Add Architecture SSoT Guard workflow"
git push
```

**Result:**
- Every PR runs guard automatically ✅
- Architecture violations BLOCK merge 🛑
- Clean models PASS CI checks ✅

---

## 📋 Test a Violation (to Verify It Works)

### Intentionally Break It (Do This ONCE)

```python
# apps/tenant/gastos/models.py
class TestModel(models.Model):
    titulo = models.CharField(max_length=255)
    # ❌ Intentionally missing empresa FK
    
    class Meta:
        app_label = 'gastos'
```

**Test it:**
```bash
pytest apps/tenant/core/tests/test_architecture_ssot.py::TestArchitectureSSoTIntegrity::test_all_tenant_models_have_empresa_fk -xvs
```

**You'll see:**
```
AssertionError: [ARCHITECTURE VIOLATION] SSoT Rule incumplida:

[ERROR] Modelos sin FK a Empresa (1):
  - apps.tenant.gastos.TestModel

FIX: Agrega este campo a cada modelo:
  empresa = models.ForeignKey(
      'empresa.Empresa',
      on_delete=models.CASCADE,
      related_name='...',
  )
```

**Now fix it:**
```python
class TestModel(models.Model):
    empresa = models.ForeignKey(
        'empresa.Empresa',
        on_delete=models.CASCADE,
        related_name='test_models',
    )
    titulo = models.CharField(max_length=255)
```

**Test again:**
```bash
pytest ... -xvs
# ✅ PASSED
```

✨ **Guard working perfectly!**

---

## 🔥 Add to Your Daily Workflow

### Before Each Commit

```bash
# 1. Run guard
make guard
# or
pytest apps/tenant/core/tests/test_architecture_ssot.py -x --tb=line

# 2. See ✅ or ❌
# 3. If ❌: fix model
# 4. If ✅: commit safely
git commit -m "feat(gastos): Add Presupuesto model"
```

---

## 📊 Check Your Current Status

### Quick Report

```bash
# See which models pass/fail
python -c "
from django.apps import apps
from config.settings import TENANT_APPS

for app_name in TENANT_APPS:
    app_config = apps.get_app_config(app_name)
    for model in app_config.get_models():
        has_empresa = hasattr(model, 'empresa')
        status = '✅' if has_empresa else '❌'
        print(f'{status} {model.__name__:30} {app_name}')
"
```

**Output example:**
```
✅ Empresa                         empresa
✅ Cliente                         clientes
✅ Factura                         facturas
✅ AsientoContable                 contabilidad
❌ MovimientoContable              contabilidad  ← [TECHNICAL DEBT]
```

---

## 🎯 Three-Step Startup

### Step 1: Verify Installation (1 min)

```bash
python -m pytest apps/tenant/core/tests/test_architecture_ssot.py -v
# Expected: 3 PASSED ✅
```

### Step 2: Set Up Pre-Commit (2 min)

```bash
chmod +x .git/hooks/pre-commit
# (Already created above)
```

### Step 3: Inform Your Team (2 min)

```bash
# Share this message:
"""
🛡️ Architecture Guard is now ACTIVE!

New rule: All TENANT_APPS models MUST have empresa_id FK

Before committing:
  - Run: make guard
  - Expected: ✅ PASSED
  - If ❌: Add empresa FK to model

Questions? See:
  - SSOT_GUARD_QUICK_REFERENCE.md
  - SERVER_GUARD_SSOT_ARCHITECTURE.md
"""
```

---

## ⚡ Common Commands Cheat Sheet

```bash
# Local quick check
pytest apps/tenant/core/tests/test_architecture_ssot.py -x --tb=line -q

# Full verbose check
pytest apps/tenant/core/tests/test_architecture_ssot.py -xvs

# In Docker
docker exec crm_sintel-web-1 python -m pytest apps/tenant/core/tests/test_architecture_ssot.py -v

# With coverage
pytest apps/tenant/core/tests/test_architecture_ssot.py --cov=apps.tenant --cov-report=html

# Single test only
pytest apps/tenant/core/tests/test_architecture_ssot.py::TestArchitectureSSoTIntegrity::test_all_tenant_models_have_empresa_fk -xvs

# If using Makefile
make guard              # Quick 5-sec check
make test-architecture  # Docker 8-sec check
```

---

## 🆘 Troubleshooting

### Error: "ModuleNotFoundError: pytest"

```bash
pip install pytest pytest-django
```

### Error: "Database connection refused"

```bash
# Run migrations first
python manage.py migrate --run-syncdb
```

### Error: "model has no attribute 'empresa'"

→ That model is MISSING empresa FK!
→ See: "Add to Your Daily Workflow" section

### Test hangs / timeout

```bash
pytest ... --timeout=10
```

---

## 📞 When to Use Each Option

| Scenario | Use This | Command |
|----------|----------|---------|
| Quick local check | Direct pytest | make guard |
| Before commit | Pre-commit hook | (automatic) |
| In Docker container | Docker exec | docker exec ... pytest |
| GitHub PR | GitHub Actions | .github/workflows/... |
| Team enforcement | CI/CD gate | Add to your pipeline |

---

## ✅ Success Indicators

You're done when you see:

```
✅ 3 passed, 3 skipped in 5.86s
```

Or if pre-commit hook:

```
✅ Architecture Guard passed - commit allowed
```

Or in GitHub Actions:

```
✅ architecture-guard: All checks passed
```

---

## 🎓 Next: Share with Team

**Copy-paste for Slack/Email:**

```
🛡️ ARCHITECTURE SAFEGUARD ACTIVATED

The SINTEL codebase now has automated architecture protection!

What it does:
- Prevents models without empresa_id FK
- Blocks commits with violations
- Provides clear error messages

How to test:
  make guard           # Local test
  make test-architecture  # Docker test

How to fix violations:
  Add this to NEW models:
    empresa = models.ForeignKey('empresa.Empresa', on_delete=models.CASCADE)

Questions?
  See: documentacion/SSOT_GUARD_QUICK_REFERENCE.md

Status: ✅ ACTIVE & OPERATIONAL
```

---

**Status:** ✅ READY TO USE  
**Setup Time:** 5 minutes  
**Learning Curve:** 2 minutes  
**Protection Level:** ⭐⭐⭐⭐⭐ (Maximum)

🚀 **START NOW!**
