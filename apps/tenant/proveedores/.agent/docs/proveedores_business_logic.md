# [LOGIC] SINTEL v3.5.0 — Proveedores Module Business Logic

Reglas de negocio, validaciones financieras e integridad de datos para el módulo de Proveedores.

## 1. Identificación y Unicidad (SSoT)

La identidad de un proveedor está definida por la tríada: `empresa_id` + `tipo_documento` + `numero_documento`.
- **Normalización**: El número de documento (NIT) se limpia de espacios y se convierte a mayúsculas antes de la validación.
- **Idempotencia**: El método `registrar_proveedor_con_contactos` utiliza `update_or_create` para permitir ingestas masivas o actualizaciones sin duplicar registros.

## 2. Validación de Cuentas Contables (NIIF)

Todo proveedor debe tener asignado un `codigo_contable` válido para la correcta integración con el módulo de Contabilidad.
- **Restricción**: Solo se permiten códigos pertenecientes al catálogo de pasivos (ej. 220505 - Proveedores Nacionales).
- **Control**: Esta validación se ejecuta en el `ProveedorBusinessService` antes de cualquier operación de persistencia.

## 3. Lógica de Retenciones e Impuestos

El módulo centraliza las reglas tributarias básicas para simplificar la creación de gastos:
- **Autorretenedores**: Si el proveedor es marcado como autorretenedor, el sistema sugiere 0% de retención en la fuente.
- **Tipo de Persona**: Las personas naturales activan sugerencias de ReteICA específicas (0.966% según normativa estándar configurada).
- **Fórmula de Neto**: `Neto = Subtotal - (Subtotal * % Retención / 100)`. Los redondeos se realizan a 2 decimales usando `ROUND_HALF_UP`.

## 4. Gestión de Estado (Soft-Delete)

- **Eliminación Protegida**: Un proveedor marcado como `activo=True` no puede ser eliminado físicamente de la base de datos.
- **Flujo**: El usuario debe primero inactivar el registro. Esto evita la ruptura de integridad referencial accidental con documentos históricos (Facturas/Gastos).

## 5. Resiliencia en Captura de Datos (Zero Trust)

El frontend (`proveedores.form.js`) implementa validaciones de tipos antes del envío:
- Los porcentajes recibidos en formato decimal (ej. 0.04) se normalizan a base-100 (4%) para consistencia con el backend.
- Se previene el envío de valores `NaN` o `undefined` mediante saneamiento en el objeto `payload`.
