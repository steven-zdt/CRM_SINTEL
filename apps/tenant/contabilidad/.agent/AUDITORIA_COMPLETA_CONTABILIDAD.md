# AUDITORIA COMPLETA — CONTABILIDAD APP v3.7

**Fecha de auditoría:** 2026-05-08 (actualizado post-correcciones)
**Estado:** ✅ Implementado y Funcional — Pista Manual On-Demand operativa end-to-end
**Arquitectura:** Feature-Sliced Design (FSD) + Service Layer
**Compliance:** AGENTS.md + NIIF PYMES Colombia


## 📑 Documentación Especializada (SSoT)

> [!NOTE]
> La documentación se ha fragmentado para garantizar la mantenibilidad y claridad siguiendo el estándar SINTEL v3.5.0.

| Documento | Descripción |
| :--- | :--- |
| [📂 Arquitectura y Microtareas](docs/contabilidad_microtasks_architecture.md) | Desglose atómico de responsabilidades y tareas técnicas. |
| [🗺️ Mapas de Flujo](docs/contabilidad_flow_map.md) | Diagramas Mermaid de ciclo de vida y procesos. |
| [🧠 Lógica de Negocio](docs/contabilidad_business_logic.md) | SSoT de reglas, validaciones y cálculos. |
| [🛠️ Habilidades y Scripts](skills/) | Repositorio de scripts especializados y automatizaciones del módulo. |

---



---

## 1. RESUMEN EJECUTIVO

La app `apps/tenant/contabilidad` implementa contabilidad multi-tenant completa alineada con NIIF PYMES Colombia.
Opera en **dos modos complementarios**:

| Modo | Mecanismo | Trigger |
|------|-----------|---------|
| **Automático (Pull Model)** | Extractores ETL leen apps origen y llaman `Contabilizador` | Management command / Celery |
| **Manual On-Demand** | Usuario selecciona documento pendiente, asigna cuentas PUC manualmente | UI — subtab "Pendientes" |

Ambos modos **comparten el mismo núcleo de validaciones** (cuadratura, período cerrado, nivel 6, idempotencia).
El modo manual **no depende de `ReglaContable`**: el usuario provee la cuenta PUC directamente.

---

## 2. MODELOS

### CatalogoMaestroNIIF
- Catálogo maestro de cuentas NIIF Colombia (SSoT). 124 cuentas estándar.
- Campos: `codigo`, `nombre`, `nivel` (1-6), `naturaleza` (D/C), `activa`
- Poblar: `python manage.py poblar_catalogo_niif`
- Idempotente: `update_or_create` por `codigo`

### CuentaContable
- Plan de cuentas personalizado por tenant (referencia opcional a `CatalogoMaestroNIIF`)
- Campos: `uuid`, `codigo`, `nombre`, `tipo`, `nivel`, `cuenta_padre`, `activa`
- **Regla inmutable:** Solo nivel 6 (auxiliar) puede recibir `MovimientoContable`

### AsientoContable
- Asiento contable de partida doble
- Campos clave: `uuid`, `numero` (único, auto-gen), `fecha`, `descripcion`, `estado`
- Estados: `BORRADOR → APROBADO → CERRADO` (unidireccional)
- **Trazabilidad:** `documento_origen_app`, `documento_origen_modelo`, `documento_origen_id`, `documento_origen_numero`
- **Totales:** `debe_total`, `haber_total` (campos primarios); `total_debe`, `total_haber` (legado, sincronizados via `save()`)
- **Reversales:** `documento_origen_reversado`, `asiento_reversado` (FK autorreferencial)

### MovimientoContable
- Línea de asiento (N por asiento)
- Campos: `cuenta` (FK), `cuenta_codigo` (redundante para resolución rápida), `debe`, `haber`
- Terceros: `tipo_tercero`, `tercero_id`, `tercero_nit`, `tercero_razon_social`
- Impuestos: `base_iva`, `iva_generado`, `iva_descontable`, `retefuente`, `reteica`
- Centro de costo: `centro_costo_id` (desacoplado, sin FK)

### PeriodoContable
- Período contable mensual por empresa
- Campos: `uuid`, `periodo` (YYYY-MM), `fecha_inicio`, `fecha_fin`, `estado`
- Estados: `ABIERTO` / `CERRADO`
- **Regla de inmutabilidad:** Período cerrado bloquea toda creación/edición de asientos

### ReglaContable
- Mapeo `(tipo_transaccion + concepto) → cuenta_codigo PUC` para el modo automático
- Solo usada por `ResolverCuentas` en el flujo automático
- **No interviene en el flujo manual On-Demand**
- Unicidad: una sola regla activa por `(empresa, tipo_transaccion, concepto)`

### TarifaImpuesto
- Tasas de impuesto/retención configurables por fecha de vigencia
- Tipos: IVA, RETEFUENTE, RETEICA, SALUD, PENSION, ARL, CAJA, ICBF, SENA, etc.
- Soporte art. 114-1 ET: exoneración parafiscales (`exonerado`, `base_minima_uvt`)

---

## 3. CAPA DE SERVICIOS

```
selectors.py      →  Queries optimizadas (.only, .select_related). SSoT de field sets.
crud_service.py   →  Persistencia @transaction.atomic. Sin lógica de negocio.
business_service.py → Validaciones de dominio + orquestación. DSV anti-IDOR.
```

### Métodos clave de `ContabilidadBusinessService`

| Método | Propósito |
|--------|-----------|
| `crear_asiento(empresa_id, payload)` | Asiento manual desde API directa |
| `contabilizar_documento_manual(empresa_id, dto)` | **Flujo On-Demand** — recibe `ComprobanteManualDTO` |
| `aprobar_asiento(asiento_id)` | Cambia BORRADOR → APROBADO validando cuadratura |
| `buscar_catalogo_niif_por_tipo(tipo, search)` | Búsqueda NIIF para el buscador del offcanvas |

### Métodos clave de `ContabilidadCRUDService`

| Método | Propósito |
|--------|-----------|
| `crear_asiento(empresa_id, data, movimientos)` | Persiste asiento desde flujo automático/API |
| `crear_asiento_manual(empresa_id, data, movimientos)` | **Flujo On-Demand** — soporta `documento_origen_*`, usa `debe_total`/`haber_total` |

---

## 4. CAPA DE INTEGRACIÓN — FLUJO AUTOMÁTICO (Pull Model)

```
ExtractorGastos / ExtractorFacturas / ExtractorInventario
  → extraer_pendientes() → List[TransaccionEconomica DTO]
  → Contabilizador(empresa_id).contabilizar(dto)
      → _resolver_periodo(fecha)
      → _validar_no_existe(documento_origen)      [idempotencia]
      → ResolverCuentas.resolver_cuenta(concepto, tipo_transaccion, cuenta_hint)
          → cuenta_hint > ReglaContable > ReglaContableNoDefinidaError
      → validar_cuadratura(debe, haber)
      → CRUD.crear_asiento()
```

**DTOs relevantes:**
- `TransaccionEconomica`: DTO principal (tipo, fecha, tercero, lineas, documento_origen)
- `LineaTransaccion`: Línea con concepto + monto + impuestos + cuenta_hint (override opcional)
- `DocumentoOrigen`: Trazabilidad (app_label, modelo, id, numero)

---

## 5. FLUJO MANUAL ON-DEMAND — CONTRATO Y ESTÁNDAR

### 5.1 Descripción del flujo

```
UI (subtab "Pendientes")
  → GET /api/v1/contabilidad/pendientes/
      → DocumentosPendientesViewSet.list()
      → qs_facturas_pendientes(empresa_id) + qs_gastos_pendientes(empresa_id)
      → Response: [{tipo_doc, app_label, modelo, documento_id, numero, fecha,
                    tercero_nit, tercero_nombre, subtotal, impuestos, total, estado}]
  
  → clic "Contabilizar"
  → HTMX GET /api/v1/contabilidad/pendientes/render-offcanvas/?app=X&modelo=Y&id=Z
      → get_documento_pendiente(app, modelo, id, empresa_id)  [DSV: filtra por empresa_id]
      → Template: pendiente_offcanvas_contabilizar.html
      → Offcanvas con resumen del documento + tabla de líneas dinámicas

  → Usuario asigna cuentas PUC + montos Debe/Haber por línea
  → Validación JS: |ΣDebe - ΣHaber| < 0.01 antes de habilitar "Generar Asiento"
  
  → POST /api/v1/contabilidad/pendientes/contabilizar-manual/
      → ContabilizarManualInputSerializer.validate()
      → DocumentosPendientesViewSet.contabilizar_manual()
      → ContabilidadBusinessService.contabilizar_documento_manual(empresa_id, ComprobanteManualDTO)
          1. Idempotencia: ¿existe AsientoContable con mismo documento_origen_*?
          2. Periodo abierto: verificar_periodo_cerrado(fecha, empresa_id)
          3. Resolver cuenta_codigo → cuenta_id + validar nivel == 6
          4. Validar cuadratura (APROBADO)
          5. Generar numero: "MAN-YYYYMMDD-XXXXXXXX"
          6. CRUD.crear_asiento_manual() → AsientoContable + MovimientoContable[]
      → Response 201: {id, uuid, numero}
  
  → JS dispara 'pendientes:refresh' → tabla recarga
```

### 5.2 DTOs del flujo manual

```python
# integracion/dtos.py

@dataclass(frozen=True)
class LineaManual:
    cuenta_codigo: str          # PUC nivel 6 — obligatorio, asignado por el usuario
    debe: Decimal = Decimal('0')
    haber: Decimal = Decimal('0')
    descripcion: str = ''
    tercero_nit: str = ''
    tercero_razon_social: str = ''
    centro_costo_id: Optional[int] = None

@dataclass(frozen=True)
class ComprobanteManualDTO:
    empresa_id: int
    fecha: date
    descripcion: str
    app_label: str              # 'facturas' | 'gastos' | <nueva_app>
    modelo: str                 # 'Factura' | 'DocumentoSoporte' | <nuevo_modelo>
    documento_id: int
    documento_numero: str
    lineas: list                # List[LineaManual], mínimo 2
```

### 5.3 Contrato para agregar una nueva app origen

Para que **cualquier app de negocio** (ej. `cotizaciones`, `proyectos`, `empleados`) aparezca en la lista de Pendientes y sea contabilizable manualmente, se requieren exactamente **4 pasos**:

#### Paso 1 — Selector en `services/selectors.py`

```python
PENDIENTE_<APP>_FIELDS = ('id', '<numero_field>', '<fecha_field>', '<subtotal>', '<total>', ...)

def qs_<app>_pendientes(empresa_id: int):
    from apps.tenant.<app>.models import <Modelo>
    ya_ids = AsientoContable.objects.filter(
        empresa_id=empresa_id,
        documento_origen_app='<app>',
        documento_origen_modelo='<Modelo>',
        documento_origen_id__isnull=False,
    ).values_list('documento_origen_id', flat=True)
    return (
        <Modelo>.objects.filter(empresa_id=empresa_id, <activo_filter>)
        .exclude(id__in=ya_ids)
        .only(*PENDIENTE_<APP>_FIELDS)
        .order_by('-<fecha_field>')
    )
```

#### Paso 2 — Registro en `get_documento_pendiente()` en `selectors.py`

```python
def get_documento_pendiente(app_label, modelo, documento_id, empresa_id):
    ...
    if app_label == '<app>' and modelo == '<Modelo>':
        from apps.tenant.<app>.models import <Modelo>
        return <Modelo>.objects.filter(empresa_id=empresa_id, id=documento_id).first()
    return None
```

#### Paso 3 — Registro en `DocumentosPendientesViewSet` en `viewsets.py`

En el método `list()`, agregar el bloque de iteración:

```python
for obj in qs_<app>_pendientes(empresa_id):
    resultado.append({
        'tipo_doc': '<TIPO>',
        'app_label': '<app>',
        'modelo': '<Modelo>',
        'documento_id': obj.id,
        'numero': obj.<numero_field>,
        'fecha': str(obj.<fecha_field>),
        'tercero_nit': obj.<tercero_nit_field>,
        'tercero_nombre': obj.<tercero_nombre_field>,
        'subtotal': str(obj.<subtotal>),
        'impuestos': str(obj.<impuestos>),
        'total': str(obj.<total>),
        'estado': obj.<estado> or 'ACTIVO',
    })
```

En el método `render_offcanvas_contabilizar()`, agregar el bloque de contexto:

```python
elif app_label == '<app>':
    ctx = {
        'app_label': app_label, 'modelo': modelo, 'documento_id': documento_id,
        'numero': doc.<numero_field>, 'fecha': doc.<fecha_field>,
        'subtotal': doc.<subtotal>, 'impuestos': doc.<impuestos>, 'total': doc.<total>,
        'tercero_nit': doc.<tercero_nit_field>, 'tercero_nombre': doc.<tercero_nombre_field>,
    }
```

#### Paso 4 — Actualizar `ContabilizarManualInputSerializer`

Agregar el nuevo valor a los `ChoiceField`:

```python
app_label = serializers.ChoiceField(choices=['facturas', 'gastos', '<app>'])
modelo = serializers.ChoiceField(choices=['Factura', 'DocumentoSoporte', '<Modelo>'])
```

**No se requiere ningún cambio en `business_service.py` ni en el CRUD** — el flujo de validación es genérico.

---

## 5.4 ORQUESTACIÓN DE CONTRAPARTIDAS (v3.7.1 - Arquitectura §18)

### Contexto

A partir de v3.7.1, **contabilidad es responsable única de determinar contrapartidas** para todos los documentos origen. Las apps source (facturas, gastos, empleados, inventario, proveedores, clientes) solo proporcionan:
- UUID de cuenta principal (opaco, sin FK)
- Metadatos del documento (fecha, tercero, montos)

**Beneficios:**
- ✅ Separación de responsabilidades (negocio vs. orquestación)
- ✅ Centralización de reglas contables
- ✅ Escalabilidad (cambios a contrapartidas = 1 lugar)
- ✅ Coherencia en 6 apps

### Patrón uniforme (6 apps source)

Todas las apps siguen el mismo patrón:

| App | Campo Principal | Responsabilidad |
|-----|-----------------|------------------|
| `clientes.Cliente` | `cuenta_contable_uuid` | Cartera (CxC) |
| `facturas.Factura` | `cuenta_contable_uuid` | Ingresos/Compras |
| `inventario.Producto` | 3x `cuenta_*_uuid` | Inventario + Gasto |
| `empleados.Devengo` | `cuenta_contable_uuid` | Nómina |
| `proveedores.Proveedor` | `cuenta_contable_uuid` | CxP |
| `gastos.DocumentoSoporte` | `cuenta_gasto_uuid` | Gastos/Egresos |

**Contrapartida:** Determinada por **contabilidad** según:
- Tipo de transacción (venta, compra, gasto, nómina, etc.)
- Reglas fiscales (art. 100-160 estatuto tributario)
- Políticas contables del tenant

### Implementación en ExtractorGastos (próxima fase)

```python
# apps/tenant/contabilidad/integracion/extractores/gastos.py

class ExtractorGastos(AbstractExtractor):
    def extraer_pendientes(self):
        # Lee DocumentoSoporte con cuenta_gasto_uuid
        qs = DocumentoSoporte.objects.filter(
            empresa_id=self.empresa_id,
            cuenta_gasto_uuid__isnull=False
        ).only(
            'id', 'numero', 'fecha', 'subtotal',
            'retefuente', 'reteica',
            'proveedor__nit', 'proveedor__razon_social',
            'cuenta_gasto_uuid'  # ← UUID opaco
        )
        
        for doc in qs:
            # Paso 1: Usar cuenta_gasto_uuid del documento
            cuenta_gasto_uuid = doc.cuenta_gasto_uuid
            
            # Paso 2: Contabilidad determina contrapartida
            contrapartida = self._resolver_contrapartida(
                tipo_transaccion='GASTO',
                subtipo='DocumentoSoporte',
                cuenta_principal_uuid=cuenta_gasto_uuid,
                metadatos={
                    'fecha': doc.fecha,
                    'monto': doc.subtotal,
                    'retefuente': doc.retefuente,
                    'reteica': doc.reteica,
                }
            )
            
            # Paso 3: Generar TransaccionEconomica con ambas cuentas
            lineas = [
                LineaTransaccion(
                    concepto="GASTO_PRINCIPAL",
                    monto=doc.subtotal,
                    cuenta_hint=str(cuenta_gasto_uuid),
                    lado='DEBE'
                ),
                LineaTransaccion(
                    concepto="CONTRAPARTIDA_AUTOMÁTICA",
                    monto=doc.subtotal,
                    cuenta_hint=contrapartida.uuid,  # ← Determinada aquí
                    lado='HABER'
                )
            ]
            
            yield TransaccionEconomica(
                tipo=TipoTransaccion.GASTO,
                fecha=doc.fecha,
                tercero=TerceroSnapshot(...),
                lineas=lineas,
                documento_origen=DocumentoOrigen(
                    app_label='gastos',
                    modelo='DocumentoSoporte',
                    id=doc.id,
                    numero=doc.numero
                )
            )

    def _resolver_contrapartida(self, tipo_transaccion, subtipo, cuenta_principal_uuid, metadatos):
        """
        Lógica central de orquestación de contrapartidas.
        Aquí vive toda la regla contable.
        """
        # Consultar tabla de reglas (próxima iteración)
        regla = ReglasOrquestacion.objects.filter(
            empresa_id=self.empresa_id,
            tipo_transaccion=tipo_transaccion,
            subtipo=subtipo,
        ).first()
        
        if not regla:
            raise OrquestacionNoDefinidaError(f"...")
        
        # Aplicar regla (puede ser condicional: depende de metadatos)
        if regla.estrategia == 'BANCOS_O_CXP':
            # Ejemplo: si fecha < fecha_pago → 2205 (CxP); si >= → 1110 (Bancos)
            if metadatos['fecha'] >= regla.fecha_umbral_pago:
                return regla.cuenta_contrapartida  # 1110
            else:
                return regla.cuenta_alternativa    # 2205
        
        return regla.cuenta_contrapartida
```

### Nueva tabla: `ReglasOrquestacion`

```python
# apps/tenant/contabilidad/models.py (futuro)

class ReglasOrquestacion(models.Model):
    """
    Reglas configurables para determinación automática de contrapartidas.
    Permite que cada tenant customice su flujo contable.
    """
    empresa = ForeignKey(Empresa, on_delete=models.CASCADE)
    tipo_transaccion = CharField(
        choices=[
            ('GASTO', 'Gasto'),
            ('VENTA', 'Venta'),
            ('COMPRA', 'Compra'),
            ('NOMINA', 'Nómina'),
            ('AJUSTE', 'Ajuste'),
        ]
    )
    subtipo = CharField(max_length=50)  # 'DocumentoSoporte', 'Factura', etc.
    
    # Cuenta principal (viene desde app origen)
    cuenta_principal_uuid = UUIDField()
    
    # Contrapartida (decidida por contabilidad)
    cuenta_contrapartida = ForeignKey(CuentaContable, ...)
    cuenta_alternativa = ForeignKey(CuentaContable, ...)  # Para estrategias condicionales
    
    # Estrategia de determinación
    estrategia = CharField(
        choices=[
            ('FIJA', 'Cuenta fija'),
            ('BANCOS_O_CXP', 'Condicional: bancos o cuentas por pagar'),
            ('SEGUN_POLITICA', 'Según política fiscal del tenant'),
        ]
    )
    
    # Parámetros (JSON flexible para soportar cualquier regla)
    parametros = JSONField(default=dict)
    
    activa = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('empresa', 'tipo_transaccion', 'subtipo')
        verbose_name_plural = "Reglas de Orquestación"
```

### Transición de Extractores Existentes

**Fase 1 (ahora):** Manual On-Demand — usuario asigna ambas cuentas (gasto + contrapartida)

**Fase 2 (próxima):** Automático — extractores usan `ReglasOrquestacion` para determinar contrapartida

```python
# Transición suave: ambos modos coexisten
if documento.cuenta_contrapartida_uuid_explícita:
    # Modo manual: usar lo que asignó el usuario
    contrapartida = documento.cuenta_contrapartida_uuid_explícita
else:
    # Modo automático: resolver via reglas
    contrapartida = self._resolver_contrapartida(...)
```

---

## 6. API REST

### Endpoints existentes

```
GET/POST   /api/v1/contabilidad/cuentas-contables/
GET/PATCH  /api/v1/contabilidad/cuentas-contables/{uuid}/
           /api/v1/contabilidad/cuentas-contables/{uuid}/render-offcanvas/crear/
           /api/v1/contabilidad/cuentas-contables/{uuid}/render-offcanvas/editar/
           /api/v1/contabilidad/cuentas-contables/{uuid}/render-offcanvas/detalle/

GET/POST   /api/v1/contabilidad/asientos-contables/
GET/PATCH  /api/v1/contabilidad/asientos-contables/{uuid}/
POST       /api/v1/contabilidad/asientos-contables/{uuid}/aprobar/
GET        /api/v1/contabilidad/asientos-contables/balance_prueba/

GET        /api/v1/contabilidad/movimientos-contables/
GET        /api/v1/contabilidad/periodos-contables/
POST       /api/v1/contabilidad/periodos-contables/
GET        /api/v1/contabilidad/catalogo-niif/
GET        /api/v1/contabilidad/catalogo-niif/buscar-por-tipo/?tipo=GASTO&search=PERSONAL
GET        /api/v1/contabilidad/tipos-comprobante/

# FLUJO ON-DEMAND (nuevo v3.6)
GET        /api/v1/contabilidad/pendientes/
GET        /api/v1/contabilidad/pendientes/render-offcanvas/?app=&modelo=&id=
POST       /api/v1/contabilidad/pendientes/contabilizar-manual/
```

### Seguridad

- Permisos: `IsTenantMember + IsTenantAdminOrReadOnly` en todos los endpoints
- Lookup field: `uuid` (no expone PK entero)
- DSV en `render-offcanvas`: `get_documento_pendiente()` filtra por `empresa_id` antes de retornar contexto
- Idempotencia: verificación `documento_origen_*` antes de crear asiento

---

## 7. VALIDACIONES DEL FLUJO MANUAL (garantías en Business Service)

| Validación | Donde | Qué hace si falla |
|-----------|-------|------------------|
| Idempotencia | `business_service.contabilizar_documento_manual()` | `ValidationError 400: El documento X ya fue contabilizado` |
| Periodo abierto | `_validar_periodo(fecha, empresa_id)` | `ValidationError 400: Periodo cerrado` |
| Cuenta existe y activa | Loop de resolución en `contabilizar_documento_manual()` | `ValidationError 400: Cuenta X no existe o está inactiva` |
| Cuenta nivel 6 | Loop de resolución | `ValidationError 400: Cuenta X no es auxiliar (nivel N)` |
| Cuadratura | `_validar_cuadratura(movimientos, 'APROBADO')` | `ValidationError 400: AsientoNoCuadrado` |
| Mínimo 2 líneas | `ContabilizarManualInputSerializer.validate_lineas()` | `ValidationError 400: mínimo 2 líneas` |
| Debe XOR Haber | `LineaManualInputSerializer.validate()` | `ValidationError 400: no puede tener debe Y haber` |
| Monto > 0 por línea | `LineaManualInputSerializer.validate()` | `ValidationError 400: debe > 0 o haber > 0` |
| Cuadratura frontend | JS: `|ΣDebe - ΣHaber| < 0.01` | Botón "Generar Asiento" permanece deshabilitado |
| DSV tenant | `get_empresa_id()` en ViewSet | `403 Forbidden` |
| DSV documento | `get_documento_pendiente(empresa_id=empresa_id)` | `404 Not Found` |

---

## 8. FRONTEND — MÓDULO PENDIENTES

### Templates

| Archivo | Propósito |
|---------|-----------|
| `partials/pendientes_list.html` | Toolbar + grid Tabulator |
| `partials/pendiente_offcanvas_contabilizar.html` | Resumen documento + tabla líneas dinámicas + submit |
| `partials/assets_pendientes.html` | Carga de scripts |

### JS

| Archivo | Propósito |
|---------|-----------|
| `static/contabilidad/js/pendiente/pendiente_list.js` | TabulatorFactory + filtros + delegación click + evento `pendientes:refresh` |

### Comportamiento del offcanvas

1. Muestra resumen readonly del documento (numero, fecha, tercero, subtotal, impuestos, total)
2. Tabla de líneas dinámica (agregar/eliminar)
3. Cada línea: buscador live de `CuentaContable` (autocompletado por código/nombre), campo Debe, campo Haber, Descripción
4. Footer con totales Debe/Haber en tiempo real + badge "Cuadrado" / "Sin cuadrar"
5. Botón "Generar Asiento" habilitado solo cuando cuadratura es exacta (tolerancia 0.01)
6. Submit via `fetch POST` con JWT. Al éxito: cierra offcanvas + dispara `pendientes:refresh`

### Buscador de cuentas en el offcanvas (con filtro contextual v3.7)

Usa `GET /api/v1/contabilidad/cuentas-contables/?search=X&activa=true&page_size=8&app_origen=<app_label>`.

El parámetro `app_origen` es inyectado automáticamente por el JS del offcanvas (`APP_LABEL` viene del contexto Django). En el backend, `CuentaContableViewSet.get_queryset()` aplica `filtrar_cuentas_por_app_origen(qs, app_origen)` que filtra por prefijos PUC relevantes para esa app:

| `app_origen` | Prefijos PUC priorizados | Cuentas nivel-6 disponibles |
|---|---|---|
| `facturas` | 1305, 1355, 4135, 4175, 240805, 2365, 2368 | 14 |
| `gastos` | 2335, 2365, 2368, 240810, 5110-5199 | 25 |
| `empleados` | 5105, 2370, 2380, 2505-2525 | 13 |
| `inventario` | 1435, 6135, 4135, 5199 | 6 |

Sin `app_origen`, retorna todas las cuentas activas del tenant (comportamiento anterior intacto).

---

## 9. INVENTARIO COMPLETO

| Componente | Ruta | Estado |
|-----------|------|--------|
| Modelos | `models.py` | ✅ 7 modelos |
| Selectors | `services/selectors.py` | ✅ Pendientes + `APP_ORIGEN_PREFIJOS` + `filtrar_cuentas_por_app_origen()` |
| CRUD Service | `services/crud_service.py` | ✅ `crear_asiento_manual()` con `tipo_comprobante_ref_id` |
| Business Service | `services/business_service.py` | ✅ `contabilizar_documento_manual()` + TipoComprobante numero |
| API Viewsets | `api/viewsets.py` | ✅ 7 ViewSets — `ReglaContable` importado, `app_origen` filter |
| API Serializers | `api/serializers.py` | ✅ `ContabilizarManualInputSerializer` con `tipo_comprobante_id` |
| API URLs | `api/urls.py` | ✅ Router `pendientes` registrado |
| DTOs | `integracion/dtos.py` | ✅ `LineaManual` + `ComprobanteManualDTO` con `tipo_comprobante_id` |
| Contabilizador | `integracion/contabilizador.py` | ✅ Flujo automático |
| Resolvedor | `integracion/resolver.py` | ✅ cuenta_hint > ReglaContable |
| Validadores | `integracion/validadores.py` | ✅ Cuadratura, periodo, vacío |
| Excepciones | `integracion/excepciones.py` | ✅ Jerarquía completa |
| Templates | `templates/tenant/contabilidad/` | ✅ 26 archivos |
| Static JS | `static/contabilidad/js/` | ✅ 13 archivos — `TabulatorFactory` en pendiente_list.js |
| Migraciones | `migrations/` | ✅ 5 migraciones aplicadas |
| Mgmt Commands | `management/commands/` | ✅ `poblar_catalogo_niif`, `seed_reglas_contables` |
| Catálogo NIIF | DB (home, cliente) | ✅ 124 cuentas maestras |
| CuentaContable nivel-6 | DB (home, cliente) | ✅ 54 cuentas seeded desde CatalogoMaestroNIIF |
| TipoComprobante | DB (home, cliente) | ✅ 6 tipos: CE, RC, GN, ND, NC, NOM |

---

## 10. COMPLIANCE

| Estándar | Estado |
|----------|--------|
| Feature-Sliced Design | ✅ |
| Service Layer (selector → CRUD → business) | ✅ |
| Multi-Tenant (django-tenants) | ✅ |
| Zero-Waste Queries (.only, .select_related) | ✅ |
| API-First Design (DRF ViewSets) | ✅ |
| Double Semantic Verification (DSV) | ✅ |
| NIIF PYMES Colombia (PUC nivel 6) | ✅ |
| Inmutabilidad (Períodos Cerrados) | ✅ |
| Idempotencia (documento_origen_*) | ✅ |
| Transacciones atómicas (@transaction.atomic) | ✅ |
| Partida Doble estricta | ✅ |
| UUID lookup (no exponer PK) | ✅ |
| No emojis en .py (SyntaxError prevention) | ✅ |
| empresa_id en toda query tenant | ✅ |
| TabulatorFactory obligatorio (cero new Tabulator()) | ✅ |
| AGENTS.md Compliance | ✅ |

---

## 11. ESTADO DE CONECTIVIDAD

| App Origen | Campo Principal | Contrapartida | Flujo Manual | Cuentas Disponibles |
|-----------|-----------------|---------------|-------------|-------------------|
| `facturas.Factura` | `cuenta_contable_uuid` | **Contabilidad orquesta** | ✅ Activo (4) | 14 (prefijos 1305, 4135…) |
| `gastos.DocumentoSoporte` | `cuenta_gasto_uuid` | **Contabilidad orquesta** | ✅ Activo (1) | 25 (prefijos 2335, 5110…) |
| `empleados.Devengo` | `cuenta_contable_uuid` | **Contabilidad orquesta** | ✅ Activo | 13 (prefijos 5105, 2370…) |
| `inventario.Producto` | 3x `cuenta_*_uuid` | **Contabilidad orquesta** | ✅ Activo | 6 (prefijos 1435, 6135…) |
| `proveedores.Proveedor` | `cuenta_contable_uuid` | **Contabilidad orquesta** | ✅ Activo | 25 (prefijos 2335, 5110…) |
| `clientes.Cliente` | `cuenta_contable_uuid` | **Contabilidad orquesta** | ✅ Activo | 14 (prefijos 1305, 4135…) |
| `cotizaciones.*` | — | — | ⏳ 4 pasos (ver §5.3) | — |

### Arquitectura de Orquestación (v3.7.1)

**Patrón uniforme:** Todas las 6 apps proporcionan UUID opaco → Contabilidad determina contrapartida

| Fase | Status | Responsabilidad |
|------|--------|-----------------|
| **Fase 1 (Ahora)** | ✅ Live | Usuario asigna ambas cuentas en offcanvas |
| **Fase 2 (Próxima)** | 📋 Planeada | ExtractorGastos/Facturas/etc. usan `ReglasOrquestacion` |
| **Fase 3** | 📋 Opcional | Dashboard de configuración de reglas por tenant |

### Datos de referencia (schema home — verificados 2026-05-13)

| Dato | Valor |
|------|-------|
| `CatalogoMaestroNIIF` (maestro) | 124 cuentas |
| `CuentaContable` total | 61 (54 nivel-6 + 7 legacy) |
| `TipoComprobante` activos | 6 (CE, RC, GN, ND, NC, NOM) |
| `AsientoContable` creados | 3 |
| `ReglaContable` activas | 0 (flujo manual no las requiere) |
| `ReglasOrquestacion` (nuevo) | 0 (tablaCreada pero vacía — próxima iteración) |

### Apps Source Status (Auditoría §18 - v3.7.1)

✅ **100% Compliant — Patrón Uniforme:**
- ✅ Clientes — UUID opaco en modelo, serializer, migración
- ✅ Facturas — UUID opaco en modelo, serializer, migración
- ✅ Inventario — 3x UUID opaco, serializers actualizados
- ✅ Empleados — UUID opaco, property removida, serializer actualizado
- ✅ Proveedores — UUID opaco, métodos removidos, serializer actualizado
- ✅ Gastos — UUID opaco único (`cuenta_gasto_uuid`), contrapartida removida, migración 0014

---

**Auditoría completada:** 2026-05-13 (v3.7.1 — Orquestación de Contrapartidas)
**Próxima revisión:** Tras implementar ExtractorGastos y `ReglasOrquestacion`

