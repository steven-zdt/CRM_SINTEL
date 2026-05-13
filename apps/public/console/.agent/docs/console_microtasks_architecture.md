# 🏗️ Arquitectura de Microtareas (MT-CON): Módulo Console

Sistema de trazabilidad técnica para la evolución de la administración central.

---

## 🛠️ Fase 1: Auditoría y Datos (Data Layer)

- `[ ]` **MT-CON-001**: Implementar `uuid` en `ConsoleActionLog` para trazabilidad externa.
- `[ ]` **MT-CON-002**: Refactorizar el registro de acciones para capturar el payload original de la petición.
- `[ ]` **MT-CON-003**: Implementar limpieza automática de logs antiguos (Data Retention Policy).
- `[ ]` **MT-CON-004**: Crear índices en `ActionLog` por `user` y `action_type`.

---

## 🧠 Fase 2: Lógica Administrativa (Service Layer)

- `[ ]` **MT-CON-010**: Desarrollar `ConsoleAuditService` para estandarizar el registro de eventos.
- `[ ]` **MT-CON-011**: Implementar lógica de detección proactiva de esquemas con migraciones pendientes.
- `[ ]` **MT-CON-012**: Crear servicio de agregación de métricas para el dashboard global (Caching).

---

## 🌐 Fase 3: API y Vistas (API Layer)

- `[ ]` **MT-CON-020**: Optimizar los endpoints JSON de la consola con soporte para filtrado Tabulator.
- `[ ]` **MT-CON-021**: Implementar `HX-Trigger` para actualización en tiempo real de notificaciones de error (Celery failures).
- `[ ]` **MT-CON-022**: Documentación de la API administrativa interna.

---

## 🎨 Fase 4: UI y Experiencia (UI Layer)

- `[ ]` **MT-CON-030**: Migrar todas las tablas administrativas a Tabulator con carga remota.
- `[ ]` **MT-CON-031**: Implementar Dark Mode en la Consola Global basado en preferencias del sistema.
- `[ ]` **MT-CON-032**: Crear buscador omni-canal (Tenants, Usuarios, Documentos) en el header de la consola.
