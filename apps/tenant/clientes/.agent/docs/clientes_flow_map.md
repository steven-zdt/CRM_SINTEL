# CLIENTES — Flow Map (Mapa de Flujos)

**Version:** 3.5.0
**App:** `apps/tenant/clientes/`

Este documento detalla los flujos de datos y secuencias de operacion del modulo de Clientes, desde la interaccion en el frontend hasta la persistencia en base de datos.

---

## 1. Renderizado de Grilla Principal (Tabulator)

```mermaid
sequenceDiagram
    participant U as Usuario
    participant JS as clientes.list.js
    participant TF as TabulatorFactory
    participant API as ClienteViewSet (DRF)
    participant SEL as ClienteSelector
    participant DB as PostgreSQL

    U->>JS: Navega a #clientes
    JS->>JS: Captura evento 'tab-shown'
    JS->>TF: create('#grid-clientes', '/api/v1/clientes/')
    TF->>API: GET /api/v1/clientes/ (Authorization: Bearer)
    API->>SEL: get_cliente_list(empresa_id, search)
    SEL->>DB: SELECT .only(LIST_FIELDS) + Prefetch(contactos principal)
    DB-->>SEL: QuerySet
    SEL-->>API: Results
    API-->>TF: JSON {count, results: [...]}
    TF->>JS: dataLoaded event
    JS->>U: Renderiza tabla con Encargado (nombre + email)
```

---

## 2. Flujo CRUD Maestro-Detalle (Crear/Editar)

```mermaid
sequenceDiagram
    participant U as Usuario
    participant JS as clientes.editor.js
    participant API as ClienteViewSet
    participant BS as ClienteBusinessService
    participant CS as ClienteCRUDService
    participant DB as PostgreSQL

    U->>U: Completa form + Contactos
    U->>JS: Click "Guardar"
    JS->>JS: recolectarDatosFormulario() (DOM Shield)
    JS->>API: POST/PATCH /api/v1/clientes/ (JSON Payload)
    API->>BS: registrar_cliente_completo(data, contactos_raw)
    Note over BS: Inicio @transaction.atomic
    BS->>CS: create_cliente / update_cliente
    CS->>DB: INSERT/UPDATE Cliente
    BS->>BS: sincronizar_contactos(contactos_raw)
    BS->>CS: update/create/delete contactos
    CS->>DB: Sync ContactoCliente items
    Note over BS: Commit Transaction
    BS-->>API: Instance
    API-->>JS: HTTP 201/200 + 'clienteGuardado' Event
    JS->>U: UIManager.success + reloadTable()
```

---

## 3. Eliminacion con Doble Validacion (Two-Step Delete)

```mermaid
sequenceDiagram
    participant U as Usuario
    participant JS as clientes.list.js
    participant API as ClienteViewSet
    participant CS as ClienteCRUDService

    U->>JS: Click "Eliminar"
    alt Cliente Activo
        JS->>U: Muestra "Debe inactivarlo primero"
    else Cliente Inactivo (activo=False)
        U->>JS: Confirma eliminacion
        JS->>API: DELETE /api/v1/clientes/{id}/
        API->>CS: delete_cliente(cliente)
        alt Check backend: activo==True
            CS-->>API: ValidationError (400)
            API-->>JS: Error response
        else
            CS->>DB: DELETE
            API-->>JS: HTTP 204
            JS->>U: 'clienteEliminado' + reloadTable()
        end
    end
```

---

## 4. Renderizado de Offcanvas (HTMX)

```mermaid
sequenceDiagram
    participant U as Usuario
    participant JS as clientes.list.js
    participant API as ClienteViewSet
    participant UI as UIManager

    U->>JS: Click "Editar" / "Ver" / "Nuevo"
    JS->>API: GET /render-offcanvas/{modo}/{id}/
    API->>API: render_template_safe(template)
    API-->>JS: HTML Partial
    JS->>JS: Inyecta en #offcanvas-container
    JS->>UI: handleOffcanvas(el, 'show')
    UI->>UI: Limpia backdrops + Dispose instances
    UI->>U: Muestra Offcanvas Bootstrap
```

---

## 5. Trazabilidad de Contactos (Directorio Global)

```mermaid
sequenceDiagram
    participant U as Usuario
    participant JS as clientes.list.js
    participant SEL as ContactoSelector
    participant DB as PostgreSQL

    U->>JS: Switch a tab "Directorio de Contactos"
    JS->>JS: loadContactosTable() (Lazy Load)
    JS->>API: GET /api/v1/clientes/contactos/
    API->>SEL: get_contacto_list(empresa_id)
    SEL->>DB: SELECT .select_related('cliente').only(...)
    DB-->>SEL: Results (con razon_social del cliente)
    SEL-->>API: Response
    API-->>JS: JSON results
    JS->>U: Renderiza tabla con columna "Cliente" (Zero Waste)
```
