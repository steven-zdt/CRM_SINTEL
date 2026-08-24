# Cierre del Ciclo Fiscal — Contrato de Transporte (FASE FISCAL-02)

**Fecha:** 2026-08-24. **Estado:** Implementado (solo el contrato — el
adaptador real sigue bloqueado, ver §4). Complementa
`docs/fiscal/DIAN_TRANSPORT_AUDIT.md` (FISCAL-01).

```python
class ElectronicDocumentTransportPort(Protocol):
    def send(self, document: ElectronicDocument) -> TransmissionResult:
        ...
```

---

## 1. Dónde vive y por qué

`apps/tenant/core/dian/transport.py` — mismo paquete neutral que ya aloja
`XadesSignerService`/`AttachedDocumentService` desde NÓMINA-03. El
contrato no pertenece a `facturas` ni a `empleados`: es infraestructura
compartida por cualquier app que emita documentos electrónicos DIAN.
Exportado desde `apps.tenant.core.dian` (mismo patrón de `__init__.py`
que los otros dos servicios).

---

## 2. Las 3 piezas del contrato

### `ElectronicDocument` (entrada, `frozen=True`)

Lo que la app de dominio ya construyó y firmó — el transporte no
construye XML, no calcula CUFE/CUNE, no firma nada, solo envía bytes
terminados:

```python
document_type: str          # "Invoice" | "NominaIndividual" | ...
numero: str                 # numero/consecutivo del documento
tracking_key: str           # CUFE o CUNE, segun document_type
signed_xml: bytes           # XML UBL firmado (XAdES)
attached_document: bytes    # AttachedDocument que envuelve signed_xml
ambiente: str = "pruebas"   # "pruebas" | "produccion"
empresa_nit: str = ""       # resuelve credenciales/certificado por tenant
```

### `TransmissionResult` (salida, `frozen=True`)

Exactamente los 7 campos que el plan pidió, sin ningún campo específico
de un proveedor:

```python
success: bool
status: str                          # ENVIADO/ACEPTADO/RECHAZADO/ERROR_TRANSMISION
track_id: str | None = None
response_code: str | None = None
response_message: str = ""
errors: list[str] = field(default_factory=list)
raw_response: str = ""               # crudo, para auditoria -- nunca secretos
```

**Distinción deliberada entre `success` y `status`:** `success` indica
si la llamada de transporte se completó sin excepción (nivel técnico);
`status` es el estado fiscal real reportado por la DIAN/proveedor (nivel
de negocio). Un `send()` que se ejecuta correctamente pero recibe un
rechazo de la DIAN es `success=True, status="RECHAZADO"` — no un error
de transporte, un resultado de negocio válido.

### `ElectronicDocumentTransportPort` (el puerto)

`typing.Protocol` (no ABC) — permite que cualquier clase con un método
`send(document) -> TransmissionResult` cumpla el contrato sin herencia
explícita (duck typing verificable), marcado `@runtime_checkable` para
que `isinstance(adapter, ElectronicDocumentTransportPort)` funcione en
tests y en validaciones defensivas.

---

## 3. `NullTransportAdapter` — por qué se construyó, sin violar el alcance

El plan pide el contrato en esta fase, no el adaptador (bloqueado, ver
§4). Pero un `Protocol` sin ninguna implementación real es difícil de
ejercitar desde el resto del pipeline sin que falle con un
`ImportError`/`AttributeError` en cuanto alguien intente usarlo. Se
construyó un adaptador **nulo, honesto**: mismo criterio que
`XadesSignerService.sign()` ya aplica cuando no hay certificado
configurado (retorna el XML sin firmar en vez de fallar silenciosamente
con una firma inválida) — aquí, `NullTransportAdapter.send()` siempre
retorna `success=False, status="ERROR_TRANSMISION"`, **nunca** un
`ACEPTADO`/`RECHAZADO` inventado. No es infraestructura especulativa
nueva — es el mismo patrón de "degradación honesta sin infraestructura
real" que el proyecto ya usa en 3 lugares distintos del pipeline DIAN
(firma, certificado, y ahora transporte).

---

## 4. Qué sigue bloqueado (sin cambios respecto a FISCAL-01 §6)

`DIANAdapter`/`ProviderAdapter` (implementaciones reales de este puerto)
requieren el WSDL/contrato SOAP real de la DIAN o del proveedor
tecnológico elegido, más credenciales de habilitación verificables —
ninguno disponible en este entorno. El contrato en sí (esta fase) no
depende de esa información porque es una interfaz Python pura, sin
lógica de red.

---

## 5. Verificación

- `manage.py check`: 0 issues.
- Suite nueva, pura (sin DB, `unittest.TestCase` sin
  `pytest.mark.django_db`): `apps/tenant/core/tests/
  test_dian_transport_contract.py` — 5 tests: `NullTransportAdapter`
  cumple el `Protocol` en runtime, nunca finge éxito, `TransmissionResult`
  expone los 7 campos exactos del contrato, `ElectronicDocument` es
  inmutable, y una clase que no implementa `send()` correctamente **no**
  cumple el `Protocol` (confirma que el `Protocol` realmente valida
  forma, no es un marcador vacío). **5/5 PASS en 0.39s** — sin overhead
  de fixture de schema tenant, al no tocar ningún modelo.

---

## 6. Estado formal

**`FISCAL-02 = COMPLETED_WITH_DEFERRED`.** Contrato completo, tipado,
verificado, con un adaptador nulo honesto para que el resto del pipeline
pueda depender de la interfaz desde ya. Implementación real
(`DIANAdapter`/`ProviderAdapter`) queda diferida como bloqueador de
infraestructura, documentado explícitamente — no bloquea el resto del
plan (FISCAL-03 en adelante puede construirse contra el contrato, no
contra una implementación concreta).
