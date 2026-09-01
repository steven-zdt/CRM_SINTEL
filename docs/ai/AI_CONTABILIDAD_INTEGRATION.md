# AI ↔ Asistente Contable — Diseño de integración (AI-03.x, 2026-09-01)

STEP 6 del roadmap de cierre de AI-03 (decisión explícita del usuario,
2026-09-01): documentar el contrato del Asistente Contable **ya
existente en producción** antes de escribir ninguna tool de
`contabilidad` en el AI Engine. La regla que gobierna este documento
(citada literalmente por el usuario): *"AI Engine debe convertirse en
orquestador/contextualizador, mientras el conocimiento y las
operaciones contables siguen siendo responsabilidad del componente
contable existente."*

## 1. El Asistente Contable ya existe -- no es un diseño nuevo

Verificado leyendo código, no es un concepto teórico:
`ContabilidadBusinessService.sugerir_lineas_asiento_ia()`
(`apps/tenant/contabilidad/services/business_service.py:1164-1259`),
expuesto vía `POST /api/v1/contabilidad/pendientes/asistente-ia/`
(`DocumentosPendientesViewSet.asistente_ia`,
`apps/tenant/contabilidad/api/viewsets.py:1109-1142`).

**Es un sistema de IA completamente independiente del AI Engine
nuevo** (`apps/services/ai/`) -- llama a Anthropic con su propio
cliente (`anthropic.Anthropic(api_key=...)`, línea 1213 de
`business_service.py`), su propio prompt construido a mano, y su
propia lectura de `ANTHROPIC_API_KEY` del entorno. Hoy son dos rutas
de IA en paralelo dentro del mismo repo, no una que dependa de la
otra. `apps/services/ai/providers/anthropic_provider.py` ya lo
menciona en un comentario (línea 4-7) como precedente de patrón, pero
no lo invoca ni lo envuelve.

### Contrato real (verificado, no inferido)

**Entrada** (`AsistenteIAInputSerializer`,
`apps/tenant/contabilidad/api/serializers.py:471-481`):

| Campo | Tipo | Obligatorio | Nota |
|---|---|---|---|
| `app_label` | choice | sí | Solo `facturas`/`gastos`/`empleados`/`inventario` -- son los 4 orígenes con `ReglaContable` seedeada hoy |
| `modelo` | choice | sí | `Factura`/`DocumentoSoporte`/`Devengo`/`MovimientoInventario`/`HistorialServicio` -- validado por el serializer pero **no leído** dentro de `sugerir_lineas_asiento_ia()` (verificado: la función solo usa `ctx.get('numero'/'subtotal'/'impuestos'/'total'/'tercero_nit'/'tercero_nombre')` y el `app_label` aparte) |
| `documento_id` | int | sí | Mismo caso que `modelo` -- validado, no usado dentro de la función actual |
| `numero`, `subtotal`, `impuestos`, `total`, `tercero_nit`, `tercero_nombre` | str/decimal | subtotal y total sí, el resto con default | Estos SÍ se usan -- forman el `ctx` real que arma el prompt |

**Salida**: `List[Dict]` con `cuenta_codigo`, `cuenta_nombre`, `debe`,
`haber`, `descripcion` por línea. **Nunca escribe nada** -- es
`SUGGEST` puro. El resultado se inyecta en un offcanvas del frontend;
el contador humano revisa y confirma llamando a un endpoint
**distinto** (`contabilizar_documento_manual`, no cubierto por esta
integración) que sí persiste el `AsientoContable`.

**Validaciones ya aplicadas dentro de la función** (no hay que
reimplementarlas, solo respetarlas):
- Cada `cuenta_codigo` sugerido debe existir como `CuentaContable`
  `nivel=6`, `activa=True`, del tenant -- si no, `ValidationError`.
  (`filtrar_cuentas_por_app_origen` limita de antemano el PUC que se
  le muestra al LLM al que corresponde a `app_label`, ver
  `apps/tenant/contabilidad/services/selectors.py`.)
- `sum(debe) == sum(haber)` con tolerancia `0.01` -- si no cuadra,
  `ValidationError`.
- Mínimo 2 líneas -- si no, `ValidationError`.
- Respuesta no-JSON del LLM -- `ValidationError` (nunca un traceback
  crudo).

**Permisos**: `DocumentosPendientesViewSet` usa
`[IsTenantMember, IsTenantAdminOrReadOnly]` -- el `POST` a
`asistente-ia/` **requiere rol `ADMIN`** (`IsTenantAdminOrReadOnly`
solo permite `SAFE_METHODS` a cualquier miembro, ver
`AI_SECURITY_MODEL.md`).

## 2. Qué significa "orquestar, no duplicar" en este caso concreto

El AI Engine **no** reimplementa un segundo prompt de contabilidad ni
llama a Anthropic por su cuenta para este dominio. La tool de
integración (STEP 7, fuera de este documento) debe ser una envoltura
delgada que:

1. Construye `AIContext` como siempre (SSoT desde `TenantProfile`, no
   del payload).
2. Verifica `context.rol == "ADMIN"` dentro de su propio `run()`
   (mismo patrón que `buscar_empleado`/`consultar_cuenta_bancaria` --
   `AIEngine.run_tool()` no aplica ningún chequeo de rol estructural
   hoy, solo flags + `AUTO_APPROVED_KINDS`).
3. Llama **directamente** a
   `ContabilidadBusinessService().sugerir_lineas_asiento_ia(empresa_id, app_label, ctx)`
   -- el mismo método que ya usa el frontend hoy, sin tocar su lógica
   interna.
4. Traduce las excepciones reales (`ValidationError`) a
   `ToolResult(status="VALIDATION_ERROR", ...)`, nunca las oculta ni
   las reinterpreta.
5. Devuelve `data=<lineas>` tal cual las retornó la función real --
   sin un segundo prompt del AI Engine que "resuma" o "explique" el
   resultado (evita una segunda llamada a Anthropic innecesaria y una
   segunda fuente de error).

```
AI Engine (apps/services/ai/)
        │
   AIContext (SSoT, rol/empresa reales)
        │
   SugerirAsientoContableTool.run()   <- STEP 7, no implementada aun
        │  (kind=SUGGEST, verifica rol=ADMIN)
        │
   ContabilidadBusinessService.sugerir_lineas_asiento_ia()   <- YA EXISTE, sin cambios
        │  (prompt propio, validacion PUC nivel-6, debe==haber)
        │
   Anthropic API (llamada directa, cliente propio del Asistente Contable)
```

## 3. Contexto requerido por la tool (STEP 7)

- De `AIContext` (nunca del payload de la tool call): `empresa_id`,
  `rol` (para el chequeo `== "ADMIN"`).
- Como argumentos explícitos de la tool call (son datos del documento
  a contabilizar, no del usuario que pregunta): `app_label`,
  `numero`, `subtotal`, `impuestos`, `total`, `tercero_nit`,
  `tercero_nombre` -- mismo shape que `AsistenteIAInputSerializer`
  hoy, para no crear un segundo contrato de entrada.
  `modelo`/`documento_id` pueden aceptarse por compatibilidad con el
  serializer real pero no son necesarios para el cálculo (la función
  actual no los usa).

## 4. Qué puede preguntar la IA vs. qué nunca debe interpretar por su cuenta

**Puede preguntar** (cuando exista un flujo conversacional real, ver
`AI_CONTEXT_MODEL.md` Fase 43-44): "sugiere el asiento para este
documento pendiente", pasando los mismos campos que hoy pasa el
frontend -- resueltos desde el documento real (`Factura`/
`DocumentoSoporte`/etc., vía los Selectors ya existentes de cada
dominio, igual que `consultar_factura`/`consultar_gasto`), nunca
inventados por el LLM.

**Nunca debe interpretar por su cuenta**:
- Qué documento contabilizar -- lo elige el humano o un flujo
  explícito, la tool solo recibe datos ya identificados.
- El `app_label`/PUC a filtrar -- debe venir explícito, nunca inferido
  por el LLM (evita que la IA elija un plan de cuentas equivocado).
- La validación de cuenta nivel-6 activa ni la de `debe == haber` --
  esas quedan **dentro** de `sugerir_lineas_asiento_ia()`, la tool no
  las reimplementa ni las relaja "porque el usuario insistió".
- Nunca debe registrar el `AsientoContable` directamente -- eso sigue
  perteneciendo exclusivamente a `contabilizar_documento_manual()`
  (flujo humano de confirmación), que queda **fuera de alcance** de
  cualquier tool `SUGGEST`/`READ` del AI Engine (Regla Absoluta 6/7:
  WRITE nunca se auto-aprueba).

## 5. Qué respuestas vienen directamente del Asistente Contable

El array `lineas` que retorna `sugerir_lineas_asiento_ia()` se expone
tal cual en `ToolResult.data` -- el AI Engine es un canal, no un
segundo intérprete. Si en el futuro se necesita explicar el resultado
en lenguaje natural para un chat, esa explicación debe citar los
campos reales (`cuenta_codigo`, `debe`, `haber`) sin alterar los
montos ni inventar una cuenta que no vino de la función real.

## 6. Fuera de alcance de este documento (STEP 7, implementación)

- `apps/services/ai/tools/contabilidad_tools.py` con
  `SugerirAsientoContableTool` (kind=`SUGGEST`, risk=`SENSITIVE_READ`
  o superior -- toca datos financieros del tenant).
- Registro en `apps/services/ai/tools/__init__.py`.
- Tests reales verificando: (a) rol no-ADMIN devuelve
  `PERMISSION_DENIED` antes de llegar a llamar Anthropic, (b) rol
  ADMIN con `AI_SUGGEST_ENABLED=True` invoca
  `sugerir_lineas_asiento_ia()` real y traduce su resultado, (c) una
  `ValidationError` real (ej. cuenta inexistente) se traduce a
  `ToolResult(status="VALIDATION_ERROR")` sin traceback.
- Actualizar `AI_TOOL_REGISTRY.md` moviendo `contabilidad` de
  `BLOCKED BY DESIGN` a `VERIFIED` una vez implementado y testeado.
