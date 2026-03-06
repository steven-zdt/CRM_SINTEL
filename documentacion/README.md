# 📚 Documentación del Proyecto SINTEL

**Ubicación:** `documentacion/`  
**Única Fuente de Verdad:** Todos los archivos de documentación del proyecto están consolidados en esta carpeta (ÚNICA UBICACIÓN).

## 📋 Índice de Documentación

### 🏗️ Arquitectura Principal

- **[arquitectura_general.md](arquitectura_general.md)** ⭐ **FUENTE ÚNICA DE VERDAD**
  - Arquitectura completa del proyecto
  - Stack tecnológico
  - Estructura de directorios
  - Configuración Django
  - Flujos de trabajo
  - Estado de todas las fases

### 🧩 Multi-tenancy (django-tenants)

- **[DJANGO_TENANTS_PLAYBOOK_SINTEL.md](DJANGO_TENANTS_PLAYBOOK_SINTEL.md)** ⭐ Playbook normalizado (routing, URLConf, migraciones, testing, troubleshooting)

### 🧱 Core Django (Django 5)

- **[DJANGO_5_PLAYBOOK_SINTEL.md](DJANGO_5_PLAYBOOK_SINTEL.md)** ⭐ Fuente de verdad normalizada (settings, seguridad, performance, testing, deployment) basada en doc oficial

### 📝 Documentos de Fases

- **[FASE_2_COMPLETA.md](FASE_2_COMPLETA.md)**: Fase 2 - Infraestructura Pública y Autenticación
- **[FASE_2_COMPLETA_VERIFICADA.md](FASE_2_COMPLETA_VERIFICADA.md)**: Verificación de Fase 2
- **[FASE_2_VERIFICACION.md](FASE_2_VERIFICACION.md)**: Checklist de verificación de Fase 2
- **FASE4_MIGRACION_PROGRESO.md** (raíz): Estado de migración por app a DataTables server-side
- **FASE5_RESUMEN.md** (raíz): Resumen de Fase 5 - Pruebas y CI completadas

### 🔧 Soluciones y Ajustes

- **[AJUSTES_BEST_PRACTICES.md](AJUSTES_BEST_PRACTICES.md)**: Ajustes de mejores prácticas
- **[CAMBIOS_MIGRACIONES_SEGURAS.md](CAMBIOS_MIGRACIONES_SEGURAS.md)**: Cambios en migraciones seguras
- **[CAMBIOS_SETTINGS.md](CAMBIOS_SETTINGS.md)**: Cambios en settings.py
- **[SOLUCION_ERROR_HTTPS.md](SOLUCION_ERROR_HTTPS.md)**: Solución al error HTTPS
- **[SOLUCION_CSRF_403.md](SOLUCION_CSRF_403.md)**: Solución al error 403 CSRF en login admin
- **[SOLUCION_MIGRACIONES_INCONSISTENTES.md](SOLUCION_MIGRACIONES_INCONSISTENTES.md)**: Solución a migraciones inconsistentes
- **[SOLUCION_TENANT_PUBLICO.md](SOLUCION_TENANT_PUBLICO.md)**: Solución para tenant público

### 📋 Checklists y Guías

- **[CHECKLIST_INICIALIZACION.md](CHECKLIST_INICIALIZACION.md)**: Checklist de inicialización
- **[COMANDOS_TENANT_PUBLICO.md](COMANDOS_TENANT_PUBLICO.md)**: Comandos para crear tenant público
- **[CONFIGURACION_TERMINAL.md](CONFIGURACION_TERMINAL.md)**: Configuración de terminal

### 🔍 Verificación y Alineación

- **[ALINEACION_COMPLETA.md](ALINEACION_COMPLETA.md)**: Alineación completa del proyecto
- **[REGLAS_ALINEACION.md](REGLAS_ALINEACION.md)**: Reglas de alineación
- **[VERIFICACION_ALINEACION.md](VERIFICACION_ALINEACION.md)**: Verificación de alineación
- **[SERVER_GUARD.md](SERVER_GUARD.md)**: Documentación del Server Guard

### 💼 Módulos de Negocio

- **[COTIZACIONES_EDITOR_V2.40.md](COTIZACIONES_EDITOR_V2.40.md)**: Editor de Cotizaciones Estilo Excel v2.40
  - Arquitectura modular en cascada
  - Visibilidad dinámica de secciones
  - Sistema CRUD de perfiles de configuración
  - Cálculo AIU con IVA solo sobre Utilidad
- **LIMPEZA_COTIZACIONES_v2.60.md** (raíz): Limpieza profunda del módulo Cotizaciones v2.60
  - Eliminación de monolitos frontend
  - Migración a arquitectura Feature-Sliced
  - Refactorización completa del backend

### 🔄 Migraciones y Refactorizaciones

- **[MIGRACION_COMPLETA_RESUMEN.md](MIGRACION_COMPLETA_RESUMEN.md)**: Migración completa del pipeline de documentos
- **[RESUMEN_FINAL_ALINEACION.md](RESUMEN_FINAL_ALINEACION.md)**: Alineación integral del módulo Facturas
- **[ALINEACION_TECNICA_O0.md](ALINEACION_TECNICA_O0.md)**: Alineación técnica Fase 0 - Normalización de assets y sanity checks

---

## ⚠️ Regla General

**TODOS los archivos de documentación (.md) deben estar en `documentacion/`**

- ✅ Esta es la ÚNICA ubicación para documentación
- ✅ Cualquier archivo .md fuera de esta carpeta debe moverse aquí
- ✅ `README.md` en la raíz es la excepción (estándar de proyectos)

## 📖 Documento Principal

**`arquitectura_general.md`** es la fuente única de verdad para:
- Arquitectura del proyecto
- Stack tecnológico
- Estructura de directorios
- Configuración
- Estado de implementación de fases

---

**Última Actualización:** 2026-02-10
