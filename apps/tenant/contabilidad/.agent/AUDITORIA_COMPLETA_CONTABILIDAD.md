# AUDITORIA COMPLETA - CONTABILIDAD APP v3.9.1

**Fecha de auditoria:** 2026-05-25 (validado contra codigo local)
**Estado:** Implementado y funcional con deuda tecnica documentada
**Arquitectura:** Feature-Sliced Design (FSD) + Service Layer
**Compliance:** AGENTS.md + NIIF PYMES Colombia

> Nota de auditoria 2026-05-25: este documento fue contrastado con `models.py`, `api/viewsets.py`, `api/serializers.py`, `api/urls.py`, `services/`, `integracion/`, `tasks.py`, `templates/`, `static/` y `tests/`. Los conteos y estados inferiores reflejan el codigo local actual, no solo la intencion historica.


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

### ConfiguracionRetenciones
- Configuracion por tenant para retenciones por tipo de tercero, NIT opcional y tipo de retencion.
- Permite reglas especificas por tercero y reglas fallback generales.
- Campo clave: `cuenta_retencion` apunta a `CuentaContable` para contabilizacion posterior.
- Expuesto por API en `/api/v1/contabilidad/configuraciones-retenciones/`.

### Retencion
- Registro materializado de retenciones aplicadas a documentos origen (`Factura`, `NotaCredito`, `ItemFactura`, `DocumentoSoporte`, etc.).
- Campos de trazabilidad: `documento_origen_app`, `documento_origen_modelo`, `documento_origen_id`, `documento_origen_numero`.
- Soporta reversas mediante campos `reversada`, `documento_reversada_*` y enlace a configuracion aplicada.
- Expuesto por API en `/api/v1/contabilidad/retenciones/` y consultable por tercero/documento.

---

## 3. CAPA DE SERVICIOS

```
selectors.py      →  Queries optimizadas (.only, .select_related). SSoT de field sets.
crud_service.py   →  Persistencia @transaction.atomic. Sin lógica de negocio.
business_service.py → Validaciones de dominio + orquestación. DSV anti-IDOR.
retenciones_service.py → Reglas de retenciones materializadas y reversas.
api_mixins.py      → Mixins por modelo para inyectar selectors/business/crud.
```

### Métodos clave de `ContabilidadBusinessService`

| Método | Propósito |
|--------|-----------|
| `crear_asiento(empresa_id, payload)` | Asiento manual desde API directa |
| `contabilizar_documento_manual(empresa_id, dto)` | **Flujo On-Demand** — recibe `ComprobanteManualDTO` |
| `aprobar_asiento(asiento_id)` | Cambia BORRADOR → APROBADO validando cuadratura |
| `buscar_catalogo_niif_por_tipo(tipo, search)` | Búsqueda NIIF para el buscador del offcanvas |
| `sincronizar_cuentas_plan(empresa_id)` | Materializa `CatalogoMaestroNIIF` faltante en `CuentaContable` |
| `ejecutar_integracion_completa(empresa_id)` | Punto de entrada para tareas Celery/backfill de extractores |
| `sugerir_lineas_asiento_ia(empresa_id, app_label, ctx)` | Sugiere lineas contables desde contexto del documento |

### Métodos clave de `ContabilidadCRUDService`

| Método | Propósito |
|--------|-----------|
| `crear_asiento(empresa_id, data, movimientos)` | Persiste asiento desde flujo automático/API |
| `crear_asiento_manual(empresa_id, data, movimientos)` | **Flujo On-Demand** — soporta `documento_origen_*`, usa `debe_total`/`haber_total` |

### Métodos clave de `RetencionesService`

| Método | Propósito |
|--------|-----------|
| `obtener_retenciones_desde_tercero()` | Resuelve configuraciones aplicables por tercero y tipo de documento |
| `calcular_monto_retencion()` | Calcula monto segun porcentaje y base |
| `crear_retencion()` / `crear_retenciones_desde_dict()` | Materializa retenciones en `Retencion` |
| `listar_retenciones_por_documento()` | Consulta retenciones por documento origen |
| `reversar_retencion()` | Crea reversa trazable de una retencion existente |

---

## 4. CAPA DE INTEGRACIÓN — FLUJO AUTOMÁTICO (Pull Model)

```
ExtractorGastos / ExtractorFacturas / ExtractorNomina
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

A partir de v3.9.2, **contabilidad no mapea directamente productos ni movimientos de inventario**. Las apps source (facturas, gastos, empleados, proveedores, clientes) solo proporcionan:
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
| `inventario.Producto` | 3x `cuenta_*_uuid` | Fuera de Contabilidad Pendientes; mapeo centralizado en Inventario / Movimientos Recientes |
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

> Estado 2026-05-25: `ReglasOrquestacion` no existe en el codigo local. El bloque inferior es propuesta de arquitectura futura y debe adaptarse antes de implementarse: al ser modelo tenant debe heredar de `SintelTenantBaseModel`, no de `models.Model`, y debe respetar la estructura autorizada de migrations/service layer.

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
GET        /api/v1/contabilidad/libro-diario/
GET/POST   /api/v1/contabilidad/retenciones/
GET/PATCH  /api/v1/contabilidad/retenciones/{uuid}/
GET        /api/v1/contabilidad/retenciones/obtener-por-tercero/
GET        /api/v1/contabilidad/retenciones/obtener-por-documento/
GET/POST   /api/v1/contabilidad/configuraciones-retenciones/
GET/PATCH  /api/v1/contabilidad/configuraciones-retenciones/{uuid}/

# FLUJO ON-DEMAND (nuevo v3.6)
GET        /api/v1/contabilidad/pendientes/
GET        /api/v1/contabilidad/pendientes/render-offcanvas/?app=&modelo=&id=
POST       /api/v1/contabilidad/pendientes/contabilizar-manual/
POST       /api/v1/contabilidad/pendientes/asistente-ia/
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
| Modelos | `models.py` | 10 modelos: Catalogo, Cuenta, TipoComprobante, Asiento, Movimiento, Periodo, Regla, Tarifa, ConfiguracionRetenciones, Retencion |
| Selectors | `services/selectors.py` | ✅ Pendientes + `APP_ORIGEN_PREFIJOS` + `filtrar_cuentas_por_app_origen()` |
| CRUD Service | `services/crud_service.py` | ✅ `crear_asiento_manual()` con `tipo_comprobante_ref_id` |
| Business Service | `services/business_service.py` | ✅ `contabilizar_documento_manual()` + TipoComprobante numero + integracion completa + asistente IA |
| Retenciones Service | `services/retenciones_service.py` | ✅ Pull Model de retenciones, materializacion y reversas |
| API Viewsets | `api/viewsets.py` | 10 ViewSets: cuentas, asientos, movimientos, periodos, catalogo, tipos, pendientes, libro diario, retenciones, configuraciones |
| API Serializers | `api/serializers.py` | ✅ `ContabilizarManualInputSerializer` con `tipo_comprobante_id` |
| API URLs | `api/urls.py` | ✅ Router DRF con `pendientes`, `libro-diario`, `retenciones`, `configuraciones-retenciones` |
| DTOs | `integracion/dtos.py` | ✅ `LineaManual` + `ComprobanteManualDTO` con `tipo_comprobante_id` |
| Contabilizador | `integracion/contabilizador.py` | ✅ Flujo automático |
| Resolvedor | `integracion/resolver.py` | ✅ cuenta_hint > ReglaContable |
| Validadores | `integracion/validadores.py` | ✅ Cuadratura, periodo, vacío |
| Excepciones | `integracion/excepciones.py` | ✅ Jerarquía completa |
| Extractores | `integracion/extractores/` | gastos, facturas, nomina; inventario se consume por Movimientos Recientes, no por extractor directo |
| Templates | `templates/tenant/contabilidad/` | 31 archivos HTML bajo ruta tenant |
| Static JS | `static/contabilidad/js/` | 14 archivos JS por dominio: asiento, cuenta, periodo, pendiente, libro, reporte |
| Migraciones | `migrations/` | 7 migraciones presentes (`0001` a `0007`) |
| Mgmt Commands | `management/commands/` | `poblar_catalogo_niif`, `seed_reglas_contables`, `backfill_contabilidad`, `migrate_retenciones` |
| Catálogo NIIF | DB (home, cliente) | ✅ 124 cuentas maestras |
| CuentaContable nivel-6 | DB (home, cliente) | ✅ 54 cuentas seeded desde CatalogoMaestroNIIF |
| TipoComprobante | DB (home, cliente) | ✅ 6 tipos: CE, RC, GN, ND, NC, NOM |

---

## 10. COMPLIANCE

| Estándar | Estado |
|----------|--------|
| Feature-Sliced Design | OK |
| Service Layer (selector -> CRUD -> business) | OK, con deuda puntual en ViewSets que aun persisten directamente |
| Multi-Tenant (django-tenants) | OK |
| Zero-Waste Queries (.only, .select_related) | Parcial: ver hallazgos AUD-2026-05-25 |
| API-First Design (DRF ViewSets) | OK |
| Double Semantic Verification (DSV) | OK en endpoints principales; revisar acciones auxiliares en cada cambio |
| NIIF PYMES Colombia (PUC nivel 6) | OK en flujo automatico; manual permite cuenta activa aunque no sea nivel 6 por decision v3.7.5 |
| Inmutabilidad (Periodos Cerrados) | OK |
| Idempotencia (documento_origen_*) | OK |
| Transacciones atomicas (@transaction.atomic) | OK en persistencia principal |
| Partida Doble estricta | OK |
| UUID lookup (no exponer PK) | OK en ViewSets BaseTenantViewSet; `LibroDiarioViewSet` es read-only sin lookup |
| No emojis en .py (SyntaxError prevention) | Validado con `py_compile` en archivos modificados |
| empresa_id en toda query tenant | Parcial: hallazgos en comandos/scripts y queries legacy |
| TabulatorFactory obligatorio (cero new Tabulator()) | OK en modulos inspeccionados |
| AGENTS.md Compliance | Parcial con deuda tecnica documentada |

### Hallazgos de auditoria 2026-05-25

| ID | Severidad | Archivo | Hallazgo | Accion recomendada |
|----|-----------|---------|----------|--------------------|
| AUD-CONT-001 | Alta | `api/viewsets.py` | Corregido 2026-05-25: `TipoComprobanteViewSet.get_queryset()` usa `TipoComprobanteSelector` con `only()` y filtro por `empresa_id`. | Revalidar en pruebas API. |
| AUD-CONT-002 | Media | `api/viewsets.py` | Corregido 2026-05-25: `CatalogoMaestroNIIFViewSet.get_queryset()` mantiene `prefetch_related()` pero agrega `only()` en rama detalle. | Revalidar si el serializer requiere campos adicionales. |
| AUD-CONT-003 | Media | `services/business_service.py` | Corregido 2026-05-25: `_obtener_o_crear_cuenta()` consulta `CatalogoMaestroNIIF` y `Empresa` con campos minimos. | Revalidar flujo manual de cuenta auto-creada. |
| AUD-CONT-004 | Media | `management/commands/migrate_retenciones.py` | Corregido 2026-05-25: elimina `.all()`, usa `only()`, `select_related()`, `iterator()` y asigna `empresa_id` en `Retencion`. | Revalidar command con `--dry-run`. |
| AUD-CONT-005 | Baja | `api/datatables.py` | No expuesto: `api/urls.py` mantiene endpoints DataTables comentados/eliminados. | Remover archivo legacy en una tarea de limpieza autorizada. |
| AUD-CONT-006 | Baja | `scratch/` | No productivo: scripts permanecen fuera de rutas de ejecucion. | Mantener como tooling o mover fuera de la app en limpieza futura. |

---

## 11. ESTADO DE CONECTIVIDAD

| App Origen | Campo Principal | Contrapartida | Flujo Manual | Cuentas Disponibles |
|-----------|-----------------|---------------|-------------|-------------------|
| `facturas.Factura` | `cuenta_contable_uuid` | Contabilidad orquesta | Activo en `pendientes` y extractores | 14 (prefijos 1305, 4135...) |
| `facturas.NotaCredito` | trazabilidad desde factura | Contabilidad orquesta | Activo en extractor automatico | 14 (prefijos 1305, 4135...) |
| `gastos.DocumentoSoporte` | `cuenta_gasto_uuid` | Contabilidad orquesta | Activo en `pendientes` y extractores | 25 (prefijos 2335, 5110...) |
| `empleados.Devengo` | `cuenta_contable_uuid` | Contabilidad orquesta | Activo en `pendientes` y extractor nomina | 13 (prefijos 5105, 2370...) |
| `inventario.Movimientos Recientes` | `get_movimientos_timeline()` | Inventario / Movimientos Recientes | Activo en `pendientes` via agregado; modelos `MovimientoInventario` / `HistorialServicio` | 6 (prefijos 1435, 6135...) |
| `proveedores.Proveedor` | `cuenta_contable_uuid` | Solo como tercero/cuenta origen | No registrado como documento pendiente directo | 25 (prefijos 2335, 5110...) |
| `clientes.Cliente` | `cuenta_contable_uuid` | Solo como tercero/cuenta origen | No registrado como documento pendiente directo | 14 (prefijos 1305, 4135...) |
| `cotizaciones.*` | - | - | Pendiente: requiere 4 pasos (ver §5.3) | - |

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

---

## 12. BOUNDARY GARANTIZADO — CONTABILIDAD <-> EMPLEADOS (v3.10.2)

**Regla:** Contabilidad SOLO puede consumir datos de Empleados a traves del modelo `Devengo` (nominas).
No esta permitido importar ni consultar `Empleado`, `Contrato` ni ningun otro modelo de la app empleados.

### Contrato de la unica via permitida

```
Contabilidad                           Empleados
-----------                            ---------
integracion/extractores/nomina.py  ─→  Devengo (solo via FK empleado para nombre/documento)
services/selectors.py               ─→  Devengo (get_documento_pendiente, qs_nominas_pendientes)
```

### Auditoria de Imports (2026-05-25)

| Archivo contabilidad | Import de empleados | Modelo | Estado |
|---------------------|---------------------|--------|--------|
| `integracion/extractores/nomina.py` | `from apps.tenant.empleados.models import Devengo` | `Devengo` | PERMITIDO |
| `services/selectors.py` — `get_documento_pendiente()` | `from apps.tenant.empleados.models import Devengo` | `Devengo` | PERMITIDO |
| `services/selectors.py` — `qs_nominas_pendientes()` | `from apps.tenant.empleados.models import Devengo` | `Devengo` | PERMITIDO |
| ~~`services/selectors.py` — `get_tercero_movimiento()`~~ | ~~`from apps.tenant.empleados.models import Empleado`~~ | ~~`Empleado`~~ | **ELIMINADO v3.10.2** |

### Violaciones corregidas en v3.10.2

**VIO-001 — HIGH** (`selectors.py:606-608`):
- Funcion `get_tercero_movimiento()` tenia rama `tipo_tercero == 'EMPLEADO'` que importaba
  y consultaba `Empleado` directamente, saltando la frontera Pull Model.
- Adicionalmente, el codigo era incorrecto: accedia a campos `nombre` y `nit` que no existen
  en el modelo `Empleado` (habria lanzado `AttributeError` en tiempo de ejecucion).
- **Correccion:** rama `EMPLEADO` eliminada. La funcion ahora solo maneja CLIENTE y PROVEEDOR.

**VIO-002 — LOW** (`selectors.py:503-505`):
- `get_documento_pendiente()` cargaba `select_related('contrato')` y `.only('contrato__salario_mensual')`
  sin que ningun codigo downstream consumiera esos datos (inspeccion completa de callers confirmada).
- **Correccion:** `select_related('contrato')` y `'contrato__salario_mensual'` eliminados.
  La query ahora solo hace `select_related('empleado')` y carga unicamente campos de `Devengo` + `Empleado`.

### Estado final del boundary (verificado 2026-05-25)

```python
# Grep de verificacion (resultado: 0 matches)
# from apps.tenant.empleados.models import (Empleado|Contrato)
# en apps/tenant/contabilidad/**
```

| Modelo empleados | Acceso desde contabilidad | Permitido |
|-----------------|--------------------------|-----------|
| `Devengo` | Via `from apps.tenant.empleados.models import Devengo` en extractor y selectors | SI |
| `Empleado` | Acceso indirecto solo via `Devengo.empleado` (select_related, no import directo) | SI (lectura de FK para nombre/documento) |
| `Contrato` | Ningun acceso — eliminado en VIO-002 | NO (boundary garantizado) |

**Compliance Pull Model: GARANTIZADO** — 0 violaciones activas.
| `ReglasOrquestacion` | No existe en `models.py` local; permanece como propuesta futura |

### Apps Source Status (Auditoría §18 - v3.7.1)

✅ **100% Compliant — Patrón Uniforme:**
- ✅ Clientes — UUID opaco en modelo, serializer, migración
- ✅ Facturas — UUID opaco en modelo, serializer, migración
- ✅ Inventario — 3x UUID opaco, serializers actualizados
- ✅ Empleados — UUID opaco, property removida, serializer actualizado
- ✅ Proveedores — UUID opaco, métodos removidos, serializer actualizado
- ✅ Gastos — UUID opaco único (`cuenta_gasto_uuid`), contrapartida removida, migración 0014

---

---

## 12. CAMBIOS v3.7.5 — 2026-05-19

### 12.1 Flujo Manual On-Demand — Correcciones

#### FIX-1: Validación nivel 6 eliminada del flujo manual

**Archivo:** `services/business_service.py` — `contabilizar_documento_manual()`

**Problema:** El campo `CuentaContable.nivel` tiene `default=1`. Cualquier cuenta creada sin asignar nivel explícito fallaba la validación `if cuenta.nivel != 6`, bloqueando la contabilización aunque las líneas cuadraran.

**Fix:** Eliminado el bloque `if cuenta.nivel != 6` del flujo manual On-Demand. El flujo automático (`_normalizar_movimientos`) conserva la validación de nivel 6 como corresponde a la normativa.

**Regla post-fix:**
- Flujo automático (ETL extractores): requiere nivel 6 — normativa estricta
- Flujo manual On-Demand: solo requiere que la cuenta exista y esté activa — el contador decide

#### FIX-2: Auto-creación de cuenta desde catálogo o inferencia PUC

**Archivo:** `services/business_service.py` — nuevo método `_obtener_o_crear_cuenta(empresa_id, codigo)`

**Problema:** El asistente IA puede sugerir códigos PUC válidos (ej. `235517`) que no existen en `CuentaContable` del tenant, lanzando "Cuenta X no existe o está inactiva".

**Comportamiento del helper:**
```
1. Busca en CuentaContable (empresa_id + codigo + activa=True)
2. Si no existe: busca en CatalogoMaestroNIIF → crea CuentaContable con nombre/nivel reales
3. Si tampoco está en catálogo: infiere propiedades desde estructura PUC:
   - nivel = len(codigo)
   - tipo: primer dígito → 1=ACTIVO, 2=PASIVO, 3=PATRIMONIO, 4=INGRESO, 5/6=GASTO
   - nombre = "Cuenta {codigo}"
4. Usa get_or_create → idempotente, seguro ante race conditions
```

**Impacto:** Cualquier código PUC de 6 dígitos es ahora utilizable en el flujo manual sin configuración previa.

#### FIX-3: Sincronización masiva del plan de cuentas

**Archivo:** `services/business_service.py` — nuevo método `sincronizar_cuentas_plan(empresa_id)`
**Archivo:** `api/viewsets.py` — nuevo `@action POST /cuentas-contables/sincronizar/`

**Propósito:** Crear en `CuentaContable` todas las entradas del `CatalogoMaestroNIIF` que no existan. Idempotente.

**Flujo de uso:**
```bash
# 1. Poblar CatalogoMaestroNIIF desde choices.py (si no está poblado)
python manage.py poblar_catalogo_niif

# 2. Sincronizar CuentaContable desde el catálogo
POST /api/v1/contabilidad/cuentas-contables/sincronizar/
# Response: { "creadas": N, "total_catalogo": 88, "total_plan": M }
```

#### FIX-4: Expansión del catálogo NIIF Colombia

**Archivo:** `choices/choices.py`

8 cuentas nivel 6 agregadas que faltaban para cubrir casos comunes de proveedores y costos:

| Código | Nombre | Tipo |
|--------|--------|------|
| `220501` | Proveedores Nacionales - Bienes | Pasivo |
| `220505` | Proveedores Nacionales - Servicios | Pasivo |
| `221005` | Proveedores del Exterior - Bienes | Pasivo |
| `221010` | Proveedores del Exterior - Servicios | Pasivo |
| `233510` | Honorarios por Pagar | Pasivo |
| `233515` | Comisiones por Pagar | Pasivo |
| `233520` | Arrendamientos por Pagar | Pasivo |
| `233525` | Servicios Públicos por Pagar | Pasivo |

---

### 12.2 Selector de Cuentas en Offcanvas Contabilizar

**Archivo:** `templates/tenant/contabilidad/partials/pendiente_offcanvas_contabilizar.html`

**Problema:** El único modo de asignar una cuenta era el autocompletado de texto (buscar por código/nombre). Si la cuenta no aparecía en búsqueda, el usuario no podía seleccionarla.

**Fix:** Agregado botón `[⊞]` en cada fila de la tabla de líneas. Al hacer clic abre un **modal Bootstrap** con el catálogo completo de `CuentaContable` del tenant.

**Arquitectura del selector:**

```
[⊞] clic → abrirSelectorCuentas(tr)
  → document.body.appendChild(modalEl)   ← sale del stacking context del offcanvas
  → bootstrap.Modal({ backdrop: false }) ← evita doble backdrop (pantalla negra)
  → cargarCuentasModal()                 ← GET /cuentas-contables/?activa=true&page_size=200&app_origen=X
  → renderCuentasModal()                 ← agrupa por tipo: Activo / Pasivo / Ingreso / Gasto
  → seleccionarDesdeLista(codigo, nombre)← rellena hidden input + search input + nombre display
  → recalcularTotales()
```

**Bug técnico Bootstrap 5 resuelto:** Modal dentro de offcanvas → el backdrop del modal queda detrás del offcanvas (z-index 1040 < 1045), pantalla negra, foco atrapado.
**Solución:** `document.body.appendChild(modalEl)` saca el modal del stacking context. `backdrop: false` elimina el segundo overlay redundante.

**Flujo de trabajo:**
```
Módulo Cuentas Contables  →  usuario crea cuenta nueva
                          ↓
Módulo Pendientes → Contabilizar Documento → [⊞] → modal → cuenta disponible
```

---

### 12.3 Grid Asientos Contables — Correcciones

**Problema:** El tab "Asientos Contables" no listaba ningún registro.

**Tres causas identificadas y corregidas:**

#### Causa 1 — Doble carga de scripts

`list_asientos.html` incluía `assets_asientos.html` al final del template. El mismo include ya existe en `workspace.html extra_js` (línea 275). Resultado: dos ejecuciones del módulo JS → dos closures → dos `onVisibleOnce` listeners → doble `initTable()` en `#grid-asiento` → conflicto Tabulator.

**Fix:** Eliminado `{% include 'tenant/contabilidad/partials/assets_asientos.html' %}` de `list_asientos.html`. Los assets se cargan una sola vez desde `extra_js`.

#### Causa 2 — Filtro por defecto ocultaba asientos APROBADO

El dropdown tenía `<option value="BORRADOR" selected>`. Los asientos generados por "Contabilizar Documento" siempre son `APROBADO`. El filtro ocultaba todo.

**Fix:** Default cambiado a `<option value="">Todos los Estados</option>` (sin `selected` en ninguna opción).

#### Causa 3 — Filtro client-side con paginación server-side

`applyFilters()` usaba `table.setFilter({field:'estado', type:'=', value:'BORRADOR'})` — filtrado en memoria sobre la página ya cargada. Con `paginationMode: "remote"`, el servidor devuelve 10 registros paginados; el filtro client-side solo ve esos 10.

**Fix:** Doble cambio en `asiento_list.js`:

1. `initTable()` pasa `ajaxParams` a `TabulatorFactory`:
```javascript
ajaxParams: function() {
    const estado = d.querySelector(FILTER_ESTADO_SELECTOR)?.value || '';
    return estado ? { estado } : {};
}
```
El factory inyecta `?estado=APROBADO` (o nada) en cada URL de request. El backend filtra via `filterset_fields = ['estado']`.

2. `applyFilters()` reemplazado por:
```javascript
function applyFilters() {
    if (!table || typeof table.replaceData !== 'function') return;
    table.replaceData(); // re-ejecuta ajaxURLGenerator con valor actual del dropdown
}
```

---

### 12.5 Alineación de Menús y Subnavegación Secuencial Cíclica (v3.7.6)

**Archivo:** `apps/tenant/core/templates/tenant/core/workspace.html`

**Problema:** Los menús de Contabilidad carecían de una secuencia natural o lógica, presentándose en un orden desorganizado. La gestión contable requiere un ciclo de vida claro y estructurado.

**Solución:** Se reorganizó la barra de pestañas (subnav) y los correspondientes paneles de contenido de la pestaña `#tab-contabilidad` para reflejar un **Flujo de Trabajo Secuencial y Cíclico** alineado con los procesos del departamento contable:
1. **Periodos Contables** (`#subtab-periodos` - Pestaña ACTIVA por defecto): Primer paso del ciclo. Define, abre o cierra periodos para regular la entrada de datos.
2. **Cuentas Contables** (`#subtab-cuentas`): Estructura del plan de cuentas (PUC) necesario para registrar movimientos.
3. **Pendientes** (`#subtab-pendientes`): Captura y procesamiento de documentos e ingresos desde módulos operativos externos (Facturas, Gastos, etc.).
4. **Asientos Contables** (`#subtab-asientos`): Creación y aprobación de asientos y comprobantes de diario.
5. **Libro Diario** (`#subtab-libro-diario`): Auditoría cronológica de las transacciones procesadas.
6. **Reportes** (`#subtab-reportes`): Cierre contable del periodo con reportes e informes financieros, completando el ciclo y guiando de vuelta a la apertura de un nuevo Periodo.

---

### 12.6 Estado post-correcciones v3.7.6

| Componente | Estado | Nota |
|-----------|--------|------|
| Contabilizar Documento — cuadratura | ✅ Funciona | Botón habilitado cuando Debe = Haber |
| Contabilizar Documento — cuentas PUC | ✅ Funciona | Auto-crea desde catálogo o inferencia |
| Selector de Cuentas (modal) | ✅ Funciona | Agrupa por tipo, filtro client-side en modal |
| Sincronizar Plan de Cuentas | ✅ Disponible | `POST /cuentas-contables/sincronizar/` |
| Listado Asientos Contables | ✅ Funciona | Tabulator con filtro server-side por estado |
| Filtro Estado (Todos/Borrador/Aprobado) | ✅ Funciona | Server-side via `?estado=X` |
| Catálogo NIIF Colombia | ✅ 88 cuentas | +8 cuentas proveedores y costos |
| Menús y Subnav Secuencial Cíclico | ✅ Implementado | Periodos → Cuentas → Pendientes → Asientos → Libro Diario → Reportes |

---

### 12.7 CRUD Periodos Contables — Correcciones (v3.7.7 — 2026-05-19)

**Objetivo:** Habilitar el listado, creación, edición, cierre y eliminación de periodos contables desde `workspace/#contabilidad` → pestaña "Periodos Contables".

**Seis bugs corregidos:**

#### BUG-1: Selector CSS incorrecto — tabla nunca inicializaba (CRÍTICO)

**Archivo:** `static/contabilidad/js/periodo/features/periodo_list.js`

**Problema:** `TABLE_SELECTOR = '#grid-periodo'` no encontraba el elemento `id="grid-periodos"` del template. `d.querySelector(TABLE_SELECTOR)` devolvía `null` → `initTable()` retornaba inmediatamente → tabla completamente en blanco.

**Fix:**
```javascript
// Antes
const TABLE_SELECTOR = '#grid-periodo';
// Después
const TABLE_SELECTOR = '#grid-periodos';
```

#### BUG-2: Botón "Refrescar" no se enlazaba

**Archivo:** `static/contabilidad/js/periodo/features/periodo_list.js`

**Problema:** `d.querySelector('#btn-refrescar-periodo')` (sin 's') no encontraba `id="btn-refrescar-periodos"` (con 's') en el template.

**Fix:**
```javascript
// Antes
const btnRefresh = d.querySelector('#btn-refrescar-periodo');
// Después
const btnRefresh = d.querySelector('#btn-refrescar-periodos');
```

#### BUG-3: Filtro client-side con paginación server-side

**Archivo:** `static/contabilidad/js/periodo/features/periodo_list.js`

**Mismo patrón que asientos (BUG corregido en §12.3 Causa 3).**

`applyFilters()` usaba `table.setFilter()` — filtra solo la página cargada, no el servidor.

**Fix:** `ajaxParams` callback + `table.replaceData()`:
```javascript
// En initTable() — ajaxParams inyecta ?estado=X en cada request
ajaxParams: function() {
    const estado = d.querySelector(FILTER_ESTADO_SELECTOR)?.value || '';
    return estado ? { estado } : {};
}

// applyFilters() — recarga desde servidor con filtro actual
function applyFilters() {
    if (!table || typeof table.replaceData !== 'function') return;
    table.replaceData();
}
```

#### BUG-4: `get_queryset()` no pasaba `empresa_id` al selector

**Archivo:** `api/viewsets.py` — `PeriodoContableViewSet.get_queryset()`

**Problema:** `PeriodoContableSelector.get_qs_list()` y `get_qs_detail()` se llamaban sin `empresa_id` — el selector acepta `empresa_id=None` y en ese caso omite el filtro. Aunque django-tenants garantiza aislamiento por esquema, el filtro por `empresa_id` es mandatorio por AGENTS.md (DSV).

**Fix:**
```python
def get_queryset(self):
    empresa_id = self.get_empresa_id()
    if self.action == "list":
        return PeriodoContableSelector.get_qs_list(empresa_id).order_by('-periodo')
    elif self.action == "retrieve":
        return PeriodoContableSelector.get_qs_detail(empresa_id)
    return self.get_mutation_queryset(PeriodoContable, 'periodo', 'estado')
```

#### BUG-5: Action `cerrar` inexistente en ViewSet

**Archivo:** `api/viewsets.py` — `PeriodoContableViewSet`

**Problema:** `PeriodoAPI.cerrar(id)` en el frontend llama `POST /periodos-contables/{id}/cerrar/` pero el ViewSet no tenía este action → 404 al intentar cerrar un periodo.

**Fix:** Action agregado:
```python
@action(detail=True, methods=['post'], url_path='cerrar')
def cerrar(self, request, **kwargs):
    """POST /periodos-contables/{uuid}/cerrar/ — Cierra un periodo ABIERTO."""
    try:
        periodo_identifier = kwargs.get('uuid') or kwargs.get('pk')
        periodo = get_periodo_by_identifier(periodo_identifier)
        resultado = self.service.cerrar_periodo(periodo.id, request.data)
        periodo_obj = PeriodoContableSelector.get_qs_detail().get(id=resultado['id'])
        serializer = PeriodoContableDetailSerializer(periodo_obj, context={'request': request})
        return Response(serializer.data)
    except Exception as e:
        return self.handle_service_error(e)
```

**Endpoint expuesto:** `POST /api/v1/contabilidad/periodos-contables/{uuid}/cerrar/`
- Body opcional: `{ "observaciones": "Cierre de mes" }`
- Respuesta: `PeriodoContableDetailSerializer` con estado `CERRADO`

#### BUG-6: `cerrar_periodo()` inexistente en Business Service

**Archivo:** `services/business_service.py` — `ContabilidadBusinessService`

**Problema:** El action de la ViewSet invocaba `self.service.cerrar_periodo()` pero el método no existía → `AttributeError`.

**Fix:** Método agregado:
```python
@transaction.atomic
def cerrar_periodo(self, periodo_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Cierra un periodo ABIERTO. Una vez cerrado no se puede reabrir."""
    from apps.tenant.contabilidad.models import PeriodoContable
    periodo = PeriodoContable.objects.get(id=periodo_id)
    if periodo.estado == 'CERRADO':
        raise ValidationError({'detail': 'El periodo ya esta cerrado.'})
    data = {'estado': 'CERRADO'}
    observaciones = payload.get('observaciones', '')
    if observaciones:
        data['observaciones'] = observaciones
    periodo = self.crud.actualizar_periodo(periodo_id, data)
    return {'id': periodo.id, 'uuid': str(periodo.uuid), 'status': 'cerrado'}
```

**Nota:** `crud.actualizar_periodo` detecta `estado == 'CERRADO'` y asigna `fecha_cierre = now()` automáticamente (ver `crud_service.py:234`).

---

### 12.8 Libro Diario — Sincronización con AsientoContable (v3.7.8 — 2026-05-19)

**Objetivo:** El módulo Libro Diario ahora muestra los **AsientoContable** del tenant filtrados por periodo contable, con búsqueda y filtros funcionales. Reemplaza la implementación ETL anterior (DocumentoEnriquecido) por consulta directa al modelo.

---

#### Cambio de arquitectura: ETL → Query directa

| Aspecto | Antes (v3.7.6) | Después (v3.7.8) |
|---------|---------------|-----------------|
| Fuente de datos | `get_libro_diario_periodo()` — extractores ETL | `AsientoContableSelector.get_qs_list()` — query directa |
| Estructura de respuesta | `DocumentoEnriquecido` (cuentas_asignadas, movimientos, estado_contable) | `AsientoContableListSerializer` (numero, fecha, descripcion, estado, totales, cuadratura) |
| Filtro de fecha | `fecha_inicio` + `fecha_fin` obligatorios | `periodo_uuid` (primario) o `fecha_inicio`+`fecha_fin` (fallback) |
| Filtros adicionales | Ninguno | `estado`, `search` (numero/descripcion) — server-side |
| Dropdown periodo | No existía | Carga `/periodos-contables/?ordering=-periodo` al abrir el tab |

---

#### `api/viewsets.py` — `LibroDiarioViewSet.list()`

Lógica de resolución del rango de fechas:
```
1. ?periodo_uuid=<uuid>  → busca PeriodoContable, extrae fecha_inicio/fecha_fin del periodo
2. ?fecha_inicio=X&fecha_fin=Y → usa directamente (fallback manual)
3. Sin parámetros → retorna [] 200 OK (Tabulator muestra placeholder)
```

Query ORM:
```python
qs = AsientoContableSelector.get_qs_list(empresa_id).filter(
    fecha__range=(fecha_inicio, fecha_fin)
)
# Filtros opcionales:
if estado: qs = qs.filter(estado=estado)
if search: qs = qs.filter(Q(numero__icontains=search) | Q(descripcion__icontains=search))
qs = qs.order_by('fecha', 'numero')  # Orden cronológico — Código de Comercio Art. 48
```

---

#### `templates/.../list_libro_diario.html`

Barra de filtros rediseñada:

| Campo | ID | Descripción |
|-------|----|-------------|
| Periodo | `#filter-periodo-libro` | Dropdown, puebla `fecha_inicio`/`fecha_fin` al seleccionar |
| Desde | `#filter-fecha-inicio-libro` | Override manual de fecha |
| Hasta | `#filter-fecha-fin-libro` | Override manual de fecha |
| Estado | `#filter-estado-libro` | BORRADOR / APROBADO / CERRADO |
| Buscar | `#search-libro-diario` | Filtro client-side sobre datos cargados |
| Consultar | `#btn-consultar-libro-diario` | Dispara `loadData()` |
| Refrescar | `#btn-refrescar-libro-diario` | Re-ejecuta `loadData()` |

---

#### `static/.../libro_diario_list.js`

**Flujo de carga:**
```
Tab visible → loadPeriodos() → puebla dropdown con períodos disponibles
                ↓
Usuario selecciona periodo → auto-rellena fecha_inicio / fecha_fin
                ↓
Consultar → loadData() → LibroDiarioAPI.list({periodo_uuid, estado})
                ↓
API devuelve [] (sin params) o AsientoContable[] (con params)
                ↓
table.setData(currentData)  →  applySearchFilter()  →  updateResumen()
```

**Columnas Tabulator (AsientoContableListSerializer):**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `numero` | strong | Número del asiento |
| `fecha` | date | Formateada es-CO |
| `descripcion` | text | Truncada a 60 chars |
| `estado` | badge | BORRADOR / APROBADO / CERRADO |
| `movimientos_count` | badge | Conteo de líneas |
| `total_debe` | money-right | Total débito (azul) |
| `total_haber` | money-right | Total crédito (rojo) |
| `cuadratura` | icon | ✅ OK / ❌ Error |
| Ver | button | HTMX → `/asientos-contables/{uuid}/render-offcanvas/detalle/` |

**Panel resumen (actualizado):**
```
[N asientos]  [N cuadrados]  [N descuadrados]  [D: $X]  [H: $X]  [Cuadratura OK / Descuadre $X]
```

**Búsqueda:** Client-side via `table.setFilter(fn)` sobre `numero` y `descripcion` (datos ya en memoria).

**Filtro estado:** Server-side — al cambiar, re-ejecuta `loadData()` con `?estado=X`.

---

#### `static/.../libro_diario.api.js`

Parámetros soportados por `LibroDiarioAPI.list(params)`:

```javascript
{
  periodo_uuid: 'uuid-del-periodo',  // Prioritario
  fecha_inicio: 'YYYY-MM-DD',        // Fallback si no hay periodo_uuid
  fecha_fin:    'YYYY-MM-DD',
  estado:       'BORRADOR',          // Opcional
  search:       'texto',             // Opcional
}
```

---

### 12.9 Estado post-correcciones v3.7.8

| Componente | Estado | Nota |
|-----------|--------|------|
| Libro Diario — dropdown periodos | ✅ Funciona | Carga automática al abrir tab |
| Libro Diario — filtro por periodo | ✅ Funciona | `?periodo_uuid=<uuid>` → rango fechas resuelto en backend |
| Libro Diario — filtro por fechas | ✅ Funciona | `?fecha_inicio=X&fecha_fin=Y` como fallback manual |
| Libro Diario — filtro estado | ✅ Funciona | Server-side `?estado=BORRADOR/APROBADO/CERRADO` |
| Libro Diario — búsqueda | ✅ Funciona | Client-side sobre numero/descripcion (datos en memoria) |
| Libro Diario — columnas | ✅ Funciona | Alineadas con AsientoContableListSerializer |
| Libro Diario — cuadratura | ✅ Funciona | Badge OK/Error por asiento + resumen del periodo |
| Libro Diario — detalle asiento | ✅ Funciona | Botón Ver → HTMX offcanvas detalle existente |
| Periodos Contables — listado | ✅ Funciona | Tabulator carga desde `/periodos-contables/` |
| Periodos Contables — CRUD completo | ✅ Funciona | Crear, Editar, Eliminar, Cerrar |
| Contabilizar Documento — cuadratura | ✅ Funciona | Botón habilitado cuando Debe = Haber |
| Contabilizar Documento — cuentas PUC | ✅ Funciona | Auto-crea desde catálogo o inferencia |
| Selector de Cuentas (modal) | ✅ Funciona | Agrupa por tipo, filtro client-side en modal |
| Sincronizar Plan de Cuentas | ✅ Disponible | `POST /cuentas-contables/sincronizar/` |
| Listado Asientos Contables | ✅ Funciona | Tabulator con filtro server-side por estado |
| Catálogo NIIF Colombia | ✅ 88 cuentas | +8 cuentas proveedores y costos |

---

### 12.10 Revalidacion documental v3.9.1 - 2026-05-25

La auditoria fue revalidada contra el arbol local de `apps/tenant/contabilidad` y se actualizaron:

| Area | Resultado 2026-05-25 |
|------|----------------------|
| Modelos | 10 clases tenant verificadas, incluyendo `ConfiguracionRetenciones` y `Retencion` |
| API | Router incluye `libro-diario`, `retenciones` y `configuraciones-retenciones` |
| Integracion | Extractores activos para gastos, facturas y nomina; inventario se consume desde Movimientos Recientes |
| Manual On-Demand | `ContabilizarManualInputSerializer` acepta `facturas`, `gastos`, `empleados`, `inventario`; para inventario solo admite documentos provenientes del timeline |
| Libro Diario | Opera como lectura directa de `AsientoContable` por periodo/fechas |
| Retenciones | Pull Model materializado en `RetencionesService` y endpoints dedicados |
| Deuda tecnica | `AUD-CONT-001` a `AUD-CONT-004` corregidos; `AUD-CONT-005` y `AUD-CONT-006` quedan como limpieza legacy no productiva |
| `ReglasOrquestacion` | No existe en codigo local; queda solo como propuesta futura |

### 12.11 Contrato Inventario / Movimientos Recientes - 2026-05-25

Se implemento la migracion de busqueda contable de Inventario al agregado `Movimientos Recientes`:

| Area | Resultado |
|------|-----------|
| Fuente unica | Contabilidad consume `apps.tenant.inventario.services.selectors.get_movimientos_timeline()` |
| Prohibicion aplicada | Contabilidad no consulta `Producto`, `Servicio`, `ActivoFijo`, `MovimientoInventario.objects` ni `HistorialServicio.objects` |
| Timeline | Inventario expone `documento_id` y `modelo_origen` (`MovimientoInventario` o `HistorialServicio`) |
| Pendientes | `/api/v1/contabilidad/pendientes/` vuelve a incluir `INVENTARIO` desde el timeline |
| Offcanvas manual | `render-offcanvas` recupera el documento de inventario por timeline, no por modelo fuente |
| Idempotencia | `AsientoContable.documento_origen_*` usa `app_label='inventario'`, `modelo_origen` y `documento_id` |
| Extractor legacy | `ExtractorInventario` permanece como no-op para compatibilidad de imports historicos |

**Auditoria completada:** 2026-05-25 (v3.9.1 - validada contra codigo local)
**Proxima revision:** Revalidar pruebas API/command y planificar limpieza legacy de `api/datatables.py` y `scratch/`.

---

## 13. ACTUALIZACION AUDITORIA v3.10.x — 2026-06-04

### 13.1 Estado Global del Modulo

**Version auditada:** v3.10.x (sincronizada con stack Sintel v4.8.0 Nominas Master-Detail)
**Fecha:** 2026-06-04
**Auditado por:** Revision profunda del arbol local `apps/tenant/contabilidad/`

| Indicador | Valor |
|-----------|-------|
| ViewSets activos | 10 (`CuentaContable`, `AsientoContable`, `MovimientoContable`, `PeriodoContable`, `CatalogoMaestroNIIF`, `TipoComprobante`, `DocumentosPendientes`, `LibroDiario`, `Retencion`, `ConfiguracionRetenciones`) |
| Endpoints API registrados en router | 10 prefijos en `api/urls.py` |
| Modelos tenant | 10 (todos heredan `SintelTenantBaseModel`) |
| Servicios | `business_service.py`, `crud_service.py`, `selectors.py`, `retenciones_service.py` |
| Extractores activos | 4: `base.py`, `facturas.py`, `gastos.py`, `nomina.py`; `inventario.py` = no-op (timeline) |
| Tests presentes | 6 archivos en `tests/` |
| Tareas Celery | 2 (`ejecutar_integracion_contable_task`, `integracion_contable_global_task`) |
| Migraciones | 7 (`0001` a `0007`) |
| Estado general | ESTABLE — sin deuda critica activa |

---

### 13.2 Hallazgos Nuevos (2026-06-04)

#### NUEVO-001 — Celery Tasks verificadas

**Archivo:** `tasks.py`

Se confirman dos tareas Celery tenant-aware:

| Tarea | Alcance | Patron |
|-------|---------|--------|
| `ejecutar_integracion_contable_task(schema_name)` | Un tenant | ETL completo via `ContabilidadBusinessService.ejecutar_integracion_completa()` |
| `integracion_contable_global_task()` | Todos los tenants | Broadcast: recorre `TenantModel` y encola la tarea individual |

**Observacion:** `ejecutar_integracion_contable_task` no tiene `max_retries` ni DLQ definidos. Aunque el error se captura y se loguea, no persiste en `FailedTenantTask`. Esto viola la regla AGENTS.md §11.3 (Tolerancia a Fallos y DLQ). Estado: **DEUDA TECNICA NUEVA**.

#### NUEVO-002 — Endpoint Asistente IA documentado

**Archivo:** `api/viewsets.py` — `DocumentosPendientesViewSet.asistente_ia()`

Endpoint confirmado:
```
POST /api/v1/contabilidad/pendientes/asistente-ia/
```

Recibe datos del documento pendiente (numero, subtotal, impuestos, total, tercero) y devuelve lineas de asiento sugeridas via `service.sugerir_lineas_asiento_ia()`. El contador revisa y confirma antes de llamar a `contabilizar-manual/`. Estado: **DOCUMENTADO, NO AUDITADO en profundidad** (validar `sugerir_lineas_asiento_ia` en `business_service.py`).

#### NUEVO-003 — `LibroDiarioViewSet` no hereda de `BaseTenantViewSet`

**Archivo:** `api/viewsets.py:1226`

```python
class LibroDiarioViewSet(SintelDSVMixin, ContabilidadServiceMixin, viewsets.ViewSet):
```

Hereda de `viewsets.ViewSet` (DRF base) en lugar de `BaseTenantViewSet`. Esto significa:
- No aplica `lookup_field = "uuid"` heredado (no relevante: no tiene acciones `detail=True`).
- Dual-Auth (`JWTAuthentication, SessionAuthentication`) no se hereda automaticamente desde `BaseTenantViewSet`.
- `permission_classes = [IsTenantMember]` esta declarado explicitamente (correcto).

**Riesgo:** Si `BaseTenantViewSet` anade logica critica de autenticacion o auditoria en el futuro, `LibroDiarioViewSet` no la heredara. Estado: **DEUDA TECNICA MENOR — Aceptado por ser read-only sin lookup**.

#### NUEVO-004 — `ConfiguracionRetencionesViewSet` usa `lookup_field = 'id'`

**Archivo:** `api/viewsets.py:1071`

```python
lookup_field = 'id'
lookup_url_kwarg = 'id'
```

Viola la regla AGENTS.md §14.6 (UUID como Lookup Field). Expone el PK entero en URLs publicas (`/configuraciones-retenciones/1/`). Estado: **DEUDA TECNICA MENOR** — Migrar a `uuid` requiere migracion de modelo y actualizacion de frontend.

#### NUEVO-005 — `RetencionesService.listar_retenciones_por_documento` sin filtro `empresa_id`

**Archivo:** `services/retenciones_service.py:300-309`

```python
qs = Retencion.objects.filter(
    documento_origen_app=documento_origen_app,
    documento_origen_modelo=documento_origen_modelo,
    documento_origen_id=documento_origen_id,
)
```

La consulta no filtra por `empresa_id`. Aunque `django-tenants` garantiza aislamiento por esquema, la ausencia del filtro viola AGENTS.md §4.4 (Zero-Trust SaaS — filtrar siempre por empresa). Estado: **DEUDA TECNICA — DSV incompleto**.

#### NUEVO-006 — `obtener_retenciones_desde_tercero` sin filtro `empresa_id`

**Archivo:** `services/retenciones_service.py:89-105`

Las queries a `ConfiguracionRetenciones.objects.filter(...)` no incluyen `empresa_id`. Mismo patron que NUEVO-005. Estado: **DEUDA TECNICA — DSV incompleto**.

---

### 13.3 Boundary Contabilidad - Empleados (Post v3.10.2, Auditado 2026-06-04)

Estado confirmado: **GARANTIZADO — 0 violaciones activas**.

Cambios desde v3.9.1 que afectan este boundary:
- El modulo Nominas fue refactorizado a Master-Detail (v4.8.0) en `apps/tenant/empleados/`.
- Los selectors de `contabilidad` que consumen `Devengo` (`qs_nominas_pendientes`, `get_documento_pendiente`) no fueron modificados — boundary intacto.
- El ViewSet `DevengoViewSet` en empleados agrego filtro `?empleado_uuid=` para el Detail panel; esto no afecta la integracion con contabilidad.

---

### 13.4 Integracion Nomina con Pull Model (v4.8.0)

**Cambio en empleados:** `DevengoViewSet.get_queryset()` ahora soporta `?empleado_uuid=` para el panel Detail del Master-Detail.

**Impacto en contabilidad:**
- `qs_nominas_pendientes(empresa_id)` consulta `Devengo.objects.filter(empresa_id=empresa_id, contabilizado=False).only(...)` — sin cambios necesarios.
- `get_documento_pendiente('empleados', 'Devengo', id, empresa_id)` — sin cambios.
- El campo `contabilizado` en `Devengo` sigue siendo el flag de idempotencia para el Pull Model.

**Estado:** Sin accion requerida. Integracion funcional.

---

### 13.5 Inventario: Confirmacion del Contrato Timeline (2026-06-04)

Verificado que `ExtractorInventario` en `integracion/extractores/inventario.py` es un no-op (743 bytes). El flujo real se realiza a traves de `qs_inventario_movimientos_recientes_pendientes(empresa_id)` que invoca `get_movimientos_timeline()` del selector de inventario.

El `DocumentosPendientesViewSet.list()` procesea los items del timeline de inventario correctamente usando los helpers `_decimal_from_value()` y `_date_from_timeline()` para manejar la estructura de diccionario en lugar de modelo ORM.

**Estado:** Funcional. No requiere accion.

---

### 13.6 Tabla de Deuda Tecnica Actualizada (2026-06-04)

| ID | Severidad | Archivo | Hallazgo | Estado | Accion recomendada |
|----|-----------|---------|----------|--------|--------------------|
| AUD-CONT-001 | Alta | `api/viewsets.py` | TipoComprobanteViewSet con `only()` y filtro empresa_id | CERRADO 2026-05-25 | - |
| AUD-CONT-002 | Media | `api/viewsets.py` | CatalogoMaestroNIIFViewSet con `only()` | CERRADO 2026-05-25 | - |
| AUD-CONT-003 | Media | `services/business_service.py` | `_obtener_o_crear_cuenta()` con campos minimos | CERRADO 2026-05-25 | - |
| AUD-CONT-004 | Media | `management/commands/migrate_retenciones.py` | `.all()` y asignacion `empresa_id` | CERRADO 2026-05-25 | - |
| AUD-CONT-005 | Baja | `api/datatables.py` | Archivo legacy no expuesto | ABIERTO | Remover en limpieza autorizada |
| AUD-CONT-006 | Baja | `scratch/` | Scripts no productivos dentro de la app | ABIERTO | Mover fuera de la app |
| AUD-CONT-007 | Media | `tasks.py` | Sin `max_retries` ni DLQ en tareas Celery | NUEVO 2026-06-04 | Agregar `max_retries`, `autoretry_for`, y fallback a `FailedTenantTask` |
| AUD-CONT-008 | Media | `services/retenciones_service.py` | Queries sin filtro `empresa_id` en metodos publicos | NUEVO 2026-06-04 | Agregar `empresa_id` en `listar_retenciones_por_documento` y `obtener_retenciones_desde_tercero` |
| AUD-CONT-009 | Baja | `api/viewsets.py:1071` | `ConfiguracionRetencionesViewSet.lookup_field = 'id'` | NUEVO 2026-06-04 | Migrar a UUID lookup (requiere migracion) |
| AUD-CONT-010 | Baja | `api/viewsets.py:1226` | `LibroDiarioViewSet` hereda `viewsets.ViewSet` no `BaseTenantViewSet` | NUEVO 2026-06-04 | Evaluar si Dual-Auth se requiere; migrar si se agregan acciones mutables |
| AUD-CONT-011 | Info | `api/viewsets.py:1022` | Endpoint `/pendientes/asistente-ia/` presente pero sin pruebas automatizadas | NUEVO 2026-06-04 | Agregar test de integracion para el endpoint IA |

---

### 13.7 Compliance AGENTS.md (2026-06-04)

| Estandar | Estado |
|----------|--------|
| Feature-Sliced Design | CONFORME |
| Service Layer (selector → CRUD → business) | CONFORME con excepciones puntuales documentadas |
| Multi-Tenant (django-tenants) | CONFORME |
| Zero-Waste Queries (.only, .select_related) | PARCIAL — `RetencionesService` sin `.only()` en algunos metodos |
| API-First Design (DRF ViewSets) | CONFORME |
| Double Semantic Verification (DSV) | PARCIAL — `RetencionesService` sin `empresa_id` (AUD-CONT-008) |
| NIIF PYMES Colombia (PUC nivel 6) | CONFORME en flujo automatico; flexible en manual |
| Inmutabilidad (Periodos Cerrados) | CONFORME |
| Idempotencia (`documento_origen_*`) | CONFORME |
| Transacciones atomicas | CONFORME en persistencia principal |
| Partida Doble estricta (cuadratura) | CONFORME |
| UUID lookup (no exponer PK) | PARCIAL — `ConfiguracionRetencionesViewSet` usa `id` (AUD-CONT-009) |
| No emojis en .py | CONFORME — validado con `py_compile` |
| empresa_id en toda query tenant | PARCIAL — `RetencionesService` pendiente (AUD-CONT-008) |
| TabulatorFactory obligatorio | CONFORME en modulos inspeccionados |
| Celery con DLQ y reintentos | NO CONFORME — AUD-CONT-007 |
| Cero archivos .py no autorizados | CONFORME — estructura services/ canononica |
| Re-exports explicitos en `__init__.py` | CONFORME — sin wildcard imports |

---

**Auditoria actualizada:** 2026-06-04 (v3.10.x — post Nominas Master-Detail v4.8.0)
**Proxima revision:** Cerrar AUD-CONT-007 (Celery DLQ) y AUD-CONT-008 (RetencionesService empresa_id) como prioridad media antes del siguiente sprint de produccion.

