"""
Consola API-First (SSOT - Single Source of Truth)

⚠️ ESTE PAQUETE ES LA ÚNICA FUENTE DE VERDAD PARA CRUD DE LA CONSOLA PÚBLICA.

Este módulo es la única fuente de verdad (SSOT) para todas las operaciones CRUD
de la consola de administración pública (esquema 'public').

Queda PROHIBIDO reintroducir lógica de negocio en vistas clásicas (FBV/CBV).
Toda la UI (templates/HTMX/JS) DEBE consumir exclusivamente estas APIs.

Endpoints disponibles:
- POST /api/admin/v1/console/dt/tenants/ - DataTables de tenants
- POST /api/admin/v1/console/dt/tenant-domains/ - DataTables de dominios
- POST /api/admin/v1/console/dt/users/ - DataTables de usuarios
- GET  /api/admin/v1/console/health/ - Estado de la consola

Todos los endpoints requieren IsAdminUser y usan POST + CSRF para DataTables.
"""
