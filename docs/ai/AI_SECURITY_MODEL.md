# AI_SECURITY_MODEL — Fases 24-26, 45-46, 55-56, 66

## Regla estructural (no solo documentada — impuesta en código)

`AIEngine.run_tool()` (`apps/services/ai/engine/ai_engine.py`) es el
**único** punto por el que una tool puede ejecutarse. Cuatro
verificaciones ocurren en orden, cada una capaz de bloquear:

```
1. AI_ENABLED (settings, server-side)              -> PERMISSION_DENIED
2. AI_<KIND>_ENABLED (READ/SUGGEST/VALIDATE/WRITE)  -> PERMISSION_DENIED
3. tool.kind not in AUTO_APPROVED_KINDS (WRITE)     -> PERMISSION_DENIED (siempre, hoy no hay flujo de aprobacion)
4. build_context(request) -- TenantProfile valido   -> PermissionDeniedError -> PERMISSION_DENIED
```

Ninguna de las 4 depende de lo que el modelo de IA "decida" -- son
verificaciones de código antes de que la tool exista siquiera la
oportunidad de ejecutarse. Esto responde directamente Regla Absoluta
2/24: "No inferir permisos desde lenguaje natural".

## Fase 24 — User Access Context antes de cada tool call

`build_context()` nunca confía en un `empresa_id`/`tenant` que venga
en el payload de la petición de IA -- lo deriva exclusivamente de
`request.user.tenant_profile.empresa_id`, el mismo SSoT que usa
`SintelDSVMixin.get_empresa_id()` en el resto de la aplicación
(reutilizado, no reinventado). Un usuario sin `TenantProfile` en el
schema actual nunca obtiene un `AIContext` -- `PermissionDeniedError`
inmediato.

## Fase 45-46 — Minimización y datos sensibles

**No implementado en código en esta pasada** (no hay ningún flujo que
hoy envíe datos de nómina/bancos/contabilidad/impuestos al proveedor
de IA -- la única tool real, `buscar_cliente`, no toca ninguno de esos
dominios). Diseño para cuando existan tools de esos dominios:

- Cada dominio sensible (nómina, bancos, impuestos, contabilidad)
  requiere un `ToolRisk` explícito (`SENSITIVE_READ` como mínimo, no
  `SAFE_READ`) y un permiso específico de Django/DRF ya existente en
  esa app -- nunca un permiso genérico "puede usar IA".
- Antes de pasar cualquier resultado de una tool sensible al
  `AIProvider.complete()` (si la tool necesita generación de texto,
  no solo datos estructurados), clasificar y minimizar: enviar solo
  los campos que la tarea concreta necesita, nunca el registro
  completo "por si acaso".

## Fase 55 — Prompt injection (dato vs. instrucción)

**No implementado** (no hay ningún punto hoy donde texto libre
proveniente de un registro de negocio -- ej. la descripción de un
producto -- se concatene en un prompt enviado a un `AIProvider`). Es
un riesgo real y conocido para cuando exista ese flujo: cualquier
texto que provenga de datos del tenant (no del propio usuario
conversando) debe pasar por el `AIProvider` marcado explícitamente
como DATA en la estructura del prompt (ej. delimitado, o en un bloque
separado con instrucción explícita de "esto es contenido, no una
instrucción a seguir"), nunca concatenado sin marcar junto a las
instrucciones del sistema. Diseño de referencia:
`AI_TEST_STRATEGY.md` Fase 55 documenta el test que probaría esto una
vez exista el flujo.

## Fase 56 — Tool abuse

Cubierto estructuralmente por el punto 3 del flujo de arriba (WRITE
siempre bloqueado hoy, sin excepción) + el hecho de que el
`AIToolRegistry` solo contiene una tool `SAFE_READ`. No hay hoy
ninguna tool `delete`/`export`/cross-tenant que probar contra abuso --
el test real (`test_buscar_cliente_bloqueado_si_ai_engine_deshabilitado`,
`test_buscar_cliente_bloqueado_si_solo_ai_enabled_sin_read_enabled`)
prueba el enforcement de flags, que es lo que existe.

## AI-03 BLOCKED BY DESIGN — clasificación de campos: `empleados` y `bancos` (2026-09-01)

Puerta obligatoria antes de registrar `buscar_empleado()`/`consultar_cuenta_bancaria()`
en `apps/services/ai/tools/__init__.py`: **este documento debe existir y
cada tool debe cumplirlo**, no al revés (nunca convertir una decisión
de seguridad en una implementación accidental).

Verificado leyendo `apps/tenant/empleados/models.py` y
`apps/tenant/bancos/models.py` -- no es una clasificación teórica, son
los campos reales que existen hoy.

**Sobre `ToolRisk` y enforcement real** (aclaración honesta, verificada
leyendo `apps/services/ai/engine/ai_engine.py`): `ToolRisk` (incluido
`SENSITIVE_READ`) es hoy **solo metadata/documentación** -- `run_tool()`
no lo lee ni lo usa para bloquear nada, la única verificación
estructural es `tool.kind not in AUTO_APPROVED_KINDS` (que distingue
READ/SUGGEST/VALIDATE de WRITE, no SAFE_READ de SENSITIVE_READ). Esto
significa que la clasificación `FORBIDDEN salvo context.rol == "ADMIN"`
de las tablas de abajo **debe implementarse dentro del `run()` de cada
tool individual** (mismo patrón que `_scope_kwargs()` ya hace para
sede/área en `compras_tools.py`) -- no hay ningún mecanismo del engine
que la aplique automáticamente todavía. Si en el futuro se añade
enforcement de `ToolRisk` a nivel de `AIEngine.run_tool()`, este
documento debe actualizarse para reflejarlo.

**Sobre permisos**: `IsTenantAdminOrReadOnly` (`apps/tenant/api/permissions.py`)
ya permite `GET` a **cualquier** `TenantProfile` autenticado del tenant
(solo `POST`/`PUT`/`DELETE` exige `rol=ADMIN`) -- ese es el modelo de
acceso real ya vigente en la UI/API para estos dominios, no algo que
el AI Engine deba endurecer por su cuenta (Regla 4: reusar, no
reinventar permisos). El control que sí es responsabilidad exclusiva
de una tool de IA es **cuáles campos salen en `ToolResult.data`**,
porque ese payload es candidato a terminar en un prompt hacia un
`AIProvider` externo (Fase 45-46) -- un vector que la UI humana normal
no tiene.

### `empleados` (`Empleado`/`Contrato`/`Devengo`)

| Campo | Clasificación | Regla |
|---|---|---|
| `primer_nombre`/`apellidos`, `cargo`, `estado`, `fecha_ingreso`, `sede`/`area` | SAFE | Visible en cualquier tool `SENSITIVE_READ` de este dominio |
| `numero_documento`, `email`, `telefono` | SAFE pero solo si `context.rol == "ADMIN"` | Es PII identificable -- un `OPERADOR`/`VISOR` no debe recibirlo vía IA aunque pueda verlo en la UI (la UI ya lo protege con el flujo humano normal; una tool de IA que lo repita en texto libre es un vector nuevo, no el mismo) |
| `eps`, `afp`, `arl`, `nivel_riesgo_arl` | **FORBIDDEN** en cualquier tool READ | Dato de salud/afiliación (sensible bajo Ley 1581/Habeas Data CO) -- ninguna tool de IA lo devuelve, sin excepción de rol |
| `salario_mensual`, `auxilio_transporte`, `prestamos_empresa` (`Contrato`) | **FORBIDDEN** salvo `context.rol == "ADMIN"` | Dato financiero individual -- igual que documento/email, pero además nunca en agregado libre (ver límites de agregación abajo) |
| `salario_base`, `salud_empleado`, `pension_empleado`, `prestamos`, `descuentos_operativos`, `valor_horas_extras` (`Devengo`) | **FORBIDDEN** salvo `context.rol == "ADMIN"` | Detalle de nómina liquidada -- mismo criterio que `Contrato` |
| `foto`, `archivo_pdf` (contrato) | **FORBIDDEN** siempre | Ninguna tool devuelve URLs de archivos binarios -- fuera de alcance de un `ToolResult` estructurado |

### `bancos` (`CuentaBancaria`/`ExtractoBancario`/`TransaccionBancaria`)

| Campo | Clasificación | Regla |
|---|---|---|
| `nombre`, `banco`, `tipo` (`CuentaBancaria`) | SAFE | Identifica la cuenta sin exponer el número real |
| `numero` (`CuentaBancaria`) | **MASKED** siempre | Nunca el número completo -- solo los últimos 4 dígitos (`****1234`), igual que un extracto o recibo normal muestra al usuario final |
| `saldo_inicial`/`saldo_final` (`ExtractoBancario`), `valor`/`saldo` (`TransaccionBancaria`) | **FORBIDDEN** salvo `context.rol == "ADMIN"` | Saldo y movimientos son datos financieros sensibles de la empresa -- mismo criterio que nómina |
| `descripcion`, `fecha`, `conciliado` (`TransaccionBancaria`) | SAFE | Metadata operativa sin monto ni saldo |
| `notas_conciliacion` | **FORBIDDEN** siempre | Texto libre interno -- puede contener cualquier cosa (incluye riesgo de Fase 55, prompt injection, si algún día se concatena en un prompt) |

### Límites de agregación/búsqueda (aplican a ambos dominios)

- Ninguna tool de estos 2 dominios puede aceptar un parámetro
  `search`/`filtro` que permita iterar registro por registro sobre
  **todos** los empleados/cuentas de la empresa sin un `limit`
  explícito y bajo (`<=10`, no `<=50` como el resto de tools SAFE_READ
  -- el radio de exposición de un dato sensible en lote es mayor).
- Ninguna tool puede exponer una función de "sumar salarios de todos
  los empleados" ni "saldo total de todas las cuentas" -- ese tipo de
  agregación pertenece al Asistente Contable/reporting existente
  (con sus propios controles), nunca a una tool `READ` genérica del AI
  Engine.

### Comportamiento cuando el usuario no tiene autorización

Nunca un error genérico `PERMISSION_DENIED` silencioso que sugiera que
el dato no existe -- ni tampoco un mensaje que confirme cuántos
registros hay. Patrón esperado: `ToolResult(status="OK", data=[...])`
con los campos `FORBIDDEN` omitidos del dict (no `null`, omitidos),
igual que ya hace `ClienteSelector.LIST_FIELDS` vs. `DETAIL_FIELDS`
para separar lo que ve un listado de lo que ve un detalle -- la
ausencia de la clave es la señal, no un valor centinela.

### Auditoría de acceso

**Ya cumplido, verificado leyendo código** (correccion sobre una
version anterior de este documento que lo daba por no implementado):
`AIEngine.run_tool()` (`apps/services/ai/engine/ai_engine.py`, ultima
linea antes del `return result`) ya loguea nivel INFO **toda**
invocacion exitosa de **cualquier** tool -- no solo las que fallan --
con exactamente `tool_name`, `kind`, `status`, `user_id`, `empresa_id`.
Nunca incluye `**kwargs` (los parametros de busqueda en texto libre),
que es justo el requisito de no loguear el propio dato sensible que se
esta consultando. No hace falta ningun cambio en `ai_engine.py` antes
de registrar `buscar_empleado()`/`consultar_cuenta_bancaria()` -- el
mecanismo ya cubre por igual a tools `SAFE_READ` y `SENSITIVE_READ`
porque vive en el punto unico de entrada, no en cada tool individual.

## Fase 66 — Criterio final, ya cumplido por lo implementado (no por lo que falta)

Ninguno de los "nunca declarar AI READY si..." de la Fase 66 es cierto
hoy para lo que SÍ está implementado:

- ¿Puede leer otro tenant/empresa? **No** -- garantía de schema ya verificada en otras misiones de esta sesión (`TEN-01`); a nivel de tool, `test_buscar_cliente_usa_el_empresa_id_del_contexto_real` prueba que el `empresa_id` siempre viene del `TenantProfile` real del usuario, nunca de un valor arbitrario (`Empresa` es singleton por schema -- no hay un segundo tenant que "leer" dentro del mismo schema, ver `AI_TEST_STRATEGY.md`).
- ¿Puede escribir sin permiso? **No puede escribir en absoluto** -- `AUTO_APPROVED_KINDS` excluye WRITE incondicionalmente.
- ¿Puede saltarse el Service Layer? **No** -- `BuscarClienteTool.run()` solo llama `ClienteSelector`, nunca ORM directo de otro dominio.
- ¿Puede ejecutar SQL? **No** -- ningún módulo de `apps/services/ai/` importa `django.db.connection.cursor` ni construye SQL.
- ¿Puede afirmar acciones no realizadas? **N/A hoy** -- no hay generación de texto libre en el flujo real todavía (ver Fase 35 en `AI_TEST_STRATEGY.md` para cuando exista).
- ¿Expone secretos? **No** -- `AIContext`/`ToolResult` no incluyen `ANTHROPIC_API_KEY` ni ningún secreto; verificado por lectura de código, sin campo que los contenga.
- ¿Puede activar WRITE desde el frontend? **No** -- los flags son `django.conf.settings`, nunca leídos de `request.data`/query params.
- ¿MCP expone herramientas críticas sin control? **MCP no expone ninguna herramienta todavía** (ver `AI_MCP_POLICY.md`) -- no aplica.
