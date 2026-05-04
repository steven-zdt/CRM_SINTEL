# Skill: Data Migration & Zero Waste — SINTEL v2.62

**Carga cuando:** Escribir scripts de ingesta de datos, migraciones complejas de Excel/CSV a PostgreSQL, o queries masivas.

---

## 1. Principio Zero Waste (Optimización de Queries)

**PROHIBIDO:** Usar `.all()` o `.filter()` sin restricciones de campos.
**OBLIGATORIO:** Encadenar siempre `.only()` o `.defer()`.

```python
# MALA PRÁCTICA (Bloqueado)
registros = Modelo.objects.filter(empresa_id=empresa_id)

# BUENA PRÁCTICA (SINTEL Standard)
registros = Modelo.objects.filter(empresa_id=empresa_id).only('id', 'codigo', 'nombre')
```

## 2. Idempotencia en la Ingesta (Upsert)

Todo proceso de migración o ingesta debe ser idempotente usando `update_or_create` o manejando `IntegrityError` con restricciones únicas de base de datos.

```python
from django.db import transaction, IntegrityError

@transaction.atomic
def procesar_lote_ingesta(lote_datos, empresa_id):
    for item in lote_datos:
        try:
            Modelo.objects.update_or_create(
                empresa_id=empresa_id,
                codigo_externo=item['codigo'],
                defaults={
                    'nombre': item['nombre'],
                    'valor': item['valor']
                }
            )
        except IntegrityError:
            # Fallback seguro o log de error sin romper el lote
            pass
```

## 3. Desacoplamiento de Memoria (Batching)

Para evitar saturación de RAM en migraciones pesadas, usar `iterator()` y procesamiento en bloques (batch).

```python
# Leer en bloques sin saturar memoria
qs = Modelo.objects.filter(empresa_id=empresa_id).only('id', 'estado').iterator(chunk_size=2000)

for registro in qs:
    # procesar...
    pass
```
