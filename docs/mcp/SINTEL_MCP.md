# SINTEL MCP - Conexion y Alcance

## Estado

Rama: `feat/mcp-sintel-project`

El proyecto ya utilizaba `django-rest-framework-mcp` y tenia rutas `/mcp/`, pero la configuracion anterior apuntaba a un proceso local inexistente y los ViewSets no estaban registrados como herramientas MCP.

Esta implementacion convierte los ViewSets DRF existentes en herramientas MCP, conservando serializers, filtros, autenticacion y permisos del proyecto.

## Endpoints

### Tenant

`http://127.0.0.1:8000/mcp/`

En produccion:

`https://<schema>.sintel.net.co/mcp/`

Autenticacion: JWT.

El middleware de django-tenants determina el tenant por hostname. El MCP no recibe `empresa_id` como parametro de confianza.

### Public/Admin

`https://sintel.net.co/mcp/`

Requiere JWT + usuario staff activo.

## Clientes MCP

### VS Code

El repositorio deja `.vscode/mcp.json` apuntando al endpoint HTTP local:

```json
{
  "servers": {
    "sintel": {
      "type": "http",
      "url": "http://127.0.0.1:8000/mcp/"
    }
  }
}
```

### Cursor / clientes compatibles

```json
{
  "mcpServers": {
    "sintel": {
      "type": "http",
      "url": "http://127.0.0.1:8000/mcp/"
    }
  }
}
```

## Cobertura

Se registran como MCP los ViewSets basados en `GenericViewSet`, incluyendo:

- Empresa
- Clientes
- Proveedores
- Inventario
- Cotizaciones
- Compras
- Facturas
- Contabilidad
- Gastos
- Empleados
- Proyectos
- Ventas
- Bancos
- Perfil
- Dashboard
- Catalogos publicos
- Tenants y administracion publica

Las operaciones CRUD disponibles en cada ViewSet se convierten automaticamente en tools cuando existen.

Las acciones personalizadas decoradas con `@action` requieren decoracion `@mcp_tool` si deben publicarse como tools MCP especificas.

## Seguridad

1. El endpoint MCP tenant exige usuario autenticado y activo.
2. Los permisos del ViewSet siguen aplicandose.
3. `BYPASS_VIEWSET_AUTHENTICATION` y `BYPASS_VIEWSET_PERMISSIONS` no deben habilitarse.
4. El MCP no crea una segunda capa ORM.
5. La logica de negocio sigue en Service Layer / ViewSet.
6. Las escrituras siguen sujetas a los permisos existentes del ViewSet.
7. El endpoint publico exige usuario staff activo.

## Arquitectura

```
MCP Client
   |
   v
/mcp/
   |
   v
SintelTenantMCPView
   |
   v
django-rest-framework-mcp
   |
   v
@ mcp_viewset ViewSets
   |
   +--> serializers / filters / permissions
   |
   +--> Service Layer
   |
   v
PostgreSQL tenant schema
```

## Regla arquitectonica

MCP es una interfaz de acceso, no un nuevo dominio.

No se debe implementar logica de negocio dentro del servidor MCP. Cualquier nueva capacidad debe agregarse al dominio existente y posteriormente exponerse como tool.

## Validacion

Desde el entorno local:

```powershell
python manage.py check
python -m pytest -q
```

Prueba funcional MCP:

1. Obtener JWT.
2. Configurar Authorization Bearer.
3. Ejecutar `tools/list`.
4. Verificar herramientas de un dominio.
5. Ejecutar una lectura.
6. Ejecutar una escritura solamente sobre un recurso de prueba y verificar los permisos.

## Pendientes para cobertura 100%

Los ViewSets que heredan directamente de `viewsets.ViewSet` no son convertidos automaticamente por la libreria porque `@mcp_viewset` requiere `GenericViewSet`.

Casos detectados:

- `apps/tenant/contabilidad/api/viewsets.py::LibroDiarioViewSet`
- `apps/tenant/landing/api/viewsets.py::LandingViewSet`

Deben exponerse mediante wrappers MCP especificos o migrarse cuidadosamente a `GenericViewSet` sin alterar su contrato HTTP.

## Fuente

La integracion usa `django-rest-framework-mcp`, que genera schemas desde serializers DRF y conserva autenticacion, permisos y filtros de los ViewSets. 
