# CLIENTES — Business Logic (Logica de Negocio)

**Version:** 3.5.0
**App:** `apps/tenant/clientes/`

Este documento centraliza las reglas de negocio, validaciones semanticas y comportamientos esperados del modulo de Clientes.

---

## 1. Identidad y Unicidad (Idempotencia)

### 1.1. Unicidad de Tercero
Un cliente se identifica de forma unica dentro de una empresa por la combinacion de:
- `tipo_documento`
- `numero_documento`
- `empresa_id` (inyectado por el tenant)

**Regla Upsert:** Si se intenta registrar un cliente que ya existe con ese documento, el sistema realiza un **Update** silencioso en lugar de fallar (implementado en `ClienteBusinessService.registrar_cliente_completo`).

### 1.2. Normalizacion de Documentos
- El `numero_documento` se limpia de puntos, guiones y espacios antes de la persistencia y validacion.
- Implementado via `NormalizationMixin` en los serializers.

---

## 2. Gestion de Contactos (Maestro-Detalle)

### 2.1. Sincronizacion Bulk
Al guardar un cliente, sus contactos se sincronizan mediante una estrategia de "Reemplazo Controlado":
1. Se comparan los IDs enviados vs los existentes.
2. Los IDs existentes que NO vienen en el payload se eliminan fisicamente.
3. Los IDs que coinciden se actualizan.
4. Los items sin ID se crean como nuevos.

### 2.2. Contacto Principal (Encargado)
- Solo un contacto puede actuar como "Encargado" principal para la vista de tabla.
- Se identifica por el campo `is_principal=True`.
- En la tabla de Clientes, se muestra el nombre y email de este contacto especifico.

---

## 3. Seguridad y Aislamiento (Zero Trust)

### 3.1. Double Semantic Verification (DSV)
Toda consulta de detalle o mutacion debe validar que el objeto pertenece al tenant:
- `filter(pk=pk, empresa_id=request.user.perfil.empresa_id)`
- Si el ID pertenece a otro tenant, el sistema retorna `404 Not Found` y registra un intento de IDOR.

### 3.2. Validacion de FKs
Al crear o actualizar contactos, el sistema valida que el `cliente_id` proporcionado pertenezca efectivamente a la misma `empresa_id` del usuario autenticado.

---

## 4. Ciclo de Vida y Borrado (Soft-Delete Policy)

### 4.1. Restriccion de Eliminacion
- **PROHIBIDO** eliminar un cliente que este marcado como `activo=True`.
- El backend (`crud_service.py`) lanza una `ValidationError` si se intenta un DELETE fisico sobre un registro activo.
- La UI implementa un flujo de dos pasos: el usuario debe inactivar el registro (PATCH `activo=False`) antes de poder eliminarlo.

### 4.2. Cascada de Datos
- La eliminacion de un Cliente dispara un `CASCADE` sobre sus `ContactoCliente`.
- **Nota:** En versiones futuras, se implementara restriccion si existen facturas o cotizaciones vinculadas (IntegrityProtection).

---

## 5. Integracion Cross-Module

### 5.1. Snapshot Pattern (Proyectos)
- El modulo de `proyectos` consume datos de `clientes`.
- Para evitar acoplamiento duro, `proyectos` almacena el `cliente_id` y una copia (snapshot) de la `razon_social` al momento de la creacion.
- Esto permite que el proyecto mantenga su integridad historica aunque el cliente cambie de nombre legal.

---

## 6. Normalizacion de Datos (SSoT)

| Tipo de Dato | Regla de Normalizacion |
|---|---|
| Strings | `.strip()`, Capitalizacion segun campo |
| Emails | `.lower().strip()` |
| Telefonos | Solo digitos numericos |
| Documentos | Solo caracteres alfanumericos, sin simbolos |
| Booleanos | Coersion estricta a `True`/`False` |
