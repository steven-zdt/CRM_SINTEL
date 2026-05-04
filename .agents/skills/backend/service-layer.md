# Skill: Service Layer — SINTEL v2.62

**Carga cuando:** Crear nueva app, nuevo modelo, nuevo CRUD.
**Stack:** Django + django-tenants + PostgreSQL

---

## Estructura Obligatoria

```
apps/tenant/<app>/
    services/
        __init__.py        <- exporta clases públicas
        selectors.py       <- lectura, QuerySets optimizados
        crud_service.py    <- escritura transaccional
        business_service.py <- lógica de negocio y orquestación
        api_mixins.py      <- inyecta servicios al ViewSet
        services.py        <- fachada de compatibilidad (si existe código heredado)
    api/
        viewsets.py
        serializers.py
        urls.py
        mixins.py
```

## Patrón `selectors.py`

```python
from apps.tenant.<app>.models import MiModelo

LIST_FIELDS = ('id', 'empresa_id', 'campo_a', 'campo_b', 'created_at')
DETAIL_FIELDS = LIST_FIELDS + ('campo_extra', 'campo_largo')

class MiModeloSelector:
    @staticmethod
    def get_list(empresa_id: int, search: str | None = None):
        qs = MiModelo.objects.filter(empresa_id=empresa_id).only(*LIST_FIELDS)
        if search:
            qs = qs.filter(campo_a__icontains=search)
        return qs.order_by('-created_at')

    @staticmethod
    def get_detail(empresa_id: int, pk: int):
        return (
            MiModelo.objects.filter(empresa_id=empresa_id, pk=pk)
            .only(*DETAIL_FIELDS)
            .first()
        )
```

## Patrón `crud_service.py`

```python
from django.db import transaction, IntegrityError
from rest_framework.exceptions import ValidationError

class MiModeloCRUDService:
    @staticmethod
    @transaction.atomic
    def crear(empresa_id: int, data: dict) -> MiModelo:
        try:
            return MiModelo.objects.create(empresa_id=empresa_id, **data)
        except IntegrityError as e:
            if 'uniq_<constraint_name>' in str(e):
                raise ValidationError({'campo': ['Ya existe.']})
            raise

    @staticmethod
    @transaction.atomic
    def actualizar(obj: MiModelo, data: dict) -> MiModelo:
        for k, v in data.items():
            setattr(obj, k, v)
        obj.save()
        return obj

    @staticmethod
    @transaction.atomic
    def eliminar(obj: MiModelo) -> None:
        obj.delete()
```

## Patrón `business_service.py`

```python
class MiModeloBusinessService:
    @staticmethod
    @transaction.atomic
    def registrar(empresa_id: int, data: dict, instance: MiModelo = None) -> MiModelo:
        """
        Orquesta creación o actualización (Upsert seguro).
        [CRITICAL HOTFIX] Soporta PATCH parcial recibiendo la instancia directamente.
        """
        # 1. DSV: verificar FKs pertenecen al tenant
        # 2. Calcular campos derivados
        
        if instance:
            # Si hay instancia (PUT/PATCH), actualiza directo sin buscar.
            return MiModeloCRUDService.actualizar(instance, data)
        else:
            # Lógica Upsert para creación idempotente
            identificador = data.get('identificador_unico')
            existing = MiModelo.objects.filter(empresa_id=empresa_id, identificador_unico=identificador).first()
            if existing:
                return MiModeloCRUDService.actualizar(existing, data)
            
            return MiModeloCRUDService.crear(empresa_id, data)
```

## Patrón `api_mixins.py`

```python
from apps.tenant.<app>.services.selectors import MiModeloSelector
from apps.tenant.<app>.services.crud_service import MiModeloCRUDService
from apps.tenant.<app>.services.business_service import MiModeloBusinessService

class MiModeloServiceMixin:
    @property
    def selector(self): return MiModeloSelector()

    @property
    def service(self): return MiModeloBusinessService()

    @property
    def crud(self): return MiModeloCRUDService()
```

## Reglas Absolutas
- `@staticmethod` en todos los métodos de servicios
- NUNCA acceder a BD desde ViewSet directamente — usar Selectors
- NUNCA lógica de negocio en Selectors ni CRUDService
- NUNCA Signals para lógica de negocio
- `services.py` solo como fachada de compatibilidad
- **[CRITICAL HOTFIX]** Los métodos "Upsert" (ej. `registrar_completo`) DEBEN aceptar un parámetro opcional `instance=None`. Si se provee, deben actualizarlo directamente en lugar de buscar por campos, para evitar que los `PATCH` parciales fallen al enviar campos nulos.
