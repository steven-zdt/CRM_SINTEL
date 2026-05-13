# 🧠 Lógica de Negocio: Módulo Facturas (SSoT)

Este documento centraliza las reglas de integridad legal y técnica para documentos electrónicos.

---

## 1. Idempotencia Legal (CUFE / CUDE)

- **Regla**: Ninguna factura puede duplicarse si su Código Único de Facturación Electrónica (CUFE) ya existe en la base de datos del tenant.
- **Mecanismo**: `fast_get_cufe` realiza un Regex sobre los bytes crudos del XML antes de iniciar el parsing pesado.
- **Silent Success**: Si un XML entrante tiene el mismo CUFE pero es un `AttachedDocument` (contiene la respuesta DIAN) y el registro actual solo tiene el `Invoice`, el sistema actualiza el anexo sin duplicar la factura.

---

## 2. Resolución de Naturaleza (VENTA vs COMPRA)

La clasificación se realiza comparando los NITs del XML contra el SSoT de la Empresa:
- **VENTA**: Si `Emisor_NIT == Empresa_NIT`. El tenant emitió la factura.
- **COMPRA**: Si `Receptor_NIT == Empresa_NIT`. El tenant recibió la factura.
- **Inconsistencia**: Si ninguno coincide, el documento se marca para revisión manual (Error de Ingesta).

---

## 3. Inmutabilidad y Snapshot Pattern

- **Inmutabilidad**: Una vez persistida, una factura NO se puede editar. Cualquier cambio debe reflejarse mediante una **Nota Crédito** vinculada.
- **Snapshot**: Los datos de emisor y receptor (NIT, Nombre, Dirección) se copian físicamente a la fila de la `Factura`. Esto garantiza resiliencia: si el nombre de un cliente cambia en el maestro de Clientes hoy, las facturas emitidas el año pasado deben conservar el nombre legal de ese momento.

---

## 4. Cálculo de Totales y Moneda

- **Validación Matemática**: El sistema recalcula totales desde los ítems de línea y los valida contra los totales informados en el XML. Diferencias > 0.01 generan advertencias.
- **Multimoneda**: Soporte para ISO 4217 (COP, USD, EUR). La contabilidad base siempre se proyecta en la moneda del tenant (COP).

---

## 5. Resumen de Facturación Neta

- **Fórmula**: `Total_Neto = Σ(Facturas sin NC)`.
- **Lógica**: Si una factura tiene una `NotaCredito` asociada (OneToOne), su valor para reportes de ingresos/gastos se considera **cero**, ya que la NC anula el documento original para efectos fiscales.

---

## 6. Pipeline Universal de Documentos

El módulo de facturas utiliza `apps.services.document_ingest` como gateway.
- **Fail Fast**: Si el parser detecta un XML que no es UBL 2.1 o está corrupto, la transacción se aborta antes de tocar la base de datos.
- **Timezone-Aware**: Todas las fechas de emisión del XML se normalizan a la zona horaria del servidor (UTC-5 para Colombia) antes de persistir.
