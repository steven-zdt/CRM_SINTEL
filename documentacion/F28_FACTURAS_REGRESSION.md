# F28 — Regresión de `facturas` (targeted, no full-suite re-run)

## Nota de alcance

Una corrida completa de `apps/tenant/facturas/tests/` (30 archivos) ya se
había ejecutado dos veces en fases previas de esta sesión (F27: 31
failed/110 passed/4 skipped; un intento de re-baseline en F28 tardó más de
30 minutos y fue interrumpido por indicación explícita del usuario —
"no pierdas tiempo en test facturas, lo hemos hecho muchas veces,
continua"). En lugar de repetir esa corrida completa una tercera vez, F28
verifica **quirúrgicamente los archivos que tocó** (12 migraciones de base
class + 1 fix de sintaxis), consistente con la norma "Testing Progresivo
por Alcance" de `CLAUDE.md`.

## Corrida real: los 13 archivos tocados en F28

```bash
docker compose exec -T web python -m pytest \
  apps/tenant/facturas/tests/test_factura_detail_anexos_api.py \
  apps/tenant/facturas/tests/test_facturas_list_detail_payloads.py \
  apps/tenant/facturas/tests/test_facturas_list_naturaleza_api.py \
  apps/tenant/facturas/tests/test_import_ubl_heavy_payload.py \
  apps/tenant/facturas/tests/test_naturaleza_import_ubl.py \
  apps/tenant/facturas/tests/test_upload_async_flow.py \
  apps/tenant/facturas/tests/test_xml_pipeline_canonical.py \
  apps/tenant/core/tests/test_workspace_facturas_links_and_column.py \
  apps/tenant/core/tests/test_workspace_facturas_modal.py \
  apps/tenant/core/tests/test_workspace_links_strict.py \
  tests/tenant/core/smoke/test_workspace_empresa_integridad.py \
  tests/tenant/core/test_workspace_crud_integration.py \
  tests/tenant/core/smoke/test_workspace_empresa_modules_smoke.py \
  -q --tb=short
```

**Resultado real:**
```
44 failed, 7 passed, 6 skipped, 1 warning in 2216.80s (0:36:56)
```

Desglose y causa real de cada fallo: ver `F28_FINDINGS.md` F28-004/F28-005
(a/b/c). Resumen honesto (la hipótesis inicial de "la migración resuelve
todo" era parcialmente incorrecta -- documentado, no ocultado):

- **Confirmado, la migración funciona:** `test_facturas_list_naturaleza_api.py`
  pasa 100% limpio con solo el swap de base class -- prueba directa de que
  el mecanismo F27-003 (`SintelTenantTestCase` fija `ROOT_URLCONF`) es la
  causa raíz real y el fix es correcto.
- **La migración desenmascaró 2 problemas preexistentes distintos**, antes
  ocultos detrás del `NoReverseMatch` que moría antes de llegar a ellos:
  (a) varios tests pasan `self.f.id` (PK entero) donde el ViewSet espera
  `self.f.uuid` (`lookup_field = "uuid"`) -- 404 real, bug de test
  preexistente; (b) el nombre de URL `workspace` no resuelve vía
  `reverse()` en **ningún** contexto (reproducido incluso fuera de pytest,
  con el código de producción intacto) -- hallazgo real pero **no
  relacionado con `TenantTestCase`/`SintelTenantTestCase`**, afecta a los
  4 archivos de `workspace`.
- `test_naturaleza_import_ubl.py` sigue fallando 5/5 exactamente como
  F27-004 predijo (causas #1 y #3, no relacionadas con el `reverse()` que
  sí se corrigió).

**No se investigó más profundo ni se corrigió ninguno de estos 2 hallazgos
nuevos** por indicación explícita del usuario de no seguir invirtiendo
tiempo en la suite de facturas en esta sesión -- documentados con evidencia
completa para una fase dedicada futura.

## F27 baseline (referencia, no re-ejecutado completo)

```
31 failed, 110 passed, 4 skipped in 3771.39s (1:02:51)
```
Corresponde a los 30 archivos completos de `apps/tenant/facturas/tests/`;
la corrida de F28 (arriba) cubre solo 13 de esos 30 archivos (los tocados
por la migración) más 3 fuera de `facturas` (`tests/tenant/core/`), así que
los números no son directamente comparables 1:1 -- no se afirma que F28
"mejoró" o "empeoró" el número global de 31, solo se documenta el resultado
real y honesto del subconjunto verificado.
