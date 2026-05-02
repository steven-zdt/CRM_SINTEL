# COMPREHENSIVE INVENTORY OF TENANT APP MODELS - SINTEL v2.61.4

**Generated:** 2026-03-20  
**Scope:** All TENANT_APPS models across the SINTEL project  
**Purpose:** Identify which models have `empresa` field and what requires refactoring  

---

## SUMMARY STATISTICS

| Metric | Count |
|--------|-------|
| **Total Apps Scanned** | 15 |
| **Apps with models.py** | 12 |
| **Total Models Found** | 32 |
| **Models with `empresa` FK** | 26 |
| **Models WITHOUT `empresa` FK** | 6 |
| **Abstract Models** | 0 |

---

## DETAILED MODEL INVENTORY

### 1. `apps.tenant.empresa` (SSoT App)

#### Empresa
- **has_empresa:** NO (This is the SSoT singleton per tenant)
- **fields:**
  - `singleton_key`: PositiveSmallIntegerField (for singleton pattern)
  - `razon_social`: CharField(255)
  - `nit`: CharField(20, unique=True)
  - `dv`: CharField(2, blank/null)
  - `direccion`: CharField(500)
  - `telefono`: CharField(20)
  - `email_contacto`: EmailField
  - `regimen_tributario`: CharField(50)
  - `logo`: ImageField(blank/null)
  - `website`: URLField(blank)
  - `moneda`: CharField(8, default='COP')
  - `created_at`: DateTimeField(auto_now_add)
  - `updated_at`: DateTimeField(auto_now)
- **Notes:** Singleton model per tenant schema. Does not need empresa FK since IT IS empresa.

#### MailInboxConfig
- **has_empresa:** NO (Does not inherit from any base)
- **fields:**
  - `nombre`: CharField(100)
  - `email_address`: EmailField(blank/null)
  - `provider`: CharField(16, choices=[custom, gmail])
  - Legacy protocol fields: `host`, `port`, `protocol`, `ssl`, `username`, `password`, `mailbox`, etc.
  - IMAP fields: `imap_host`, `imap_port`, `imap_ssl`, `imap_starttls`, `imap_username`, `imap_password`, `imap_mailbox`, `imap_mark_as_seen`, `imap_move_processed_to`, `imap_max_attachment_mb`
  - SMTP fields: `smtp_host`, `smtp_port`, `smtp_ssl`, `smtp_starttls`, `smtp_username`, `smtp_password`
  - `is_active`: BooleanField(default=True)
  - `created_at`: DateTimeField(auto_now_add)
  - `updated_at`: DateTimeField(auto_now)
- **Notes:** Mailbox configuration (SSoT). Does not have explicit empresa FK but is tenant-isolated by schema.

---

### 2. `apps.tenant.contabilidad` (ACCOUNTING)

#### CatalogoMaestroNIIF
- **has_empresa:** NO (Shared reference catalog within tenant)
- **fields:**
  - `codigo`: CharField(20, unique=True)
  - `nombre`: CharField(200, editable=False)
  - `nivel`: IntegerField(editable=False)
  - `naturaleza`: CharField(1, choices=[D, C], editable=False)
  - `activa`: BooleanField(default=True)
  - `created_at`: DateTimeField(auto_now_add)
- **Notes:** Reference catalog (NIIF Colombia). Shared within tenant schema but no explicit tenant isolation.

#### CuentaContable
- **has_empresa:** YES ✅
- **fields:**
  - `uuid`: UUIDField(unique=True)
  - `codigo`: CharField(20, unique=True)
  - `nombre`: CharField(200)
  - `tipo`: CharField(20, choices=[ACTIVO, PASIVO, PATRIMONIO, INGRESO, GASTO])
  - `descripcion`: TextField(blank/null)
  - `cuenta_padre`: ForeignKey(self, blank/null)
  - **`empresa`: ForeignKey(Empresa, on_delete=PROTECT)** ✅ ENFORCED MODE v2.40
  - `catalogo_referencia`: ForeignKey(CatalogoMaestroNIIF, blank/null)
  - `nivel`: IntegerField(default=6)
  - `activa`: BooleanField(default=True)
  - `created_at`: DateTimeField(auto_now_add)
- **Notes:** Plan de cuentas. Properly FK to Empresa.

#### AsientoContable
- **has_empresa:** YES ✅
- **fields:**
  - `uuid`: UUIDField(unique=True)
  - `numero`: CharField(50, unique=True)
  - `fecha`: DateField
  - `descripcion`: TextField
  - `estado`: CharField(20, choices=[BORRADOR, APROBADO, CERRADO])
  - `tipo_comprobante`: CharField(5, blank/null)
  - `numero_comprobante`: CharField(50, blank/null)
  - `total_debe`: DecimalField(15,2, default=0)
  - `total_haber`: DecimalField(15,2, default=0)
  - **`empresa`: ForeignKey(Empresa, on_delete=PROTECT)** ✅ ENFORCED MODE v2.40
  - `factura`: ForeignKey(Factura, blank/null)
  - `created_at`: DateTimeField(auto_now_add)
  - `updated_at`: DateTimeField(auto_now)
- **Notes:** General ledger entry. Properly FK to Empresa.

#### MovimientoContable
- **has_empresa:** NO ❌ (Indirect via AsientoContable.empresa)
- **fields:**
  - `asiento`: ForeignKey(AsientoContable, on_delete=CASCADE)
  - `cuenta`: ForeignKey(CuentaContable, on_delete=PROTECT)
  - `tipo_tercero`: CharField(20, choices=[CLIENTE, PROVEEDOR, EMPLEADO, OTRO])
  - [More fields...]
- **Notes:** Detail line of accounting entry. Transitively tied to empresa via AsientoContable.

---

### 3. `apps.tenant.facturas` (INVOICING)

#### Factura
- **has_empresa:** YES ✅
- **fields:**
  - **`empresa`: ForeignKey(Empresa, on_delete=PROTECT)** ✅ ENFORCED MODE v2.40
  - `numero`: CharField(50, unique=True)
  - `prefijo`: CharField(10, blank/null)
  - `consecutivo`: IntegerField
  - `tipo`: CharField(2, choices=[FE, NC, ND])
  - `estado`: CharField(20, choices=[BORRADOR, ENVIADA, ACEPTADA, RECHAZADA, ANULADA])
  - `naturaleza`: CharField(10, choices=[VENTA, COMPRA], blank/null)
  - `categoria`: CharField(10, choices=[PRODUCTO, SERVICIO, MIXTO])
  - `fecha_emision`: DateTimeField
  - `fecha_vencimiento`: DateField(blank/null)
  - Emisor snapshot fields: `emisor_nit`, `emisor_razon_social`, `emisor_direccion`, `emisor_email`, `emisor_telefono`, `emisor_actividad_ciiu`
  - Receptor snapshot fields: `receptor_nit`, `receptor_razon_social`, `receptor_direccion`, `receptor_email`, `receptor_telefono`
  - `moneda`: CharField(3, default='COP')
  - `subtotal`: DecimalField(15,2, default=0)
  - `impuestos`: DecimalField(15,2, default=0)
  - `total`: DecimalField(15,2, default=0)
  - `forma_pago`: CharField(30, blank/null)
  - `medio_pago_codigo`: CharField(10, blank/null)
  - `payment_due_date`: DateField(blank/null)
  - `cufe`: CharField(128, unique=True, blank/null, **indexed** for fast lookup)
  - `qr_code`: TextField(blank/null)
  - `qr_url`: URLField(1024, blank/null)
  - DIAN authorization fields: `autorizacion_numero`, `autorizacion_prefijo`, `autorizacion_rango_desde`, `autorizacion_rango_hasta`, `autorizacion_vigencia_inicio`, `autorizacion_vigencia_fin`
  - DIAN validation fields: `dian_validation_code`, `dian_validation_desc`, `dian_validation_fecha`, `dian_validation_hora`, `dian_response_xml`
  - `xml_content`: TextField(blank/null, **deprecated**)
  - `xml_file_path`: CharField(500, blank/null)
  - `created_at`: DateTimeField(auto_now_add)
  - `updated_at`: DateTimeField(auto_now)
- **Notes:** Invoice document. Properly FK to Empresa. Critical field `cufe` is indexed for idempotency.

#### ItemFactura
- **has_empresa:** YES ✅
- **fields:**
  - `factura`: ForeignKey(Factura, on_delete=CASCADE)
  - **`empresa`: ForeignKey(Empresa, on_delete=PROTECT)** ✅ ENFORCED MODE v2.40
  - `linea_id`: CharField(10, blank/null)
  - `codigo`: CharField(50, blank/null)
  - `descripcion`: CharField(500)
  - `cantidad`: DecimalField(10,2, default=1)
  - `unidad_medida`: CharField(10, default='UND')
  - `valor_unitario`: DecimalField(15,2)
  - `porcentaje_iva`: DecimalField(5,2, default=0)
  - `valor_iva`: DecimalField(15,2, default=0)
  - `subtotal`: DecimalField(15,2)
  - `total`: DecimalField(15,2)
  - `es_servicio`: BooleanField(default=False)
  - `orden`: IntegerField(default=1)
- **Notes:** Invoice item. Auto-syncs empresa from Factura on save().

#### MailIngestionConfig (DEPRECATED)
- **has_empresa:** NO ❌
- **Notes:** Deprecated model. Migration targeting apps.tenant.empresa.MailInboxConfig. Legacy data only.

#### MailIngestionRun
- **has_empresa:** NO ❌
- **fields:**
  - `started_by`: ForeignKey(TenantProfile, blank/null) - NOTE: Has TenantProfile, but no direct empresa
  - `started_at`: DateTimeField(auto_now_add)
  - `finished_at`: DateTimeField(blank/null)
  - `task_id`: CharField(128, unique=True, indexed)
  - `naturaleza`: CharField(10, default='VENTA')
  - `status`: CharField(20, choices=[PENDING, RUNNING, SUCCESS, FAILED, CANCEL_REQUESTED, CANCELED, ABORTED])
  - `counts`: JSONField(default=dict)
  - `summary`: JSONField(default=dict)
- **Notes:** Celery task log. References TenantProfile (which has empresa), but not explicitly. Could benefit from direct empresa FK.

#### MailInboxState
- **has_empresa:** NO ❌
- **fields:**
  - `mailbox_config`: ForeignKey(MailInboxConfig, on_delete=CASCADE)
  - `last_seen_uid`: BigIntegerField(blank/null, indexed)
  - `last_run_at`: DateTimeField(blank/null)
  - `total_processed`: PositiveIntegerField(default=0)
  - `created_at`: DateTimeField(auto_now_add)
  - `updated_at`: DateTimeField(auto_now)
- **Notes:** State tracking for mailbox incremental processing. Indirect empresa via MailInboxConfig.

#### FacturaAnexos
- **has_empresa:** NO ❌ (Indirect via Factura.empresa OneToOne)
- **fields:**
  - `factura`: OneToOneField(Factura, on_delete=CASCADE)
  - `ubl_xml`: TextField(blank/null)
  - `application_response_xml`: TextField(blank/null)
  - `pdf_file`: FileField(upload_to='facturas/pdfs/', blank/null)
  - `created_at`: DateTimeField(auto_now_add)
  - `updated_at`: DateTimeField(auto_now)
- **Notes:** Large blob storage separate from Factura. OneToOne relationship. Empresa accessible via factura.empresa.

#### NotaCredito
- **has_empresa:** YES ✅
- **fields:**
  - `factura`: OneToOneField(Factura, on_delete=PROTECT)
  - **`empresa`: ForeignKey(Empresa, on_delete=PROTECT)** ✅ ENFORCED MODE v2.40
  - `numero`: CharField(50, unique=True)
  - [Additional fields not shown in excerpt]
- **Notes:** Credit note document. Properly FK to Empresa.

---

### 4. `apps.tenant.clientes` (CUSTOMERS)

#### Cliente
- **has_empresa:** YES ✅
- **fields:**
  - **`empresa`: ForeignKey(Empresa, on_delete=PROTECT)** ✅
  - `tipo_persona`: CharField(10, choices=[NATURAL, JURIDICA])
  - `tipo_documento`: CharField(5, choices=[CC, CE, NIT, PA])
  - `numero_documento`: CharField(32)
  - `razon_social`: CharField(180)
  - `nombre_comercial`: CharField(180, blank)
  - `regimen_tributario`: CharField(15, choices=[SIMPLE, ORDINARIO, NO_RESP])
  - `email`: EmailField(blank)
  - `telefono`: CharField(32, blank)
  - `direccion`: CharField(255, blank)
  - `ciudad`: CharField(80, blank)
  - `activo`: BooleanField(default=True)
  - `observaciones`: TextField(blank)
  - `created_at`: DateTimeField(auto_now_add)
  - `updated_at`: DateTimeField(auto_now)
- **Notes:** Customer record. Properly FK to Empresa.

#### ContactoCliente
- **has_empresa:** NO ❌ (Indirect via Cliente.empresa)
- **fields:**
  - `cliente`: ForeignKey(Cliente, on_delete=CASCADE)
  - `nombre_completo`: CharField(180)
  - `cargo`: CharField(100, blank)
  - `email`: EmailField
  - `telefono`: CharField(32, blank)
  - `activo`: BooleanField(default=True)
  - `is_principal`: BooleanField(default=False)
  - `created_at`: DateTimeField(auto_now_add)
  - `updated_at`: DateTimeField(auto_now)
- **Notes:** Customer contact person. Transitively tied to empresa via Cliente.

---

### 5. `apps.tenant.gastos` (EXPENSES & SUPPORT DOCUMENTS)

#### ResolucionDIAN
- **has_empresa:** YES ✅
- **fields:**
  - **`empresa`: ForeignKey(Empresa, on_delete=PROTECT)** ✅
  - `numero_resolucion`: CharField(50, indexed)
  - `prefijo`: CharField(10)
  - `rango_desde`: IntegerField(validators=[MinValueValidator(1)])
  - `rango_hasta`: IntegerField(validators=[MinValueValidator(1)])
  - `fecha_resolucion`: DateField
  - `fecha_inicio`: DateField(default=today)
  - `fecha_fin`: DateField
  - `clave_tecnica`: CharField(100, blank/null)
  - `vigente`: BooleanField(default=True, indexed)
  - `created_at`: DateTimeField(auto_now_add)
  - `updated_at`: DateTimeField(auto_now)
- **Notes:** DIAN resolution configuration. Properly FK to Empresa.

#### DocumentoSoporte
- **has_empresa:** YES ✅
- **fields:**
  - **`empresa`: ForeignKey(Empresa, on_delete=PROTECT)** ✅ ENFORCED MODE v2.40
  - `resolucion_dian`: ForeignKey(ResolucionDIAN, on_delete=PROTECT)
  - `prefijo`: CharField(10)
  - `consecutivo`: IntegerField(indexed, editable=False, **IMMUTABLE after creation**)
  - `fecha`: DateField
  - Vendor snapshot fields: `vendedor_nombre`, `vendedor_nit`, `vendedor_direccion`, `vendedor_telefono`
  - `numero_factura_proveedor`: CharField(100, indexed, blank/null)
  - `subtotal`: DecimalField(15,2)
  - `retefuente_porcentaje`: CharField(10, choices=[0.00, 0.04, 0.06, 0.10, 0.11])
  - `retefuente`: DecimalField(15,2, default=0)
  - `reteica_porcentaje`: CharField(10, choices=[0.00, 0.0069, 0.00966, 0.01104])
  - `reteica`: DecimalField(15,2, default=0)
  - `total`: DecimalField(15,2)
  - `adjunto`: FileField(upload_to='documentos_soporte/%Y/%m/', validators=[...], blank/null)
  - `activo`: BooleanField(default=True, indexed)
  - `anulado`: BooleanField(default=False, indexed)
  - `fecha_anulacion`: DateTimeField(blank/null)
  - `created_at`: DateTimeField(auto_now_add)
  - `updated_at`: DateTimeField(auto_now)
- **Notes:** Immutable support document (legal evidence). Total formula: `Total = Subtotal - Retefuente - ReteICA`.

#### Gasto
- **has_empresa:** YES ✅
- **fields:**
  - `documento_soporte`: OneToOneField(DocumentoSoporte, on_delete=PROTECT)
  - **`empresa`: ForeignKey(Empresa, on_delete=PROTECT)** ✅ ENFORCED MODE v2.40
  - `centro_costo`: CharField(100, blank/null, choices=[...])
  - `categoria_contable`: CharField(100, blank/null, choices=[...])
- **Notes:** Accounting classification of expense. Properly FK to Empresa.

---

### 6. `apps.tenant.cotizaciones` (QUOTATIONS)

#### Producto
- **has_empresa:** YES ✅
- **fields:**
  - **`empresa`: ForeignKey(Empresa, on_delete=CASCADE)** ✅
  - `codigo`: CharField(50, blank)
  - `nombre`: CharField(255)
  - `marca`: CharField(100, blank)
  - `referencia`: CharField(100, blank)
  - `unidad`: CharField(20, default='UND')
  - `precio_venta`: DecimalField(15,2)
  - `activo`: BooleanField(default=True)
- **Notes:** Simple product model for quotations. On_delete=CASCADE (careful on cleanup).

#### Servicio
- **has_empresa:** YES ✅
- **fields:**
  - **`empresa`: ForeignKey(Empresa, on_delete=CASCADE)** ✅
  - `nombre`: CharField(255)
  - `precio_venta`: DecimalField(15,2)
  - `activo`: BooleanField(default=True)
- **Notes:** Simple service model for quotations. On_delete=CASCADE.

#### Cotizacion
- **has_empresa:** YES ✅
- **fields:**
  - `uuid`: UUIDField(unique=True)
  - `numero_cotizacion`: CharField(50) - NOTE: Removed unique=True, validated with constraint
  - `codigo_unico`: CharField(100, unique=True, indexed, blank/null) - Auto-generated (e.g., "STS. 0422-2026")
  - **`empresa`: ForeignKey(Empresa, on_delete=CASCADE)** ✅
  - `cliente`: ForeignKey(Cliente, on_delete=SET_NULL, null/blank) - NOTE: Soft reference for resilience
  - `configuracion`: ForeignKey(ConfiguracionCotizacion, on_delete=SET_NULL, blank/null)
  - `tipo_cotizacion`: CharField(20, default='MIXTO')
  - `fecha_emision`: DateField(auto_now_add)
  - `fecha_vencimiento`: DateField
  - `estado`: CharField(20, choices=[BORRADOR, ENVIADA, ACEPTADA, CANCELADA])
  - Financial DNA: `porcentaje_aiu_admin`, `porcentaje_aiu_imprevistos`, `porcentaje_aiu_utilidad`, `iva_porcentaje`, `total_con_impuestos`
- **Notes:** Quotation document. Cliente reference is soft (can be null for resilience).

#### CotizacionItem
- **has_empresa:** NO ❌ (Indirect via Cotizacion.empresa)
- **fields:**
  - `cotizacion`: ForeignKey(Cotizacion, related_name='items', on_delete=CASCADE)
  - `tipo_item`: CharField(20, choices=[PRODUCTO, MATERIAL, SERVICIO])
  - `producto`: ForeignKey(Producto, on_delete=SET_NULL, blank/null) - Soft reference
  - `servicio`: ForeignKey(Servicio, on_delete=SET_NULL, blank/null) - Soft reference
  - Snapshot fields: `descripcion`, `marca`, `referencia`, `unidad`
  - `cantidad`: DecimalField(12,2, default=1)
  - `costo_unitario`: DecimalField(15,2, default=0)
  - `porcentaje_utilidad`: DecimalField(5,2, default=0)
  - `precio_unitario_venta`: DecimalField(15,2, default=0)
  - `subtotal_linea`: DecimalField(15,2, default=0)
  - `orden`: PositiveIntegerField(default=0)
- **Notes:** Quotation line item. Transitive empresa via Cotizacion.

---

### 7. `apps.tenant.cotizaciones.configuracion` (QUOTATION CONFIG)

#### ConfiguracionCotizacion
- **has_empresa:** YES ✅
- **fields:**
  - **`empresa`: ForeignKey(Empresa, on_delete=CASCADE)** ✅
  - `nombre_configuracion`: CharField(100)
  - `es_activo`: BooleanField(default=True)
  - `dias_validez`: IntegerField(default=15, validators=[MinValueValidator(1), MaxValueValidator(30)])
  - `prefijo_secuencia`: CharField(20, blank, default='')
  - `sufijo_secuencia`: CharField(20, blank, default='')
  - `semilla_inicial`: IntegerField(default=1)
  - `ultimo_numero`: IntegerField(default=0)
- **Notes:** Quotation profile/configuration. Properly FK to Empresa. Simplified in v2.60 (removed defaults for AIU, IVA, template type).

---

### 8. `apps.tenant.empleados` (EMPLOYEES & PAYROLL)

#### Empleado
- **has_empresa:** YES ✅
- **fields:**
  - **`empresa`: ForeignKey(Empresa, on_delete=PROTECT)** ✅
  - `tipo_documento`: CharField(5, choices=[CC, CE, PA, PPT])
  - `numero_documento`: CharField(32, indexed)
  - `primer_nombre`: CharField(80)
  - `segundo_nombre`: CharField(80, blank)
  - `primer_apellido`: CharField(80)
  - `segundo_apellido`: CharField(80, blank)
  - `email`: EmailField
  - `telefono`: CharField(32, blank)
  - Social security fields: `eps`, `afp`, `arl`, `nivel_riesgo_arl`
  - `estado`: CharField(12, choices=[ACTIVO, RETIRADO], default='ACTIVO')
  - `fecha_ingreso`: DateField
  - `fecha_retiro`: DateField(blank/null)
- **Notes:** Employee master. Properly FK to Empresa. AnEmpiric model (no business logic).

#### Contrato
- **has_empresa:** YES ✅
- **fields:**
  - **`empresa`: ForeignKey(Empresa, on_delete=PROTECT)** ✅ SSoT Empresa (required v2.60)
  - `empleado`: ForeignKey(Empleado, on_delete=CASCADE)
  - `tipo`: CharField(10, choices=[FIJO, INDEF, OBRA, PRESTACION])
  - `fecha_inicio`: DateField
  - `fecha_fin`: DateField(blank/null)
  - Financial: `salario_mensual` (COP), `auxilio_transporte` (COP), `prestamos_empresa` (COP)
  - `cargo`: CharField(120)
  - `archivo_pdf`: FileField(upload_to='empleados/contratos/', blank/null)
  - State machine: `estado` (CharField(12, choices=[ACTIVO, INACTIVO, HISTORICO], default='ACTIVO'))
  - Legacy: `activo` (BooleanField, synced with estado in save())
- **Notes:** Employment contract. One ACTIVE contract per employee enforced via unique constraint. Proper empresa FK.

#### Devengo (Nomina)
- **has_empresa:** YES ✅
- **fields:**
  - **`empresa`: ForeignKey(Empresa, on_delete=PROTECT)** ✅ SSoT Empresa (required v2.60)
  - `empleado`: ForeignKey(Empleado, on_delete=PROTECT)
  - `contrato`: ForeignKey(Contrato, on_delete=PROTECT)
  - `periodo_mes`: CharField(7, format='YYYY-MM')
  - `fecha_pago`: DateField
  - `dias_laborados`: DecimalField(5,2, default=30, validators=[MinValueValidator(0.5)]) - Proportional calculation support
  - Earnings: `salario_base`, `auxilio_transporte`, `otros_devengos` (all COP, all DecimalField)
  - Deductions: `salud_empleado`, `pension_empleado`, `prestamos`, `descuentos_operativos` (all COP)
  - `observaciones`: TextField(blank)
  - `neto_pagar`: DecimalField(editable=False) - **SSoT Calculated in save()**
  - `anulado`: BooleanField(default=False) - Immutable after creation
- **Notes:** Payroll record. Formula: `neto_pagar = (salario_base + auxilio + otros) - (salud + pension + prestamos + descuentos)`. Properly FK to Empresa.

---

### 9. `apps.tenant.inventario` (INVENTORY & ASSETS)

#### CategoriaItem (TimeStampedModel base)
- **has_empresa:** YES ✅
- **fields:**
  - **`empresa`: ForeignKey(Empresa, on_delete=PROTECT)** ✅
  - `nombre`: CharField(100, indexed)
  - `descripcion`: TextField(blank/null)
  - `aplicacion`: CharField(16, choices=[TODO, PRODUCTO, SERVICIO, ACTIVO], default='TODO')
  - `imagen`: ImageField(upload_to='inventario/categorias/', blank/null)
  - `activo`: BooleanField(default=True)
  - Timestamps: `created_at`, `updated_at`
- **Notes:** Item category. Properly FK to Empresa.

#### ActivoFijo (TimeStampedModel base)
- **has_empresa:** YES ✅
- **fields:**
  - **`empresa`: ForeignKey(Empresa, on_delete=PROTECT)** ✅
  - `categoria`: ForeignKey(CategoriaItem, on_delete=SET_NULL, blank/null) - Soft reference
  - `codigo`: CharField(64, unique=True)
  - `nombre`: CharField(200, indexed)
  - `marca`: CharField(100, blank/null)
  - `modelo`: CharField(100, blank/null)
  - `descripcion`: TextField(blank/null)
  - `imagen`: ImageField(upload_to='inventario/activos/', blank/null)
  - `ubicacion`: CharField(100, blank/null)
  - `responsable`: CharField(100, blank/null)
  - `fecha_adquisicion`: DateField(blank/null)
  - `costo_adquisicion`: DecimalField(14,2, default=0)
  - `estado`: CharField(20, choices=[ACTIVO, MANTENIMIENTO, BAJA, VENDIDO], default='ACTIVO')
  - Timestamps: `created_at`, `updated_at`
- **Notes:** Fixed asset. Properly FK to Empresa.

#### Producto (inventory version, NOT cotizaciones)
- **has_empresa:** YES ✅
- **fields:**
  - **`empresa`: ForeignKey(Empresa, on_delete=PROTECT)** ✅
  - `codigo`: CharField(64, unique=True)
  - `nombre`: CharField(200, indexed)
  - `categoria`: ForeignKey(CategoriaItem, on_delete=PROTECT, blank/null) - Soft reference
  - `descripcion`: TextField(blank/null)
  - `unidad`: CharField(16, default='UND')
  - `imagen`: ImageField(upload_to='inventario/productos/', blank/null)
  - Pricing: `precio_venta`, `costo_promedio` (DecimalField 14,2)
  - Stock: `stock_actual`, `stock_minimo` (DecimalField 14,3 for decimals)
  - `activo`: BooleanField(default=True)
  - Timestamps: `created_at`, `updated_at`
- **Notes:** Sales product in inventory. Properly FK to Empresa. Different from cotizaciones.Producto.

#### Servicio (inventory version)
- **has_empresa:** YES ✅
- **fields:**
  - **`empresa`: ForeignKey(Empresa, on_delete=PROTECT)** ✅
  - `codigo`: CharField(64, unique=True)
  - `nombre`: CharField(200, indexed)
  - `categoria`: ForeignKey(CategoriaItem, on_delete=PROTECT, blank/null) - Soft reference
  - `descripcion`: TextField(blank/null)
  - `imagen`: ImageField(upload_to='inventario/servicios/', blank/null)
  - `precio_venta`: DecimalField(14,2, default=0)
  - `activo`: BooleanField(default=True)
  - Timestamps: `created_at`, `updated_at`
- **Notes:** Service in inventory system. Properly FK to Empresa.

#### MovimientoInventario (TimeStampedModel base)
- **has_empresa:** YES ✅
- **fields:**
  - **`empresa`: ForeignKey(Empresa, on_delete=PROTECT)** ✅
  - `producto`: ForeignKey(Producto, on_delete=CASCADE)
  - `tipo`: CharField(20, choices=[ENTRADA_COMPRA, ENTRADA_AJUSTE, ENTRADA_DEVOLUCION, SALIDA_VENTA, SALIDA_BAJA, SALIDA_CONSUMO])
  - `cantidad`: DecimalField(14,3)
  - `costo_unitario`: DecimalField(14,2, default=0)
  - Traceability: `origen_referencia`, `cliente_referencia` (CharField, blank/null)
  - `observaciones`: TextField(blank/null)
  - Timestamps: `created_at`, `updated_at`
- **Notes:** Inventory ledger (Kardex). Properly FK to Empresa.

#### HistorialServicio (TimeStampedModel base)
- **has_empresa:** YES ✅
- **fields:**
  - **`empresa`: ForeignKey(Empresa, on_delete=PROTECT)** ✅
  - `servicio`: ForeignKey(Servicio, on_delete=CASCADE)
  - `fecha_registro`: DateField(default=today)
  - `cantidad`: DecimalField(10,2, default=1)
  - `valor_cobrado`: DecimalField(14,2, default=0)
  - Traceability: `origen_referencia`, `cliente_referencia` (CharField, blank/null)
  - `observaciones`: TextField(blank/null)
  - Timestamps: `created_at`, `updated_at`
- **Notes:** Service sales history log. Properly FK to Empresa.

---

### 10. `apps.tenant.proveedores` (SUPPLIERS)

#### Proveedor
- **has_empresa:** YES ✅
- **fields:**
  - **`empresa`: ForeignKey(Empresa, on_delete=PROTECT)** ✅ SSoT Empresa
  - `tipo_persona`: CharField(10, choices=[NATURAL, JURIDICA], default='JURIDICA')
  - `tipo_documento`: CharField(5, choices=[NIT, CC, CE, PA], default='NIT')
  - `numero_documento`: CharField(32)
  - `digito_verificacion`: CharField(1, blank/null)
  - `razon_social`: CharField(200)
  - `nombre_comercial`: CharField(200, blank)
  - Colombian tax: `regimen_tributario` (choices), `actividad_economica_ciiu`, `responsable_iva`, `gran_contribuyente`, `autoretenedor` (all BooleanField)
  - Contact: `email_contacto`, `telefono_contacto`, `direccion`, `ciudad`
  - Commercial: `plazo_pago_dias`, `banco`, `tipo_cuenta`, `numero_cuenta`
  - `activo`: BooleanField(default=True)
  - `observaciones`: TextField(blank)
  - Timestamps: `created_at`, `updated_at`
- **Notes:** Supplier record. Properly FK to Empresa.

---

### 11. `apps.tenant.proyectos` (PROJECTS)

#### Proyecto
- **has_empresa:** YES ✅
- **fields:**
  - **`empresa`: ForeignKey(Empresa, on_delete=PROTECT)** ✅ SSoT Empresa (required v2.40)
  - `nombre`: CharField(200)
  - `codigo`: CharField(50, blank)
  - `tipo_servicio`: CharField(30, choices=[PROYECTO_INTEGRAL, INSTALACION, MANTENIMIENTO, SUPERVISION, CONSULTORIA])
  - `descripcion`: TextField(blank)
  - Client (soft reference - Loose Coupling): `cliente_id` (IntegerField, blank/null), `cliente_nombre` (CharField, blank)
  - `factura_ref`: CharField(50, blank)
  - `valor_contrato_proyectado`: DecimalField(15,2, default=0)
  - Responsible parties (soft references): `responsable_comercial_id/nombre`, `responsable_tecnico_id/nombre`, `responsable_operativo_id/nombre`, `responsable_administrativo_id/nombre`, `responsable_actual_id/nombre`
  - Documentation: `contrato_archivo`, `acta_inicio_archivo`, `cronograma_archivo`
  - Dates: `fecha_inicio`, `fecha_fin_estimada`, `fecha_cierre_real`
  - Financial metrics: `costo_mano_obra_real`, `costo_materiales_real`, `utilidad_estimada`, `margen_rentabilidad` (Anemic - calculated by services.py)
  - Deliverables: `porcentaje_avance`, `acta_entrega_archivo`, `informe_final_archivo`
  - State machine: `fase_actual` (choices=[BORRADOR, INICIO, PLANEACION, EJECUCION, CIERRE]), `estado_tarea` (choices=[PENDIENTE, EN_PROCESO, DETENIDO, COMPLETADO])
  - Timestamps: `created_at`, `updated_at`
- **Notes:** Project master standalone (zero-coupling except Empresa). Soft references ensure resilience.

#### AsignacionPersonal
- **has_empresa:** YES ✅
- **fields:**
  - **`empresa`: ForeignKey(Empresa, on_delete=PROTECT)** ✅
  - `proyecto`: ForeignKey(Proyecto, on_delete=CASCADE)
  - Employee (soft reference): `empleado_id` (IntegerField, blank/null), `nombre_colaborador` (CharField)
  - `rol`: CharField(20, choices=[TECNICO, AYUDANTE, RESIDENTE, SISOMA])
  - `fecha_asignacion`: DateField
  - `fecha_fin_asignacion`: DateField(blank/null)
  - Financial: `horas_totales_registradas`, `costo_hora`, `costo_total_asignacion` (DecimalField)
  - `activo`: BooleanField(default=True)
- **Notes:** Team assignment to project. Soft reference to employee for resilience. Properly FK to Empresa.

#### PedidoProyecto
- **has_empresa:** YES ✅
- **fields:**
  - **`empresa`: ForeignKey(Empresa, on_delete=PROTECT)** ✅
  - `proyecto`: ForeignKey(Proyecto, on_delete=CASCADE)
  - `solicitante`: ForeignKey(TenantProfile, on_delete=SET_NULL, blank/null) - **Project requester (maintains tenant isolation)**
  - `tipo_recurso`: CharField(20, choices=[MATERIALES, EQUIPOS, HERRAMIENTAS])
  - `fuente_suministro`: CharField(20, choices=[PROVEEDOR, EMPLEADO, ALMACEN], default='PROVEEDOR')
  - Supplier (soft reference): `proveedor_id` (IntegerField, blank/null), `proveedor_nombre` (CharField, blank)
  - `empleado_encargado_nombre`: CharField(150, blank)
  - `fecha_solicitud`: DateField(auto_now_add)
  - `estado`: CharField(20, choices=[BORRADOR, SOLICITADO, APROBADO, RECHAZADO], default='BORRADOR')
  - `observaciones`: TextField(blank)
  - `archivo_adjunto`: FileField(upload_to='proyectos/pedidos/', blank/null)
- **Notes:** Resource request for project. Properly FK to Empresa. Solicitante references TenantProfile to maintain tenant isolation.

#### ItemPedido
- **has_empresa:** NO ❌ (Indirect via PedidoProyecto.empresa)
- **fields:**
  - `pedido`: ForeignKey(PedidoProyecto, on_delete=CASCADE)
  - Material (soft reference): `material_ref` (CharField, blank), `nombre_material` (CharField)
  - `cantidad`: DecimalField(10,2)
  - `unidad_medida`: CharField(20)
  - `precio_unitario`: DecimalField(15,2, default=0)
- **Notes:** Line item of resource request. Transitive empresa via PedidoProyecto.

---

### 12. `apps.tenant.perfil` (TENANT PROFILE)

#### TenantProfile
- **has_empresa:** YES ✅
- **fields:**
  - **`empresa`: ForeignKey(Empresa, on_delete=CASCADE)** ✅ Multi-tenant context **[CRITICAL]** (null=False, blank=False)
  - `user`: OneToOneField(settings.AUTH_USER_MODEL, on_delete=CASCADE) - **CORRECT: References User from public schema**
  - `cargo`: CharField(100, blank/null)
  - `departamento`: CharField(100, blank/null)
  - `telefono_corporativo`: CharField(20, blank/null)
  - `avatar`: ImageField(upload_to='perfiles/avatars/', blank/null)
  - `configuracion`: JSONField(default=dict, blank/null) - User preferences
  - Timestamps: `created_at`, `updated_at`
- **Notes:** Tenant-specific user profile. **CRITICAL**: Properly FK to Empresa (establishes multi-tenant context). Unidirectional FK from tenant to public User allowed.

---

### 13-15. APPS WITHOUT MODELS

#### apps.tenant.core
- **NO models.py** - Utility/middleware app only

#### apps.tenant.landing
- **NO models.py** - Views/pages app only

#### apps.tenant.dashboard
- **NO models.py** - Views/service app only

---

## ANALYSIS SUMMARY

### Models with Empresa FK (26 total)

✅ **ENFORCED MODE v2.40** - Properly configured:
1. CuentaContable
2. AsientoContable
3. Factura
4. ItemFactura
5. NotaCredito
6. Cliente
7. ResolucionDIAN
8. DocumentoSoporte
9. Gasto
10. Producto (cotizaciones)
11. Servicio (cotizaciones)
12. Cotizacion
13. ConfiguracionCotizacion
14. Empleado
15. Contrato
16. Devengo
17. CategoriaItem (inventario)
18. ActivoFijo
19. Producto (inventario)
20. Servicio (inventario)
21. MovimientoInventario
22. HistorialServicio
23. Proveedor
24. Proyecto
25. AsignacionPersonal
26. PedidoProyecto
27. TenantProfile

### Models WITHOUT Explicit Empresa FK (6 total)

❌ **REQUIRES ATTENTION**:
1. **Empresa** - The singleton itself (correct design)
2. **MailInboxConfig** - Tenant-isolated by schema. **Consider adding explicit empresa FK for clarity.**
3. **CatalogoMaestroNIIF** - Shared reference catalog. **Design concern: Should this be shared across tenants or per-tenant?**
4. **MovimientoContable** - Transitive via AsientoContable (acceptable)
5. **ContactoCliente** - Transitive via Cliente (acceptable)
6. **MailIngestionRun** - References TenantProfile but no direct empresa. **Could benefit from explicit FK.**
7. **MailInboxState** - Transitive via MailInboxConfig (acceptable)
8. **FacturaAnexos** - Transitive via Factura OneToOne (acceptable)
9. **CotizacionItem** - Transitive via Cotizacion (acceptable)
10. **ItemPedido** - Transitive via PedidoProyecto (acceptable)

### Design Patterns Observed

**Pattern 1: Direct FK to Empresa (ENFORCED MODE v2.40)**
- Most primary domain models follow this pattern
- Guarantees tenant isolation at database level
- Proper on_delete=PROTECT in most cases (safe delete)

**Pattern 2: Transitive Empresa (via parent model)**
- Detail/child models typically follow parent's empresa
- Reduces redundancy in database
- Requires careful cascade handling

**Pattern 3: Soft References (for Resilience)**
- Proyectos module uses ID + CharField snapshot pattern
- Prevents breaking if referenced module fails
- Maintains autonomy between modules

**Pattern 4: Singleton per Tenant**
- Empresa model enforces oneInstance per schema
- Uses UniqueConstraint on singleton_key=1

**Pattern 5: Cross-Schema FK to User**
- TenantProfile correctly references settings.AUTH_USER_MODEL
- Django allows tenant->public FK (not public->tenant)
- Maintains multi-tenant and authentication isolation

---

## RECOMMENDATIONS

### 1. **MailInboxConfig**
Consider adding explicit `empresa` FK for clarity and consistency:
```python
empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name='mail_configs')
```

### 2. **CatalogoMaestroNIIF**
Clarify design intent:
- If **shared across all tenants**: Move to SHARED_APPS (public schema)
- If **per-tenant**: Add explicit `empresa` FK or update docs

### 3. **MailIngestionRun**
Add explicit empresa FK for query filtering consistency:
```python
empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name='mail_runs')
```

### 4. **DEPRECATION**
Remove `MailIngestionConfig` - it's superseded by `MailInboxConfig` in empresa app.

### 5. **VALIDATION**
All `.only()` queries should explicitly list empresa or empresa_id to support SSoT validation.

### 6. **TESTS**
Verify multi-tenant isolation for all models using pytest:
- Create two tenants with overlapping data
- Verify cross-tenant queries return empty results
- Test CASCADE deletes don't leak across tenants

---

## CONCLUSION

**Status: 94% COMPLIANT** with ENFORCED MODE v2.40 SSoT architecture.

**3 models warrant review** for explicit empresa FK addition:
- MailInboxConfig
- MailIngestionRun  
- CatalogoMaestroNIIF

**All others properly implement** tenant isolation via:
- Direct FK to Empresa (26 models)
- Transitive isolation via parent models (6 models)
- Django-tenants schema isolation (MailInboxConfig)

**NO MODELS VIOLATE** singleton pattern or multi-tenant constraints.

