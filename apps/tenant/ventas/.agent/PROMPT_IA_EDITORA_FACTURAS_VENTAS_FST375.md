# PROMPT MAESTRO IA EDITORA
# INTEGRACIÓN FACTURAS ↔ VENTAS + NUEVA FACTURA
# BASADO EN LA FACTURA REAL FST 375

## MISIÓN

Auditar y corregir la integración entre:

- `http://admin.sintel.net.co/workspace/#facturas`
- `http://admin.sintel.net.co/workspace/#ventas`

La finalidad es que las facturas ya cargadas/procesadas en **Facturas** puedan ser utilizadas directamente en **Ventas**, y que el formulario **Nueva Factura** represente la estructura real utilizada actualmente por SINTEL, tomando como referencia visual y funcional exacta el documento adjunto:

```text
FST 375.pdf
```

La implementación debe ejecutarse mediante el ciclo:

```text
INSPECT
→ BASELINE
→ MAP
→ DESIGN
→ IMPLEMENT
→ RECONCILE
→ TEST
→ AUDIT
→ FIX
→ REGRESSION
→ VERIFY
→ DOCUMENT
→ PASS
```

NO modificar código antes de inspeccionar el código real.

NO asumir que los modelos, campos, servicios, endpoints o componentes descritos en esta instrucción existen.

---

# 1. FACTURA REAL DE REFERENCIA

El documento adjunto es una factura electrónica de venta de 2 páginas.

Debe utilizarse como **referencia estructural real** para diseñar y probar el formulario.

La factura muestra visualmente:

## Encabezado

En la parte superior:

```text
Logo SINTEL
SINTEL TECHNOLOGY SAS
NIT 901.123.299-1
Calle 30 58 CD 20
Tel: 3196561797
Bogotá - Colombia
sintel.technology@gmail.com
```

También contiene:

```text
Código QR
```

y el bloque:

```text
Factura electrónica de venta
No. FST 375
```

El documento se identifica visualmente como:

```text
Factura-FV-2-375
```

---

# 2. DATOS DEL CLIENTE OBSERVADOS EN FST 375

En la factura:

```text
Señores:
Focus electronic security sistem S.A.S

NIT:
900.860.947-3

Teléfono:
(601) 7561406

Dirección:
CL 90 60 B 08 P4

Ciudad:
Bogotá - Colombia
```

IMPORTANTE:

Estos datos son únicamente el caso real de referencia para pruebas.

NO hardcodear:

```text
Focus electronic security sistem S.A.S
900.860.947-3
FST 375
```

La aplicación debe obtenerlos desde:

```text
Factura
Cliente
Organización
XML
```

según el SSoT real.

---

# 3. FECHAS DE LA FACTURA FST 375

El documento muestra:

```text
Generación:
20/06/2026, 10:18

Expedición:
20/06/2026, 10:18

Vencimiento:
20/07/2026
```

La nueva estructura debe soportar separadamente:

```text
fecha_generacion
hora_generacion
fecha_expedicion
hora_expedicion
fecha_vencimiento
```

No combinar las fechas si el modelo actual puede conservarlas separadas.

---

# 4. DETALLE REAL DE LA FACTURA

La tabla de FST 375 tiene exactamente esta estructura visual:

```text
Item | Descripción | Cantidad | Vr. Total | Vr. Unitario | Valor Impto.Cargo
```

La factura contiene:

```text
Item:
1

Descripción:
SERVICIO MANO OBRA INSTALACION PP241173

Cantidad:
1,00

Vr. Total:
5.139.915,83

Vr. Unitario:
4.319.257,00

Valor Impto.Cargo:
820.658,83
```

Este formato es FUNDAMENTAL.

El formulario Nueva Factura debe permitir múltiples líneas y debe conservar conceptualmente estas columnas.

---

# 5. REGLA DE MONEDA

Todos los valores monetarios de esta implementación deben manejar:

```text
COP
```

La UI debe mostrar:

```text
$ 5.139.915,83
```

o el formato monetario COP ya establecido por el proyecto.

NO almacenar valores monetarios como strings formateados.

Backend:

```text
Decimal
```

Frontend:

```text
formato COP
```

Base de datos:

```text
DecimalField
```

si ese es el patrón existente.

---

# 6. RESUMEN FISCAL REAL DE FST 375

Página 2 muestra:

```text
Total Bruto:
4.319.257,00

IVA 19%:
820.658,83

Total a Pagar:
5.139.915,83
```

El formulario Nueva Factura debe representar claramente:

```text
Total Bruto
IVA
Total a Pagar
```

No reemplazar estas etiquetas por una terminología diferente si el diseño actual busca replicar la factura.

Internamente se pueden mapear a:

```text
subtotal
iva
total
```

pero la presentación debe ser comprensible para el usuario.

---

# 7. VALOR EN LETRAS

FST 375 muestra:

```text
Cinco millones ciento treinta y nueve mil novecientos quince pesos m/cte con ochenta y tres cent.
```

El formulario debe poder mostrar:

```text
Valor en Letras
```

Debe generarse automáticamente desde el total.

NO permitir que el frontend sea la fuente definitiva del valor en letras.

La fuente definitiva debe ser el valor monetario validado por backend.

---

# 8. FORMA DE PAGO REAL

FST 375 contiene:

```text
Forma de pago:
Crédito
```

El formulario debe tener:

```text
Forma de pago
```

con los choices/catálogos existentes.

No crear otro catálogo si ya existe.

---

# 9. MEDIO DE PAGO REAL

FST 375 contiene:

```text
Medio de pago:
Otro - Crédito
```

y:

```text
Cuota No. 001
vence el 2026-07-20
por $ 5.139.915,83
```

Por tanto, Nueva Factura debe poder representar:

```text
Medio de pago
Código medio de pago
Tipo de crédito
Número de cuota
Fecha de vencimiento
Valor de cuota
```

SOLO agregar los campos que sean compatibles con el modelo real y la estructura fiscal existente.

No duplicar campos existentes.

---

# 10. OBSERVACIONES REALES

FST 375 muestra:

```text
Observaciones:

Prestacion de Servicio mano de obra instalacion equipos CCTV,
Segun OC- Pedido de compra #P01879-COT-EM-2511-720-SANAUTOS PALOMEQUE

Fecha de la Orden:
10-06-2026 09:29:54
```

El formulario debe incluir:

```text
Observaciones
```

y, si el modelo lo permite:

```text
Número / referencia de orden de compra
Fecha de orden
```

No mezclar estos datos con los campos fiscales principales.

---

# 11. INFORMACIÓN FISCAL / DIAN DE FST 375

La parte inferior de la factura contiene:

```text
Número Autorización Electrónica:
18764101371367

aprobado en:
20251109

prefijo:
FST

desde el número:
343

al:
850

Vigencia:
24 Meses
```

También:

```text
Régimen simple de tributación
```

y:

```text
Actividad Económica:
8020
Actividades de servicios de sistemas de seguridad

Tarifa:
10x1000
```

La nueva factura debe permitir visualizar/administrar estos datos según el modelo y proceso fiscal real.

Los datos generados por autorización DIAN deben ser:

```text
SOLO LECTURA
```

cuando procedan del proceso fiscal.

NO permitir editar manualmente desde el frontend:

```text
CUFE
autorización
rango autorizado
consecutivo ya emitido
estado DIAN
```

---

# 12. CUFE

La factura FST 375 contiene un CUFE en la parte inferior.

Debe existir una única fuente del CUFE.

Regla:

```text
CUFE = dato fiscal
```

Por tanto:

```text
Facturas → SSoT
Ventas → referencia
```

No generar un CUFE diferente en Ventas.

No copiarlo manualmente.

No permitir editarlo.

---

# 13. QR

La primera página contiene un QR asociado a la factura electrónica.

El sistema debe conservar la relación:

```text
Factura
→ QR / representación fiscal
```

si dicha información existe en el modelo/documentos actuales.

No generar un QR ficticio para satisfacer la UI.

---

# 14. FACTURAS ES EL SSoT FISCAL

Esta es la regla arquitectónica principal.

```text
apps/tenant/facturas/
```

es dueño de:

```text
Factura
CUFE
XML
datos fiscales
impuestos fiscales
consecutivo
autorización
estado DIAN
representación fiscal
```

Ventas NO debe crear otra factura fiscal.

NO crear:

```text
ventas.Factura
```

si ya existe:

```text
facturas.Factura
```

---

# 15. VENTAS ES EL SSoT COMERCIAL

Ventas administra:

```text
Venta
Cliente
Proyecto
seguimiento comercial
estado comercial
estado de pago
gestión manual
responsable
observaciones comerciales
```

La relación correcta debe ser conceptualmente:

```text
Factura fiscal
      │
      │ 1 : 0..1
      ▼
Venta
```

Si el proyecto ya tiene:

```python
Venta.factura_asociada
```

con:

```python
OneToOneField(Factura)
```

conservarlo.

NO reemplazarlo sin justificación técnica.

---

# 16. "MIGRAR FACTURAS A VENTAS" — INTERPRETACIÓN OBLIGATORIA

La petición:

> Migrar las facturas existentes de Facturas a Ventas

NO significa duplicar las facturas.

Significa:

```text
Factura existente
       ↓
identificar naturaleza VENTA
       ↓
buscar Venta correspondiente
       ↓
si no existe:
crear Venta comercial
       ↓
vincular Factura original
```

Resultado:

```text
1 Factura
1 Venta
1 vínculo
0 duplicados fiscales
```

---

# 17. AUDITORÍA DE FACTURAS EXISTENTES

Antes de migrar ejecutar DRY RUN.

Obtener:

```text
Facturas totales
Facturas de venta
Facturas de compra
Notas crédito
Notas débito
Facturas ya vinculadas
Facturas sin venta
Ventas existentes
Ventas con factura
Duplicados
Ambiguos
Errores
```

Generar:

```text
reporte_reconciliacion_facturas_ventas
```

---

# 18. CRITERIOS DE MATCH

Para determinar si una factura ya tiene Venta:

1. vínculo directo existente;
2. UUID;
3. CUFE;
4. número + prefijo + empresa;
5. combinación inequívoca de datos fiscales.

NO utilizar únicamente:

```text
total
cliente
fecha
```

para crear una relación automática.

Si hay ambigüedad:

```text
NO VINCULAR AUTOMÁTICAMENTE
```

Marcar:

```text
AMBIGUO
```

---

# 19. NUEVA VENTA — BOTÓN VINCULAR FACTURA

En:

```text
#/ventas
→ Nueva Venta
```

agregar:

```text
[ Buscar / Vincular Factura ]
```

Debe abrir el patrón visual existente:

```text
modal
offcanvas
```

según la arquitectura actual.

NO crear una nueva librería UI.

---

# 20. BUSCADOR DE FACTURAS

Permitir buscar:

```text
Número
Prefijo
CUFE
NIT
Cliente
Fecha
Estado
Total
```

Mostrar:

```text
Factura
Cliente
NIT
Fecha
Vencimiento
Estado fiscal
Total
CUFE
```

Acción:

```text
[ Vincular ]
```

---

# 21. AUTORRELLENO DE NUEVA VENTA

Cuando el usuario seleccione FST 375:

```text
Factura
↓
Vincular
↓
Nueva Venta
```

autorrellenar los campos correspondientes.

Como mínimo:

```text
Cliente
Fecha emisión
Fecha vencimiento
Subtotal
IVA
Total
Forma de pago
Medio de pago
Referencia fiscal
```

y cualquier otro campo comercial compatible.

---

# 22. DATOS DE SOLO LECTURA EN VENTAS

Si vienen de Factura fiscal:

```text
Número factura
CUFE
Fecha emisión fiscal
IVA fiscal
Subtotal fiscal
Total fiscal
Estado DIAN
```

deben ser:

```text
solo lectura
```

o mostrados como datos provenientes de Facturas.

Ventas NO puede convertirse en un editor fiscal alternativo.

---

# 23. GESTIÓN DE PAGO EN VENTAS

Debe permanecer separada.

Ejemplo:

```text
Factura:
VALIDADA

Venta:
FACTURADA

Pago:
PENDIENTE
```

Posteriormente:

```text
Pago:
PAGADA

Fecha de pago:
...
```

Esto NO debe modificar:

```text
CUFE
XML
autorización
número fiscal
```

---

# 24. FORMULARIO NUEVA FACTURA — ESTRUCTURA FINAL

La pantalla debe seguir conceptualmente la estructura de FST 375.

## SECCIÓN 1 — ENCABEZADO

```text
[LOGO]

Razón social
NIT
Dirección
Teléfono
Ciudad
Correo

[QR]

Factura electrónica de venta
No. [PREFIJO] [CONSECUTIVO]
```

---

## SECCIÓN 2 — CLIENTE

```text
Señores
[Cliente]

NIT
[Documento]

Teléfono
[Teléfono]

Dirección
[Dirección]

Ciudad
[Ciudad]
```

---

## SECCIÓN 3 — FECHA Y HORA FACTURA

```text
Generación
[Fecha] [Hora]

Expedición
[Fecha] [Hora]

Vencimiento
[Fecha]
```

---

## SECCIÓN 4 — DETALLE

Tabla:

```text
| Item |
| Descripción |
| Cantidad |
| Vr. Total |
| Vr. Unitario |
| Valor Impto.Cargo |
```

Agregar:

```text
[ + Agregar línea ]
```

Cada línea debe permitir:

```text
Producto/Servicio
Código
Descripción
Cantidad
Precio unitario
Impuesto
Total
```

La descripción puede tomar el catálogo de:

```text
productos
servicios
inventario
```

según arquitectura existente.

---

# 25. CÁLCULO DE LÍNEAS

Ejemplo FST 375:

```text
Cantidad = 1

Vr. Unitario = 4.319.257,00

IVA = 820.658,83

Vr. Total = 5.139.915,83
```

El backend debe validar:

```text
subtotal
+
impuestos
-
descuentos
=
total
```

según las reglas fiscales reales.

No confiar únicamente en JavaScript.

---

# 26. RESUMEN DE TOTALES

Visualizar:

```text
Total Bruto        $ 4.319.257,00

IVA 19%            $   820.658,83

Total a Pagar      $ 5.139.915,83
```

Mostrar también:

```text
Total items: 1
```

---

# 27. VALOR EN LETRAS

Mostrar:

```text
Valor en Letras:
[valor generado automáticamente]
```

Debe actualizarse al modificar el total.

---

# 28. FORMA DE PAGO

Mostrar:

```text
Forma de pago:
[ Crédito ]
```

---

# 29. MEDIO DE PAGO

Mostrar:

```text
Medio de pago:
[ Otro - Crédito ]
```

Si corresponde:

```text
Cuota No.
Vencimiento
Valor
```

---

# 30. OBSERVACIONES

Bloque:

```text
Observaciones:

[textarea]
```

Opcionalmente:

```text
Pedido / Orden de compra
Fecha de la orden
```

si existe soporte real en el modelo.

---

# 31. PIE FISCAL

Mostrar:

```text
A esta factura de venta aplican las normas relativas
a la letra de cambio...
```

y la información fiscal real disponible:

```text
Número autorización
Fecha autorización
Prefijo
Rango
Vigencia
Régimen
Actividad económica
Tarifa
CUFE
```

No escribir textos fiscales arbitrarios si ya existe una representación oficial proveniente del proceso fiscal.

---

# 32. IMPORTACIÓN DE FACTURA

La app Facturas debe continuar soportando:

```text
PDF
XML
```

cuando ya exista ese flujo.

Al procesar una factura:

```text
Documento
↓
Parser
↓
DTO
↓
Factura
↓
Datos normalizados
```

Después:

```text
Factura
↓
Disponible para Ventas
```

No duplicar el documento.

---

# 33. PROCESAMIENTO DEL PDF FST 375

La prueba funcional debe comprobar que el sistema puede reconocer los bloques visibles:

```text
Emisor
Cliente
NIT
Fechas
Número
Ítems
Cantidad
Precio
IVA
Total
Forma de pago
Medio de pago
Observaciones
Autorización
Rango
Actividad económica
CUFE
QR
```

La factura contiene 2 páginas.

El parser NO debe asumir que todos los datos están en la primera página.

---

# 34. PROCESAMIENTO XML

Si existe XML asociado:

```text
XML
```

debe ser la fuente estructurada preferida frente a OCR/PDF para datos fiscales.

Orden recomendado:

```text
XML estructurado
↓
datos fiscales
```

y:

```text
PDF
↓
representación / respaldo / OCR cuando sea necesario
```

No sobrescribir datos fiscales válidos del XML con OCR menos confiable.

---

# 35. SINCRONIZACIÓN FACTURA → VENTA

Crear/extender un servicio de negocio.

Ejemplo conceptual:

```python
FacturaVentaLinkService.vincular(
    factura_uuid=...,
    venta_uuid=...,
    actor=...
)
```

Debe:

```text
validar tenant
validar permisos
validar factura
validar naturaleza
validar venta
validar vínculos
bloquear registros
vincular
sincronizar campos permitidos
preservar gestión manual
auditar
```

Usar:

```python
transaction.atomic()
```

y:

```python
select_for_update()
```

cuando corresponda.

---

# 36. IDEMPOTENCIA

Ejecutar dos veces:

```text
Factura FST 375 → Venta
```

Resultado:

```text
1 factura
1 venta
1 relación
0 duplicados
```

No crear una nueva Venta cada vez.

---

# 37. CONCURRENCIA

Probar simultáneamente:

```text
Factura FST 375 → Venta A
Factura FST 375 → Venta B
```

Debe existir una única relación válida.

Validar:

```text
OneToOne
UNIQUE
transaction.atomic
select_for_update
IntegrityError
```

según el diseño real.

---

# 38. MULTITENANT / SEGURIDAD

Una factura de empresa A:

```text
Factura A
```

NO puede vincularse a:

```text
Venta empresa B
```

Todas las operaciones deben respetar:

```text
tenant
empresa
usuario
permisos
```

Nunca confiar únicamente en el UUID enviado por frontend.

---

# 39. AUDITORÍA DE CAMBIOS

Registrar:

```text
Factura vinculada
Venta vinculada
Usuario
Fecha
Tenant
Datos afectados
```

Si ya existe sistema de auditoría:

```text
reutilizarlo
```

No crear uno paralelo.

---

# 40. TEST ESPECÍFICO FST 375

Ejecutar:

```text
FST 375
↓
Facturas
↓
Buscar desde Nueva Venta
↓
Vincular
↓
Autorrellenar
↓
Guardar
```

Validar:

```text
Factura = FST 375

Cliente = Focus electronic security sistem S.A.S

NIT = 900.860.947-3

Generación = 20/06/2026 10:18

Expedición = 20/06/2026 10:18

Vencimiento = 20/07/2026

Descripción =
SERVICIO MANO OBRA INSTALACION PP241173

Cantidad = 1,00

Vr. Unitario = 4.319.257,00

IVA = 820.658,83

Total = 5.139.915,83

Forma de pago = Crédito

Medio de pago = Otro - Crédito
```

El CUFE debe coincidir exactamente con el documento procesado.

NO codificar estos valores.

---

# 41. PRUEBA VISUAL

Comparar el formulario Nueva Factura contra FST 375.

Verificar:

```text
[ ] Encabezado
[ ] Logo
[ ] QR
[ ] Número
[ ] Emisor
[ ] Cliente
[ ] NIT
[ ] Fechas
[ ] Tabla de ítems
[ ] Cantidad
[ ] Valor unitario
[ ] Valor impuesto
[ ] Total bruto
[ ] IVA
[ ] Total a pagar
[ ] Valor en letras
[ ] Forma de pago
[ ] Medio de pago
[ ] Observaciones
[ ] Autorización
[ ] Rango
[ ] Vigencia
[ ] Actividad económica
[ ] CUFE
```

No necesariamente se exige copiar gráficamente cada píxel; se exige reproducir la **estructura funcional y los datos que representa**.

---

# 42. PRUEBAS DE REGRESIÓN

Ejecutar:

```bash
python manage.py check
```

Luego las suites reales relacionadas con:

```text
facturas
ventas
clientes
inventario
contabilidad
bancos
```

Probar especialmente:

```text
Factura → Venta
Venta → Factura
Factura → XML
Factura → CUFE
Factura → PDF
Venta → Inventario
Factura → Contabilidad
```

---

# 43. NO HACER

NO:

```text
crear una segunda factura fiscal
duplicar XML
duplicar CUFE
duplicar consecutivos
copiar facturas físicamente a Ventas
crear catálogo paralelo de clientes
crear catálogo paralelo de productos
generar CUFE desde frontend
permitir edición manual del CUFE
permitir edición fiscal desde Ventas
sobrescribir estado de pago
sobrescribir gestión manual
crear lógica fiscal compleja en JavaScript
crear servicios duplicados
crear endpoints paralelos
ignorar tenant
hacer migración destructiva
eliminar facturas históricas
```

---

# 44. CRITERIOS DE ACEPTACIÓN

La implementación solo es PASS si:

```text
[ ] Facturas continúa siendo SSoT fiscal.
[ ] FST 375 puede procesarse correctamente.
[ ] Facturas históricas de venta pueden proyectarse a Ventas.
[ ] No se duplican facturas.
[ ] No se duplican XML.
[ ] No se duplican CUFE.
[ ] Nueva Venta permite Buscar/Vincular Factura.
[ ] Vincular autorrellena los datos correspondientes.
[ ] Los datos fiscales quedan protegidos.
[ ] Estado de pago permanece independiente.
[ ] Nueva Factura refleja la estructura real de FST 375.
[ ] Los ítems soportan múltiples líneas.
[ ] IVA y totales se validan en backend.
[ ] Forma de pago funciona.
[ ] Medio de pago funciona.
[ ] Observaciones funcionan.
[ ] Autorización fiscal se conserva.
[ ] CUFE se conserva.
[ ] QR/representación se conserva cuando exista.
[ ] Migración es idempotente.
[ ] Migración es transaccional.
[ ] Concurrencia está controlada.
[ ] Tenant está aislado.
[ ] Permisos están respetados.
[ ] Auditoría existe.
[ ] Tests pasan.
[ ] Facturas no se rompe.
[ ] Ventas no se rompe.
[ ] Inventario no se rompe.
[ ] Contabilidad no se rompe.
[ ] Bancos no se rompe.
```

---

# 45. ENTREGABLE FINAL

La IA editora debe entregar:

## 45.1 Informe de auditoría

```text
estado anterior
hallazgos
riesgos
correcciones
```

## 45.2 Matriz de mapeo

```text
Factura → Venta
```

campo por campo.

## 45.3 Matriz FST 375

```text
dato visible
campo backend
campo frontend
origen
editable
```

## 45.4 Migración

```text
total facturas
ventas creadas
ventas ya existentes
vínculos creados
omitidas
ambiguas
errores
duplicados
```

## 45.5 Tests

```text
PASS
FAIL
SKIP
```

con evidencia.

## 45.6 Evidencia UI

Probar:

```text
#/facturas
#/ventas
Nueva Factura
Nueva Venta
Buscar/Vincular Factura
Autorrelleno
```

---

# 46. ARQUITECTURA OBJETIVO

La arquitectura final debe quedar:

```text
                         ┌───────────────────────┐
                         │       FACTURAS        │
                         │      SSoT FISCAL      │
                         │                       │
                         │ XML                   │
                         │ CUFE                  │
                         │ DIAN                  │
                         │ impuestos             │
                         │ autorización          │
                         │ representación        │
                         └───────────┬───────────┘
                                     │
                              API / DTO / SERVICE
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │        VENTAS         │
                         │    SSoT COMERCIAL     │
                         │                       │
                         │ Venta                 │
                         │ Cliente               │
                         │ Proyecto              │
                         │ Gestión comercial     │
                         │ Estado de pago        │
                         └───────────────────────┘
```

Y el flujo de usuario:

```text
                 FACTURA EXISTENTE
                        │
                        ▼
                 BUSCAR FACTURA
                        │
                        ▼
                   VINCULAR
                        │
                        ▼
                 NUEVA VENTA
                        │
                        ▼
                  AUTORRELLENO
                        │
                        ▼
                     GUARDAR
```

Mientras que el flujo de creación fiscal es:

```text
                    NUEVA FACTURA
                          │
                          ▼
                 Datos fiscales
                          │
                          ▼
                    Validaciones
                          │
                          ▼
                  Proceso fiscal
                          │
                          ▼
                     FACTURA
                          │
                          ▼
                    DISPONIBLE
                     PARA VENTAS
```

---

# 47. REGLA FINAL

La factura **FST 375.pdf** debe ser utilizada como referencia real para validar la estructura del formulario.

No convertir sus datos en constantes.

No inventar campos que no tengan soporte en el código o en el documento.

Cuando exista diferencia entre:

```text
documentación
código real
factura FST 375
```

la IA editora debe:

1. inspeccionar;
2. identificar la diferencia;
3. documentarla;
4. determinar el SSoT;
5. implementar la corrección mínima necesaria;
6. agregar pruebas;
7. ejecutar regresión.

La prioridad arquitectónica es:

```text
INTEGRIDAD FISCAL
>
NO DUPLICACIÓN
>
CONSISTENCIA FACTURA ↔ VENTA
>
TRAZABILIDAD
>
SEGURIDAD TENANT
>
UX
```

Resultado esperado:

```text
             FACTURA FST 375
                    │
                    ▼
                FACTURAS
              SSoT fiscal
                    │
             Vincular factura
                    │
                    ▼
                 VENTAS
            SSoT comercial
                    │
                    ▼
             Venta autorrellena
```

## FIN DEL PROMPT
