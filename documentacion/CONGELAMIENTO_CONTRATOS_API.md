# Congelamiento de Contratos API

**Fecha de inicio:** 2026-02-12  
**Vigencia:** Durante Olas 1-5 del refactor frontend (estimado: 2-3 semanas)  
**Responsable:** Equipo de desarrollo SINTEL

---

## 1. Alcance del Freeze

### 1.1 Contratos Congelados

Durante el período de refactor frontend (Olas 1-5), **NO se realizarán cambios** en:

1. **Paths de endpoints actuales**
   - Todas las rutas bajo `/api/v1/{app}/` permanecen inmutables
   - Endpoints DataTables (`/api/v1/{app}/dt/{resource}/`) no cambian
   - Rutas de Core API (`/api/v1/core/{resource}/`) no cambian

2. **Contratos JSON (shape de request/response)**
   - Estructura de list/detail/DataTables permanece igual
   - Campos de serializers no cambian
   - Códigos de estado HTTP (200, 201, 400, 401, 403, 404) no cambian
   - Mensajes de error mantienen formato actual

3. **Comportamiento de endpoints**
   - Paginación DRF mantiene formato actual
   - Filtros y búsqueda funcionan igual
   - Ordenamiento mantiene lógica actual

---

### 1.2 Motivo del Freeze

**Refactor frontend modular para reducir regresiones durante migración.**

El objetivo es:
- Centralizar lógica JS común en helpers (`http.js`, `routes.js`, `dom.js`, `datatable.js`, `crud.js`, `module.js`)
- Eliminar URLs hardcodeadas mediante Core Routes API
- Estandarizar manejo de CSRF, 401/403, y visibilidad
- **Sin romper contratos existentes** durante la migración

---

## 2. Excepciones

### 2.1 Hotfixes de Seguridad

**Permitidos con documentación obligatoria:**

- Parches de seguridad críticos (CVE, vulnerabilidades)
- Correcciones de bugs que afecten integridad de datos
- Cambios requeridos por compliance/regulación

**Proceso:**
1. Documentar cambio en este archivo (sección 4)
2. Notificar al equipo antes de desplegar
3. Actualizar Core Routes API si aplica
4. Actualizar `documentacion/arquitectura_general.md` si aplica

---

### 2.2 Cambios Documentados y Aprobados

Si un cambio es **absolutamente necesario** durante el freeze:

1. **Crear issue** con label `freeze-exception`
2. **Obtener aprobación** del tech lead
3. **Actualizar este documento** (sección 4)
4. **Actualizar Core Routes API** si cambia path
5. **Actualizar arquitectura** si cambia contrato

---

## 3. Endpoints Sensibles (Solo Informativo)

Esta sección lista los endpoints más usados por módulos críticos para que el equipo evite cambios accidentales.

### 3.1 Facturas

| Endpoint | Método | Uso | Módulo |
|----------|--------|-----|--------|
| `/api/v1/facturas/dt/facturas/` | POST | DataTables server-side | `facturas.page.js`, `facturas.dt.js` |
| `/api/v1/facturas/` | GET | Lista de facturas | `facturas.page.js` |
| `/api/v1/facturas/{id}/` | GET | Detalle de factura | `facturas.page.js` |

**Impacto:** Alto - Módulo crítico, 2 DataTables

---

### 3.2 Contabilidad

| Endpoint | Método | Uso | Módulo |
|----------|--------|-----|--------|
| `/api/v1/contabilidad/dt/cuentas-contables/` | POST | DataTables server-side | `contabilidad.table.js` |
| `/api/v1/contabilidad/dt/asientos-contables/` | POST | DataTables server-side | `contabilidad.table.js` |
| `/api/v1/contabilidad/asientos-contables/` | GET | Lista de asientos | `asientos.page.js` |

**Impacto:** Alto - Módulo crítico, 2 DataTables

---

### 3.3 Inventario

| Endpoint | Método | Uso | Módulo |
|----------|--------|-----|--------|
| `/api/v1/inventario/dt/catalogo/` | POST | DataTables server-side | `inventario.table.js` |
| `/api/v1/inventario/dt/activos-fijos/` | POST | DataTables server-side | `inventario.table.js` |
| `/api/v1/inventario/dt/movimientos/` | POST | DataTables server-side | `inventario.table.js` |
| `/api/v1/inventario/catalogo/` | GET | Lista de catálogo | `catalogo.page.js`, `movimientos.page.js` |
| `/api/v1/inventario/activos-fijos/` | GET | Lista de activos | `activos.page.js` |

**Impacto:** Alto - Módulo crítico, 3 DataTables

---

### 3.4 Clientes

| Endpoint | Método | Uso | Módulo |
|----------|--------|-----|--------|
| `/api/v1/clientes/dt/clientes/` | POST | DataTables server-side | `clientes.table.js` |
| `/api/v1/clientes/` | GET | Lista de clientes (HATEOAS) | `clientes.page.js` |

**Impacto:** Medio - 1 DataTable, usa HATEOAS discovery

---

### 3.5 Proveedores

| Endpoint | Método | Uso | Módulo |
|----------|--------|-----|--------|
| `/api/v1/proveedores/dt/proveedores/` | POST | DataTables server-side | `proveedores.dt.js` |
| `/api/v1/proveedores/` | GET | Lista de proveedores (HATEOAS) | `proveedores.page.js` |

**Impacto:** Medio - 1 DataTable, usa HATEOAS discovery

---

### 3.6 Empleados

| Endpoint | Método | Uso | Módulo |
|----------|--------|-----|--------|
| `/api/v1/empleados/dt/empleados/` | POST | DataTables server-side | `empleados.dt.js` |

**Impacto:** Medio - 1 DataTable

---

### 3.7 Gastos

| Endpoint | Método | Uso | Módulo |
|----------|--------|-----|--------|
| `/api/v1/gastos/dt/gastos/` | POST | DataTables server-side | `gastos.dt.js` |

**Impacto:** Medio - 1 DataTable

---

### 3.8 Perfil

| Endpoint | Método | Uso | Módulo |
|----------|--------|-----|--------|
| `/api/v1/perfil/perfiles/me/` | GET, PATCH | Singleton de perfil | `perfil.page.js` |

**Impacto:** Bajo - Singleton, no crítico

---

### 3.9 Empresa

| Endpoint | Método | Uso | Módulo |
|----------|--------|-----|--------|
| `/api/v1/core/empresa/` | GET, PATCH | Mi empresa (singleton) | `empresa.page.js` |
| `/api/v1/empresas/` | GET, POST | Lista de empresas | `empresa.page.js` |
| `/api/v1/empresas/mail-inbox-config/` | GET, POST, PATCH, DELETE | Configuración mailbox | `mailinbox.page.js` |

**Impacto:** Medio - CRUD completo, configuración crítica

---

## 4. Registro de Excepciones

### 4.1 Cambios Durante Freeze

**Formato:**
```
### [YYYY-MM-DD] - Título del Cambio

**Motivo:** [Seguridad/Bug crítico/Compliance]
**Endpoint afectado:** `/api/v1/{app}/{resource}/`
**Cambio realizado:** [Descripción breve]
**Aprobado por:** [Nombre]
**Issue/PR:** [#N]
**Actualizado Core Routes API:** [Sí/No]
**Actualizado arquitectura:** [Sí/No]
```

---

### 4.2 Historial

*(Se llenará durante el período de freeze si hay excepciones)*

---

## 5. Proceso Post-Freeze

Una vez completadas las Olas 1-5:

1. **Auditoría final** de cambios en frontend
2. **Validación** de que todos los módulos funcionan con Core Routes API
3. **Lift del freeze** con comunicación al equipo
4. **Actualización** de este documento con fecha de fin de freeze

---

## 6. Contacto

**Preguntas sobre el freeze:**
- Crear issue con label `freeze-question`
- Consultar `documentacion/arquitectura_general.md` para estándares

**Cambios necesarios durante freeze:**
- Seguir proceso de excepciones (sección 2.2)

---

**Estado actual:** 🟢 FREEZE ACTIVO  
**Próxima revisión:** Al completar Ola 5
