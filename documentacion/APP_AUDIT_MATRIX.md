# APP_AUDIT_MATRIX — Inventario real de `apps/tenant/*`

Construido con inspeccion directa del filesystem (no de documentacion),
2026-08-20. Sirve de FASE 1 para `APP_AUDIT_MASTER_STATUS.md`.

| App | Modelos | Migraciones | Archivos service | tasks.py | Tests (archivos) | JS | Templates |
|---|---|---|---|---|---|---|---|
| bancos | 3 | 5 | 4 | no | 4 | 6 | 9 |
| clientes | 3 | 8 | 5 | no | 9 | 7 | 14 |
| compras | 3 | 8 | 4 | no | 7 | 4 | 8 |
| contabilidad | 13 | 16 | 5 | si | 14 | 25 | 32 |
| core | 2 | 0 | 26 | no | 19 | 18 | 22 |
| cotizaciones | 4 | 5 | 10 | no | 9 | 18 | 13 |
| dashboard | 1 | 3 | 13 | si | 4 | 3 | 5 |
| empleados | 6 | 13 | 4 | no | 12 | 13 | 25 |
| empresa | 4 | 9 | 4 | no | 11 | 9 | 15 |
| facturas | 8 | 33 | 9 | si | 31 | 7 | 8 |
| gastos | 2 | 22 | 4 | no | 11 | 5 | 9 |
| inventario | 1 | 11 | 5 | no | 7 | 15 | 17 |
| perfil | 2 | 8 | 5 | no | 4 | 4 | 8 |
| proveedores | 3 | 18 | 5 | no | 7 | 9 | 10 |
| proyectos | 7 | 20 | 6 | no | 11 | 5 | 7 |
| ventas | 3 | 3 | 4 | no | 5 | 4 | 8 |

**Notas de lectura:**
- `core` tiene 0 migraciones propias (2 modelos, probablemente
  abstractos/soporte -- confirmar en su auditoria; concentra el mayor
  numero de archivos de servicio (26) y tests (19), consistente con
  ser el modulo de infraestructura compartida (middleware, contexto
  organizacional, gateway `_apps/`, endpoint universal de documentos).
- `facturas` tiene el mayor numero de migraciones (33) y archivos de
  test (31) -- la app mas grande, confirmada con 132 tests limpios
  (13 skip documentados) al cierre de F33.15-B Nivel 3.
- `gastos` tiene 22 migraciones para solo 2 modelos -- posible señal
  de iteracion de schema frecuente, revisar en su auditoria (FASE B).
- `dashboard` y `contabilidad` son las unicas 2 apps con `tasks.py`
  (Celery) fuera de `facturas`.
- Conteo de "Modelos" via
  `grep -c "^class .*SintelTenantBaseModel\|^class .*(models.Model)"`
  sobre `models.py` -- puede subcontar si hay modelos definidos fuera
  de `models.py` o via herencia indirecta; se revisa con precision en
  FASE B de cada app.

**Apps fuera del orden de la mision (excluidas del alcance actual,
por decision explicita del usuario -- orden termina en `dashboard`):**
ninguna app de `apps/tenant/` queda fuera del listado de 16.
`apps/tenant/landing/` existe en el filesystem pero no aparece en el
orden de la mision -- se trata como fuera de alcance salvo instruccion
en contrario (tiene tests, `?? apps/tenant/landing/tests/`, sin
trackear, WIP ajeno a esta mision).
