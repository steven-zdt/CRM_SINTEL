# Cotizaciones — Guía de UI real (FASE 27, consolidado)

**Fecha:** 2026-08-27. Describe el frontend TAL COMO ES tras los fixes de esta misión — no un diseño aspiracional.

---

## Mapa de flujo real (confirmado por auditoría de código)

```
workspace/#cotizaciones (list.html)
  │
  ├── Grilla principal de Cotizaciones (Tabulator vía TabulatorFactory)
  │     ├── Botón "Nueva Cotización" → /cotizaciones/editor/draft/ → editor_cotizacion.html
  │     ├── Botón "Editar" (fila) → /cotizaciones/editor/{uuid}/ → editor_cotizacion.html
  │     ├── Botón "Detalle" (fila) → offcanvas_detalle_cotizacion.html
  │     ├── Botón "PDF" (fila) → descarga directa
  │     └── Botón "Eliminar" (fila) → confirmación modal → DELETE (bloqueado si hay Factura vinculada)
  │
  ├── Botón "Plantilla" / "Config." → offcanvas_list_plantillas.html (ConfiguracionCotizacion)
  │     ├── Grilla de Plantillas (Tabulator vía TabulatorFactory, corregido hoy)
  │     └── Editar/Crear → mismo formulario, con reload() corregido hoy
  │
  └── [Producto/Servicio: backend + formularios completos y corregidos hoy,
        pero SIN punto de entrada de UI real -- ver COTIZACIONES_RELEASE_GATE.md
        §"Hallazgo nuevo" -- ningún template tiene los contenedores que
        cotizaciones.main.js busca para mostrarlos]
```

## El editor de Cotización (`editor_cotizacion.html` + `cotizacion_editor.js`)

Es un único formulario (no un wizard de varios pasos — decisión explícita de esta misión, ver `COTIZACIONES_AUDIT_BASELINE.md` §3) con:

1. Selector de Cliente y Plantilla (obligatorios, únicos campos validados client-side antes de enviar).
2. Tres secciones de ítems (Dispositivos/Materiales/Servicios), con pegado desde Excel soportado.
3. Panel de porcentajes AIU/IVA.
4. Campos de tiempos del proyecto (días de infraestructura/instalación/configuración/pruebas).
5. Botón "Guardar" — deshabilitado durante el envío (correcto, sin doble-submit), reactivado siempre en `.finally()`.

Tras guardar: redirige a `/workspace/#cotizaciones` (recarga completa de página) — fricción documentada, no corregida en esta pasada por ser una reescritura de flujo, no una corrección de bug.

**Errores de validación del backend**: corregido hoy — antes siempre mostraban "Error desconocido" (formato incorrecto pasado a `UIManager.handleError`), ahora muestran el mensaje real de campo.

## Formularios de Producto/Servicio

Un solo template por entidad (`offcanvas_crear_producto.html`/`offcanvas_crear_servicio.html`) sirve tanto creación como edición (según si `instance` está presente en el contexto) — mismo patrón que usa `editor_cotizacion.html` para Cotización, sin duplicar formularios (Regla Absoluta #1).

**Corregido hoy**: fallo silencioso (mostraba "guardado" aunque el backend rechazara los datos), doble-submit posible, botón "Editar" que no hacía nada, y un bug de locale en el valor pre-poblado de precio (coma en vez de punto, que habría invalidado el campo).

## Iconografía y accesibilidad

Los botones de acción de la grilla principal ya usan `title` descriptivo (`"Editar"`, `"Detalle"`, `"PDF"`, `"Eliminar"`) — cumple el mínimo de nombre accesible. El estado de una Cotización siempre se muestra como color + texto juntos (badge), nunca solo color. Mejora opcional no aplicada: `aria-label` explícito en vez de solo `title` (más robusto en touch/mobile).

## Responsive

La tabla de ítems del editor tiene ancho mínimo con scroll horizontal — funciona en móvil pero es incómoda para una creación completa desde un teléfono (fricción documentada, no un bug).
