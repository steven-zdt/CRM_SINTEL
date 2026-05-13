# 🛡️ SSoT Architecture Guard - Developer Quick Reference

**TL;DR:** The Architecture Guard automatically prevents you from committing models without `empresa_id`.

---

## ⚡ Quick Commands

```bash
# ✅ Run the guard locally
pytest apps/tenant/core/tests/test_architecture_ssot.py -xvs

# ✅ Run single test
pytest apps/tenant/core/tests/test_architecture_ssot.py::TestArchitectureSSoTIntegrity::test_all_tenant_models_have_empresa_fk -xvs

# ✅ Run in Docker
docker exec crm_sintel-web-1 python -m pytest \
  apps/tenant/core/tests/test_architecture_ssot.py -v

# ✅ Quick local check (before commit)
python -m pytest \
  apps/tenant/core/tests/test_architecture_ssot.py \
  -x --tb=line -q
```

---

## 🚨 Common Errors & Fixes

### Error 1: New Model But Forgot empresa FK

**You see:**
```
AssertionError: [ARCHITECTURE VIOLATION] SSoT Rule incumplida:

[ERROR] Modelos sin FK a Empresa (1):
  - apps.tenant.gastos.Presupuesto
```

**Fix - Add to your model:**
```python
class Presupuesto(models.Model):
    empresa = models.ForeignKey(
        'empresa.Empresa',
        on_delete=models.CASCADE,
        related_name='presupuestos',
    )
    titulo = models.CharField(max_length=255)
```

**Then:**
```bash
# Create migration
python manage.py makemigrations

# Test again
pytest apps/tenant/core/tests/test_architecture_ssot.py -xvs
# ✅ PASS
```

---

### Error 2: empresa Field is Nullable

**You see:**
```
AssertionError: [ARCHITECTURE VIOLATION] SSoT Rule incumplida:

[ERROR] Modelos con empresa.null=True (1):
  - apps.tenant.gastos.Presupuesto
```

**❌ WRONG:**
```python
empresa = models.ForeignKey(
    'empresa.Empresa',
    on_delete=models.CASCADE,
    null=True,  # ← WRONG!
)
```

**✅ CORRECT:**
```python
empresa = models.ForeignKey(
    'empresa.Empresa',
    on_delete=models.CASCADE,
    null=False,  # ← CORRECT (or omit - False is default)
)
```

---

## 📋 Multi-Tenant Model Template

**Copy this template for NEW TENANT MODELS:**

```python
# apps/tenant/{app_name}/models.py

from django.db import models
from apps.tenant.empresa.models import Empresa


class MyNewModel(models.Model):
    """
    [REQUIRED] Empresa tenant link - NEVER NULL
    [REQUIRED] Always filter .filter(empresa_id=...)
    """
    
    # 1️⃣ ALWAYS FIRST: empresa FK [REQUIRED]
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='my_new_models',  # Change this!
    )
    
    # 2️⃣ Your business fields
    titulo = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = '{app_name}'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['empresa', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.titulo} ({self.empresa.razon_social})"


class MyNewModelQuerySet(models.QuerySet):
    """
    [REQUIRED] Always scope by empresa
    """
    def for_empresa(self, empresa_id):
        return self.filter(empresa_id=empresa_id)


class MyNewModelManager(models.Manager):
    def get_queryset(self):
        return MyNewModelQuerySet(self.model, using=self._db)
    
    def for_empresa(self, empresa_id):
        return self.get_queryset().for_empresa(empresa_id)


# Usage:
# MyNewModel.objects.for_empresa(empresa_id=1).all()
```

---

## ✅ Checklist Before Committing

```
Before you git push:

[ ] Model added to existing app?
    → Run: pytest apps/tenant/core/tests/test_architecture_ssot.py -xvs
    → Must see: ✅ PASSED

[ ] Nueva app created with models?
    → Update: apps/config/settings.py TENANT_APPS list
    → Run: pytest apps/tenant/core/tests/test_architecture_ssot.py -xvs
    → Must see: ✅ PASSED

[ ] Model added to SHARED_APPS (public)?
    → SKIP architecture guard (not required for shared)
    → Just make sure: python manage.py makemigrations
    → Normal testing applies

[ ] Created migration?
    → Run: python manage.py migrate
    → Deploy: python manage.py migr ate --run-syncdb

[ ] Celery tasks added?
    → Ensure task scopes by empresa
    → ✅ ARCHITECTURE GUARD does NOT check tasks (only models)

[ ] Passed local guard?
    → pip install -r requirements.txt  (if needed)
    → pytest apps/tenant/core/tests/test_architecture_ssot.py -x
    → See: ✅ 3 PASSED
```

---

## 🎯 What the Guard Actually Checks

| Item | Checked | Required Value |
|------|---------|-----------------|
| Model has `empresa` field | ✅ | ForeignKey |
| No model is missing FK | ✅ | All must have it |
| `empresa.null` is False | ✅ | NOT nullable |
| `empresa.blank` is False | ✅ | NOT blank |
| `on_delete` strategy | ✅ | CASCADE or PROTECT |
| Model in TENANT_APPS | ✅ | Not in SHARED_APPS |

**NOT checked:**
- Service layer implementation
- Query optimization
- Field naming conventions

---

## 🔍 Real Example: Adding a "Presupuesto" Model

### Step 1: Create model with empresa FK

```python
# apps/tenant/gastos/models.py

from django.db import models
from apps.tenant.empresa.models import Empresa


class Presupuesto(models.Model):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='presupuestos',
    )
    
    numero = models.CharField(max_length=50)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    
    class Meta:
        app_label = 'gastos'
    
    def __str__(self):
        return f"Presupuesto {self.numero}"
```

### Step 2: Run migrations

```bash
python manage.py makemigrations gastos
python manage.py migrate gastos
```

### Step 3: Test the guard

```bash
pytest apps/tenant/core/tests/test_architecture_ssot.py -xvs
```

**Expected output:**
```
✅ test_all_tenant_models_have_empresa_fk PASSED
✅ test_empresa_fk_field_constraints PASSED
✅ test_base_model_consistency_check PASSED

=================== 3 passed in 0.82s ====================
```

### Step 4: Commit

```bash
git add apps/tenant/gastos/models.py
git add apps/tenant/gastos/migrations/000X_add_presupuesto.py
git commit -m "feat(gastos): Add Presupuesto model with empresa_id FK"
git push
```

**GitHub Actions will:**
1. Run the guard test automatically ✅
2. Verify your model has empresa FK ✅
3. Allow merge if PASSED ✅

---

## ❌ What Happens If You Break It

### Scenario: Forgot empresa FK

```python
class Presupuesto(models.Model):
    numero = models.CharField(max_length=50)
    # ❌ FORGOT empresa!
```

**CI/CD Output:**
```
FAILED apps/tenant/core/tests/test_architecture_ssot.py::TestArchitectureSSoTIntegrity::test_all_tenant_models_have_empresa_fk

AssertionError: [ARCHITECTURE VIOLATION] SSoT Rule incumplida:

  [ERROR] Modelos sin FK a Empresa (1):
    - apps.tenant.gastos.Presupuesto

Pull Request: ❌ BLOCKED (cannot merge)

Action Required:
  1. Add empresa FK to Presupuesto
  2. Create migration
  3. Push fix
  4. Re-run tests
```

---

## 📞 Help & Escalation

**I don't understand the error:**
→ See: [SERVER_GUARD_SSOT_ARCHITECTURE.md](SERVER_GUARD_SSOT_ARCHITECTURE.md)

**Test failing but model looks correct:**
→ Run: `pytest ... -xvs` (verbose output shows details)

**Need to add exception (temporary):**
→ Contact: Architecture Team
→ File: [apps/tenant/core/tests/test_architecture_ssot.py](../../apps/tenant/core/tests/test_architecture_ssot.py)
→ Section: `MODELS_WITHOUT_EMPRESA_FK`

---

## 🚀 Pro Tips

### Tip 1: Pre-Commit Hook (Recommended)

```bash
# Auto-run guard before every commit
chmod +x .git/hooks/pre-commit
```

If you forget, the hook will catch it! 🎣

### Tip 2: VS Code Snippet

Add to `.vscode/python.code-snippets`:

```json
{
  "Tenant Model": {
    "prefix": "tenant-model",
    "body": [
      "class ${1:ModelName}(models.Model):",
      "    empresa = models.ForeignKey(",
      "        'empresa.Empresa',",
      "        on_delete=models.CASCADE,",
      "        related_name='${2:related_name}',",
      "    )",
      "    ",
      "    # TODO: Add fields",
      "    ",
      "    class Meta:",
      "        app_label = '${3:app_name}'"
    ]
  }
}
```

**Usage:** Type `tenant-model` + Tab → boilerplate generated! ✨

### Tip 3: Makefile Shortcut

```bash
make guard-check     # Quick local test
make test-architecture  # Full test in Docker
```

---

## 📊 Test Coverage

The guard tests:
- ✅ 12 TENANT_APPS
- ✅ ~50+ models
- ✅ Field constraints
- ✅ Execution time: ~6 seconds

---

**Remember:** Any new tenant model MUST have `empresa_id` FK. The Guard will catch it! 🛡️
