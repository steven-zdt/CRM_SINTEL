---
name: sintel-mcp-integrity-dependencies
description: Protege relaciones, invariantes, estados y dependencias entre módulos durante operaciones MCP.
---
# INTEGRITY & DEPENDENCIES

Antes de mutar: target → FKs → reverse FKs → state → downstream consumers → side effects → accounting/fiscal/inventory consequences.

Consultar EKG para impacto estructural.

Reglas críticas documentadas:
- Factura: respetar Venta, DIAN, impuestos, retenciones, CxP/CxC, contabilidad y bancos.
- Venta: no crear hermana al facturar; usar `VentaBusinessService` real.
- Inventario: no escribir stock directamente; usar Kardex/movimiento real.
- Contabilidad: no escribir asientos desde otros dominios.
- Bancos: consumir contrato interapp real; no inventar saldos.
- Cotizaciones: respetar estados y conversiones idempotentes.
- Compras→Inventario: no inventar reglas de abastecimiento.

No inferir relaciones por similitud de nombres. Si falta relación real, marcar `DEFERRED`.

Después de mutar verificar objeto, invariantes, relaciones críticas y tests focalizados.
