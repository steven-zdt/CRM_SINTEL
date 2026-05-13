# Arquitectura de Microtareas: Módulo Proyectos v3.5.0

Este documento descompone el módulo de **Proyectos** en tareas atómicas para su mantenimiento, evolución y cumplimiento de estándares SINTEL v3.5.0.

## [PROY-1] Estandarización de Identificadores (UUID)
- [ ] Refactorizar `ProyectoViewSet` para heredar de `BaseTenantViewSet`.
- [ ] Implementar campo `uuid` en el modelo `Proyecto` (vía `SintelTenantBaseModel` si se actualiza, o manualmente).
- [ ] Actualizar `lookup_field="uuid"` en ViewSets y URLs.
- [ ] Migrar el frontend (`proyectos.api.js`) para consumir endpoints vía UUID.
- [ ] Ajustar `ProyectoSelector.qs_detail` para filtrar por `uuid` en lugar de `pk`.

## [PROY-2] Fortalecimiento de la Capa de Servicios (Zero Trust)
- [ ] Implementar **Doble Verificación Semántica (DSV)** en `ProyectoBusinessService`: Validar que `cliente_id` y `responsable_id` (snapshots) existan y sean válidos antes de persistir.
- [ ] Migrar lógica de `generar_codigo_proyecto` a un helper global de infraestructura si es reutilizable.
- [ ] Asegurar que `save_proyecto` en `crud_service.py` use `@transaction.atomic` (ya implementado, verificar consistencia).
- [ ] Eliminar imports directos de modelos en `viewsets.py` y delegar 100% a Mixins.

## [PROY-3] Optimización de Consultas (Zero Waste)
- [ ] Revisar `LIST_FIELDS` en `selectors.py` para asegurar que solo se traigan los campos estrictamente necesarios para la grilla Tabulator.
- [ ] Implementar `prefetch_related` para `equipo_trabajo` y `pedidos` en la vista de detalle para evitar N+1 en el renderizado de Offcanvas.
- [ ] Validar el uso de `.distinct()` en búsquedas complejas para evitar duplicados en el listado.

## [PROY-4] Interfaz de Usuario y FSD (Frontend)
- [ ] Sincronizar `proyectos_editor.js` con el patrón "Auto-Healing" para reinicializar componentes Bootstrap tras swaps de HTMX.
- [ ] Implementar validación en tiempo real en el frontend para el campo `codigo` (unicidad).
- [ ] Refactorizar `offcanvas_form.html` para usar partials de Bootstrap 5 consistentes con el resto del sistema.
- [ ] Asegurar que el objeto `window.jwtAuth` se use correctamente para todas las peticiones asíncronas desde `proyectos.api.js`.

## [PROY-5] Lógica de Negocio y Snapshots
- [ ] Documentar formalmente el patrón "Snapshot" en el módulo para evitar que futuros desarrolladores intenten convertir `cliente_id` en una ForeignKey real.
- [ ] Implementar tareas programadas (Celery) para la recalculación masiva de indicadores financieros (`costo_total`, `margen`) en proyectos de larga duración.
- [ ] Mejorar la gestión de archivos adjuntos: mover la lógica de subida a un servicio dedicado que maneje versionado o limpieza.
