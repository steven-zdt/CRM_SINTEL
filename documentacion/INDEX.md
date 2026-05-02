# 📚 Documentación — Índice y Guía

**Estado:** 2026-05-02 · Sprint 2 — Consolidación  
**Documentos activos:** 95 · **Archivados:** 232

---

## 🚀 Comienza aquí

### Documentación vigente (Sprint 1-2)

- **[SPRINT_1_DESBLOQUEAR_CRUD.md](SPRINT_1_DESBLOQUEAR_CRUD.md)** — Plan y ejecución de Sprint 1 (fases 1-6)
  - Desbloqueo de CRUD mediante http.js v3.4
  - Verificación de 13 módulos de tenant
  - Suite Playwright E2E
  
- **[README.md](README.md)** — Guía rápida del proyecto

---

## 📖 Documentación por categoría

### Arquitectura y Diseño

- [API_FIRST.md](API_FIRST.md) — Arquitectura API-First
- [DJANGO_TENANTS_PLAYBOOK_SINTEL.md](DJANGO_TENANTS_PLAYBOOK_SINTEL.md) — django-tenants multi-tenant setup
- [DJANGO_5_PLAYBOOK_SINTEL.md](DJANGO_5_PLAYBOOK_SINTEL.md) — Upgrade a Django 5

### Implementación y Configuración

- `CONFIGURACION_*.md` — Setups de dominio, puertos, acceso
- `VARIABLES_ENTORNO_*.md` — Variables de entorno
- `COMANDOS_TENANT_*.md` — Comandos útiles

### Seguridad

- [SEGURIDAD_AMBITO_PUBLICO_v2.29.md](SEGURIDAD_AMBITO_PUBLICO_v2.29.md) — Aislamiento público vs privado
- `JWT_*.md` — Autenticación JWT

### Módulos específicos

- `MODULO_*.md` — Documentación de módulos (gastos, cotizaciones, etc.)

---

## 🗂️ Archivos históricos

Documentos de versiones antiguas, auditorías completadas, y reportes históricos se encuentran en:

```
documentacion/_archive/
```

Incluye:
- Auditorías (v2.x) — `AUDITORIA_*.md`, `AUDIT_REPORT_*.md`
- Planes de migración completados — `MIGRACION_*.md`, `PLAN_MIGRACION_*.md`
- Diagnósticos y reportes — `DIAGNOSTICO_*.md`, `INFORME_*.md`, `REPORTE_*.md`
- Documentación de versiones v2.x, v3.0-v3.2 — `*v2.*md`, `*v3.[012].*md`
- Refactorización completada — `REFACTOR_*.md`, `PURGA_*.md`, `LIMPIEZA_*.md`

**Por qué archivamos:** Mantiene la raíz limpia, enfocada en documentación vigente (v3.3+).

---

## 📋 Cómo se organiza este proyecto

### Ramas principales

- `main` — Producción (estable)
- `feat/onboarding-cookie` — Rama activa de trabajo (Sprint 1-2)

### Flujo de sprints

**Sprint 1 (Completado)** — Desbloquear CRUD (fases 1-6)
- http.js v3.4 dual-contract
- Carga en tenant/base.html
- Verificación de 13 módulos
- Edit Tenant funcional
- Playwright E2E suite

**Sprint 2 (En progreso)** — Consolidación
- Añadir primary_domain a serializers
- Debounce en búsqueda Tabulator
- Archivar documentación (este documento)
- Verificar hardening básico

**Sprint 3 (Próxima)** — Consolidación de APIs
- Migrar workspace.html a assets modernos
- Consolidar *.api.js duplicados
- Unificar templates offcanvas

---

## 🔗 Referencias rápidas

| Tópico | Documento |
|--------|-----------|
| Autenticación JWT | [JWT_AUTENTICACION.md](JWT_AUTENTICACION.md) |
| URLs y rutas | [informe_rutas_completo.md](informe_rutas_completo.md) |
| Modelos y bases de datos | Avisos en docstrings de `models.py` |
| Testing | Tests en `apps/*/tests/` |
| API REST | Swagger: `/api/docs/`, ReDoc: `/api/redoc/` |

---

## ⚡ Próximos pasos

1. Leer [SPRINT_1_DESBLOQUEAR_CRUD.md](SPRINT_1_DESBLOQUEAR_CRUD.md) para entender http.js y la suite E2E
2. Revisar módulos en `/clientes/`, `/inventario/`, `/contabilidad/` para CRUD funcional
3. Ejecutar tests: `cd tests/e2e && npm test`
4. En Sprint 2, verificar debounce en búsquedas y primary_domain en API

---

**Última actualización:** 2026-05-02  
**Responsable:** Equipo de desarrollo Sintel
