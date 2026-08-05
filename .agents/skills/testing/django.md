# Skill: Testing Django — General (SINTEL v1.0)

**Carga cuando:** Configurar pytest, fixtures generales, factories, o cualquier test que no sea DRF API.

> Para tests de API REST con TenantAPITestCase (el 99% de los tests en este proyecto) → cargar `testing/api.md`

---

## Configuración pytest

```ini
# pytest.ini (ya configurado en el proyecto)
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

Ejecutar desde Docker:
```bash
make test                              # todos
make test-file FILE="path/to/test.py" # uno solo
docker compose exec web python -m pytest -v -x  # verbose + stop on first fail
docker compose exec web python -m pytest -v -k "test_crear"  # filtrar por nombre
```

---

## Donde van los tests

```
apps/tenant/<app>/
  tests/
    __init__.py          # archivo vacío obligatorio
    test_<modelo>_crud.py     # CRUD básico (list, create, retrieve, update, delete)
    test_<modelo>_delete.py   # Reglas de negocio para eliminación (si existen)
    test_<modelo>_business.py # Validaciones complejas, cálculos, reglas
```

---

## Principios (Karpathy adaptado a tests)

1. **Un test = una sola afirmación conceptual** — no mezclar "crear + listar + actualizar" en un test
2. **`setUp()` independiente** — cada test debe poder correr solo, sin depender del orden
3. **Nombres descriptivos** — `test_crear_devengo_exito`, `test_devengo_duplicado_falla`, no `test_1`
4. **Verificar comportamiento del negocio**, no implementación interna

---

## Referencia Rápida de Imports

```python
# Siempre necesarios
from django.test import override_settings
from rest_framework import status
from apps.config.tests.base_tenant import TenantAPITestCase

# Para cross-schema
from django_tenants.utils import schema_context
from apps.public.tenants.models import Client

# Para obtener empresa (SIEMPRE así, nunca self.empresa_id)
from apps.tenant.empresa.models import Empresa
empresa = Empresa.objects.first()

# Para verificar lógica de negocio directamente
from apps.tenant.<app>.models import MiModelo
from apps.tenant.<app>.services.business_service import MiModeloBusinessService
```
