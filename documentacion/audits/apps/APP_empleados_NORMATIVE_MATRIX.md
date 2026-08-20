# APP_empleados_NORMATIVE_MATRIX — Matriz normativa colombiana

Parte de `documentacion/audits/apps/APP_empleados_AUDIT.md` (FASE M).
Metodologia: evidencia-primero -- cada fila cita la norma exacta
encontrada en el codigo (`business_service.py`) o, cuando el codigo no
trae cita inline, se marca explicitamente como tal y se clasifica de
forma conservadora. **No se afirma vigencia/aplicabilidad de una norma
sin evidencia verificable en este pase** (regla de la mision: nunca
inventar obligaciones).

| # | Obligacion | Sujeto obligado | Supuesto de hecho | Norma citada en codigo | Evidencia (archivo:linea) | Aplicabilidad |
|---|---|---|---|---|---|---|
| 1 | Cotizacion salud empleado 4% sobre IBC | Empleador (retiene) / Empleado (aporta) | Contrato laboral (`tipo != PRESTACION`) | Ley 100/1993, art. 204 | `business_service.py:642` | **OBLIGATORIO** para contratos FIJO/INDEF/OBRA. **NO_APLICA** a PRESTACION (verificado: `if contrato.tipo == 'PRESTACION'` fuerza 0 en linea 641) |
| 2 | Cotizacion pension empleado 4% sobre IBC | Empleador (retiene) / Empleado (aporta) | Contrato laboral (`tipo != PRESTACION`) | Ley 100/1993, art. 20 | `business_service.py:643` | **OBLIGATORIO** (misma logica que #1) |
| 3 | Auxilio de transporte excluido de IBC | Empleador | Todo contrato con auxilio | Ley 100/1993, art. 30 | `business_service.py:634` | **OBLIGATORIO** (comentario confirma exclusion expresa) |
| 4 | Contratos de prestacion de servicios sin auxilio de transporte | Empleador | `Contrato.tipo == PRESTACION` | Ley 1393/2010, art. 2 | `business_service.py:625-626` | **OBLIGATORIO** (verificado con guard explicito en codigo) |
| 5 | Jornada maxima mensual de referencia = 200h (42h/semana) | Empleador | Calculo de valor-hora para H.E./recargos | Ley 2101/2021 | `business_service.py:32,522,600,615` | **OBLIGATORIO** desde vigencia de la ley (jornada reducida progresiva 2023-2026) -- el codigo asume el escalon final vigente (42h). **REQUIERE_VALIDACION**: la Ley 2101/2021 establece un escalonamiento progresivo (47h -> 44h -> 42h por años); el codigo no parametriza por fecha de contrato/periodo, asume 42h/200h fijo para todos los periodos. Si el tenant tiene devengos de periodos anteriores a la entrada en vigencia del escalon de 42h, el calculo podria no reflejar la jornada legal vigente en ESE periodo historico. Ver deferred #1. |
| 6 | Recargo hora extra diurna +25% | Empleador | Horas extras diurnas trabajadas (Lun-Sab 6am-9pm) | Decreto 2663/1950 (CST), art. 168 | `business_service.py:645,648` | **OBLIGATORIO** |
| 7 | Recargo hora extra nocturna +75% | Empleador | Horas extras nocturnas (9pm-6am) | CST art. 168 | `business_service.py:649` | **OBLIGATORIO** |
| 8 | Recargo nocturno ordinario +35% | Empleador | Horas ordinarias en horario nocturno | CST art. 168 | `business_service.py:650` | **OBLIGATORIO** |
| 9 | Limite 2h extras/dia (~62h/mes en la practica) | Empleador | Registro de horas extras | CST art. 168 | `business_service.py:568` (comentario, sin enforcement de limite duro encontrado en el guard de validacion) | **REQUIERE_VALIDACION** -- el comentario referencia el limite legal pero no se confirmo en este pase si `validar_limite_dias_mes`/el guard de horas (max 80h por tipo, 200h total, segun `.agent/AUDITORIA_FLUJO_EMPLEADOS.md` linea 311) aplica el limite diario de 2h/dia del art. 168 o solo el tope mensual agregado. Deferred #2. |
| 10 | Prima de servicios (salario/360 dias del semestre) | Empleador | Todo trabajador con contrato laboral (no PRESTACION) | Formula estandar CST art. 306 (**sin cita inline en el codigo**) | `business_service.py:791` (formula, sin comentario de norma) | **OBLIGATORIO** -- formula tecnica correcta (salario_base × dias/360) pero **sin cita normativa inline**, a diferencia de las deducciones (#1-#4). Deferred #3 (agregar comentario de norma, no es un error de calculo). |
| 11 | Cesantias (salario/360 dias del año) | Empleador | Todo trabajador con contrato laboral | Formula estandar, regimen Ley 50/1990 (fondos de cesantias) -- **sin cita inline** | `business_service.py:792` | **OBLIGATORIO** -- mismo hallazgo que #10, formula correcta sin cita. Deferred #3. |
| 12 | Intereses sobre cesantias 12% anual | Empleador | Todo trabajador con derecho a cesantias | Ley 52/1975, art. 1 -- **sin cita inline** (codigo usa `Decimal('0.12')` sin comentario de norma) | `business_service.py:795` | **OBLIGATORIO** -- tasa correcta (12% es la tasa legal estandar) pero sin cita. Deferred #3. |
| 13 | Vacaciones (salario/720 dias) | Empleador | Todo trabajador con contrato laboral | CST art. 186 -- **sin cita inline** | `business_service.py:798` | **OBLIGATORIO** -- formula correcta (15 dias habiles/año = salario/720 en la convencion estandar), sin cita. Deferred #3. |
| 14 | Contratos PRESTACION sin prestaciones sociales | Empleador | `Contrato.tipo == PRESTACION` | Naturaleza civil/comercial del contrato de prestacion (no laboral) -- coherente con CST art. 34 y jurisprudencia sobre tercerizacion, sin cita especifica en codigo | `business_service.py:737-738` (guard: retorna todo en cero) | **OBLIGATORIO** -- verificado con guard explicito |
| 15 | Nomina electronica DIAN (DSPNE): resolucion vigente, consecutivo dentro de rango, CUNE | Empleador (como emisor obligado ante DIAN) | Toda liquidacion de nomina (`Devengo`) sujeta a transmision electronica | Resolucion DIAN de nomina electronica (numero/año no verificable desde el codigo -- el modelo `ResolucionDIAN` es generico y se configura por tenant, no hardcodea una resolucion especifica de la DIAN) | `models.py` (`ResolucionDIAN`, `TransmisionNominaDIAN`), `business_service.py` `procesar_devengo()` | **OBLIGATORIO** para responsables de nomina electronica (segun umbral DIAN vigente) -- **REQUIERE_VALIDACION** del numero de Resolucion DIAN marco (ej. Resolucion 000013 de 2021 y modificatorias) porque el sistema es agnostico a la resolucion especifica (correcto, ya que cada tenant configura la suya), pero esta auditoria no verifico contra el sitio oficial de la DIAN si la infraestructura de generacion de XML (DEUDA-11, ver audit doc principal) cumple el esquema XSD vigente -- **la transmision XML real NO esta implementada** (`xml_enviado`/`xml_respuesta` quedan null, `estado_dian` permanece `PENDIENTE` indefinidamente, documentado como DEUDA-11 ABIERTA desde 2026-06-17). |

## Resumen de items REQUIERE_VALIDACION / deferred (no bloquean cierre, requieren revision legal/producto)

1. **Jornada Ley 2101/2021 no parametrizada por fecha histórica** -- el
   sistema usa siempre 42h/200h como jornada de referencia,
   independientemente de la fecha del periodo del devengo. Si existen
   devengos de periodos anteriores al escalon final de la ley, el
   calculo de valor-hora podria no coincidir con la jornada legal
   vigente en ese periodo especifico. Requiere: (a) confirmar con
   Ministerio del Trabajo (fuente oficial) el calendario exacto de
   escalonamiento, (b) decidir si el sistema debe parametrizar por
   fecha o si el negocio acepta aplicar siempre la jornada vigente
   actual (aceptable si el sistema no maneja retroactivamente periodos
   anteriores a 2026). **P2** -- afecta el calculo de nomina, pero solo
   en un escenario de uso retroactivo no confirmado.
2. **Limite de horas extras diarias (CST art. 168, 2h/dia) no
   confirmado como validado explicitamente** -- el sistema valida
   topes agregados (80h/tipo, 200h/mes segun el .agent doc existente)
   pero no se confirmo en este pase si existe un guard por-dia de 2h.
   Requiere lectura linea por linea de `validar_limite_dias_mes` (fuera
   del alcance de este primer pase FASE M) antes de concluir
   conformidad o no-conformidad. **P2**.
3. **Formulas de prestaciones sociales (prima, cesantias, intereses,
   vacaciones) correctas pero sin cita normativa inline en el codigo**
   -- a diferencia de las deducciones de ley (que si citan articulo
   exacto), estas 4 formulas no tienen comentario de norma. No es un
   error de calculo (las formulas coinciden con la practica estandar
   colombiana), es una brecha de trazabilidad/documentacion. **P3**
   -- agregar comentarios de norma (CST art. 306, Ley 50/1990, Ley
   52/1975 art. 1, CST art. 186) en una sesion futura, sin tocar la
   logica.
4. **DSPNE (nomina electronica DIAN) sin transmision XML real
   (DEUDA-11)** -- ya documentado y ABIERTO en el `.agent/` audit doc
   de la app desde 2026-06-17, confirmado vigente en este pase. La
   infraestructura de datos (CUNE, consecutivo, resolucion) esta
   completa y correcta; falta la generacion/envio del XML UBL 2.1 real
   contra el webservice DIAN. **P1** si el negocio ya tiene tenants
   reales obligados a DSPNE operando en produccion (fuera del alcance
   de esta auditoria confirmar cuantos); **P2** si ningun tenant real
   esta aun en el umbral de obligatoriedad.
