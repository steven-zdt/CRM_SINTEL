# REM-P3-08 — `Factura.consecutivo = 0` para documentos externos

**Estado:** VERIFIED (documentado, decisión de no migrar el esquema)
**Prioridad:** P3
**App involucrada:** `facturas`
**Fecha:** 2026-08-28

## Hallazgo

`guardar_desde_dto()` (importación XML) asigna `consecutivo: dto.get(
"consecutivo", 0)` — el DTO de un documento `Origen.EXTERNO` nunca trae
ese campo, así que **todas las facturas externas comparten
`consecutivo=0`**.

## Investigación

- **Identidad fiscal real**: `Factura.numero` (`unique=True`) — ya
  confirmado como el identificador real y único de cualquier Factura,
  interna o externa. `consecutivo` nunca se usó como identificador en
  ningún lugar del código (confirmado en la auditoría de numeración de la
  misión empresarial — solo `ResolucionFacturacion`/`Empresa.
  select_for_update()+Max()+1` lo generan, exclusivamente para
  `Origen.INTERNO`).
- **¿Existe un campo mejor para reutilizar?** No — no hay un "consecutivo
  externo" real que capturar; el emisor externo tiene su propia
  numeración, ya capturada íntegramente en `numero`.
- **¿Vale la pena hacer el campo nullable?** Evaluado y descartado:
  `IntegerField` sin `null=True` hoy — hacerlo nullable requeriría
  migración + auditar cada consumidor que asuma un `int` (ordenamientos,
  serializers, templates). Para un campo que ya no es identificador en
  ningún flujo real, el costo no se justifica para un hallazgo P3.

## Corrección

**Documentación, no migración de esquema.** Se agregó `help_text` al
campo del modelo y un comentario en el punto de asignación
(`business_service.py:687-698`) explicando que `0` es un sentinel de "no
aplica" para `Origen.EXTERNO`, nunca un consecutivo real — para que una
futura lectura del código no lo malinterprete ni intente usarlo como
identificador.

## Archivos modificados

- `apps/tenant/facturas/models.py` (`help_text` de `consecutivo`)
- `apps/tenant/facturas/services/business_service.py` (comentario)

## Modelo afectado

`Factura.consecutivo` — solo cambió `help_text` (metadata), no el tipo ni
la nulabilidad de la columna. `makemigrations facturas` sí la detectó
(cambio de `help_text` es parte del estado de campo que Django rastrea) —
generada como `0040_alter_factura_consecutivo.py` y **aplicada a los 3
tenants reales** (migración de solo metadata, sin DDL real de datos).

## Tests

Ninguno nuevo — es un cambio puramente de documentación/metadata, sin
comportamiento nuevo que probar.

## Governance

Migración aplicada y confirmada (`information_schema.columns`: columna
`consecutivo` presente, `NOT NULL`, sin cambio de tipo). Pendiente el
barrido de governance final de la misión (`makemigrations --check`
global, `manage.py check`).

## Riesgos / deuda pendiente

Ninguno — decisión de bajo riesgo, reversible, sin impacto funcional.
