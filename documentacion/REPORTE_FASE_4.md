# REPORTE FASE 4 — Performance (Hallazgos PERF-A y PERF-M)

**Fecha:** 2026-07-26
**Alcance:** Los 3 hallazgos PERF-A (ALTO) y los 7 hallazgos PERF-M (MEDIO) de `documentacion/AUDITORIA_ENTERPRISE_2026-07-26.md`, más un hallazgo recuperado (ver §0).

Misma limitación de entorno que Fases 1-3: verificación por `py_compile` + lectura manual, sin `make dj-check`/`make test` reales.

---

## 0. Gap detectado en el reporte consolidado (auto-corrección)

Al iniciar esta fase se encontró que el hallazgo **más severo de la auditoría de Performance** (Track C original, `F-01`, clasificado **CRÍTICO**: N+1 en `FacturaListSerializer`, hasta ~140 queries extra por página) nunca recibió un ID propio en `AUDITORIA_ENTERPRISE_2026-07-26.md` — la fila `PERF-A1` de la tabla de ALTOS quedó apuntando por error a `PERF-C3` (un hallazgo distinto, ya resuelto en Fase 1), y el N+1 real solo se mencionó en prosa (resumen ejecutivo, score de Performance, objetivo de la fase 3 del plan original) sin nunca aparecer en las tablas de hallazgos ni en "Hallazgos por Aplicación". Se corrige aquí: el hallazgo se resolvió en esta fase (ver §1) y se deja esta nota para que el índice de la auditoría original quede trazable.

---

## 1. Hallazgos resueltos

### N+1 en listado de Facturas (hallazgo recuperado, ver §0)
**Archivos:** `apps/tenant/contabilidad/services/retenciones_service.py` (nuevo método bulk), `apps/tenant/facturas/api/viewsets.py`, `apps/tenant/facturas/api/serializers.py`.

`FacturaListSerializer.get_retefuente/get_reteica/get_reteiva` llamaban a `obj.total_retencion_fuente`/etc. (properties del modelo, cada una con su propia query vía `RetencionesService`) **una vez por fila** — 3 queries × 20 filas = 60 queries extra solo para retenciones, en el endpoint más usado del sistema.

**Cambio (patrón "prefetch + context map", ya probado en `clientes/api/viewsets.py:ClienteListSerializer`):**
1. `RetencionesService.totales_retenciones_por_documentos(...)` — nuevo método bulk: una sola query `GROUP BY (documento_origen_id, tipo)` para todos los IDs de la página, en vez de N queries individuales.
2. `FacturaViewSet.paginate_queryset()` intercepta la página ya resuelta (sin reescribir `list()`, que sigue siendo el de `ModelViewSet` por defecto) y construye `{factura_id: {tipo: monto}}` con esa única query.
3. `FacturaViewSet.get_serializer_context()` inyecta el mapa como `retenciones_map`.
4. `FacturaListSerializer.get_retefuente/reteica/reteiva` leen del mapa si está en el contexto; si no (p.ej. el serializer se instancia directo en otro lugar sin pasar por el listado paginado), caen al property original — **sin cambio de comportamiento para esos casos**.

**Resultado:** 60 queries → 1 query para el bloque de retenciones de una página completa.

**No resuelto en esta fase (documentado explícitamente para seguimiento):** el mismo listado tiene 2-4 queries extra más por fila via `ClienteBridge`/`ProveedorBridge` (cliente o proveedor vinculado) y `BancosBridge` (`total_pagado_bancos` + `saldo_pendiente`, que internamente vuelve a llamar `total_pagado_bancos`). Optimizar estas requeriría el mismo patrón pero tocando 3 apps más (`clientes`, `proveedores`, `bancos`) cuyos bridges no tienen aún una variante bulk — se prefirió resolver con solidez la fuente de mayor volumen (retenciones, 3 de las ~7 queries/fila) en vez de apresurar cambios en 3 bridges adicionales de otras apps sin poder correr tests, dado que uno de ellos (`BancosBridge`) afecta un dato mostrado al usuario como saldo pendiente de pago — un error ahí es un error de negocio, no solo de performance.

### PERF-A2 / PERF-M7 — `bulk_create` en contabilidad
**Archivos:** `apps/tenant/contabilidad/integracion/contabilizador.py`, `apps/tenant/contabilidad/services/crud_service.py`.

Reemplazado `.save()`/`.create()` por línea con `bulk_create()` en **4 flujos**: `Contabilizador.contabilizar()` (usado por el extractor Pull Model para todo el backlog de pendientes), `CRUDService.crear_asiento`, `actualizar_asiento` y `crear_asiento_manual`. Verificado antes de aplicar que ni `MovimientoContable` ni `ImpuestoDocumento` tienen `save()` propio (solo el de `SintelTenantBaseModel`, que valida `empresa_id` — ya seteado explícitamente en cada instancia antes de `bulk_create`, así que la validación no se pierde en la práctica). Se preserva una escritura a BD por asiento (no se agrupan movimientos de asientos distintos), manteniendo el aislamiento de fallos por documento que ya tenía el código original.

### PERF-A3 — `.only()`/`.defer()` en catálogo DIAN público
**Archivos:** `apps/public/impuestos/api/serializers.py`, `apps/public/impuestos/api/viewsets.py`.

Al revisar los 9 ViewSets se encontró que **todos sus serializers usan `fields = "__all__"`** — es decir, necesitan literalmente todas las columnas del modelo, por lo que `.only()` no puede reducir nada real ahí sin antes dividir cada uno en un serializer de lista más liviano (un cambio de diseño mayor al que amerita este hallazgo puntual). La única excepción genuina es `NormaTributaria`, que tiene 2 `TextField` grandes (`texto_html`, `texto_plano` — el artículo legal completo). Se agregó `NormaTributariaListSerializer` (excluye ambos campos) y `NormaTributariaViewSet.get_queryset()` los excluye con `.defer()` solo en `list`; `retrieve` sigue sirviendo el contenido completo. Se verificó que `search_fields` (incluye `texto_plano`) sigue funcionando: el filtro de búsqueda opera a nivel de `WHERE ... ILIKE` en SQL, no depende de que el campo se traiga a Python.

**No aplicado a los otros 8 catálogos** (documentado, no omitido silenciosamente): `fields="__all__"` sobre columnas pequeñas (código/nombre/descripción/vigencia) no tiene una optimización segura de aplicar sin cambiar el contrato del serializer.

### PERF-M1 — Transacción única en presupuesto de proyectos
**Archivo:** `apps/tenant/proyectos/services/presupuesto_service.py`.

`crear_item`/`actualizar_item`/`eliminar_item` ahora están decorados `@transaction.atomic` — la escritura del item y el recálculo de los 3 totales cacheados del proyecto padre (`_recalcular_proyecto`) ahora ocurren en una sola transacción. `PresupuestoCRUDService.save_item`/`delete_item` ya eran atómicos por separado; anidar `@transaction.atomic` es seguro en Django (se convierte en savepoint).

### PERF-M2 — Query de historial de inventario sin filtro de fecha
**Archivos:** `apps/tenant/inventario/services/selectors.py`, `apps/tenant/contabilidad/services/selectors.py`.

`get_movimientos_timeline()` ganó un parámetro opcional `desde` (default `None`, preserva el comportamiento actual para todo llamador existente, incluida la UI de "ver historial completo" de inventario). `qs_inventario_movimientos_recientes_pendientes()` (el consumidor de contabilidad que repetía esta query completa solo para diferenciar contra IDs ya contabilizados) ahora pasa `desde = hoy - 730 días`.

**Decisión de diseño consciente:** se usó una ventana generosa (~2 años), no una corta, precisamente para no arriesgar ocultar silenciosamente un documento pendiente genuinamente antiguo de un chequeo de completitud financiera — un documento pendiente de contabilizar con más de 2 años de antigüedad indicaría un problema de proceso mayor que esta función no está pensada para resolver, y debería auditarse aparte, no ampliando esta ventana.

### PERF-M3 — Código muerto `get_balance_prueba`/`calcular_saldos_cuenta`
**Archivos:** `apps/tenant/contabilidad/services/selectors.py`, `apps/tenant/contabilidad/services/__init__.py`.

Re-verificado independientemente (grep de todo el árbol) que estas 2 funciones no tienen ningún llamador fuera de sí mismas y del re-export en `__init__.py` — el ViewSet real (`contabilidad/api/viewsets.py:415`) usa `balance_prueba_selector()` (ya optimizado con `GROUP BY`), no estas. Eliminadas ambas funciones y sus 2 re-exports. Limpieza adicional en la misma edición: los imports `Coalesce` y `DecimalField`/`F` a nivel de módulo en `selectors.py` quedaron sin uso tras la eliminación (`DecimalField`/`F` solo se usaban, y se siguen usando, vía un import local dentro de otra función que ya los reimporta) — se removieron de la línea de import de nivel de módulo.

### PERF-M5 — `--fake-initial` incondicional en Makefile
**Archivo:** `Makefile`.

`migrate-shared`/`migrate-tenants` ya no usan `--fake-initial` por defecto (así lo hacía ya, sin este flag, el path automático de `entrypoint.sh` que corre en cada arranque de contenedor — el Makefile era la única inconsistencia). Se agregaron `migrate-shared-init`/`migrate-tenants-init` como targets explícitos que sí lo incluyen, para el caso legítimo de adoptar un esquema cuyas tablas ya existen sin historial de migraciones Django.

**Riesgo residual reconocido:** si algún tenant tiene drift de esquema real que `--fake-initial` venía enmascarando, el próximo `make migrate-tenants` del equipo podría fallar de forma visible por primera vez — es exactamente el comportamiento buscado (superficie el problema en vez de esconderlo), pero se documenta como posible sorpresa operativa.

---

## 2. Hallazgos investigados y NO corregidos (con la razón concreta)

### PERF-M4 — Migraciones de `proveedores` (candidato a squash)
Confirmado el patrón de alta rotación ya descrito en la auditoría (crear→borrar→recrear→renombrar un modelo en 8 migraciones). **No se ejecutó `squashmigrations`**: esta operación reescribe el historial de migraciones y, si algún tenant ya tiene ese historial aplicado con nombres de migración distintos a los que generaría el squash, puede requerir reconciliación manual por esquema (`--fake` selectivo). Sin un entorno donde poder aplicar y verificar esto contra al menos un esquema tenant real, ejecutarlo a ciegas es más riesgoso que el problema que resuelve (que es de mantenibilidad/legibilidad del historial, no un bug activo). Recomendado como tarea dedicada con acceso a los esquemas tenant reales.

### PERF-M6 — `.only()` faltante en `gastos.DocumentoSelector.get_detail()`
Se investigó a fondo antes de aplicar el fix "obvio" que sugería la auditoría (usar la constante `DOCUMENTO_DETAIL_FIELDS` ya existente) y se encontró que **esa constante está desactualizada**: `DocumentoSoporteDetailSerializer.Meta.fields` serializa ~25 campos (incluyendo `vendedor_nit`, `vendedor_nombre`, `vendedor_direccion`, `vendedor_telefono`, `total_retefuente`, `total_reteica`, `total_reteiva`, `adjunto`, `movimiento_referencia`), de los cuales **al menos 9 no están en `DOCUMENTO_DETAIL_FIELDS`**. Aplicar `.only(*DOCUMENTO_DETAIL_FIELDS)` como sugería el hallazgo habría sido una **regresión disguised as fix**: cada campo faltante dispara su propia carga diferida (query adicional) por instancia accedida, potencialmente empeorando el rendimiento en vez de mejorarlo. Corregir esto bien requiere primero reescribir la constante para que coincida con el serializer real (o eliminarla y usar `.only()` inline con la lista completa) — trabajo de mayor alcance que un cambio quirúrgico de una línea, que no se ejecutó sin poder verificar el resultado contra el serializer real.

---

## 3. Criterios de "fase estable" — checklist

- [x] `py_compile` limpio en los 11 archivos `.py` tocados.
- [x] Verificados los nombres de campo exactos de `Retencion` (`tipo`, `monto`, `documento_origen_*`, `reversada`) contra el modelo antes de escribir la query bulk.
- [x] Verificado que `MovimientoContable`/`ImpuestoDocumento` no tienen `save()` propio antes de introducir `bulk_create`.
- [x] Verificado que ninguna otra parte del código importa `get_balance_prueba`/`calcular_saldos_cuenta` antes de eliminarlas.
- [x] Verificado que `entrypoint.sh` (el path automático de arranque) ya no usaba `--fake-initial`, confirmando que el cambio de Makefile alinea una inconsistencia en vez de introducir un comportamiento nuevo no probado en producción.
- [x] Cada decisión de "no corregir" (PERF-M4, PERF-M6, y las partes no resueltas del N+1 de Facturas) tiene evidencia concreta documentada, no una omisión silenciosa.
- [x] Se documentó y corrigió el gap de trazabilidad del propio reporte de auditoría (§0).

## 4. Archivos tocados (10 modificados)

```
M  Makefile
M  apps/public/impuestos/api/serializers.py
M  apps/public/impuestos/api/viewsets.py
M  apps/tenant/contabilidad/integracion/contabilizador.py
M  apps/tenant/contabilidad/services/__init__.py
M  apps/tenant/contabilidad/services/crud_service.py
M  apps/tenant/contabilidad/services/retenciones_service.py
M  apps/tenant/contabilidad/services/selectors.py
M  apps/tenant/facturas/api/serializers.py
M  apps/tenant/facturas/api/viewsets.py
M  apps/tenant/inventario/services/selectors.py
M  apps/tenant/proyectos/services/presupuesto_service.py
```

No se ejecutó ningún `git add`/`git commit`.

## 5. Siguiente paso

Antes de Fase 5 (Frontend — FE-A/FE-M): recomendado ejecutar `make dj-check` y, si es posible, medir con `django-debug-toolbar` o `EXPLAIN ANALYZE` el conteo real de queries en `GET /api/v1/facturas/` antes/después de este cambio, para confirmar la reducción esperada (~60 queries menos por página) y decidir si vale la pena completar la optimización de `ClienteBridge`/`ProveedorBridge`/`BancosBridge` documentada como pendiente.
