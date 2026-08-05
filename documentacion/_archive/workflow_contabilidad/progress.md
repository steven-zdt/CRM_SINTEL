# Progress Log — Integración Contable SINTEL v3.6

**Última actualización:** 2026-05-08 (v3.7 — post-correcciones On-Demand)

---

## Historial de sesiones

| Timestamp | Track | Acción | Resultado |
|-----------|-------|--------|-----------|
| 2026-05-08 10:17 | Setup | Inicialización `task_plan.md`, `findings.md`, `progress.md` | Workflow persistente inicializado |
| 2026-05-08 10:18 | B.0 | Verificado `Contabilizador` y `dtos.py` | Arquitectura lista para extractores |
| 2026-05-08 10:19 | B.0 | Implementado `AbstractExtractor` + estructura directorios | Fase B.0 completa |
| 2026-05-08 10:25 | B.1 | Implementado `ExtractorGastos` | Entradas balanceadas para `DocumentoSoporte` |
| 2026-05-08 10:30 | B.2 | Implementado `ExtractorInventario` | Sincronización Kardex implementada |
| 2026-05-08 10:35 | B.0 | Orquestador añadido a `ContabilidadBusinessService` | Pipeline ETL listo para ejecución |
| 2026-05-08 (tarde) | B.3 | Implementado `ExtractorFacturas` + NC | Causación automática facturas venta |
| 2026-05-08 (tarde) | B.3 | Fix conceptos (`INGRESO_PRINCIPAL`, `CXC`, etc.) | Conceptos alineados con seed |
| 2026-05-08 (tarde) | B.3 | Añadido `COMPRA_NOTA_CREDITO` a `TipoTransaccion` | NC compra manejadas correctamente |
| 2026-05-08 (tarde) | B.4 | Implementado `ExtractorNomina` | Devengos y deducciones básicas |
| 2026-05-08 (tarde) | B.5 | `seed_reglas_contables` actualizado con nuevos conceptos | Reglas nómina disponibles |
| 2026-05-08 | Global | Fix `NameError TipoComprobanteListSerializer` | 500 en workspace resuelto |
| 2026-05-08 | Global | Fix `poblar_catalogo_niif` (empresa_id + todos los campos) | 124 cuentas en schemas home y cliente |
| 2026-05-08 | UI | Fix `#grid-cuenta` → `#grid-cuentas` en `cuenta_list.js` | Lista cuentas contables visible |
| 2026-05-08 | A.0 | DTOs `LineaManual` + `ComprobanteManualDTO` | Contrato manual definido |
| 2026-05-08 | A.0 | Selectors pendientes en `selectors.py` | `qs_facturas_pendientes`, `qs_gastos_pendientes` |
| 2026-05-08 | A.0 | `crear_asiento_manual()` en CRUD service | Soporte `documento_origen_*` y totales correctos |
| 2026-05-08 | A.0 | `contabilizar_documento_manual()` en business service | Validaciones completas (idempotencia, periodo, nivel 6, cuadratura) |
| 2026-05-08 | A.0 | `DocumentosPendientesViewSet` + 3 acciones API | `GET /pendientes/`, render-offcanvas, `POST /contabilizar-manual/` |
| 2026-05-08 | A.0 | Templates `pendientes_list.html` + `pendiente_offcanvas_contabilizar.html` | UI On-Demand completa |
| 2026-05-08 | A.0 | JS `pendiente_list.js` con `TabulatorFactory.create()` | Cumple regla FSD |
| 2026-05-08 | A.0 | Subtab `#subtab-pendientes` en workspace | Accesible desde módulo contabilidad |
| 2026-05-08 | Docs | `AUDITORIA_COMPLETA_CONTABILIDAD.md` actualizada a v3.6 | Estado real documentado |
| 2026-05-08 | Docs | `PLAN_INTEGRACION_CONTABLE.md` reestructurado a v3.6 | Arquitectura dual + contrato 4 pasos |
| 2026-05-08 | Docs | `workflow_contabilidad/*` alineados con v3.6 | Docs sincronizados |
| 2026-05-08 | A.0 | `APP_ORIGEN_PREFIJOS` + `filtrar_cuentas_por_app_origen()` en selectors.py | Filtro contextual cuentas |
| 2026-05-08 | A.0 (UI) | `buscarCuenta` inyecta `&app_origen=${APP_LABEL}` en offcanvas JS | Búsqueda contextual activa |
| 2026-05-08 | A.0 | Seed `TipoComprobante` (6 tipos) en schemas home + cliente | Botón "Generar Asiento" habilitado |
| 2026-05-08 | A.0 | Seed `CuentaContable` nivel-6 (54 cuentas) en schemas home + cliente | ValidationError nivel-6 resuelto |
| 2026-05-08 | A.0 | Fix import `ReglaContable` en `viewsets.py` | 500 en render-offcanvas resuelto |
| 2026-05-08 | A (UI) | Fix `clearFilter(false)` en `pendiente_list.js` | Header filters preservados |
| 2026-05-08 | A (UI) | `TIPO_BADGE` object con NOMINA/INVENTARIO en `pendiente_list.js` | Badges correctos |
| 2026-05-08 | A (UI) | Opciones NOMINA/INVENTARIO en `filter-tipo-pendiente` select | Dropdown completo |
| 2026-05-08 | Docs | `AUDITORIA_COMPLETA_CONTABILIDAD.md` v3.7 | Filtro app_origen, inventario DB, conectividad |
| 2026-05-08 | Docs | `PLAN_INTEGRACION_CONTABLE.md` v3.7 | Paso 5 contrato, acciones completadas, roadmap |
| 2026-05-08 | Docs | `workflow_contabilidad/*` v3.7 | Este commit |

| 2026-05-08 (v3.8) | C.0 | `anthropic>=0.40.0` añadido a `requirements.txt` | Dependencia IA declarada |
| 2026-05-08 (v3.8) | C.0 | `AsistenteIAInputSerializer` en `serializers.py` | Contrato de entrada validado |
| 2026-05-08 (v3.8) | C.0 | `sugerir_lineas_asiento_ia()` en `business_service.py` | Orquestador IA + DSV cuentas |
| 2026-05-08 (v3.8) | C.0 | `asistente_ia` action en `DocumentosPendientesViewSet` | Endpoint `POST /asistente-ia/` operativo |
| 2026-05-08 (v3.8) | C.0 (UI) | Botón "Diligenciar con IA" + `diligenciarConIA()` JS en offcanvas | UX autocompletado IA activa |
| 2026-05-08 (v3.8) | Docs | Sección `[AI-AGENTS] 20.` en `AGENTS.md` | Arquitectura routed agents documentada |
| 2026-05-08 (v3.8) | Docs | `workflow_contabilidad/*` alineados con v3.8 | Docs sincronizados |
| 2026-05-08 (v3.8) | B | Ejecutado `seed_reglas_contables` manual | 13 ReglaContable activas en schemas home + cliente |
| 2026-05-08 (fix) | API | NameError: Decimal en render-offcanvas/empleados | Añadido import Decimal en viewsets.py, container reloaded |
| 2026-05-08 (fix) | API | KeyError: numero_actual en render-offcanvas/gastos | Cambiar campo a consecutivo en selectors.py, container reloaded |

---

## Resultados de verificación

| Verificación | Resultado |
|-------------|-----------|
| Compilación Python (todos archivos) | ✅ ALL OK |
| Django system check | ✅ 0 issues |
| `CatalogoMaestroNIIF.objects.count()` | ✅ 124 cuentas (home + cliente) |
| `CuentaContable.objects.filter(nivel=6).count()` | ✅ 54 cuentas nivel-6 (home + cliente) |
| `TipoComprobante.objects.filter(activa=True).count()` | ✅ 6 tipos (home + cliente) |
| `ReglaContable.objects.filter(activo=True).count()` | ✅ 13 reglas (home + cliente) |
| `qs_facturas_pendientes(1).count()` | ✅ 4 facturas |
| `qs_gastos_pendientes(1).count()` | ✅ 1 gasto |
| `filtrar_cuentas_por_app_origen(qs, 'gastos').count()` | ✅ 25 cuentas nivel-6 |
| `filtrar_cuentas_por_app_origen(qs, 'facturas').count()` | ✅ 14 cuentas nivel-6 |
| `from viewsets import DocumentosPendientesViewSet` | ✅ OK (ReglaContable importado) |
| `GET /api/v1/contabilidad/pendientes/render-offcanvas/?app=facturas&...` | ✅ 200 OK (era 500) |
| Servidor web | ✅ Up — 0 errores en logs |
| Static files | ✅ 1 archivo copiado (pendiente_list.js) |

---

## Tests pendientes

| Test | Track | Bloqueante | Prioridad |
|------|-------|-----------|-----------|
| Pruebas unitarias `ExtractorGastos` | B.1 | DB locks Windows | Media |
| Pruebas unitarias `ExtractorInventario` | B.2 | DB locks Windows | Media |
| Pruebas unitarias `ExtractorFacturas` | B.3 | DB locks Windows | Media |
| Golden path completo offcanvas: seleccionar factura → asignar cuentas → generar asiento | A.0 | Ninguno | Alta |
| Test idempotencia: contabilizar mismo documento 2 veces → error esperado | A.0 | Ninguno | Alta |
| Test TipoComprobante: consecutivo incrementa correctamente tras crear asiento | A.0 | Ninguno | Alta |
| Test periodo cerrado: intento contabilizar en periodo CERRADO → error esperado | A.0 | Ninguno | Media |
| Test app_origen filter: búsqueda cuentas con/sin `?app_origen=` | A (UI) | Ninguno | Media |
