# 🏗️ Arquitectura de Microtareas (MT-IMP): Módulo Impuestos

Sistema de trazabilidad técnica para la evolución del catálogo normativo global.

---

## 🛠️ Fase 1: Calidad de Datos e Integridad (Data Layer)

- `[ ]` **MT-IMP-001**: Implementar `uuid` como identificador primario en todos los modelos de catálogo.
- `[ ]` **MT-IMP-002**: Refactorizar la tabla `ActividadEconomica` para soportar búsqueda semántica (OpenSearch).
- `[ ]` **MT-IMP-003**: Auditoría de consistencia de códigos DIAN contra el anexo técnico v1.8.
- `[ ]` **MT-IMP-004**: Implementar campos de vigencia (`valido_desde`, `valido_hasta`) en `TarifaIVA`.

---

## 🧠 Fase 2: Servicios de Provisión (Service Layer)

- `[ ]` **MT-IMP-010**: Desarrollar el `ImpuestosProvider` con soporte para caché multinivel.
- `[ ]` **MT-IMP-011**: Implementar lógica de cálculo de retenciones basada en matriz de compatibilidad tributaria.
- `[ ]` **MT-IMP-012**: Crear pipeline ETL para la ingesta automatizada de tasas UVT anuales.

---

## 🌐 Fase 3: API y Conectividad (API Layer)

- `[ ]` **MT-IMP-020**: Optimizar `CatalogoViewSet` para entregas rápidas con `.only()` y `.defer()`.
- `[ ]` **MT-IMP-021**: Implementar endpoints de salud para verificar la sincronización del catálogo con la DIAN.
- `[ ]` **MT-IMP-022**: Documentación Swagger de los esquemas de impuestos para integración de terceros.

---

## 🎨 Fase 4: Consola de Administración (UI Layer)

- `[ ]` **MT-IMP-030**: Crear editor masivo de tarifas en la Consola Global con validación cruzada.
- `[ ]` **MT-IMP-031**: UI para el monitoreo de tareas de ingesta (ETL logs).
- `[ ]` **MT-IMP-032**: Buscador avanzado de CIIU con filtros por sector económico.
