# F26 — Política de Datos XML

**Fecha:** 2026-08-10

**Principio rector:** el XML UBL/DIAN es una fuente de datos, no el modelo de datos de
SINTEL. Se persiste únicamente lo necesario para negocio, trazabilidad legal/técnica,
idempotencia, integración con otras apps, o reconstrucción/auditoría del documento.

## Muestra real auditada

398 archivos XML reales en `apps/tenant/facturas/facturas_xml/` (~20MB total,
~48KB promedio por archivo). Muestra representativa
(`019f2d07_6c8b369c-c4ef-45d9-8ede-7ff215000c2c.xml`, 41KB): **107 elementos XML**
distintos (`ElementTree.iter()` sobre el árbol completo, incluyendo namespaces
UBL/CAC/CBC anidados varios niveles).

`Factura` persiste ~56 campos propios (incluyendo los heredados de
`SintelTenantBaseModel`). Esto **no es sobre-persistencia** dado el contexto: DIAN
exige trazabilidad legal extensa (CUFE, autorización, validación, snapshot de
emisor/receptor por ley — ver `facturas_business_logic.md` §3 "Snapshot Pattern").
La proporción real (~56 campos persistidos vs 107 elementos XML de un documento
promedio) ya refleja una normalización razonable, no una copia 1:1 del schema UBL —
confirmado por auditoría de campos (`F26_FINDINGS.md` Parte 2): de 9 campos
investigados a fondo, solo 1 (`xml_file_path`) resultó ser puro ruido sin
consumidores, ya eliminado.

## Clasificación por dato (A-E)

| Categoría | Definición | Ejemplos reales en `facturas` |
|---|---|---|
| **A — Persistir** | Necesario para negocio/trazabilidad/idempotencia/integración | `numero`, `cufe`, `fecha_emision`, `emisor_nit`, `receptor_nit`, `subtotal`/`impuestos`/`total`, `naturaleza` (calculado), items (`ItemFactura`/`ItemNotaCredito`), `FacturaImpuesto` (desglose real) |
| **B — Persistir solo como dato derivado** | No viene literal del XML, se calcula a partir de otros datos ya persistidos | `naturaleza` (comparación NIT emisor vs `Empresa.nit`, no un campo UBL), `es_servicio` (heurística sobre `unidad_medida`), `consecutivo`/`prefijo` (parseados de `numero`) |
| **C — Usar durante procesamiento, NO persistir** | Se lee del XML para validar/calcular y se descarta | Casi todos los nodos de estructura UBL intermedia (`cac:Party`, `cac:TaxCategory` wrappers, namespaces, atributos de formato) — el parser los recorre para extraer valores, pero no hay ningún campo Django que almacene la estructura del árbol en sí |
| **D — Conservar únicamente dentro del XML original** | Trazabilidad legal completa sin necesidad de campo propio | Todo el XML crudo vive en `FacturaAnexos.ubl_xml`/`NotaCredito.xml_content` (ver §"XML original" abajo) — cualquier dato que no calce en A/B pero que DIAN pudiera auditar más adelante sigue disponible ahí, sin necesidad de un campo Django dedicado |
| **E — Ignorar** | Nodos UBL sin ningún consumidor identificado, ni siquiera para trazabilidad | Metadata de firma XAdES de bajo nivel, namespaces de extensión de vendors específicos no estandarizados — el parser usa `local-name()`/xpath robusto precisamente para ignorar variaciones de prefijo sin necesidad de mapear cada nodo posible |

## XML original — mecanismo de trazabilidad existente (no duplicar)

- **Factura**: `FacturaAnexos.ubl_xml` (modelo separado, 1:1, `apps/tenant/facturas/models.py:624-680`) — deliberadamente separado de la fila principal de `Factura` para "evitar cargar blobs en listados" (comentario original del modelo). Este ES el mecanismo de trazabilidad correcto.
  - `Factura.xml_content` es un **duplicado histórico** de este mismo dato, marcado deprecado desde antes de F26. Auditoría real (`F26_FINDINGS.md` F26-003): sigue vivo solo en el flujo de venta emisora (`crear_factura_desde_venta`), no en el flujo de ingesta (que ya usa exclusivamente `FacturaAnexos.ubl_xml`). **DEFER**, no eliminado en este pase — requiere primero unificar el flujo de venta emisora para que también escriba a `FacturaAnexos`, cambio de código real fuera del alcance verificable de F26 sin una suite de tests dedicada a ese flujo.
  - `Factura.xml_file_path`: sin mecanismo de trazabilidad real detrás (nunca se escribió una ruta de archivo real) — **eliminado** en F26 (0 consumidores, 0 datos históricos, ver `F26_FINDINGS.md` F26-002).
- **NotaCredito**: `xml_content` propio (sin modelo "Anexos" separado, dado que el documento es más pequeño que una Factura completa — decisión de diseño preexistente, no un problema identificado).

**No se crea ningún mecanismo de trazabilidad nuevo.** El existente (`FacturaAnexos`) ya es suficiente y correcto; el problema real era la duplicación parcial con `Factura.xml_content`/`xml_file_path`, no la ausencia de un mecanismo.

## Conclusión

La aplicación `facturas` **ya sigue mayormente** el principio "XML es fuente, no modelo" — no se encontró evidencia de que el modelo Django sea una copia mecánica del schema UBL. Las excepciones identificadas (F26-002 a F26-005 en `F26_FINDINGS.md`) son duplicaciones puntuales y localizadas, no un patrón sistémico. La corrección proporcionada en F26 (eliminar `xml_file_path`, corregir `orden_compra`) resuelve la única sobre-persistencia con evidencia sólida de cero consumidores; el resto queda documentado como deuda técnica real pero no ejecutable de forma segura en este pase.
