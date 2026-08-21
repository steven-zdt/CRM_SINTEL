# Nómina — Baseline (FASE 0 de la misión de evolución del ciclo empresarial)

**Fecha:** 2026-08-21. **Fase:** 0 (Baseline). **Estado del código: sin
modificar** — este documento es 100% lectura y análisis, tal como exige la
FASE 0 de la misión.

**Fuentes leídas:** `apps/tenant/empleados/.agent/AUDITORIA_FLUJO_EMPLEADOS.md`
(v4.8.1, PRODUCTION READY, 23/23 compliance AGENTS.md), código real de
`models.py`, `services/selectors.py`, `services/business_service.py`,
`api/viewsets.py`, `apps/tenant/contabilidad/integracion/extractores/nomina.py`.

---

## 0. Veredicto adelantado (para no enterrar el hallazgo más importante)

El sistema actual de nómina **no tiene la forma que pide esta misión** —
no por estar mal construido, sino por una decisión de diseño consciente y
ya probada: **cada `Devengo` se calcula y persiste de forma atómica e
inmediata, por empleado, en un solo paso** (`procesar_devengo()`), sin
ningún concepto de "período" como entidad que agrupe varios empleados, sin
etapas de preliquidación/revisión/aprobación separadas, y sin separación
entre "novedad" (hecho) y "devengo" (resultado) — los hechos (horas
extras, recargos) se capturan como campos directos del propio `Devengo`.

Pasar al flujo objetivo de la misión (`Período → Novedades →
Preliquidación → Revisión → Aprobación → Pago → DIAN → PILA → Contabilidad
→ Cierre`) **no es una evolución incremental — es un rediseño real** que
requiere crear al menos 1-2 modelos nuevos genuinamente inexistentes hoy
(`PeriodoNomina` como mínimo; `Novedad` si se decide separarla de
`Devengo`), más una máquina de estados de aprobación que hoy no existe en
ningún lugar del dominio. Esto no viola la Regla Principal ("no crear
arquitectura nueva sin demostrar que la existente no resuelve la
necesidad") — **la demostración ya está hecha** (ver §2): no existe hoy
ninguna entidad que pueda representar un período/lote/proceso de nómina.
El resto de este documento detalla exactamente qué existe y qué no, para
que la fase de diseño (FASE 2+) parta de evidencia, no de suposición.

---

## 1. Modelos existentes (6, confirmados por lectura directa de `models.py`)

| Modelo | Rol actual | Inmutable | Estados |
|---|---|---|---|
| `Empleado` | Identidad + datos laborales/EPS/AFP/ARL | No | `ACTIVO` / `RETIRADO` |
| `Contrato` | Términos laborales vigentes | No (salvo mientras ACTIVO) | `ACTIVO` / `INACTIVO` / `HISTORICO`. Constraint: máx. 1 `ACTIVO` por empleado (`uniq_contrato_activo_per_empleado`) |
| `Devengo` | **Resultado calculado de nómina de UN empleado en UN período**, creado y persistido en un solo paso atómico | **Sí** — `update()`/`partial_update()` → HTTP 405, solo `crear`/`anular` | `anulado` (bool, no una máquina de estados) |
| `ResolucionDIAN` | Rango de numeración autorizado para nómina electrónica | No | `vigente` (bool) |
| `TransmisionNominaDIAN` | 1:1 con `Devengo` — metadatos del documento DIAN | Parcial (campos XML nullable, nunca poblados hoy) | `estado_dian`: `PENDIENTE` / `ACEPTADO` / `RECHAZADO` (**solo 3 estados, no los 6 que pide la misión**) |
| `LiquidacionPrestacion` | Prima/Cesantías/Intereses/Vacaciones/Liquidación definitiva — INDEPENDIENTE de `Devengo` | No | `PROYECTADO` / `PAGADO` |

**No existen:** `PeriodoNomina`, `Novedad`, `Pago` (ni genérico ni
específico de nómina), ningún modelo de integración PILA/seguridad social.
Confirmado por grep exhaustivo de `class Pago\b|class PeriodoNomina\b|class
Novedad\b` en todos los `models.py` del proyecto — 0 resultados.

---

## 2. FASE 1/2 — Mapa del dominio actual vs. lo que pide la misión

| Pieza del flujo objetivo | ¿Existe ya? | Dónde / Cómo se ve hoy |
|---|---|---|
| `Empleado` | ✅ Completo | `Empleado`, con `sede`/`area` FK (nullable), `resolucion_dian` FK preferida |
| `Contrato ACTIVO` | ✅ Completo | `Contrato`, constraint DB de 1 solo activo, `ContratoBusinessService.gestionar_contrato()` desactiva el anterior automáticamente |
| `Período de nómina` (como entidad) | ❌ **No existe** | `Devengo.periodo_mes` es un `CharField` libre (`"YYYY-MM"`) en CADA devengo individual — no hay una fila/entidad que agrupe "todos los devengos de agosto 2026" con su propio estado |
| `Novedades` (hecho, separado del cálculo) | ❌ **No existe como entidad separada** | Los "hechos" (horas extras diurnas/nocturnas, recargos, préstamos, descuentos operativos) son **campos directos del formulario de creación de `Devengo`** — se capturan y calculan en el mismo paso, no hay una tabla `Novedad` previa que el motor de cálculo consuma después |
| `Preliquidación` (calcular sin comprometer) | ⚠️ Parcial | Existe `POST /devengos/preview-calculo/` — calcula y muestra el resultado SIN persistir. Es "preliquidación de 1 empleado a la vez", no de un período completo con N empleados en un solo lote revisable |
| `Revisión` (vista agregada de un lote antes de aprobar) | ❌ No existe | No hay pantalla ni endpoint "nómina de agosto: 42 empleados, total devengado X, total neto Y" — cada devengo se ve individualmente |
| `Aprobación` (paso explícito, separado de calcular) | ❌ No existe | `procesar_devengo()` calcula Y persiste en la misma llamada — no hay un estado intermedio "calculado pero no aprobado" |
| `Pago` (como proceso, con registro de ejecución) | ❌ No existe para nómina específicamente | `LiquidacionPrestacion.estado` tiene `PAGADO`, pero es solo un flag, sin fecha/referencia/cuenta/usuario de ejecución. `Devengo` no tiene ningún campo de estado de pago en absoluto (se asume pagado al crearse, dado que `fecha_pago` es un campo obligatorio desde el inicio) |
| `Nómina electrónica DIAN` | ⚠️ Parcial, deuda técnica abierta y documentada (**DEUDA-11**) | `TransmisionNominaDIAN` existe con CUNE (SHA-256) y consecutivo DIAN correctamente atómicos (`select_for_update()`), pero **XML UBL 2.1 nunca se genera** — `xml_enviado`/`xml_respuesta` quedan `NULL` para siempre, `estado_dian` queda en `PENDIENTE` indefinidamente. Esto es exactamente lo que la Regla Crítica DIAN de esta misión advierte: "no considerar enviada simplemente porque exista el registro" — **ya se respeta correctamente hoy**, el estado real SÍ refleja que nunca se transmitió. |
| `Seguridad social / PILA` | ❌ No existe en absoluto | Ni modelo, ni servicio, ni integración, ni mención en ningún archivo del proyecto (grep de "PILA"/"planilla"/"SeguridadSocial": 0 resultados relevantes) |
| `Contabilidad` (Pull Model) | ✅ Completo y correcto | `ExtractorNomina.extraer_pendientes()` (verificado leyendo el código real) extrae cada `Devengo` no anulado y no contabilizado — Empleados nunca importa Contabilidad, el contrato se respeta al 100% |
| `Cierre` (de período o laboral) | ❌ No existe concepto de "cierre" — ni de período (no hay período) ni laboral explícito más allá de `Empleado.estado=RETIRADO` |
| **RETIRO → Liquidación definitiva → Cierre laboral** | ⚠️ Parcial | `Empleado.estado=RETIRADO` + `fecha_retiro` existen; `actualizar_empleado()` cancela contratos activos automáticamente al retirar. `LiquidacionPrestacion` con `tipo_liquidacion=LIQUIDACION_DEFINITIVA` existe y calcula. **Falta:** un flujo guiado/orquestado que conecte "marcar retirado" → "calcular liquidación definitiva" → "pagar" → "cerrar" como pasos explícitos con estado — hoy son 2-3 acciones manuales independientes que un usuario debe saber encadenar por su cuenta |

---

## 3. Motor de cálculo real (`NominaCalculationService`) — NO tocar sin evidencia normativa

Verificado en `business_service.py` (no se modifica en esta fase, solo se
documenta):

- Salario proporcional: `dias_laborados / 30`.
- Auxilio de transporte: 0 si `Contrato.tipo == PRESTACION`.
- Horas extras: factores Decreto 2663/1950 (diurna +25%, nocturna +75%,
  recargo nocturno ordinario +35%, recargo festivo +75%). Máximo 80h por
  tipo, 200h total (Ley 2101/2021, semana de 42h).
- Deducciones de ley: Salud 4% + Pensión 4% del IBC — **0 si
  `Contrato.tipo == PRESTACION`** (un contrato de prestación de servicios
  no tiene deducciones de nómina por ley, es correcto).
- `calcular_dias_360()`: estándar 30/360 europeo, `d2=31→30`
  incondicional — corregido en v4.5.1 (bug histórico ya cerrado, con
  impacto financiero documentado de ~$6.000 COP/empleado/período antes del
  fix).
- Prestaciones (Prima/Cesantías/Intereses 12%/Vacaciones): también
  retornan 0 para `PRESTACION`.

**Ninguna fórmula se toca en esta fase ni se tocará sin evidencia concreta
de un error, tal como exige la Regla Crítica de esta misión.**

---

## 4. Integraciones (matriz mínima pedida por FASE 24, adelantada aquí)

| Origen | Destino | Contrato | Dirección | Estado |
|---|---|---|---|---|
| Perfil | Empleados | Ninguno hoy — `Empleado` no tiene FK a `TenantProfile`/`User` | N/A | Sin integración directa (un Empleado es un dato laboral, no necesariamente un usuario del sistema) |
| Empresa | Empleados | `Empleado.empresa` FK (PROTECT) | Empleados → Empresa | ✅ Completo |
| Empleados | Contabilidad | `ExtractorNomina` (Pull Model) | Contabilidad → Empleados (lee, nunca escribe) | ✅ Completo y correcto |
| Empleados | Bancos | **Ninguna** | N/A | ❌ No existe — `Devengo`/`LiquidacionPrestacion` no referencian ninguna cuenta bancaria ni transacción |
| Empleados | DIAN | `TransmisionNominaDIAN` + `ResolucionDIAN` | Empleados → DIAN (saliente, nunca implementado el envío real) | ⚠️ Infraestructura de numeración/CUNE completa; generación/firma/envío XML: **DEUDA-11, abierta** |
| Empleados | PILA | **Ninguna** | N/A | ❌ No existe |

**Sin dependencias circulares detectadas** — Empleados no importa
Contabilidad ni Bancos ni DIAN (correcto, Empleados es el origen, no el
consumidor).

---

## 5. Deuda técnica ya documentada (no descubierta ahora, heredada de la auditoría v4.8.1)

- **DEUDA-11 (ABIERTA, prioridad MEDIA):** XML UBL 2.1 de nómina
  electrónica no implementado. Infraestructura de numeración lista.
- 3 deudas previas ya CERRADAS (campos `.only()`, `calcular_dias_360()`,
  `create()` completo en `LiquidacionPrestacionViewSet`) — no requieren
  atención.

---

## 6. Conclusión de FASE 0 y recomendación para las fases siguientes

**No hay error en el sistema actual** — es una implementación correcta,
probada (23/23 compliance) y en producción de un modelo de nómina más
simple ("calcular y persistir de inmediato, por empleado") que el modelo
de proceso por lotes con aprobación multi-etapa que esta misión describe
como objetivo. Ambos son diseños legítimos; la pregunta no es cuál es
"correcto" sino si el negocio real necesita el segundo.

**Bloqueadores normativos/de alcance que esta auditoría no puede resolver
por sí sola** (Regla Crítica de esta misión: "si existe duda normativa,
documentar, marcar BLOCKED/REVIEW, no inventar"):

1. **Estructura XML UBL 2.1 de nómina electrónica DIAN real** — implementar
   FASE 14 correctamente requiere la especificación técnica exacta de la
   DIAN (Resolución 000013 de 2021 y sus anexos técnicos), no inventar una
   estructura aproximada. Generar y firmar un documento fiscal incorrecto
   tiene consecuencias regulatorias reales, no solo un bug de software.
2. **Diseño de la máquina de estados de aprobación** (`ABIERTO → ... →
   CERRADO`) — la misión propone una máquina de 9 estados, pero pide
   explícitamente "verificar si ya existen estados equivalentes... no
   duplicar estados" antes de crearla. Ya verificado: no existen. Diseñarla
   bien requiere saber, con el negocio real (no asumido), quién aprueba,
   qué pasa si se rechaza, y si "PAGADO" debe ser automático o manual —
   información que no está en ningún documento del repositorio.
3. **PILA / seguridad social** — la misión explícitamente permite
   "documentar como integración futura" si no existe. Se documenta así:
   **no existe, no se construye especulativamente sin caso de uso
   confirmado** (mismo criterio ya aplicado consistentemente por la
   misión OCF/OSF anterior en este mismo proyecto para casos análogos).

**Recomendación:** dado que (a) el núcleo actual está en producción y es
correcto, (b) el gap real es un rediseño arquitectónico de fondo, no un
ajuste, y (c) el punto de mayor riesgo (DIAN XML real) requiere
información normativa que esta auditoría no tiene forma de verificar de
forma segura, se recomienda **confirmar con el usuario el alcance real
antes de crear `PeriodoNomina` u otros modelos nuevos** — no por
timidez, sino porque construir la arquitectura de período/aprobación
equivocada (sin conocer el proceso real que el negocio quiere seguir)
sería exactamente el tipo de "arquitectura especulativa sin caso de uso
confirmado" que esta misión, y el resto de este proyecto, prohíben
consistentemente.

**Estado formal de esta fase:** 🟢 **FASE 0 COMPLETED.** Cero código
modificado. Ver recomendación arriba para FASE 1-2 (que, dado que ya se
resolvió aquí "no existe nada reutilizable para período/novedad/pago", se
reducen a una decisión de diseño, no de investigación adicional).
