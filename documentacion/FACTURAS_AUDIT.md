# Auditoría de Facturas — FASE 8

**Fecha:** 2026-08-09
**Estado de la fase:** 🟢 COMPLETED — auditoría, cero código modificado
**Alcance:** `Factura`/`ItemFactura`/`NotaCredito`/`FacturaImpuesto`, `FacturaBusinessService`/`FacturaCRUDService`/`FacturaSelectors`, `FacturaInterAppAPI`, `FacturaViewSet`/`ItemFacturaViewSet`/`NotaCreditoViewSet`, `FacturaSerializer`, y los 5 Bridges (`CotizacionBridge`, `ClienteBridge`, `ProveedorBridge`, `InventarioItemBridge`, `BancosBridge`).

---

## 1. Corrección a lo que documentación anterior (MEMORY.md, OCF Fase 0) afirmaba

`MEMORY.md` describe "`FacturaInterAppAPI` (consumida por bancos/proyectos/gastos/empleados/proveedores/contabilidad) expone lectura de `Factura` sin filtro `empresa_id`". Verificado con grep real de imports en las 6 apps — **esto mezcla dos patrones distintos que no son lo mismo**:

| App | Cómo lee `Factura` | ¿Vía `FacturaInterAppAPI` (sin `empresa_id`)? |
|---|---|---|
| `bancos` | `from apps.tenant.facturas.services.business_service import FacturaInterAppAPI` | ✅ Sí — riesgo real |
| `proyectos` | Idem (`import ... as _FacturaInterAppAPI`) | ✅ Sí — riesgo real |
| `proveedores` | `from apps.tenant.facturas.models import Factura` + `.filter(empresa_id=empresa_id, ...)` directo | ❌ No — query propia, filtrada correctamente |
| `contabilidad` | Idem — `Factura.objects.filter(empresa_id=empresa_id, ...)` directo, con comentario explícito "Aplica DSV: filtra por `empresa_id`" | ❌ No — filtrada correctamente |
| `gastos` | **Sin ningún import de `facturas`** (verificado, `grep` vacío) | N/A — no consume `Factura` en absoluto |
| `empleados` | **Sin ningún import de `facturas`** (verificado, `grep` vacío) | N/A — no consume `Factura` en absoluto |

**Corrección:** solo `bancos` y `proyectos` usan la vía realmente abierta (`FacturaInterAppAPI`, sin `empresa_id`). `proveedores`/`contabilidad` usan el patrón "Bounded Context" ya sancionado por `AGENTS.md` §18 (query directa de solo lectura, siempre con `empresa_id` explícito, sin FK) — no es el mismo riesgo. `gastos`/`empleados` no consumen `Factura` en absoluto hoy.

---

## 2. `FacturaInterAppAPI` — riesgo R-2 (Fase 0 OCF / D-4 ADR-004), confirmado sin cambios

`apps/tenant/facturas/services/business_service.py:976-1075` — clase explícitamente marcada
`[ABIERTO] ... Contrato de acceso sin restriccion empresa_id para lectura` desde **v3.10.0**
(anterior a OCF/OSF por completo). `list_all()`, `get_by_id()`, `summary_all()`, `get_by_cufe()`,
`get_by_numero()` — ninguno filtra por `empresa_id`. Docstring de clase: "Llamadas desde servicios
internos SOLO — no exponible como API HTTP" (mitigación parcial: no es un endpoint público, pero
sigue siendo lectura cross-tenant-schema... realmente cross-EMPRESA dentro del mismo schema tenant,
ya que el aislamiento de esquema por tenant lo cubre `django-tenants`, no `empresa_id`).

**Estado confirmado, sin cambios desde ADR-004 (2026-08-07):** ADR-004 ya documentó esto como
"Riesgo D-4 ... resolverlo (agregar filtro) es una decisión de producto ... excede el alcance de
diseño". `organizational_bridges.py` (OCF Fase 7) propuso conceptualmente que `FacturaInterAppAPI`
se declare "explícitamente" como excepción abierta vía el contrato `OrganizationalBridge` — pero
`FacturaInterAppAPI` **no implementa** ese contrato (no tiene `get_by_uuid`/`exists` con la firma
`Protocol`), así que esa "resolución conceptual" nunca se materializó en código. Sigue siendo una
excepción documentada pero no formalizada bajo el nuevo contrato.

**No se introduce ninguna FK nueva** para resolver esto — consistente con la regla del prompt
maestro. Queda como decisión de producto pendiente, igual que ADR-004 ya la dejó.

---

## 3. Los 5 Bridges — consumidores reales (corrección de dirección)

Verificado por grep de cada clase en todo el repo: **los 5 Bridges se consumen desde DENTRO de
`facturas`** (`api/serializers.py`, `api/viewsets.py`, `services/business_service.py`) para
enriquecer las respuestas de `Factura` con datos de Cliente/Proveedor/Cotización/Inventario/Bancos
— no al revés. La única excepción parcial: `CotizacionBridge` también se usa desde
`apps/tenant/cotizaciones/services/selectors.py` (la dirección inversa, cotizaciones leyendo hacia
sí misma vía el mismo bridge que facturas expone — mismo bridge, dos consumidores).

**Inconsistencia de firma, confirmada sin cambios respecto a lo que ADR-004 ya documentó (D-2):**

| Bridge | `empresa_id` | Filtrado por `OrganizationalScope` |
|---|---|---|
| `CotizacionBridge.obtener_cotizacion_por_uuid` | Opcional (`None` por defecto) | ✅ **Sí** — `sede_ids` opcional agregado en OSF Fase F9 (`selectors.py:281-291`): si se pasa, una Cotización fuera del alcance se trata como "no encontrada" (mismo criterio NULL-safe que F7) |
| `ClienteBridge.obtener_cliente_por_uuid` | Opcional (`None` por defecto) | ❌ No |
| `ProveedorBridge.obtener_proveedor_por_uuid` | Opcional (`None` por defecto) | ❌ No |
| `InventarioItemBridge.buscar_catalogo` | **Obligatorio** | ❌ No (no tiene sede) |
| `BancosBridge.obtener_total_conciliado` | **Obligatorio** | ❌ No (agregado numérico, no un objeto individual) |

`CotizacionBridge` es hoy el único de los 5 con integración real de `OrganizationalScope` — no
por generalidad del diseño, sino porque `facturas` es la única app con las Fases F9/F11 de OSF ya
ejecutadas (ver §4). El resto de los 5 Bridges no tiene ningún cambio relacionado con OCF/OSF.

---

## 4. Dónde aplica `OrganizationalContext` vs `OrganizationalScope` en `facturas` — el caso más maduro de las 17 apps

`facturas` es la app con **más fases de OSF aplicadas** de las 6 candidatas de F7 (tiene F7, F9,
F10, F11 — las otras 5 solo tienen F7/F8):

| Componente | `OrganizationalContext` | `OrganizationalScope` |
|---|---|---|
| `FacturaViewSet` (`api/viewsets.py:121`) | Hereda `OrganizationalContextMixin` — **no invocado** (mismo patrón que las otras 13 apps, ver `OCF_TECHNICAL_AUDIT.md` §1) | `get_queryset()` (acción `list`) usa `OrganizationalScope.resolve()` + `filter_by_scope_null_safe()` vía `FacturaSelectors.qs_list()` (F7) |
| `FacturaSerializer.validate()` (`api/serializers.py:312-328`) | No aplica | `sede_esta_en_alcance()` — anti-IDOR de escritura: la `sede` asignada debe pertenecer a la empresa Y estar en el alcance del perfil (F8/F11) |
| `FacturaBusinessService` (edición limitada, `services/business_service.py:815-824`) | No aplica | `sede_ids` se propaga a `CotizacionBridge` al vincular `cotizacion_uuid` — un perfil `alcance=SEDE`/`AREA` no puede vincular una Cotización fuera de su alcance aunque sea de la misma empresa (F9); también restringe la propia asignación de `sede` de la Factura (F11) |
| `apps/tenant/facturas/views.py:61-66` | No aplica | Mismo patrón `OrganizationalScope.resolve()` directo (sin Mixin) que el resto de vistas no-DRF |

**Conclusión de la fase:** en `facturas`, `OrganizationalContext` sigue sin ningún consumidor
real (idéntico al resto del proyecto); `OrganizationalScope` sí tiene la integración más profunda
de las 17 apps — no solo filtra listas (como las otras 5 de F7), sino que también valida
escritura propia (`sede` de la Factura) y escritura cross-app (vínculo a `Cotizacion` vía Bridge).

---

## 5. `ItemFacturaViewSet` / `NotaCreditoViewSet` — confirmación de hallazgo EKG previo, sin cambios

Ambos (`api/viewsets.py:1090,1137`) heredan solo `OrganizationalContextMixin` + `BaseTenantViewSet`
— **sin ningún ServiceMixin** (`ItemFacturaServiceMixin`/`NotaCreditoServiceMixin` no existen).
Esto ya estaba documentado como hallazgo real (no falso positivo) en la auditoría EKG
2026-08-07 (`documentacion/INFORME_FINAL_EKG_GOBERNANZA_2026-08-07.md` §4.1) — confirmado aquí sin
cambios, no es un hallazgo nuevo de OCF/OSF ni afecta el análisis de alcance organizacional (ninguno
de los dos tiene campo `sede`/`area`, así que no hay nada de OSF que integrar ahí de todas formas).

---

## 6. `Factura.sede` — confirmación del patrón OSF (no `SedeAwareModel`)

`Factura.sede` (`models.py:195`) es un `ForeignKey` nullable directo, **no** vía `SedeAwareModel`
— consistente con la decisión de ADR-005 (§2, "rollout sin migración de esquema") para las 6 apps
candidatas de F7. `ItemFactura`/`NotaCredito`/`FacturaImpuesto` no tienen campo `sede`/`area`
propio — heredan el contexto organizacional de su `Factura` padre (vía FK), no necesitan uno
propio. Ningún cambio de esquema se aplicó a `facturas` en este proyecto — confirma que la
auditoría no encontró ninguna migración nueva de `facturas` relacionada con OCF/OSF más allá de
las ya conocidas.

---

## 7. No se introdujeron FK directas — verificado

Ninguno de los cambios de OCF/OSF en `facturas` agrega una FK nueva hacia otra app de negocio —
toda la integración cross-app sigue vía los Bridges existentes (lectura) o Soft References/UUID
(escritura, `cotizacion_uuid`, `cliente_uuid`, etc., patrón ya documentado en `AGENTS.md`). Regla
del prompt maestro cumplida sin necesidad de intervención.

---

## Cierre de FASE 8

Ningún archivo de código funcional modificado. Documento creado: `documentacion/FACTURAS_AUDIT.md` (este archivo). Corrige una imprecisión de `MEMORY.md` (consumidores reales de `FacturaInterAppAPI`) sin editar `MEMORY.md` directamente (fuera del alcance de esta auditoría; documentado aquí para quien lo consulte).

**Fase completada o bloqueada. No iniciar la siguiente fase hasta recibir autorización explícita del usuario.**
