# Cierre del Ciclo Fiscal — Auditoría de Transporte DIAN (FASE FISCAL-01)

**Fecha:** 2026-08-24. **Estado:** Auditoría (sin cambios de código).
Ámbito: `apps.tenant.facturas`, `apps.tenant.core.dian`,
`apps.tenant.empresa`, configuración, certificados, variables de entorno.

**Conclusión adelantada: Escenario C — no existe transporte real.** El
tramo `FIRMA → TRANSMISIÓN REAL → RESPUESTA DIAN → VALIDACIÓN →
ACEPTADA/RECHAZADA` no está implementado en ningún punto del proyecto.
Esto reconfirma (con auditoría fresca y más profunda, no reciclada) los
hallazgos ya apuntados en `docs/nomina/NOMINA_DIAN_AUDIT.md` §1 — esta
fase los desarrolla con el detalle completo que el plan pide.

---

## 1. Inventario de `apps.tenant.core.dian/`

```
apps/tenant/core/dian/
├── __init__.py
├── xades_signer.py        -- signature (real, funcional)
└── attached_document.py   -- wrapper de transporte (genérico, sin transporte HTTP real)
```

| Pieza pedida por el plan | ¿Existe? | Dónde |
|---|---|---|
| `xml_builder` | Parcial — existe pero **no vive aquí** | `apps/tenant/facturas/services/dian/ubl21_builder.py` (`UBL21BuilderService`), específico de Invoice, no movido a `core.dian` por diseño (NÓMINA-03, no reutilizable para NominaIndividual) |
| `signature` | **Sí, real y funcional** | `core/dian/xades_signer.py` (`XadesSignerService`) — XAdES-EPES completo (`SignedInfo`/`SignatureValue`/`KeyInfo`/`QualifyingProperties`), certificado PKCS#12 vía `cryptography` |
| `certificate` | **No existe módulo de gestión** | Sin archivo dedicado; el certificado se referencia solo como una ruta de archivo (`settings.DIAN_CERT_P12`) que **nunca está configurada** (ver §3) |
| `cufe` | Parcial — existe pero **no vive aquí** | `apps/tenant/facturas/services/dian/cufe.py` (`CufeService`), fórmula específica de Factura Electrónica |
| `transport` | **No existe** | Cero archivos, cero clases, en ningún paquete del proyecto |
| `response_parser` | **No existe** | Sin ningún parser de respuesta DIAN real (solo `AttachedDocumentService.build_application_response()`, que **genera** un `ApplicationResponse` *ficticio* con `validation_code="02"` fijo — nunca parsea una respuesta real recibida) |
| `validators` | **No existe** | Ningún validador de esquema XSD DIAN, ningún validador de respuesta |

---

## 2. ¿Existe un cliente real de transmisión (DIAN o proveedor)?

**Hallazgo nuevo, no documentado en ninguna auditoría previa de esta
sesión:** sí existe una clase con esa forma, pero es **código muerto,
nunca conectado a nada**.

### `apps/services/integrations/dian_service.py` — `DIANService`

- Creado en el **commit inicial del proyecto** (`9d8c94a`, 2026-03-06,
  "migración inicial SINTEL v2.60") — anterior a toda la infraestructura
  UBL/CUFE/XAdES real que se construyó después.
- Expone `enviar_factura_electronica()`, `consultar_estado_documento()`,
  `validar_factura_electronica()` — la forma que el plan pregunta por
  "Escenario A/B" (`DIANClient`/`ProviderClient`).
- **Cero consumidores en todo el repo** — confirmado por grep de
  `DIANService`/`obtener_servicio_dian`/`apps.services.integrations`: no
  aparece importado desde `facturas`, desde ningún ViewSet, desde ningún
  management command, desde ningún test real. Ni siquiera hereda de
  `BaseIntegration` (`apps/services/integrations/base_integration.py`),
  el patrón que el propio paquete establece para sus integraciones —
  otra señal de que quedó desconectado del resto del código desde el
  principio.
- **El endpoint al que apunta no es el real de la DIAN.** Usa
  `{base_url}/api/factura-electronica/{validar,enviar,consultar}` con
  autenticación `Bearer` — una forma de API REST moderna. La DIAN real
  (Anexo Técnico FE v1.9) expone un **webservice SOAP/WCF**
  (`WcfDianCustomerServices`, operaciones `SendBillSync`/
  `GetStatus`/etc.), no una API REST con Bearer token. Esta clase no
  corresponde a ninguna integración real conocida — parece haber sido
  placeholder/scaffolding temprano, nunca actualizado cuando el resto
  del pipeline DIAN real (CUFE/UBL/XAdES) se construyó correctamente más
  tarde con las referencias normativas correctas.

**Conclusión:** no hay que "completar" ni "validar" este cliente — no
es una base utilizable (protocolo equivocado, endpoint inventado, sin
ninguna evidencia de que corresponda a un proveedor tecnológico real
contratado). Construir el transporte real empieza desde cero
(Escenario C), no desde esta clase.

---

## 3. Certificados y variables de entorno

| Variable | ¿Configurada? | Uso real |
|---|---|---|
| `DIAN_CERT_P12` | **No** (ninguna referencia en `.env`, `config/settings*.py`, ni documentación de deploy) | `XadesSignerService.sign()` cae siempre a `if not cert_path: return xml_bytes` — firma real nunca se ejecuta hoy |
| `DIAN_CERT_PASSWORD` | **No** | Idem |
| `DIAN_TIP_AMB` | **No** (usa default `"2"` = habilitación/pruebas, nunca producción) | `CufeService.calcular_desde_dto()` |
| `DIAN_API_KEY` / `DIAN_API_URL_TEST` / `DIAN_API_URL_PRODUCTION` / `DIAN_AMBIENTE` | **Sí, declaradas en `config/settings.py:883-887`** (con `os.getenv(...)`, defaults a string vacío o URLs) | **Solo consumidas por el `DIANService` muerto de §2** — declaradas pero sin ningún efecto real en el pipeline que sí funciona (`facturas/services/dian/` + `core/dian/`) |

**`apps.tenant.empresa`:** el modelo `Empresa` **no tiene ningún campo**
para certificado, clave técnica de habilitación, ni configuración de
proveedor tecnológico — grep de `cert`/`certificado`/`DIAN_`/`proveedor
tecnológico`/`tercero autorizado` sobre `apps/tenant/empresa/models.py`:
cero resultados. Si se necesita almacenar esa configuración por tenant
(cada empresa tendría su propio certificado DIAN), **no hay dónde
guardarla hoy** — es trabajo de modelo nuevo, no de configuración
existente sin usar.

---

## 4. Hallazgo adicional, relevante para FISCAL-03 (Estados)

`FacturaViewSet.cambiar_estado()` (`apps/tenant/facturas/api/
viewsets.py:648`) permite a cualquier usuario con rol ADMIN del tenant
(`IsTenantMember, IsTenantAdminOrReadOnly`, línea 167) hacer
`POST /api/v1/facturas/{uuid}/cambiar-estado/` con
`{"estado": "ACEPTADA"}` y la transición se ejecuta **sin ninguna
verificación de que exista una respuesta DIAN real detrás**. No es un
bug de esta fase — es el estado actual real, y confirma exactamente la
preocupación que el plan adelanta para FISCAL-03 ("no permitir que un
error HTTP deje una factura marcada como ACEPTADA"): hoy ni siquiera
hace falta un error HTTP, el estado es de escritura libre por API.

---

## 5. Determinación de escenario

**Escenario C — No existe.** Ni transporte, ni certificado configurado,
ni un cliente reutilizable (el único candidato, `DIANService`, es código
muerto con protocolo/endpoint incorrectos, sin consumidores). Corresponde
diseñar `ElectronicDocumentTransportPort` con adaptadores
(`DIANAdapter`/`ProviderAdapter`) desde cero, tal como el plan anticipa
para este escenario — **no hay atajo real disponible**.

**Piezas que SÍ están listas para conectar detrás del puerto**, sin
necesidad de reconstruirlas (confirmado funcional en auditorías previas
de esta sesión, `docs/nomina/NOMINA_DIAN_AUDIT.md` + `docs/comercial/`):

- Construcción del XML UBL 2.1 (`UBL21BuilderService`).
- Cálculo de CUFE (`CufeService`).
- Firma XAdES-EPES (`XadesSignerService`, en `core.dian`, ya compartida
  entre `facturas` y `empleados`/nómina).
- Wrapper `AttachedDocument` + `ApplicationResponse` (`AttachedDocumentService`,
  ya con `document_type` parametrizable desde NÓMINA-03).

Lo único que falta construir es exactamente lo que el plan ya identificó:
`ElectronicDocumentTransportPort` + un adaptador real, y (nuevo hallazgo
de esta auditoría) **dónde y cómo se configura el certificado por
tenant** — hoy no hay campo de modelo para eso en `Empresa`.

---

## 6. Bloqueador real, no de arquitectura

Igual que en `NOMINA_DIAN_CONTRATO_COMPARTIDO.md` §2: construir el
adaptador de transporte real (`DIANAdapter`) requiere el WSDL/contrato
SOAP real de la DIAN (o del proveedor tecnológico si se opta por uno) y
credenciales de habilitación verificables — ninguno disponible en este
entorno. El **contrato** (`ElectronicDocumentTransportPort`, FASE
FISCAL-02) sí puede diseñarse y validarse sin esa información (es una
interfaz Python, no una implementación) — la implementación concreta del
adaptador queda sujeta a la misma decisión que ya se tomó en
NÓMINA-03 (diferir como bloqueador documentado, no fabricar un cliente
sin verificación real).

---

## 7. Conclusión de esta fase

**`FISCAL-01 = AUDITORÍA COMPLETA`**, sin cambios de código. Confirma
Escenario C con evidencia exhaustiva (no solo "no encontré nada" — se
identificó y descartó explícitamente el único candidato plausible,
`DIANService`, con la razón concreta de por qué no sirve). Hallazgo
nuevo relevante para el resto del plan: `Empresa` no tiene campo para
certificado DIAN por tenant — FISCAL-02/03 deben contemplar si ese
modelo se necesita antes de que el transporte real pueda funcionar para
más de un tenant con certificados distintos.

Siguiente fase recomendada: **FISCAL-02 — Contrato de transporte**
(`ElectronicDocumentTransportPort`), que sí puede completarse en esta
sesión al ser diseño de interfaz, no una implementación que dependa del
WSDL real.
