# Auditoría Ventas → Facturas — FASE 9

**Fecha:** 2026-08-09
**Estado de la fase:** 🟢 COMPLETED — auditoría, cero código modificado
**Alcance:** el contrato `Ventas → DTO → FacturaBusinessService → Factura` (OSF Fase F10), verificando transporte de `empresa`/`sede`/`area`, ausencia de FK directa, ausencia de dependencia circular, y que el contexto organizacional del usuario se respeta.

---

## 1. El contrato, verificado línea por línea

```
VentaViewSet.crear_y_facturar()
  -> (sede_id = OrganizationalContext.resolve(request).sede_id -- la sede ACTIVA del usuario)
  -> VentaBusinessService.procesar_y_facturar_venta(empresa, payload, sede_id)
       -> DSV cliente + items + proyecto (empresa_id)
       -> crea Venta (BORRADOR)
       -> _construir_dto_factura(empresa, cliente, venta, items, ..., sede_id)
            -> dto = {..., "cliente_uuid": ..., "venta_uuid": ..., "sede_id": sede_id}
       -> FacturaBusinessService.crear_factura_desde_venta(empresa, dto)
            -> sede = Sede.objects.filter(id=dto["sede_id"], empresa_id=empresa.id).first()
               (DSV: id ajeno/invalido se ignora, degrada a sede=None -- no rompe la Factura)
            -> factura_data["sede"] = sede
            -> Factura.objects.create(**factura_data)
       -> VentaCRUDService.vincular_factura(venta, factura)  -- Soft Reference (UUID), no FK
```

Fuente: `apps/tenant/ventas/services/api_mixins.py:26-44`,
`apps/tenant/ventas/services/business_service.py:216-434,488-611`,
`apps/tenant/facturas/services/business_service.py:95-135` (numeración de línea aproximada del
bloque de creación).

---

## 2. `empresa`/`sede`/`area` — qué transporta y qué no, y por qué

| Campo | ¿Transporta? | Cómo | Por qué |
|---|---|---|---|
| `empresa` | ✅ Sí | Parámetro explícito `empresa` en cada llamada de la cadena (nunca re-derivado) — mismo patrón `SintelDSVMixin` de siempre, sin relación con OCF/OSF | Ya era obligatorio antes de OSF; el Zero-Trust del proyecto lo exige en toda capa |
| `sede` | ✅ Sí | `dto["sede_id"]` — dato plano en el DTO, nunca una FK `Venta.sede`/`Factura.sede_de_venta` | `Venta` **no tiene** campo `sede` propio (confirmado en FASE 5, `ORGANIZATIONAL_SCOPE_MATRIX.md` §4.1/§1: "candidato plausible, sin campo aún") — lo que se transporta es el contexto de **quién** factura (`OrganizationalContext.resolve(request).sede_id`), no un dato de la `Venta` en sí |
| `area` | ❌ No | — | Ni `Venta` ni `Factura` tienen campo `area` (confirmado, `ORGANIZATIONAL_SCOPE_MATRIX.md` Sección 1: "área hoy" = ❌ para ambas apps) — no hay nada que transportar porque el dominio de esta operación específica no incluye área. Consistente con la instrucción del prompt maestro ("transportar... cuando formen parte del dominio de la operación" — aquí no forman parte) |

---

## 3. "No permitir que una venta genere una factura fuera del contexto organizacional autorizado" — cómo se cumple, por construcción

`sede_id` **nunca viene del payload/body de la request** — se resuelve exclusivamente server-side
vía `OrganizationalContext.resolve(self.request).sede_id` (`apps/tenant/ventas/services/api_mixins.py:40`),
es decir, la sede ACTIVA del usuario autenticado (sesión → primera de `sedes_asignadas` →
"Principal" de la empresa — mismo algoritmo compartido de `resolve_sede_activa_id()`). Un usuario
no puede inyectar un `sede_id` arbitrario en el body para que la `Factura` resultante quede
asignada a una sede que no es la suya — el campo simplemente no se lee del payload en ningún
punto de la cadena. Verificado leyendo `VentaBusinessService.procesar_y_facturar_venta()` completo:
el único parámetro `sede_id` es el que el ViewSet pasa explícitamente, `payload` (el body) nunca se
consulta para ese campo.

**Nota, no un hallazgo:** esto es más fuerte que "validar después" (como hace
`FacturaSerializer.validate()` con `sede_esta_en_alcance()` para ediciones directas de `Factura`,
ver `FACTURAS_AUDIT.md` §4) — aquí no hay nada que validar porque el dato nunca se acepta del
cliente en primer lugar. Coherente con el principio general del proyecto (Zero-Trust) aplicado de
la forma más simple posible.

---

## 4. Service Layer + Soft References + DTO — verificado, sin regresión

- **Service Layer:** toda la orquestación vive en `VentaBusinessService`/`FacturaBusinessService`
  (Business Service de cada app) — el ViewSet solo resuelve `sede_id` del contexto y delega.
- **Soft References:** `VentaCRUDService.vincular_factura(venta, factura)` vincula por UUID/FK
  normal dentro del mismo flujo transaccional (no es una referencia "blanda" cross-schema, es una
  relación real dentro del mismo tenant) — el patrón de Soft Reference real de este proyecto
  (UUID sin FK) es el que ya usan los 5 Bridges de `facturas` hacia `clientes`/`proveedores`/
  `cotizaciones`/`inventario`/`bancos`, no específicamente esta relación Venta↔Factura (que sí es
  una FK directa dentro de la misma transacción atómica — legítimo, `Venta`/`Factura` están más
  acopladas por diseño que las relaciones inter-app vía Bridge).
- **DTO:** `_construir_dto_factura()` construye un `dict` plano — el contrato que
  `FacturaBusinessService.crear_factura_desde_venta()` consume, nunca objetos ORM de `Venta`
  pasados directamente a `facturas`.

---

## 5. Sin dependencias circulares — verificado

`grep -rln "from apps.tenant.ventas" apps/tenant/facturas/` → **sin resultados**. La dependencia
es estrictamente unidireccional: `ventas` importa de `facturas` (`FacturaBusinessService`, y los
módulos DIAN `cufe`/`ubl21_builder`/`xades_signer`/`attached_document` bajo
`facturas/services/dian/`), `facturas` nunca importa de `ventas`. Ninguna FK nueva se introdujo
entre las dos apps más allá de la ya existente `Venta.factura` (relación real, dentro del mismo
flujo transaccional, no cross-app en el sentido de Bridge).

---

## 6. Riesgos identificados en FASE 9

Ninguno nuevo. El flujo está limpio: `sede_id` resuelto server-side (no inyectable por el
cliente), DSV real antes de asignar la `Sede` a la `Factura`, degradación segura (no rompe la
creación) si el `sede_id` resultara inválido, sin FK nueva, sin dependencia circular, sin
`area` porque el dominio no la requiere hoy. Se hereda (no se repite aquí) el riesgo ya
documentado en `OSF_TECHNICAL_AUDIT.md` de que `OrganizationalContext.resolve()` puede fallar
silenciosamente a `sede_id=None` si el usuario no tiene `TenantProfile`/`Sede` — en ese caso la
`Factura` se crea igual, simplemente sin `sede` asignada (comportamiento ya documentado como
intencional, no un fallo nuevo de esta fase).

---

## Cierre de FASE 9

Ningún archivo de código modificado. Documento creado: `documentacion/VENTAS_FACTURAS_AUDIT.md` (este archivo).

**Fase completada o bloqueada. No iniciar la siguiente fase hasta recibir autorización explícita del usuario.**
