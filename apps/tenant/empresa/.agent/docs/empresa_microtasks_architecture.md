# 🏗️ Arquitectura de Microtareas: Módulo Empresa

**Namespace:** `MT-EMP`
**Alineación:** SINTEL v3.5.0

Este documento desglosa las tareas técnicas necesarias para el mantenimiento y evolución del núcleo de identidad del tenant.

---

## 🛠️ MT-EMP-01: Infraestructura y Modelado (Core)

- [x] **MT-EMP-01-01**: Herencia de `SintelTenantBaseModel` en el modelo `Empresa`.
- [x] **MT-EMP-01-02**: Implementación de constraint `Unique(singleton_key)`.
- [ ] **MT-EMP-01-03**: Migración de `lookup_field` de Integer PK a UUID en el ViewSet.

---

## ⚙️ MT-EMP-02: Capa de Servicios (Logic)

- [x] **MT-EMP-02-01**: Creación de `EmpresaSelector` con métodos `.only()` para optimización "Zero Waste".
- [x] **MT-EMP-02-02**: Implementación de `EmpresaBusinessService` para validación de NIT.
- [ ] **MT-EMP-02-03**: Refactorización de encriptación de MailInbox para usar `cryptography` estándar.

---

## 🌐 MT-EMP-03: API y Comunicaciones

- [x] **MT-EMP-03-01**: Endpoint `GET /api/v1/empresas/mi-empresa/`.
- [ ] **MT-EMP-03-02**: Endpoint `POST /api/v1/empresas/test-connection-imap/` con feedback HTMX.
- [ ] **MT-EMP-03-03**: Implementación de validación DSV en endpoints de actualización.

---

## 🎨 MT-EMP-04: Interfaz de Usuario (UI/UX)

- [x] **MT-EMP-04-01**: Integración de Bootstrap Offcanvas para perfil de empresa.
- [ ] **MT-EMP-04-02**: Implementación de "DOM Shield" en el formulario de configuración.
- [ ] **MT-EMP-04-03**: Micro-animación de feedback durante el test de conexión MailInbox.

---

## 🧪 MT-EMP-05: Validación y Calidad

- [ ] **MT-EMP-05-01**: Test unitario para validación de DV (Dígito de Verificación).
- [ ] **MT-EMP-05-02**: Test de integración para el patrón Singleton (prevención de duplicados).
- [ ] **MT-EMP-05-03**: Auditoría de logs de acceso a credenciales de correo.

---

## 📚 Referencias Técnicas
- **Ubicación Código**: `apps/tenant/empresa/`
- **Namespace JS**: `window.Sintel.Empresa`
- **Selector SSoT**: `EmpresaSelector`
