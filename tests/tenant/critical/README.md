# ⚠️ Fase 6: Tests Críticos del Sistema Multitenant

## 📋 Resumen

Esta fase implementa pruebas mínimas pero críticas que validan los puntos esenciales del sistema multitenant:

- ✅ Tenant Onboarding
- ✅ Aislamiento de Datos
- ✅ Autenticación y Autorización
- ✅ Funcionales Básicas (apps core)
- ✅ Errores Críticos
- ✅ Arranque y Disponibilidad

## 🎯 Objetivo

Validar que el sistema multitenant funciona correctamente en los puntos críticos de negocio y arquitectura, garantizando:

- Aislamiento de datos por tenant
- Correcto onboarding de empresas
- Operación básica y segura del sistema
- Estabilidad mínima antes de despliegue

**Principio clave:** No se busca cobertura total, sino pruebas estratégicas de alto impacto.

## 📁 Estructura de Tests

### 1. `test_tenant_onboarding.py`
**Tests críticos de Tenant Onboarding**

Valida que el sistema pueda crear y operar nuevos tenants sin intervención manual.

**Tests incluidos:**
- `test_crear_tenant_completo`: Creación completa de tenant (empresa, esquema, dominio, admin)
- `test_esquema_se_crea_correctamente`: El esquema PostgreSQL se crea correctamente
- `test_dominio_resuelve_al_tenant_correcto`: El dominio resuelve al tenant correcto
- `test_admin_puede_iniciar_sesion`: El admin puede iniciar sesión
- `test_no_afecta_tenants_existentes`: La creación de un nuevo tenant no afecta tenants existentes
- `test_idempotencia_onboarding`: El onboarding es idempotente

**Criterios de aceptación:**
- El esquema se crea correctamente
- El dominio resuelve al tenant correcto
- El admin puede iniciar sesión
- No se afecta ningún tenant existente

### 2. `test_data_isolation.py`
**Tests críticos de Aislamiento de Datos**

Confirman el principio fundamental del SaaS multitenant: cada tenant solo accede a sus propios datos.

**Tests incluidos:**
- `test_tenant_a_no_ve_datos_tenant_b`: Tenant A no puede leer datos del Tenant B
- `test_queries_ejecutan_esquema_correcto`: Queries ejecutadas bajo el esquema correcto
- `test_acceso_directo_por_id_imposible`: Acceso directo por ID entre tenants es imposible
- `test_empresa_aislamiento_por_tenant`: Cada tenant tiene su propia Empresa (SSoT)

**Criterios de aceptación:**
- Cada tenant solo accede a su propio esquema
- No hay filtraciones de datos entre empresas

### 3. `test_auth_authorization.py`
**Tests críticos de Autenticación y Autorización**

Validan el control de acceso básico del sistema multitenant.

**Tests incluidos:**
- `test_login_valido_dentro_tenant`: Login válido dentro de un tenant
- `test_login_invalido_credenciales_incorrectas`: Login inválido (credenciales incorrectas)
- `test_usuario_sin_permisos_no_accede_modulos_restringidos`: Usuario sin permisos no accede a módulos restringidos
- `test_middleware_tenant_activo_en_cada_request`: Middleware de tenant activo en cada request

**Criterios de aceptación:**
- Sesión asociada correctamente al tenant
- Middleware de tenant activo en cada request

### 4. `test_functional_basic.py`
**Tests Funcionales Básicos (por app core)**

Solo para apps core del ciclo activo: CRUD básico dentro del tenant.

**Tests incluidos:**
- `FacturasFunctionalTests`: CRUD básico para Facturas
  - `test_crear_factura`: Crear factura dentro del tenant
  - `test_listar_facturas`: Listar facturas dentro del tenant
  - `test_eliminar_factura`: Eliminar factura dentro del tenant
- `ClientesFunctionalTests`: CRUD básico para Clientes
  - `test_crear_cliente`: Crear cliente dentro del tenant
  - `test_listar_clientes`: Listar clientes dentro del tenant
- `EmpresaFunctionalTests`: Validar que SSoT funciona correctamente
  - `test_crear_empresa_singleton`: Crear empresa (debe ser singleton por tenant)

**Criterios de aceptación:**
- CRUD funciona dentro del tenant
- No rompe el esquema compartido
- Dashboards cargan sin error

### 5. `test_critical_errors.py`
**Tests de Errores Críticos**

Validan la resiliencia mínima del sistema ante errores esperables.

**Tests incluidos:**
- `test_acceso_dominio_inexistente`: Acceso a dominio inexistente
- `test_tenant_desactivado`: Acceso a tenant desactivado
- `test_error_esquema_no_encontrado`: Error de esquema no encontrado
- `test_request_sin_contexto_tenant`: Request sin contexto de tenant
- `test_sistema_no_cae_ante_errores_esperables`: El sistema no cae ante errores esperables

**Criterios de aceptación:**
- Mensajes de error controlados
- No exposición de información sensible
- No caída total del sistema

### 6. `test_startup_availability.py`
**Tests de Arranque y Disponibilidad**

Validan que el sistema pueda iniciar y operar correctamente.

**Tests incluidos:**
- `test_migraciones_ejecutan_sin_error`: Migraciones ejecutan sin error
- `test_servidor_inicia_correctamente`: Servidor inicia correctamente
- `test_acceso_tenant_publico`: Acceso a tenant público (si existe)
- `test_acceso_tenant_privado`: Acceso a tenant privado
- `test_modelos_tenant_cargables`: Modelos tenant son cargables
- `test_healthcheck_endpoint_disponible`: Healthcheck endpoint está disponible

**Criterios de aceptación:**
- Sistema operativo tras deploy
- Sin errores críticos en logs

## 🚀 Ejecución de Tests

### Ejecutar todos los tests críticos:
```bash
python manage.py test tests.tenant.critical
```

### Ejecutar tests específicos:
```bash
# Tests de onboarding
python manage.py test tests.tenant.critical.test_tenant_onboarding

# Tests de aislamiento
python manage.py test tests.tenant.critical.test_data_isolation

# Tests de autenticación
python manage.py test tests.tenant.critical.test_auth_authorization

# Tests funcionales
python manage.py test tests.tenant.critical.test_functional_basic

# Tests de errores
python manage.py test tests.tenant.critical.test_critical_errors

# Tests de arranque
python manage.py test tests.tenant.critical.test_startup_availability
```

### Ejecutar con verbosidad:
```bash
python manage.py test tests.tenant.critical -v 2
```

## ✅ Resultado Esperado

Al finalizar esta fase, el sistema:

✅ Soporta múltiples empresas sin fuga de datos  
✅ Permite alta y operación básica de tenants  
✅ Es estable para uso controlado (piloto / beta)  
✅ Está listo para despliegue inicial  

## 📌 Notas Importantes

- **No se incluyen:** Pruebas de carga, pruebas de estrés, cobertura completa de código, automatización CI/CD avanzada
- **Enfoque MVP:** Pruebas estratégicas de alto impacto
- **Herramientas:** pytest / pytest-django, django.test.TestCase, django-tenants test utilities

## 🔗 Referencias

- [django-tenants Testing](https://django-tenants.readthedocs.io/en/latest/testing.html)
- [Django Testing](https://docs.djangoproject.com/en/stable/topics/testing/)
- Arquitectura SINTEL: `documentacion/arquitectura_general.md`
