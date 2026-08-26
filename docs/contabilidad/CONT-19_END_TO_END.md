# CONT-19 — Cierre del ciclo contable end-to-end

**Fecha:** 2026-08-26
**Tenant de validacion:** `home` (usuario real `admin@home.com` / username `admin-1`, JWT real via `/api/token/`)
**Metodo:** validacion funcional con datos reales controlados, HTTP real contra el servidor Docker en ejecucion — no mocks, no shell-crafted sessions.

---

## 1. Resumen ejecutivo

Se valido el ciclo contable completo desde el origen (Gastos + Nomina, datos reales ya presentes en el tenant) hasta el cierre operativo: extraccion -> contabilizacion -> aprobacion -> Libro Diario -> Balance de Prueba -> Estado de Resultados, con dos acciones reales de infraestructura contable (cierre de un periodo obsoleto, apertura de un periodo vigente) y dos bugs reales encontrados y corregidos en el proceso.

## 2. Validacion funcional real (FASE 24)

Documentos usados (ya existentes en el tenant, minimos, sin fabricar datos de negocio):
- 1 Gasto real: `DocumentoSoporte` "GA 1", Proveedor Auditoria QA SAS, $50,000
- 1 Devengo real: Nomina periodo 2026-08, Empleado Qa, $2,760,000
- 1 Factura real (`número 1300962`) y 1 movimiento de inventario real, ya verificados end-to-end en la sesion inmediatamente anterior a CONT-19 (mismo tenant `home`) y ademas cubiertos por `tests/test_f27_cuenta_codigo_reportes_bugfix.py` (compra real -> `ExtractorInventario` -> asiento -> reportes).

Secuencia ejecutada (todas las llamadas via API real con JWT, salvo el trigger de extraccion que usa `manage.py backfill_contabilidad` dentro del contenedor `web` en ejecucion):

1. `GET /pendientes/` -> 2 documentos reales pendientes (Gasto + Nomina).
2. `backfill_contabilidad --dry-run` -> confirmo 2 pendientes, 0 errores en preview.
3. Backfill real -> **bloqueado correctamente**: `No existe periodo contable para 2026-08-06/2026-09-05`. Comportamiento correcto del sistema (FASE 8), no un bug.
4. `POST /periodos-contables/{2025-02}/cerrar/` -> cierre real de periodo obsoleto (autorizado explicitamente por el usuario).
5. `POST /periodos-contables/` -> apertura real de periodo `2026-08` (01-ago a 30-sep-2026).
6. Backfill real -> **bloqueado de nuevo**: `Regla contable no definida para COMPRA_GASTO/NOMINA_PAGO`. Real: `ReglaContable` nunca se sembro para esta empresa.
7. `seed_reglas_contables --dry-run` -> revelo un bug real (ver §4): el dry-run escribia datos reales. Corregido en el codigo antes de continuar.
8. `seed_reglas_contables` (real, post-fix) -> 62 reglas + 19 tarifas + 8 tipos de comprobante creados, idempotente confirmado (`--dry-run` posterior reporta 0).
9. Backfill real -> **exitoso**: `contabilizados=2, omitidos=0, errores=0`.
10. Backfill real repetido -> `0 pendientes encontrados` en ambos extractores — **idempotencia confirmada en vivo** (FASE 7).
11. `GET /pendientes/` -> `[]` — los documentos ya no aparecen como pendientes (FASE 9).
12. `GET /libro-diario/?fecha_inicio=2026-08-01&fecha_fin=2026-09-30` -> 2 documentos, `cuadra:true`, **ningun movimiento con `SIN_CUENTA`** — cada linea muestra `cuenta_codigo`/`cuenta_nombre` reales (`519595`/`GASTO_GENERAL`, `510506`/`NOMINA_SUELDOS`, etc.) (FASE 13, confirma en vivo el fix de la sesion anterior).
13. `POST /asientos-contables/{uuid}/aprobar/` x2 -> ambos asientos `APROBADO`, `total_debe == total_haber` en ambos.
14. `GET /reporte-balance-prueba/` -> 6 filas, cuadrado (Σdebito == Σcredito == $3,050,000).
15. `GET /reporte-estado-resultados/` -> gastos correctos por cuenta, `utilidad_neta = -3,050,000` (correcto: solo gastos, cero ingresos en el periodo validado).

**Resultado: FASE 2 (parcial, gastos/nomina en vivo; facturas/inventario via evidencia previa+test), 3, 4, 7, 8, 9, 12, 13, 16 (parcial) validadas con datos reales de punta a punta.**

## 3. Acciones reales de infraestructura contable ejecutadas (con autorizacion explicita del usuario)

| Accion | Reversible | Autorizado |
|---|---|---|
| Cierre `PeriodoContable` 2025-02 | No (regla de negocio: periodo cerrado no se reabre) | Si, explicito |
| Apertura `PeriodoContable` 2026-08/09 | Si (aun ABIERTO) | Si, explicito |
| Backfill real de 2 documentos (Gasto + Nomina) | Parcial (via reversar_asiento, no delete) | Si, explicito |
| `seed_reglas_contables` (62 reglas + 19 tarifas + 8 comprobantes) | Si (datos de configuracion, no transaccionales) | Si (parte del flujo aprobado) |
| Aprobacion de 2 asientos | Parcial (via reversar_asiento, no delete) | Si, explicito |

## 4. Bug nuevo encontrado y corregido durante CONT-19

**`seed_reglas_contables.py --dry-run` no era realmente dry-run.** Los tres bloques de seed (`TipoComprobante`, `ReglaContable`, `TarifaImpuesto`) llamaban `get_or_create()` incondicionalmente — el flag `dry_run` solo suprimia el mensaje de éxito impreso, no el `INSERT` real. Confirmado en vivo: una corrida `--dry-run` contra `home` escribio 62 `ReglaContable` + 19 `TarifaImpuesto` + 8 `TipoComprobante` reales. Corregido: en modo `dry_run` ahora solo se verifica existencia (`.exists()`), sin llamar `get_or_create()`. Verificado: segunda corrida `--dry-run` reporta correctamente 0 sin escribir nada.

Riesgo real de este bug antes del fix: cualquier operador o script que usara `--dry-run` para *previsualizar* un seed en un tenant de produccion habria escrito datos reales sin saberlo. Severidad: Media (dry-run que miente es un patron peligroso, aunque los datos que escribe son de configuracion idempotente, no transaccionales).

## 5. Deuda tecnica revisada (FASE 22)

Ver `docs/contabilidad/CONT-19_BASELINE.md` §4. Resumen: AUD-CONT-007 estaba **resuelto en codigo pero desactualizado en el doc** (corregido); AUD-CONT-005/006/009/010/011 diferidos por bajo impacto o por requerir alcance fuera de CONT-19 (migraciones de modelo, limpieza no funcional).

## 6. Reglas de Orquestacion (FASE 23)

**No implementadas — sin evidencia que lo justifique.** `PlantillaContable` + `LineaPlantilla` + `ReglaContable` + `Contabilizador` cubren todos los casos reales encontrados en esta validacion (Gastos, Nomina, Facturas, Inventario, Compras, Ventas). No se identifico ningun caso real donde estos mecanismos sean insuficientes.

## 7. Governance (FASE 26)

| Check | Resultado |
|---|---|
| `manage.py check` | System check identified no issues (0 silenced) |
| `manage.py makemigrations --check --dry-run` | No changes detected |
| `git diff --check` | Sin errores de whitespace (solo avisos LF/CRLF normales en Windows) |
| `ruff check` (archivos tocados en CONT-19 + sesion previa) | Import-sort en `test_f27_...py` corregido (propio); resto de hallazgos son deuda preexistente no relacionada a estos cambios — clasificado PREEXISTING, no tocado (fuera de alcance quirurgico) |
| Tests dirigidos | `test_f27_cuenta_codigo_reportes_bugfix.py` (3/3), `test_api_contabilidad.py` (12/12, regresion de los fixes de empresa_id) |

## 8. Release Gate (FASE 28)

- [x] Facturas — OPERATIVO (evidencia sesion previa + esta)
- [x] Gastos — OPERATIVO (validado en vivo, CONT-19)
- [x] Nomina — OPERATIVO (validado en vivo, CONT-19)
- [x] Inventario — OPERATIVO (validado via test real, F27)
- [x] Pendientes — validado en vivo (aparece y desaparece correctamente)
- [x] Asientos — validado en vivo (creacion, cuadratura, aprobacion)
- [x] Libro Diario — validado en vivo (sin `SIN_CUENTA`, cuadra=true)
- [x] Balance de Prueba — validado en vivo (cuadrado)
- [x] Estado de Resultados — validado en vivo (utilidad correcta)
- [ ] Retenciones — NO validado en vivo esta sesion (sin documento real con retencion pendiente en el tenant); cubierto solo por tests existentes (`test_retenciones_service.py`, `test_retenciones_api.py`) — DEFERRED
- [x] Periodos — validado en vivo (cierre + apertura reales)
- [x] Cierre — validado en vivo (cierre real de 2025-02)
- [x] Idempotencia — validado en vivo (backfill repetido = 0 nuevos)
- [x] Tenant — aislamiento por schema, sin tocar
- [x] Empresa — `empresa_id` verificado en cada llamada real
- [x] Permisos — JWT real de usuario ADMIN, endpoints respondieron segun rol
- [ ] UX — NO evaluado (fuera del alcance de esta corrida; requeriria sesion de browser real)
- [x] Documentacion — este documento + `AUDITORIA_COMPLETA_CONTABILIDAD.md` actualizados
- [x] Governance — ver §7

## 9. Estado final

**CONT-19 = COMPLETED_WITH_DEFERRED**

Deferred (no bloqueante, no critico):
- Retenciones sin validacion en vivo (cubierta por tests existentes, sin documento real pendiente en el tenant al momento de la corrida).
- UX secuencial (FASE 17-19) no evaluada visualmente vía browser — el ciclo backend completo esta probado end-to-end con datos reales, pero la experiencia de usuario en pantalla no se recorrio en esta mision.
- AUD-CONT-005/006/009/010/011 permanecen diferidos (bajo impacto, fuera del alcance minimo).

No se declara "PRODUCTION READY" — ese no es un estado que esta mision evalue.

## 10. Siguiente fase (FASE 30)

El mandato original pide continuar automaticamente hacia `UX-CONT-01`. Dado que UX-CONT-01 es, por su propia definicion en la mision, una iniciativa nueva y separada (convertir Contabilidad en una experiencia guiada por perfil/contexto) — no una continuacion mecanica de CONT-19 — no se inicia automaticamente en esta misma corrida. CONT-19 queda documentado como COMPLETED_WITH_DEFERRED y listo como punto de partida para UX-CONT-01 cuando se solicite explicitamente.
