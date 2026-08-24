# Nómina — Auditoría de Infraestructura DIAN Compartida (FASE NÓMINA-02)

**Fecha:** 2026-08-24. **Estado:** Auditoría (sin cambios de código).
Complementa `NOMINA_BASELINE.md` (FASE 0) y `NOMINA_FLUJO_EMPRESARIAL.md`
(FASE 28) con el análisis de qué infraestructura DIAN ya existe en
`facturas` y cómo debe compartirse (o no) con `empleados` para completar
`TransmisionNominaDIAN` (DSPNE — Documento Soporte de Pago de Nómina
Electrónica).

Metodología: lectura directa de `apps/tenant/facturas/services/dian/*.py`
(4 archivos) contra el modelo `TransmisionNominaDIAN`/`ResolucionDIAN` de
`empleados`, más grep de imports cruzados y de configuración DIAN en
`settings`. Sin asunciones — cada afirmación de esta auditoría está
anclada a una línea de código real.

---

## 1. Qué infraestructura DIAN ya existe en `facturas`

`apps/tenant/facturas/services/dian/` — 4 servicios, todos `@classmethod`,
sin estado:

| Servicio | Responsabilidad | Acoplamiento a Factura |
|---|---|---|
| `CufeService` | Calcula CUFE (SHA-384 sobre 14 campos concatenados, Anexo Técnico FE v1.9 §5.4.3) | **Alto** — la fórmula (`NumFac+FecFac+HorFac+ValFac+CodImp1...`) es específica de Factura Electrónica |
| `UBL21BuilderService` | Construye el XML `Invoice` UBL 2.1 completo | **Alto** — namespace `...schema:xsd:Invoice-2` hardcodeado, estructura Invoice específica |
| `XadesSignerService` | Firma XAdES-EPES sobre bytes XML crudos | **Ninguno** — opera sobre `bytes`, inserta la firma buscando el marcador literal `<ext:UBLExtension/>` en el string. No conoce Invoice ni ningún otro schema. |
| `AttachedDocumentService` | Envuelve el XML firmado en `AttachedDocument` + genera `ApplicationResponse` mínimo | **Medio** — hardcodea `<cbc:DocumentType>Invoice</cbc:DocumentType>` y `schemeName="CUFE-SHA384"`, pero la estructura del wrapper (`SenderParty`/`ReceiverParty`/`Attachment`/`ExternalReference`) es el mismo contenedor genérico DIAN para cualquier documento electrónico |

**Hallazgo crítico (no documentado hasta ahora):** ninguno de los 4
servicios transmite el XML a la DIAN. Se buscó explícitamente cualquier
llamada SOAP/webservice (`SendBillSync`, `zeep`, endpoints
`dian.gov.co/WcfDianCustomerServices`) en todo `apps/tenant/facturas/` —
**no existe**. El pipeline construye, firma y calcula CUFE, pero el envío
real al webservice DIAN **no está implementado en ningún punto del
proyecto**, ni para Factura Electrónica ni para Nómina.

**Hallazgo crítico #2:** no existe ninguna variable `DIAN_CERT_P12` /
`DIAN_CERT_PASSWORD` / `DIAN_TIP_AMB` / `DIAN_CL_TECN` configurada en
`config/settings*.py` (grep sin resultados). `XadesSignerService.sign()`
cae siempre en `if not cert_path: return xml_bytes` — **el pipeline de
Factura Electrónica corre hoy en modo borrador permanente (XML sin
firmar)**, no solo en desarrollo. Esto es un bloqueador de infraestructura
real (certificado + habilitación DIAN), no de código, y aplica igual a
cualquier trabajo de nómina electrónica.

---

## 2. Qué puede reutilizar `empleados` tal cual

Solo **`XadesSignerService.sign(xml_bytes: bytes) -> bytes`**. Es
genérico por diseño: no importa nada de `facturas.models`, no conoce UBL
Invoice, y el marcador de inserción (`<ext:UBLExtension/>`) es parte del
estándar `UBLExtensions` que también usa el XML de Nómina Electrónica DIAN
(mismo mecanismo de extensión UBL). Puede invocarse sin modificar una sola
línea, siempre que el XML de nómina deje el mismo placeholder vacío.

Nada más es reutilizable sin adaptar — ver §4.

---

## 3. Qué debe abstraerse como contrato compartido

1. **`XadesSignerService`** — moverlo (no duplicarlo) a una ubicación
   neutral fuera de `facturas` (ver §5), ya que hoy vive en un paquete de
   dominio (`facturas`) que `empleados` no puede importar sin violar el
   Bounded Context (AGENTS.md §17/§18).
2. **El wrapper `AttachedDocument`** (`AttachedDocumentService.build()`)
   — la estructura es genérica pero el `DocumentType` está hardcodeado a
   `"Invoice"`. Debe parametrizarse (`document_type: str`) para servir
   también a `NominaIndividual` sin duplicar la función completa.
3. **El transporte SOAP hacia la DIAN** — como se documenta en §1, **no
   existe hoy en ningún lado**. No hay nada que "abstraer" porque no hay
   nada que reutilizar; debe construirse una única vez en la ubicación
   compartida para que ni Factura Electrónica ni Nómina Electrónica lo
   dupliquen cuando se implemente.

---

## 4. Qué debe permanecer específico de DSPNE

- **CUNE, no CUFE.** El Anexo Técnico de Nómina Electrónica define una
  fórmula de hash propia (campos distintos: `NumNIE`/`FecNIE`/`HorNIE`,
  NIT empleador/empleado, valores propios de nómina) — **no es la misma
  fórmula que CUFE**. `CufeService` no debe reutilizarse ni renombrarse;
  se necesita un `CuneService` nuevo, específico, con su propia
  referencia normativa documentada (mismo patrón de docstring que
  `cufe.py`, citando el Anexo Técnico de Nómina, no el de Factura).
- **El builder XML `NominaIndividual`.** Schema y namespace DIAN
  distintos de `Invoice-2`; requiere un `NominaXMLBuilderService` nuevo,
  específico — no es una variante de `UBL21BuilderService`.
- **`TransmisionNominaDIAN` y `ResolucionDIAN`** (`empleados/models.py`)
  ya existen y no tienen equivalente en `facturas` (confirmado: `facturas`
  no tiene modelo `ResolucionDIAN` propio — la numeración de Factura vive
  como campos `autorizacion_*` directos en `Factura`). No hay colisión de
  nombres ni necesidad de unificar modelos entre apps.

---

## 5. Cómo evitar dependencias circulares entre `facturas` y `empleados`

**Estado actual: cero acoplamiento.** Grep confirmado en ambas
direcciones — ningún archivo de `empleados` importa `facturas` y ningún
archivo de `facturas` importa `empleados`. Punto de partida limpio.

Para no romper esto al compartir `XadesSignerService` (y el futuro
transporte SOAP + wrapper `AttachedDocument` genérico), la regla es la
misma que ya rige el resto del proyecto (Bounded Context, AGENTS.md §17):
**ninguna de las dos apps de dominio debe importar servicios DIAN de la
otra.** La infraestructura compartida debe vivir en un tercer lugar
neutral que ambas puedan importar sin crear una dependencia
`facturas → empleados` ni `empleados → facturas`.

Candidato recomendado: `apps/tenant/core/services/dian/` (paralelo a
`apps/tenant/core/services/membership.py`, ya el punto neutral
establecido para bridges cross-app) o un paquete nuevo dedicado
`apps/tenant/dian_common/` si el volumen de código lo justifica. Cualquiera
de los dos evita el ciclo; la decisión concreta es de bajo riesgo y puede
tomarse en la fase de implementación (NÓMINA-03), no bloquea esta
auditoría.

---

## 6. Cómo completar `TransmisionNominaDIAN` sin duplicar XML/XAdES/transporte

Plan concreto para FASE NÓMINA-03, en orden de dependencia:

1. **Mover** `XadesSignerService` (sin modificarlo) del paquete
   `facturas.services.dian` a la ubicación neutral elegida en §5.
   `facturas` pasa a importarlo desde ahí (import interno, no cambia
   comportamiento) — evita que quede "prestado" de un dominio a otro.
2. **Generalizar** `AttachedDocumentService.build()` con un parámetro
   `document_type` (default `"Invoice"` para no romper `facturas`) y
   moverlo junto al signer.
3. **Construir** el transporte SOAP real hacia la DIAN **una sola vez**,
   en la ubicación neutral, parametrizado por tipo de documento — hoy no
   existe para ninguna de las dos apps, así que no hay riesgo de
   duplicarlo si se hace ahí desde el principio.
4. **Crear específicos de nómina** (dentro de `empleados`, sin mover a lo
   compartido): `CuneService` (fórmula propia) y
   `NominaXMLBuilderService` (schema `NominaIndividual` propio).
5. **Bloqueador real, no de código:** ninguno de los puntos anteriores
   sirve para transmitir a producción sin un certificado DIAN real
   configurado (`DIAN_CERT_P12` no existe hoy en `settings` para ninguna
   app). Igual que con Factura Electrónica, Nómina Electrónica quedará en
   modo borrador (XML sin firmar) hasta que se provisione ese
   certificado — **decisión de negocio/infraestructura, se documenta
   como bloqueador, no se inventa una firma falsa.**

---

## 7. Estado formal

**`NOMINA-02 = AUDITORÍA COMPLETA`** — sin cambios de código en esta
fase. Las 6 preguntas del alcance quedan respondidas con evidencia de
código citada línea por línea. Dos bloqueadores reales identificados y
documentados (transporte SOAP inexistente para ambas apps; certificado
DIAN no configurado en ningún entorno) — ninguno de los dos es exclusivo
de Nómina, ambos afectan también al pipeline de Factura Electrónica ya
"production ready" según `COMPLETO_FLUJO_FACTURAS.md`, lo cual matiza esa
etiqueta: el documento es correcto en que no hay 0 críticos *internos*,
pero el envío real a DIAN no está verificado end-to-end en ningún flujo
del proyecto todavía.

Siguiente fase recomendada: **NÓMINA-03 — Contrato compartido DIAN**,
ejecutando el plan de §6 (mover signer, generalizar AttachedDocument,
construir transporte SOAP compartido, crear CuneService/
NominaXMLBuilderService específicos).
