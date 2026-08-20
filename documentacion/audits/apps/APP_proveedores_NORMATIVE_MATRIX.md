# APP_proveedores_NORMATIVE_MATRIX — Matriz normativa colombiana

Parte de `documentacion/audits/apps/APP_proveedores_AUDIT.md` (FASE M).

## Diferencia clave con `clientes`

A diferencia de `clientes` (que SOLO guarda configuracion de
retencion, sin calcular nada -- ver `APP_clientes_NORMATIVE_MATRIX.md`),
`apps/tenant/proveedores` **SI contiene logica de calculo real** en
`ProveedorBusinessService.obtener_configuracion_retenciones()` y
`calcular_componentes_retencion()` (`business_service.py:164-208`).
Esto cambia el perfil de riesgo: aqui hay tarifas y formulas concretas
que auditar, no solo un campo de configuracion.

## Hallazgo critico: la SSoT de retenciones documentada NO esta wireada a `gastos`

El propio `.agent/docs/proveedores_flow_map.md` (linea 27-31) documenta
el flujo esperado: *"Al crear un gasto relacionado con un proveedor:
1. El sistema invoca `obtener_configuracion_retenciones`. 2. Se evalua
el flag `autoretenedor`. 3. Se aplica el porcentaje de ReteFuente (4%
por defecto) y ReteICA (0.966% para personas naturales)."* El
`.agent/docs/proveedores_microtasks_architecture.md` (linea 22-24)
marca esto como `[COMPLETED]`.

**Verificado con grep repo-wide (nombre de funcion, todo el repo):
`obtener_configuracion_retenciones`, `calcular_componentes_retencion`
y `calcular_neto_gasto` NO tienen NINGUN consumidor fuera de su propia
definicion en `business_service.py`** -- ni en `apps/tenant/gastos`
(el consumidor documentado), ni en `apps/tenant/contabilidad`, ni en
`api/viewsets.py` de `proveedores`, ni en ningun test. Es codigo
real, bien escrito, con validaciones (`ValidationError` si porcentaje
fuera de 0-100, `ROUND_HALF_UP`), pero **nunca se ejecuta en el flujo
real de creacion de gastos**, contradiciendo la documentacion propia
de la app que lo marca como `[COMPLETED]` e integrado.

**Clasificacion: CONTRACT_DRIFT** (la documentacion afirma una
integracion que el codigo no tiene) -- no es codigo muerto en el
sentido de "resto de un refactor" (como los casos de `empresa`/
`clientes`), es codigo **diseñado correctamente pero nunca conectado**
a su consumidor previsto. No se elimina (tiene valor real, validaciones
correctas) ni se fuerza su integracion en esta auditoria (modificar
`gastos` para invocarlo esta fuera del alcance minimo de la auditoria
de `proveedores` -- requiere primero auditar `gastos`, app 12/16, para
confirmar si ya tiene su propio calculo de retenciones -- posible
duplicacion en sentido inverso -- o si el gasto simplemente no aplica
retencion en absoluto hoy). **Se registra aqui como hallazgo P1 y se
revisara con evidencia completa cuando se audite `gastos`.**

## Matriz

| # | Obligacion | Sujeto obligado | Supuesto de hecho | Norma citada en codigo | Evidencia | Aplicabilidad |
|---|---|---|---|---|---|---|
| 1 | Identificacion tributaria unica por documento legal | Empresa (tenant) | Todo proveedor | Sin articulo especifico citado | `models.py` (`UniqueConstraint(empresa, tipo_documento, numero_documento)`) | **OBLIGATORIO** -- constraint DB |
| 2 | Retefuente 4% si el proveedor NO es autorretenedor | Empresa (agente retenedor) | Pago/abono a proveedor no autorretenedor | Sin articulo citado en codigo (tasa hardcodeada `Decimal("4")`) | `business_service.py:177-178` | **REQUIERE_VALIDACION** -- 4% corresponde a la tarifa de retefuente por "servicios en general" (Concepto 365 DIAN, sujeto a confirmacion oficial), pero la tarifa real de retefuente en Colombia **varia por concepto** (compras generales ~2.5%, servicios generales 4%, honorarios/comisiones 11%, arrendamientos, etc.) -- el codigo aplica un 4% plano sin distinguir el tipo de bien/servicio del gasto. **Ademas, no valida cuantia minima (UVT)** antes de aplicar retencion -- la normativa DIAN generalmente exige un monto base minimo por concepto antes de que aplique la retencion. Riesgo real de sub/sobre-retencion si esta funcion llegara a activarse sin ajustes. **Y, como se documento arriba, esta funcion no se ejecuta actualmente en ningun flujo real -- el riesgo es teorico mientras siga desconectada.** |
| 3 | ReteICA 0.966% si tipo_persona=NATURAL, 0% si JURIDICA | Empresa (agente retenedor) | Pago a proveedor NATURAL | Sin articulo citado (tasa hardcodeada `Decimal("0.966")`) | `business_service.py:180-181` | **REQUIERE_VALIDACION** -- la tarifa de ReteICA en Colombia es **especifica por municipio** (cada municipio fija su propia tabla de tarifas segun actividad economica CIIU) y generalmente **no depende del tipo de persona** (natural vs juridica) sino de la actividad. El codigo usa una regla simplificada (solo NATURAL, tarifa fija) que no reflejaria correctamente la variacion real por municipio/actividad. Mismo comentario que #2: funcion actualmente desconectada de cualquier flujo real. |
| 4 | Configuracion de gran contribuyente / autoretenedor / responsable IVA (flags booleanos) | Proveedor | Segun clasificacion DIAN del tercero | Sin logica normativa asociada mas alla del flag -- son datos de entrada, no calculos | `models.py` (`gran_contribuyente`, `autoretenedor`, `responsable_iva`) | **OBLIGATORIO** registrar el dato correctamente (afecta el calculo de retenciones downstream), pero esta app no valida estos flags contra el RUT/DIAN -- son autodeclarados por quien registra el proveedor |

## Deferred

| # | Item | Prioridad |
|---|---|---|
| 1 | `obtener_configuracion_retenciones`/`calcular_componentes_retencion` documentadas como integradas con `gastos` pero sin ningun consumidor real -- CONTRACT_DRIFT confirmado. Revisar con evidencia completa al auditar `gastos` (app 12/16): ¿tiene su propio calculo duplicado, o simplemente no aplica retencion hoy? | **P1** -- afecta correccion financiera si `gastos` deberia estar aplicando retenciones y no lo hace |
| 2 | Si/cuando se conecte esta funcion, la tarifa de retefuente deberia parametrizarse por concepto (no un 4% plano) y validar cuantia minima UVT -- requiere fuente oficial DIAN antes de implementar | P2 (condicional a que se resuelva el item #1 primero) |
| 3 | Tarifa de ReteICA deberia parametrizarse por municipio/actividad, no solo por tipo_persona -- requiere fuente oficial (cada municipio publica su propia tabla) | P2 (mismo condicionamiento que #2) |
