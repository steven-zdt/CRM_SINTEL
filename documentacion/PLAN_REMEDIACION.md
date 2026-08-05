# PLAN DE REMEDIACIÓN — SINTEL ERP

**Fase:** 0 — Preparación
**Fecha:** 2026-07-26
**Fuente de hallazgos:** `documentacion/AUDITORIA_ENTERPRISE_2026-07-26.md`
**Documentos canónicos leídos íntegramente antes de este plan:** `AGENTS.md`, `documentacion/arquitectura_general.md`, `MEMORY.md`, `docs/ADR-001-retention-pull-model.md`, `docs/ADR-002-public-schema-api-dual-registration.md`, `CLAUDE.md`, más los `.agent/AUDITORIA_FLUJO_*.md` de `facturas`, `contabilidad`, `inventario`, `ventas`, `perfil`, `empresa` (apps objetivo de Fase 1).

---

## 1. Restricción de entorno detectada (afecta la validación de todas las fases)

Antes de tocar código se intentó levantar el stack Docker (`docker compose up -d db redis web`) para validar con `manage.py check` / `pytest`. Resultado:

- La red `crm_sintel_default` no resolvía nombres de host entre contenedores (`could not translate host name "db"`) incluso tras recrear la red desde cero.
- Los puertos `5432`/`8000` ya están ocupados por otro proyecto no relacionado corriendo en el mismo host (`ecommerce_sintel_db`, `ecommerce_sintel_django`), y existe además un stack `sintel_prod_*` (aparente entorno productivo) corriendo en paralelo — no se tocó ninguno de los dos.
- El intérprete referenciado por `venv/pyvenv.cfg` (`C:\Python314\python.exe`) no existe en este host; solo hay un Python 3.13 instalado en `AppData\Local\Programs\Python\Python313`, sin las dependencias del proyecto instaladas.

**Consecuencia:** ninguna fase de esta remediación podrá validarse en este entorno con `make dj-check` / `make test` / aplicando migraciones reales. Cada corrección se verificará con:
1. `python -m py_compile` sobre cada archivo `.py` tocado (sintaxis).
2. Lectura completa del archivo modificado y de sus consumidores directos (imports, tests existentes, templates/JS que llaman al endpoint).
3. Comparación de patrón contra código ya correcto en el mismo repositorio (p. ej. `select_for_update` ya usado correctamente en `gastos`/`inventario`/`ventas`/`cotizaciones` se usa como plantilla para el fix de `facturas`).

Se deja constancia explícita en cada `REPORTE_FASE_N.md` de qué quedó pendiente de verificación en un entorno con Docker/venv funcional, y se recomienda ejecutar `make dj-check && make test` antes de hacer merge de cualquier fase.

---

## 2. Mapa de dependencias relevante para la remediación

(Detallado en `AUDITORIA_ENTERPRISE_2026-07-26.md` §7; resumen operativo aquí.)

- **`config/settings.py` → `apps/tenant/api/permissions.py` → `apps/tenant/api/mixins.py` → `apps/public/core/middleware.py`**: los cuatro comparten el flag `DEBUG`. Corregir SEC-C1 requiere tocar los cuatro de forma coordinada en la misma fase, o el fix queda incompleto (p. ej. arreglar `settings.py` sin tocar `permissions.py` no cierra el hallazgo).
- **`facturas/api/viewsets.py` (SEC-C2) es independiente** de lo anterior — no comparte archivos con SEC-C1.
- **`contabilidad/models.py` (PERF-C1) requiere una migración nueva** — se coordina con `contabilidad/integracion/contabilizador.py` (debe capturar `IntegrityError` como respaldo del `UniqueConstraint`).
- **`facturas/services/business_service.py` (PERF-C2) es independiente** de PERF-C1/C3 — no comparte archivos.
- **`facturas/utils/ubl_parser.py` + `facturas/services/services_mail_ingestion.py` (PERF-C3) son un único cambio coordinado** — el fix de tipo en un archivo depende del contrato que retorna el otro.
- **`inventario_editor.js` + `offcanvas_producto.html` (FE-C1/C2) son un único cambio coordinado** — mismo formulario.
- **`core/js/lib/http.js` + `assets_core.html` (FE-C3) son un único cambio coordinado** — eliminar el archivo sin quitar su `<script src>` rompería el include; hay que verificar primero que ningún otro archivo dependa de una función exclusiva de la versión obsoleta.
- **`facturas/models.py` (ARQ-C1) depende de la API pública de `RetencionesService`** (`contabilidad/services/retenciones_service.py`) — se debe leer esa API antes de reemplazar las 6 líneas de import directo, para no cambiar el contrato de los `@property` que las consumen (usados por serializers de facturas).
- **`inventario/services/business_service.py` → `api_mixins.py` (ARQ-C2)** — mover clases de un archivo a otro es mecánico pero `services/__init__.py` re-exporta por nombre; hay que actualizar los imports ahí para no romper el `ViewSet`.
- **`ventas` (TEST-C1) requiere leer su `.agent/ARQUITECTURA_VENTAS.md` y `models.py`/`business_service.py`** antes de escribir el test, para que las 3 verificaciones de aislamiento (lectura, escritura, DSV) sean reales y no tautológicas — ver hallazgo TEST-A2 (assertion tautológica ya presente en el repo, a NO repetir).
- **CI (DEVOPS-C1) y documentación (DOC-C1/C2) no comparten archivos con nada del código** — se pueden hacer en paralelo al resto.

## 3. Orden de ejecución dentro de Fase 1

1. SEC-C1 (settings + permissions + mixins + middleware) — el de mayor radio de impacto, se corrige primero.
2. SEC-C2 (facturas viewsets) — independiente, rápido.
3. PERF-C2 (facturas consecutivo) — independiente, patrón ya existe en el repo.
4. PERF-C1 (contabilidad UniqueConstraint + migración) — requiere diseño de migración, se hace con calma después de los quick-wins.
5. PERF-C3 (ubl_parser + mail ingestion) — el más delicado, toca el pipeline de ingesta DIAN.
6. FE-C1/C2 (inventario) — independiente del resto.
7. FE-C3 (http.js) — requiere verificar consumidores antes de tocar.
8. ARQ-C1 (facturas → RetencionesService) — requiere leer el servicio primero.
9. ARQ-C2 (inventario api_mixins.py) — mecánico, bajo riesgo.
10. TEST-C1 (test de ventas) — se hace después de que el resto del código esté estable, para no testear un estado transitorio.
11. DEVOPS-C1 (CI) + DOC-C1/DOC-C2 (documentación) — en paralelo, sin dependencias de código.

## 4. Criterios de "fase estable" para cerrar Fase 1

- 0 `SyntaxError` (`py_compile` limpio en todos los archivos tocados).
- Cada `@property`/método reemplazado conserva su firma y tipo de retorno original (verificado leyendo cada call site).
- Ningún archivo queda con imports muertos tras el refactor (ARQ-C1/C2).
- La migración nueva de `contabilidad` es aditiva (no altera datos existentes, solo agrega una restricción) y se puede revertir con `migrate contabilidad <migracion_anterior>`.
- Documentado explícitamente qué no pudo probarse en runtime por la restricción de entorno (§1).

---

*Siguiente entregable: `REPORTE_FASE_1.md` al finalizar la corrección de los 15 hallazgos CRÍTICOS.*
