# Skill: Django Multi-Tenant — SINTEL v2.62

**Carga cuando:** Crear modelos, migraciones, queries que involucran empresa_id.

---

## Modelo Obligatorio

```python
from apps.tenant.core.models import SintelTenantBaseModel

class MiModelo(SintelTenantBaseModel):
    # SintelTenantBaseModel inyecta:
    # - empresa: FK('empresa.Empresa', PROTECT, db_index=True)
    # - created_at: DateTimeField(auto_now_add=True)
    # - updated_at: DateTimeField(auto_now=True)

    campo_a = models.CharField(max_length=200)
    campo_b = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'campo_a'],
                name='uniq_<modelo>_empresa_campo'
            )
        ]
        indexes = [
            models.Index(fields=['empresa', 'activo']),
            models.Index(fields=['empresa', '-created_at']),
        ]
        ordering = ['-created_at']
```

## Queries Obligatorias

```python
# CORRECTO: siempre filtrar por empresa_id
qs = MiModelo.objects.filter(empresa_id=empresa_id).only('id', 'campo_a')

# PROHIBIDO: sin filtro de empresa
qs = MiModelo.objects.all()                      # PROHIBIDO
qs = MiModelo.objects.filter(campo_a='x')        # PROHIBIDO (sin empresa_id)
qs = MiModelo.objects.filter(empresa_id=empresa_id)  # PROHIBIDO (sin .only())
```

## Resolver Empresa desde Request

```python
def resolve_tenant_empresa(request, view_instance=None):
    """Patrón canónico. Copiar en cada ViewSet que lo necesite."""
    from django.db.utils import ProgrammingError

    if view_instance is not None:
        cached = view_instance.__dict__.get('tenant_empresa')
        if cached:
            return cached

    tenant = getattr(request, 'tenant', None)
    empresa = getattr(tenant, 'empresa', None)
    if empresa:
        return empresa

    empresa = getattr(request, 'tenant_empresa', None)
    if empresa:
        return empresa

    try:
        from apps.tenant.empresa.models import Empresa
        return Empresa.objects.only('id', 'razon_social').first()
    except ProgrammingError:
        return None
```

## Migraciones Multi-Tenant

```bash
# Tenant schemas
docker compose exec web python manage.py makemigrations <app>
docker compose exec web python manage.py migrate_schemas

# Shared schemas (apps/public/)
docker compose exec web python manage.py migrate_schemas --shared
```

### PROHIBIDO: usar el nombre de carpeta en `dependencies` cuando el app tiene `label` propio

`AppConfig.label` (no el nombre de la carpeta bajo `apps/tenant/`) es el namespace real que Django
usa para resolver `dependencies = [('<app_label>', '000N_...')]` entre migraciones. Escribir a mano
`dependencies` con el nombre de carpeta cuando la app sobre-escribe su `label` rompe
`migrate_schemas` con `NodeNotFoundError` y bloquea el arranque de **todo** el proyecto, no solo
esa app (incidente real: `apps/tenant/proyectos/migrations/0020...py` tenia
`('proyectos', '0019_proyecto_sede')` en vez de `('tenant_proyectos', ...)` — ver
`apps/tenant/proyectos/.agent/AUDITORIA_FLUJO_COMPLETO.md` FIX v3.10.5).

**Antes de escribir `dependencies` a mano, verificar:**
```bash
grep -n "label" apps/tenant/<app>/apps.py
```

Apps que SI sobre-escriben `label` (usar `tenant_<nombre>` en `dependencies`, NO el nombre de
carpeta): `clientes`, `compras`, `core`, `cotizaciones`, `empleados`, `gastos`, `inventario`,
`proveedores`, `proyectos`, `ventas`.

Apps que usan el default de Django (el nombre de carpeta SI es el `app_label` correcto):
`bancos`, `contabilidad`, `dashboard`, `empresa`, `facturas`, `landing`, `perfil`.

**Mejor practica:** dejar que `makemigrations` genere `dependencies` automaticamente — Django
siempre resuelve el `app_label` correcto por si mismo. Este bug solo aparece cuando se edita o
crea `dependencies` a mano.

## Bridge a Esquema Público

```python
# CORRECTO: siempre via Bridge
from apps.tenant.core.services.membership import check_membership

# PROHIBIDO en apps tenant (excepto core/ y api/)
from apps.public.tenants.models import TenantMembership  # PROHIBIDO
```

## Reglas
- NUNCA `models.Model` directamente — siempre `SintelTenantBaseModel`
- NUNCA `.filter()` sin `empresa_id` en TENANT_APPS
- NUNCA `.all()` sin `.only()` encadenado
- `empresa_id` es la clave de partición de seguridad — filtrar SIEMPRE
