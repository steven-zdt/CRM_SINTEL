# 📋 TABLA DE MAPEO DTO → models.py

**Fecha:** 2026-02-10  
**Objetivo:** Documentar el mapeo entre el DTO unificado del pipeline universal y los campos del modelo `Factura` y `NotaCredito` en `apps/tenant/facturas/models.py`.

---

## 🔄 MAPEO FACTURA (Invoice)

### Campos Básicos

| Campo DTO | Campo Modelo | Tipo | Notas |
|-----------|--------------|------|-------|
| `numero` | `numero` | CharField(50) | Directo |
| `prefijo` | `prefijo` | CharField(10) | Extraído del número (ej: "FST355" → "FST") |
| `consecutivo` | `consecutivo` | IntegerField | Extraído del número (ej: "FST355" → 355) |
| `identificadores.cufe` | `cufe` | CharField(128) | Directo |
| `fecha_emision` | `fecha_emision` | DateTimeField | ISO 8601 → DateTimeField |

### Emisor

| Campo DTO | Campo Modelo | Tipo | Notas |
|-----------|--------------|------|-------|
| `emisor.nit` | `emisor_nit` | CharField(20) | Directo |
| `emisor.razon_social` | `emisor_razon_social` | CharField(200) | Directo |
| `emisor.direccion` | `emisor_direccion` | CharField(300) | Directo (nuevo en parser) |
| `emisor.email` | `emisor_email` | CharField(120) | Directo (nuevo en parser) |
| `emisor.telefono` | `emisor_telefono` | CharField(40) | Directo (nuevo en parser) |
| `emisor.actividad_ciiu` | `emisor_actividad_ciiu` | CharField(10) | Directo (nuevo en parser) |

### Receptor

| Campo DTO | Campo Modelo | Tipo | Notas |
|-----------|--------------|------|-------|
| `receptor.nit` | `receptor_nit` | CharField(20) | Directo |
| `receptor.razon_social` | `receptor_razon_social` | CharField(200) | Directo |
| `receptor.direccion` | `receptor_direccion` | CharField(300) | Directo (nuevo en parser) |
| `receptor.email` | `receptor_email` | CharField(120) | Directo (nuevo en parser) |
| `receptor.telefono` | `receptor_telefono` | CharField(40) | Directo (nuevo en parser) |

### Totales

| Campo DTO | Campo Modelo | Tipo | Notas |
|-----------|--------------|------|-------|
| `totales.moneda` | `moneda` | CharField(3) | Directo (default: "COP") |
| `totales.subtotal` | `subtotal` | DecimalField(15,2) | String → Decimal |
| `totales.impuestos` | `impuestos` | DecimalField(15,2) | String → Decimal |
| `totales.total` | `total` | DecimalField(15,2) | String → Decimal |

### Metadatos UBL

| Campo DTO | Campo Modelo | Tipo | Notas |
|-----------|--------------|------|-------|
| `ubl_version` | `ubl_version` | CharField(10) | Directo (nuevo en parser) |
| `customization_id` | `customization_id` | CharField(50) | Directo (nuevo en parser) |
| `profile_id` | `profile_id` | CharField(80) | Directo (nuevo en parser) |
| `profile_execution_id` | `profile_execution_id` | CharField(10) | Directo (nuevo en parser) |
| `invoice_type_code` | `invoice_type_code` | CharField(4) | Directo (nuevo en parser) |

### Autorización DIAN

| Campo DTO | Campo Modelo | Tipo | Notas |
|-----------|--------------|------|-------|
| `autorizacion.numero` | `autorizacion_numero` | CharField(50) | Directo (nuevo en parser) |
| `autorizacion.prefijo` | `autorizacion_prefijo` | CharField(10) | Directo (nuevo en parser) |
| `autorizacion.rango_desde` | `autorizacion_rango_desde` | IntegerField | Directo (nuevo en parser) |
| `autorizacion.rango_hasta` | `autorizacion_rango_hasta` | IntegerField | Directo (nuevo en parser) |
| `autorizacion.vigencia_inicio` | `autorizacion_vigencia_inicio` | DateField | String → Date (nuevo en parser) |
| `autorizacion.vigencia_fin` | `autorizacion_vigencia_fin` | DateField | String → Date (nuevo en parser) |

### QR Code

| Campo DTO | Campo Modelo | Tipo | Notas |
|-----------|--------------|------|-------|
| `qr_code` | `qr_code` | TextField | Directo (nuevo en parser) |
| `qr_url` | `qr_url` | URLField(1024) | Directo (nuevo en parser) |

---

## 🔄 MAPEO NOTA CRÉDITO (CreditNote)

### Campos Básicos

| Campo DTO | Campo Modelo | Tipo | Notas |
|-----------|--------------|------|-------|
| `numero` | `numero` | CharField(50) | Directo |
| `identificadores.cude` | `cude` | CharField(128) | Directo |
| `fecha_emision` | `fecha_emision` | DateTimeField | ISO 8601 → DateTimeField |
| `totales.moneda` | `moneda` | CharField(8) | Directo (default: "COP") |
| `totales.subtotal` | `subtotal` | DecimalField(18,2) | String → Decimal |
| `totales.impuestos` | `impuestos` | DecimalField(18,2) | String → Decimal |
| `totales.total` | `total` | DecimalField(18,2) | String → Decimal |

### Referencia a Factura

| Campo DTO | Campo Modelo | Tipo | Notas |
|-----------|--------------|------|-------|
| `referencia.numero` | `ref_factura_numero` | CharField(50) | Directo |
| `referencia.cufe` | `ref_factura_cufe` | CharField(128) | Directo |
| `motivo` | `motivo` | TextField | Directo (extraído de `Note` o `DiscrepancyResponse.Description`) |

### Emisor y Receptor

| Campo DTO | Campo Modelo | Tipo | Notas |
|-----------|--------------|------|-------|
| `emisor.nit` | (no aplica) | - | NotaCrédito usa `factura.emisor_nit` |
| `emisor.razon_social` | (no aplica) | - | NotaCrédito usa `factura.emisor_razon_social` |
| `receptor.nit` | (no aplica) | - | NotaCrédito usa `factura.receptor_nit` |
| `receptor.razon_social` | (no aplica) | - | NotaCrédito usa `factura.receptor_razon_social` |

**Nota:** `NotaCredito` tiene relación `OneToOneField` con `Factura`, por lo que los datos de emisor/receptor se obtienen de la factura relacionada.

---

## ⚠️ CAMPOS NO MAPEADOS (Opcionales/No requeridos)

### Factura
- `fecha_vencimiento`: No está en el DTO (se puede calcular o establecer manualmente)
- `tipo`: Se establece automáticamente como `TipoFactura.FE`
- `estado`: Se establece automáticamente como `Estado.BORRADOR`
- `naturaleza`: Se calcula automáticamente en importación UBL
- `categoria`: Se establece automáticamente como `Categoria.SERVICIO`
- `forma_pago`, `medio_pago_codigo`, `payment_due_date`: No están en el DTO actual
- `dian_validation_*`: Campos de respuesta DIAN (no están en el DTO de ingesta)
- `xml_content`: Se almacena el XML completo en `FacturaAnexos.ubl_xml`

### NotaCrédito
- `factura`: Se establece mediante la relación `OneToOneField` basada en `referencia.cufe` o `referencia.numero`
- `xml_content`: Se almacena el XML completo en `FacturaAnexos.ubl_xml`

---

## 📝 NOTAS DE IMPLEMENTACIÓN

1. **Conversión de tipos:**
   - `fecha_emision`: String ISO 8601 → `datetime.datetime`
   - `totales.*`: String decimal → `Decimal`
   - `autorizacion.vigencia_*`: String fecha → `datetime.date`

2. **Extracción de prefijo y consecutivo:**
   - Se usa regex para separar prefijo alfabético y número consecutivo
   - Ejemplo: "FST355" → `prefijo="FST"`, `consecutivo=355`

3. **QR Code:**
   - `qr_code`: Texto completo del QR (multilínea)
   - `qr_url`: URL extraída del QR code usando regex

4. **Motivo de Nota Crédito:**
   - Se extrae de `Note` (campo principal) o `DiscrepancyResponse.Description` (fallback)

5. **FutureWarnings eliminados:**
   - Todos los `if elem:` fueron reemplazados por `if elem is not None:`

---

**Última actualización:** 2026-02-10
