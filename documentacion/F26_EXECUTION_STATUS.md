# F26 — Estado de Ejecución

**Fecha inicio:** 2026-08-10 · **Fecha cierre:** 2026-08-10
**Commit inicial:** `b022cb8` (branch `feat/onboarding-cookie`)
**Baseline documental:** Arquitectura General SINTEL ERP v3.27.0, DOC-M14.
**Estado F21-F25/DOC-M14 al iniciar:** COMPLETED, governance PASS, 64/64 en la
última regresión consolidada (ver `documentacion/F23_TEST_MATRIX.md` y commits
`b141d91`..`b022cb8`).

## Baseline técnico (F26.0)

```
git status --short   -> arbol de trabajo con cambios preexistentes NO relacionados
                         (mismo criterio de todas las fases previas)
manage.py check                             -> System check identified no issues
manage.py makemigrations --check --dry-run  -> No changes detected (antes de F26)
governance --report                         -> FINAL STATUS: PASS
```

Suite completa de `apps/tenant/facturas/tests/` (32 archivos) ejecutada como
baseline real: **94 failed, 45 passed, 4 skipped** en 61:15 -- muy por encima de los
"~18 tests históricos" documentados. Investigación posterior (ver
`F26_TEST_REPORT.md`) determinó que la mayoría de esos 94 fallos son producto de
contaminación de schema `"test"` compartido entre archivos que usan
`django_tenants.test.cases.TenantTestCase` directamente, no defectos reales de
`facturas` -- los 18 tests históricos originales siguen siendo el conjunto real
investigado a fondo en esta fase.

## Estados por sub-fase

| Fase | Estado | Evidencia |
|---|---|---|
| F26.0 Baseline | COMPLETED | Este documento |
| F26.1 Inventario facturas | COMPLETED | `F26_FACTURAS_FIELD_INVENTORY.md` |
| F26.2-3 Auditoría 18 fail + reproducción | COMPLETED | `F26_FINDINGS.md` Parte 1 |
| F26.4 Auditoría XML | COMPLETED | `F26_XML_DATA_POLICY.md`, `F26_XML_CONTRACT.md` |
| F26.5 Perfil de memoria | COMPLETED (cualitativo, sin medición instrumentada -- ver nota) | `F26_XML_DATA_POLICY.md` (107 elementos XML vs ~56 campos persistidos, muestra real) |
| F26.6 Auditoría modelos | COMPLETED | `F26_FACTURAS_FIELD_INVENTORY.md` |
| F26.7 Factura | COMPLETED, sin cambios estructurales necesarios | `F26_REFACTOR_REPORT.md` |
| F26.8 Nota Crédito | COMPLETED, DOC-M14 intacto | `F26_REGRESSION_REPORT.md` |
| F26.9 Inventario | COMPLETED, `ENTRADA_DEVOLUCION` intacto | `F26_REGRESSION_REPORT.md` |
| F26.10 Contabilidad | COMPLETED, Pull Model sin cambios | confirmado por lectura, sin nuevos imports |
| F26.11 DIAN | COMPLETED | `F26_XML_CONTRACT.md` |
| F26.12 Ingesta correo | COMPLETED (auditoría, sin cambios -- `MailIngestionRun`/`MailInboxState` sin duplicación real encontrada) | `F26_FACTURAS_FIELD_INVENTORY.md` |
| F26.13 Anexos | COMPLETED | `F26_FACTURAS_FIELD_INVENTORY.md` (`FacturaAnexos` KEEP) |
| F26.14 Impuestos | COMPLETED | `F26_FACTURAS_FIELD_INVENTORY.md` (`FacturaImpuesto` KEEP) |
| F26.15 Selectors | COMPLETED, sin cambios necesarios | `F26_REFACTOR_REPORT.md` §2 |
| F26.16 Service Layer | COMPLETED, confirmado intacto | `F26_REFACTOR_REPORT.md` §3 |
| F26.17 API | COMPLETED, sin endpoints muertos encontrados en el alcance auditado | — |
| F26.18 Frontend | COMPLETED (auditoría ligera, sin cambios -- fuera de riesgo dado que no se tocó ningún contrato de API/campo consumido por JS) | — |
| F26.19 Tabulator | N/A -- sin cambios de grilla en este pase (regla explícita de no migrar en F26) | — |
| F26.20-29 Idempotencia/atomicidad/multi-tenant/NC/organizacional | COMPLETED | `F26_REGRESSION_REPORT.md` (DOC-M14 + F21-F25 reconfirmados) |
| F26.30-32 Tests/tests obsoletos/cobertura | COMPLETED | `F26_TEST_REPORT.md` |
| F26.33 Performance | COMPLETED (cualitativo) | `F26_XML_DATA_POLICY.md` |
| F26.34 Datos históricos | COMPLETED | `F26_FINDINGS.md` F26-002 (0 filas verificadas antes de eliminar campo) |
| F26.35 Backward compatibility | COMPLETED | Migración aditiva/remove-only, sin romper facturas/NC existentes |
| F26.36-39 Regresión DOC-M14/F21-F25/facturas/global | COMPLETED | `F26_REGRESSION_REPORT.md` |
| F26.40 Governance | COMPLETED | `FINAL STATUS: PASS` |
| F26.41 Dependency Graph | COMPLETED, sin cambios (0 imports nuevos entre apps) | — |
| F26.42 Knowledge Graph | COMPLETED -- NO CAMBIO DE GRAFO (sin modelos/servicios/dependencias nuevas, solo 1 campo eliminado) | — |
| F26.43 Git | COMPLETED | commits en lotes lógicos |
| F26.44 Migraciones | COMPLETED | `0032_remove_factura_xml_file_path.py`, aplicada a 3 empresas |
| F26.45 Documentación | COMPLETED | 9 documentos + sync `arquitectura_general.md` |

## Migraciones

**1 nueva:** `0032_remove_factura_xml_file_path.py` (RemoveField, verificada segura:
0 consumidores + 0 datos históricos en las 3 empresas del entorno antes de aplicar).

## Knowledge Graph / Dependency Graph

**NO CAMBIO DE GRAFO.** F26 no agrega modelos, servicios ni dependencias nuevas
entre apps -- es una auditoría y simplificación quirúrgica dentro de `facturas`.
