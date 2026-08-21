# Nómina — Flujo Empresarial (FASE 28)

**Fecha:** 2026-08-21. **Estado:** `UX_ACCESS... ` no aplica aquí — este es
el estado formal de esta misión: **`NOMINA_CORE = COMPLETED_WITH_DEFERRED`**.

Complementa `NOMINA_BASELINE.md` (FASE 0, qué existía antes de este
cambio) con el diseño final implementado y las decisiones tomadas.

---

## 1. Flujo implementado

```
PeriodoNomina (ABIERTO)
        |
        |  POST /periodos-nomina/{uuid}/preliquidar/
        |  -> por cada empleado elegible (contrato activo, sin
        |     devengo solapado): DevengoBusinessService.procesar_devengo()
        |     -- el motor de calculo YA EXISTENTE, sin cambios.
        v
PeriodoNomina (PRELIQUIDADO)  ---- Devengo x N (uno por empleado, inmutable)
        |
        |  POST .../enviar-revision/
        v
PeriodoNomina (EN_REVISION)  ---- GET .../resumen/ (totales + lista)
        |
        |  POST .../aprobar/  [SOLO ADMIN]
        v
PeriodoNomina (APROBADO)
        |
        |  POST .../marcar-pagado/  [SOLO ADMIN]
        |  (registro MANUAL -- sin integracion bancaria real, ver §4)
        v
PeriodoNomina (PAGADO)
        |
        |  POST .../cerrar/  [SOLO ADMIN]
        v
PeriodoNomina (CERRADO)
```

Excepciones: `ANULADO` (desde cualquier estado antes de PAGADO, anula en
cascada los `Devengo` del período vía `DevengoBusinessService.anular_devengo`
ya existente) y `BLOQUEADO` (pausa reversible con `desbloquear_periodo()`).

---

## 2. Entidades

| Entidad | Rol | Cambió en esta fase |
|---|---|---|
| `Empleado` | Identidad laboral | No |
| `Contrato` | Términos vigentes | No |
| `Devengo` | Cálculo individual, inmutable | Solo se agregó `periodo` FK (nullable) |
| `PeriodoNomina` | **Nuevo** — orquesta el lote y la aprobación | Creado |
| `ResolucionDIAN` / `TransmisionNominaDIAN` | Numeración DIAN | No (DEUDA-11 sigue abierta, ver §5) |
| `LiquidacionPrestacion` | Prestaciones sociales / retiro | No |

`PeriodoNomina` **nunca calcula montos** — siempre delega a
`procesar_devengo()`. Esto significa que las fórmulas, factores y reglas
laborales documentadas en `NOMINA_BASELINE.md` §3 siguen siendo exactamente
las mismas; esta fase no las tocó.

---

## 3. Reglas de negocio implementadas (con evidencia, no inventadas)

- **Un solo período activo por empresa+mes**: constraint de base de datos
  (`uniq_periodo_nomina_activo_per_empresa_mes`), no solo validación en
  Python — no se puede burlar con una llamada concurrente.
- **Transiciones de estado validadas en backend**, no solo en UI
  (`PeriodoNominaBusinessService.TRANSICIONES_VALIDAS`, única fuente de
  verdad) — confirmado con prueba real: intentar `PAGADO` desde
  `EN_REVISION` devuelve error explícito, no se ejecuta silenciosamente.
- **Backend es la autoridad de permisos**, no la UI (Regla Absoluta #3 de
  la misión) — confirmado con prueba real vía HTTP: usuario con rol
  `VISOR` recibe `403` al intentar `preliquidar`; usuario `OPERADOR` recibe
  `403` al intentar `aprobar`.
- **Preliquidación no es todo-o-nada**: cada empleado se procesa en su
  propia transacción atómica independiente — si un empleado falla (ej. sin
  contrato, límite de días excedido, sin resolución DIAN vigente para su
  fecha de pago), el resto de la empresa sigue preliquidándose. El período
  solo permanece en `ABIERTO` si **ningún** empleado pudo procesarse.
- **Inmutabilidad de `Devengo` sin cambios**: sigue devolviendo `405` en
  `update`/`partial_update`. Corregir un devengo puntual dentro de un
  período preliquidado usa el mismo patrón ya existente (anular + crear
  uno nuevo), ahora simplemente vinculado al mismo `periodo`.

---

## 4. Supuestos documentados (sin evidencia normativa confirmada — Regla Crítica de la misión)

Estos son decisiones de diseño razonables tomadas para poder entregar el
núcleo, **no verificadas contra un proceso de negocio real confirmado por
el usuario**. Si alguno no coincide con la operación real de la empresa,
son los primeros puntos a ajustar:

1. **Sin modelo `Novedad` separado.** La preliquidación genera el devengo
   BASE (salario proporcional + auxilio + deducciones de ley, sin horas
   extras/préstamos/descuentos). Si un empleado específico tuvo horas
   extras u otras novedades reales ese período, se corrige con el flujo ya
   existente (crear/anular un devengo individual) — el formulario
   individual de creación de devengo (`offcanvas_crear_devengo.html`,
   sin cambios en esta fase) ya captura esos campos uno por uno.
2. **"Marcar pagado" es un registro manual**, no una transferencia real.
   No existe hoy integración con `bancos` para nómina — `fecha_pago_real`
   y `pagado_por` solo documentan que alguien marcó el período como
   pagado, sin mover dinero ni validar contra un saldo real.
3. **`aprobado_por`/`pagado_por`/`creado_por` usan `SET_NULL`** al eliminar
   el perfil que aprobó/pagó/creó — prioriza no bloquear la eliminación de
   perfiles sobre preservar la atribución exacta. Si la política contable
   real exige preservar siempre quién aprobó cada pago de nómina
   (aunque su perfil de usuario se elimine después), este campo debería
   ser `PROTECT` en vez de `SET_NULL` — cambio de una línea si se
   confirma que es necesario.
4. **8 estados del período** (los que propuso la misión textualmente) se
   implementaron todos como opciones válidas, pero solo 6 transiciones
   tienen una acción real de negocio detrás (`preliquidar`,
   `enviar-revision`, `rechazar-revision`, `aprobar`, `marcar-pagado`,
   `cerrar`) más las 2 de excepción (`anular`, `bloquear`/`desbloquear`).
   Ninguna transición es automática por tiempo/cron — todas requieren una
   llamada explícita a la API.

---

## 5. Deliberadamente NO construido en esta fase (BLOCKED_SAFE)

| Ítem | Por qué no se construyó | Qué se necesitaría para desbloquear |
|---|---|---|
| **XML UBL 2.1 de nómina electrónica DIAN** | Bloqueador normativo real (Resolución 000013/2021 y anexos técnicos) — generar/firmar un documento fiscal incorrecto tiene consecuencias regulatorias reales, no es un bug de software común. `TransmisionNominaDIAN.estado_dian` sigue reflejando honestamente `PENDIENTE` (nunca se marca como enviado sin haberlo hecho — la Regla Crítica DIAN de la misión ya se cumplía antes de este cambio y sigue cumpliéndose). | Especificación técnica DIAN verificada + decisión de negocio sobre proveedor/mecanismo de firma digital. |
| **PILA / seguridad social** | No existe ninguna infraestructura previa ni caso de uso confirmado — construir algo aquí sería exactamente la "infraestructura especulativa" que este proyecto evita consistentemente (mismo criterio aplicado por la misión OCF/OSF anterior). | Confirmación del usuario de que se necesita, más el operador/formato real de integración (¿API de un PILA provider? ¿archivo plano?). |
| **Integración bancaria real para pago de nómina** | Mismo criterio — no existe hoy, "marcar pagado" es un registro manual honesto en vez de una integración fingida. | Confirmar con el usuario si `apps/tenant/bancos` ya tiene algo reutilizable para esto (no auditado a fondo en esta pasada) antes de diseñar nada nuevo. |
| **Modelo `Novedad` separado del `Devengo`** | Separar "hecho" de "resultado calculado" (FASE 6 de la misión) es un cambio real al contrato de `procesar_devengo()` — mayor riesgo sobre el motor de cálculo ya probado, sin un caso de uso de UI confirmado para justificarlo en esta pasada. | Confirmar con el usuario el flujo de captura de novedades deseado (¿un formulario por empleado antes de preliquidar? ¿carga masiva?). |

**Frontend de `PeriodoNomina` — ya NO diferido**, construido en el
incremento siguiente (mismo día): nuevo sub-tab "Períodos de Nómina" en
`empleados_list.html` (django-tables2 + HTMX, patrón Fase 5-BIS, igual que
Resoluciones DIAN), offcanvas de creación, y un offcanvas de
detalle/gestión que consume `GET .../resumen/` y ofrece solo las acciones
válidas para el estado actual del período (preliquidar / enviar a revisión
/ rechazar / aprobar / marcar pagado / cerrar / anular / bloquear /
desbloquear) — la UI es una guía de UX, la autoridad real de qué transición
se permite sigue siendo el backend (`TRANSICIONES_VALIDAS` +
`HasTenantRole`). Verificado end-to-end vía Django test Client con
rollback: render de la página, tabla vacía y poblada, formulario de
creación, creación real, resumen, y una acción de transición ejecutada
contra datos reales.

---

## 6. Verificación realizada

- `manage.py check`: 0 issues.
- `makemigrations --check --dry-run`: sin cambios pendientes (migración
  0014 ya generada y aplicada a los 3 schemas de tenant).
- Flujo completo end-to-end vía HTTP real (Django test Client, con
  rollback — sin dejar datos de prueba): crear → preliquidar → resumen →
  enviar-revisión → aprobar → marcar-pagado → listar. Montos verificados
  correctos (3.000.000 devengado, 240.000 deducciones = 4%+4% de ley,
  2.760.000 neto).
- Transición de estado inválida rechazada correctamente con mensaje
  explícito.
- Permisos por rol verificados con datos reales (no solo leyendo código):
  `VISOR` → `403` en `preliquidar`; `OPERADOR` → `403` en `aprobar`.
- No se ejecutó la suite de tests completa (regla explícita de la misión,
  FASE 26: "no ejecutar otra ronda global de testing").

---

## 7. Estado formal

**`NOMINA_CORE = COMPLETED_WITH_DEFERRED`**

Núcleo (`PeriodoNomina` + máquina de estados + preliquidación en lote +
permisos por rol) completo y verificado. Diferido explícitamente: DIAN XML
real, PILA, integración bancaria real, modelo `Novedad` separado, y el
frontend — todos documentados en §5 con lo que se necesitaría para
desbloquear cada uno, no simplemente marcados "pendiente" sin contexto.
