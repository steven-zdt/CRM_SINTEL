# Ciclo Comercial — Contrato Formal Venta → Factura (FASE COMERCIAL-03)

**Fecha:** 2026-08-24. **Estado:** Formalización + validación (0 cambios
de código — el contrato real ya es correcto, esta fase lo documenta como
tal, con 1 nota DRY menor no bloqueante).

```
VentaBusinessService._construir_dto_factura()
        ↓
   VentaFacturaDTO   (dict, sin clase propia — ver §3)
        ↓
FacturaBusinessService.crear_factura_desde_venta()
```

---

## 1. Checklist del plan, verificado con evidencia

| Pregunta | Resultado | Evidencia |
|---|---|---|
| ¿DTOs duplicados? | **No** | Un solo método construye un dict con la forma `emisor`/`receptor`/`totales`/`lineas` en todo el repo (`_construir_dto_factura()`) — confirmado por grep de esa combinación de claves |
| ¿Construcción duplicada? | **No** | `crear_factura_desde_venta()` es el único consumidor de ese DTO que crea una `Factura` a partir de él |
| ¿Cálculo duplicado de **totales de cabecera**? | **No** | `_construir_dto_factura()` lee `venta.subtotal`/`.impuestos`/`.total_neto` ya calculados por `VentaCRUDService.crear_venta()` — no los recalcula |
| ¿Cálculo duplicado de **totales por línea**? | **Sí, técnicamente — ver §2** | Mismo `cant * pu` se calcula una vez en `crear_venta()` (persistido en `ItemVenta.subtotal`) y otra vez en `_construir_dto_factura()` (para `lineas[]`/`impuestos_por_tasa`) |
| ¿Impuestos calculados de manera diferente? | **No** | Misma fórmula (`sub_linea * pct_iva/100`) en ambos sitios — ver §2, no hay una segunda fórmula independiente |
| ¿Datos de cliente inconsistentes? | **No** | `receptor{}` se construye una sola vez desde el objeto `cliente` real (`_construir_dto_factura()`), y `crear_factura_desde_venta()` solo lee ese mismo `dto["receptor"]` — sin una segunda consulta independiente al `Cliente` |

---

## 2. La única duplicación real encontrada: no es un riesgo de divergencia

`VentaCRUDService.crear_venta()` calcula `sub = cant * pu` /
`iva_item = sub * pct_iva/100` por cada item, para poblar
`ItemVenta.subtotal` y agregar `Venta.subtotal`/`.impuestos`.
`_construir_dto_factura()` **recalcula exactamente la misma fórmula**
sobre el mismo `items_data` (el mismo dict de entrada, no `ItemVenta` ya
persistido) para construir `lineas[]` e `impuestos_por_tasa` — necesario
porque el DTO UBL necesita el desglose por tasa de IVA (`cac:TaxTotal`),
que `Venta`/`ItemVenta` no almacenan agregado por tasa.

**Por qué no es un riesgo real:** ambos cálculos parten del **mismo**
`items_data` (la lista que llega en el payload original, nunca se
transforma entre medio) y usan la **misma** fórmula literal — no hay
forma de que diverjan salvo que alguien edite una de las dos copias sin
la otra en el futuro. Es una violación DRY (duplicación de código), no
un bug de consistencia de datos hoy. Se documenta como deuda técnica
menor, no como hallazgo crítico — corregirla requeriría que
`_construir_dto_factura()` reciba `ItemVenta` ya persistidos en vez de
`items_data` crudo, o que `crear_venta()` devuelva el desglose por tasa
ya calculado; ninguna de las dos es necesaria para que el contrato sea
correcto hoy.

---

## 3. `VentaFacturaDTO` — forma formalizada (no una clase nueva)

El contrato es un `dict` plano, no una clase/dataclass — formalizarlo
aquí significa fijar por escrito su forma exacta, no crear código nuevo
(el plan no pide una clase `VentaFacturaDTO`, pide "definir el
contrato"). Claves reales, tal como las produce `_construir_dto_factura()`
y consume `crear_factura_desde_venta()`:

```
{
  "document_type": "FE", "tipo": "FE", "naturaleza": "VENTA",
  "customization_id", "profile_id", "tip_amb", "invoice_type_code",
  "num_fac", "fec_fac", "hor_fac", "moneda", "observaciones",
  "emisor": {nit, dv, razon_social, direccion, ciudad, departamento,
             email, telefono, tipo_documento, additional_account_id,
             tax_level_code, tax_level_list_name, tax_scheme_id, tax_scheme_name},
  "receptor": {nit, razon_social, email, telefono, direccion, ciudad,
               tipo_documento, additional_account_id, tax_level_code,
               tax_level_list_name, tax_scheme_id, tax_scheme_name},
  "dian_software": {provider_id, software_id, software_security_code, authorization_id},
  "resolucion": {numero_autorizacion, prefijo, desde, hasta, fecha_inicio, fecha_fin},
  "medio_pago": {codigo, fecha_vencimiento, instruccion},
  "totales": {subtotal, impuestos, total, line_extension_amount,
              tax_exclusive_amount, tax_inclusive_amount,
              allowance_total, charge_total, payable_amount},
  "impuestos_discriminados": [{porcentaje, valor, base, tax_scheme_id, tax_scheme_name}, ...],
  "lineas": [{id, descripcion, cantidad, valor_unitario, porcentaje_iva,
              subtotal, iva, total, unidad, tax_scheme_id, tax_scheme_name,
              seller_item_id, std_item_id}, ...],
  "fecha_emision", "fecha_vencimiento",
  "cliente_uuid", "venta_uuid", "sede_id",
  "numero_externo"?,                          # solo si numero_factura fue pasado
  "cufe", "qr_string",                        # agregados por el caller tras construir (Paso 5a)
  "xml_content", "dian_response_xml",         # agregados por el caller tras construir (Paso 5c-5d)
}
```

**Nota importante:** el DTO **no está completo** cuando sale de
`_construir_dto_factura()` — `cufe`/`qr_string`/`xml_content`/
`dian_response_xml` se agregan **después**, mutando el mismo dict, en
`procesar_y_facturar_venta()` (pasos 5a-5d, `apps/tenant/ventas/services/
business_service.py:576-601`). El "contrato formal" real tiene 2 etapas,
no 1: `_construir_dto_factura()` produce la base UBL, el orquestador la
enriquece con lo que solo él puede calcular (CUFE depende de campos que
ya están en el DTO, firma depende del XML ya construido). Documentado
aquí para que quien lea `crear_factura_desde_venta()` sepa que el DTO
que recibe no es 100% el que `_construir_dto_factura()` devolvió.

---

## 4. Conclusión

**`COMERCIAL-03 = COMPLETED`**, sin deuda bloqueante. El contrato ya
existente es correcto: una sola fuente de construcción, un solo consumidor,
un solo cálculo de impuestos, datos de cliente consistentes. Única
observación real (§2) es una duplicación de fórmula sin riesgo de
divergencia práctica, documentada como deuda técnica menor, no como
bloqueador para COMERCIAL-04+.
