# 🧠 Lógica de Negocio: Módulo Empresa (SSoT)

Este documento centraliza las reglas de integridad, cálculos y seguridad para la gestión de la identidad del Tenant.

---

## 1. Regla de Oro: El Patrón Singleton

- **Definición**: El modelo `Empresa` en el esquema tenant DEBE contener un único registro activo.
- **Implementación**: Constraint Unique sobre el campo `singleton_key` (valor default: `"default"`).
- **Impacto**: Cualquier intento de crear una segunda empresa en el mismo tenant resultará en un error de integridad a nivel de base de datos.
- **Justificación**: SINTEL opera bajo un modelo de "1 Tenant = 1 Empresa Legal".

---

## 2. Validación de Identidad Tributaria (NIT)

- **Formato**: El NIT es numérico. El Dígito de Verificación (DV) es un campo calculado.
- **Cálculo de DV**: Sigue el algoritmo estándar de la DIAN (Colombia).
- **Constraint**: No se permite el guardado de empresas con NIT inconsistente con su DV si el país es Colombia.

---

## 3. Seguridad de MailInbox (Cifrado)

Para la captura automática de facturas, se gestionan credenciales de correo:
- **Almacenamiento**: Las contraseñas IMAP/SMTP NUNCA se guardan en texto plano.
- **Algoritmo**: AES-256-CBC con clave de sistema.
- **Capa de Servicio**: `EmpresaBusinessService` es el único autorizado para orquestar el cifrado/descifrado antes de la persistencia o uso en workers.

---

## 4. Estado de Conectividad

- **Estados**: `SIN_CONFIGURAR`, `PENDIENTE_TEST`, `ACTIVO`, `ERROR_AUTENTICACION`.
- **Lógica de Test**:
  1. Invocación desde UI.
  2. Despacho a Worker (aislamiento de red).
  3. Intento de conexión IMAP (timeout 15s).
  4. Actualización de timestamp `last_successful_connection`.

---

## 5. SSoT para Documentos Electrónicos

La información de la empresa actúa como el bloque **Emisor** en toda factura electrónica:
- **Campos Críticos**: Razón Social, NIT, Tipo de Régimen, Dirección, Ciudad (Código Dane).
- **Acceso Directo**: Los módulos de `Facturación` y `Nómina` deben invocar `EmpresaSelector.get_emisor_context()` para garantizar que los XMLs generados usen la versión más reciente de los datos maestros.
