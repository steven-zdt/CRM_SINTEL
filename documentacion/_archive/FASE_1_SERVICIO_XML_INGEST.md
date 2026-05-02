# Fase 1: Servicio General de Ingesta XML

**Objetivo**: Crear el paquete `apps/services/xml_ingest/` que provea parseo/validación/normalización XML reusable (multi-app), agnóstico del dominio, con soporte para tareas Celery tenant-aware.

**Fecha de implementación**: 2026-02-09

---

## Estructura del Paquete

```
apps/services/xml_ingest/
├── __init__.py              # Documentación y versión
├── contracts.py             # DTOs canónicos (Party, Totales, DocumentoXML)
├── normalizers.py           # Normalizadores transversales (NIT, moneda, fechas)
├── router.py                # Router inteligente (detección de tipo XML)
├── tasks.py                 # Tareas Celery tenant-aware
├── storage.py               # Storage opcional de blobs (FileField/S3)
├── parsers/
│   ├── __init__.py
│   └── ubl21.py            # Parsers UBL 2.1 (Invoice, ApplicationResponse, AttachedDocument)
└── tests/
    ├── __init__.py
    ├── test_parsers_ubl21.py
    ├── test_router.py
    └── test_normalizers.py
```

---

## Componentes Implementados

### 1. Contratos Canónicos (`contracts.py`)

**DTOs inmutables (frozen dataclasses)**:
- `Party`: Parte (emisor/receptor) con NIT y razón social normalizados
- `Totales`: Totales monetarios (subtotal, impuestos, total, moneda)
- `DocumentoXML`: DTO canónico completo con tipo, emisor, receptor, número, fecha, totales, identificadores, anexos y extras

**Principios**:
- Mínimo necesario: Solo campos esenciales para permitir persistencia parcializada
- Agnóstico del dominio: No conoce Factura, Gasto, Proveedor, etc.
- Inmutable: Dataclasses frozen para evitar mutaciones accidentales
- Estable: Cambios requieren versionado (v1, v2) para no romper consumidores

---

### 2. Normalizadores Transversales (`normalizers.py`)

**Funciones reutilizables**:
- `norm_nit(value)`: Normaliza NIT (elimina separadores, quita ceros a la izquierda, extrae base sin DV)
- `norm_moneda(value)`: Normaliza código de moneda (mayúsculas, sin espacios)
- `norm_fecha_iso(value)`: Normaliza fechas a ISO 8601 (tolerante a variantes)

**Principios**:
- Reutilizables: Usados por todas las apps consumidoras
- Consistentes: Misma lógica de normalización en todo el sistema
- Tolerantes: Manejan casos edge (None, vacíos, formatos variados)

---

### 3. Router Inteligente (`router.py`)

**Funciones**:
- `_sniff_root_element(xml_bytes)`: Detecta tipo de XML inspeccionando primeros bytes
- `parse_xml(xml_bytes)`: Parsea XML detectando automáticamente el tipo y delegando al parser correcto

**Tipos soportados**:
- `Invoice` → `parse_invoice_ubl21()`
- `ApplicationResponse` → `parse_application_response_ubl21()`
- `AttachedDocument` → `parse_attached_document_ubl21()`
- `Unknown` → Lanza `ValueError`

**Principios**:
- Detección automática: Sniff del root element para identificar tipo
- Extensible: Fácil agregar nuevos tipos sin tocar consumidores
- Delegación clara: Cada parser maneja su tipo específico

---

### 4. Parsers UBL 2.1 (`parsers/ubl21.py`)

**Funciones**:
- `parse_invoice_ubl21(xml_bytes)`: Parsea Invoice UBL 2.1
- `parse_application_response_ubl21(xml_bytes)`: Parsea ApplicationResponse UBL 2.1
- `parse_attached_document_ubl21(xml_bytes)`: Parsea AttachedDocument UBL 2.1

**Helpers internos**:
- `_get_text(element)`: Extrae texto de elemento XML de forma segura
- `_parse_party_ubl21(party_el)`: Parsea Party (emisor/receptor) desde XML UBL
- `_parse_totales_ubl21(root)`: Parsea totales monetarios desde XML UBL

**Principios**:
- Agnóstico: No inserta en BD de negocio; retorna `DocumentoXML` estandarizado
- Tolerante: Maneja variantes de UBL (diacríticos, offsets, namespaces)
- Mínimo: Extrae solo campos esenciales para permitir persistencia parcializada

---

### 5. Tareas Celery Tenant-Aware (`tasks.py`)

**Tarea**:
- `xml_ingest_task(schema, file_b64, hints)`: Procesa XML en background dentro del schema del tenant

**Características**:
- **Tenant-aware**: Usa `schema_context(schema)` para garantizar aislamiento por esquema
- **Agnóstico**: Retorna DTO serializable (sin acoplar a modelos de negocio)
- **Reintentos**: Configurados con backoff para errores transitorios
- **Logging**: Sin volcar XML completo (solo hash/longitud para depuración)

**Configuración**:
- `@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)`
- Nombre canónico: `xml_ingest.xml_ingest_task`

---

### 6. Storage Opcional (`storage.py`)

**Funciones**:
- `save_xml_bytes_storage(path_prefix, xml_bytes)`: Guarda XML bytes en storage (FileField/S3/MinIO/FS)
- `get_xml_bytes_from_storage(stored_path)`: Recupera XML bytes desde storage

**Uso opcional**: Si decides no retornar blobs por el DTO (por tamaño/seguridad), guarda xml_bytes en storage y expón solo la ruta/id.

---

## Tests Implementados

### ✅ Tests Unitarios (15 tests, todos pasando)

1. **`test_normalizers.py`** (7 tests):
   - `test_norm_nit_elimina_separadores`
   - `test_norm_nit_elimina_dv`
   - `test_norm_nit_elimina_ceros_izquierda`
   - `test_norm_nit_maneja_none`
   - `test_norm_moneda`
   - `test_norm_fecha_iso`
   - `test_norm_fecha_iso_invalida_retorna_original`

2. **`test_parsers_ubl21.py`** (3 tests):
   - `test_parse_invoice_minimo`
   - `test_parse_invoice_con_uuid`
   - `test_parse_invoice_invalido_lanza_error`

3. **`test_router.py`** (5 tests):
   - `test_invoice_routing`
   - `test_application_response_routing`
   - `test_attached_document_routing`
   - `test_unknown_type_lanza_error`
   - `test_sniff_root_element`

---

## Uso del Servicio

### Parseo Síncrono

```python
from apps.services.xml_ingest.router import parse_xml

# Parsear XML
xml_bytes = b'<Invoice xmlns="...">...</Invoice>'
doc = parse_xml(xml_bytes)

# Acceder a datos normalizados
print(doc.tipo)  # "UBL_INVOICE"
print(doc.emisor.nit)  # "901123299"
print(doc.totales.total)  # 1190000.0
```

### Parseo Asíncrono (Celery)

```python
from apps.services.xml_ingest.tasks import xml_ingest_task
import base64

# Codificar XML en base64
file_b64 = base64.b64encode(xml_bytes).decode('utf-8')

# Encolar tarea
result = xml_ingest_task.delay(
    schema="tenant1",
    file_b64=file_b64,
    hints={"source": "email", "mailbox_id": 123}
)

# Obtener resultado (cuando termine)
doc_dict = result.get()
```

---

## Integración con Apps Consumidoras (Fase 2)

**Nota**: La integración con `apps/tenant/facturas` se hará en la Fase 2. Por ahora, el servicio está listo para ser consumido.

**Contrato esperado**:
1. Apps consumidoras llaman a `parse_xml()` o `xml_ingest_task.delay()`
2. Reciben `DocumentoXML` o dict serializado
3. Aplican sus reglas de negocio (ej: determinación de naturaleza VENTA/COMPRA usando SSoT empresa)
4. Persisten solo lo necesario en su propio modelo (cumpliendo lista mínima)

---

## Criterios de Aceptación

### ✅ Completado

- ✅ Paquete `apps/services/xml_ingest/` creado con contracts, normalizers, router, parsers/ubl21.py, tasks (Celery tenant-aware)
- ✅ Tests unitarios de parser/router en verde (15 tests, todos pasando)
- ✅ Sin dependencias a modelos de negocio (agnóstico)
- ✅ Nombres de funciones compuestos (evita nombres reservados de librerías):
  - `parse_invoice_ubl21()` (no `parse_invoice()`)
  - `parse_application_response_ubl21()` (no `parse_application_response()`)
  - `parse_attached_document_ubl21()` (no `parse_attached_document()`)
  - `_parse_party_ubl21()` (no `_parse_party()`)
  - `_parse_totales_ubl21()` (no `_parse_totales()`)
  - `_sniff_root_element()` (no `_sniff()`)
  - `save_xml_bytes_storage()` (no `save()`)
  - `get_xml_bytes_from_storage()` (no `get()`)

---

## Próximos Pasos (Fase 2)

1. **Integración con `apps/tenant/facturas`**:
   - Reemplazar `apps/tenant/facturas/ubl_parser.py` por consumo de `apps/services/xml_ingest/`
   - Mantener reglas de negocio (naturaleza VENTA/COMPRA) en Service Layer de facturas
   - Aplicar idempotencia y persistencia parcializada

2. **Extensión a otras apps**:
   - `apps/tenant/gastos`: Consumir servicio para parseo de XMLs de gastos
   - Otras apps que requieran parseo XML

3. **Mejoras opcionales**:
   - Soporte para notas crédito (CreditNote)
   - Soporte para otros formatos XML (no UBL)
   - Métricas y observabilidad

---

## Notas de Calidad y Seguridad

- ✅ **No loguear XML completo**: Solo hash y longitud para depuración
- ✅ **Manejar encoding/namespaces**: Tolerancia a variantes UBL (diacríticos, offsets)
- ✅ **Contratos estables**: Cambios requieren versionado (v1, v2) para no romper consumidores
- ✅ **Preparado para umbrales de tamaño**: Si XML > X MB → 413 o usar storage

---

## Conclusión

El servicio general de ingesta XML está **completamente implementado y probado**, listo para ser consumido por las apps tenant en la Fase 2. Todos los tests pasan y el código está libre de errores de linting.
