# TESTING_AGENT.md (v4.1) -- Protocolo de Testing Alineado con AGENTS.md

Este protocolo define el estandar de testing y QA autonomo para garantizar que toda creacion o refactorizacion cumpla estrictamente con la arquitectura SINTEL v2.61.8 establecida en `AGENTS.md`.

## [OBJETIVO]
Garantizar que ninguna creación o refactorización rompa el sistema y que cumpla estrictamente con la arquitectura de SINTEL. El agente debe ejecutar, observar, auditar código estático, fallar, corregir y repetir el ciclo hasta obtener un `test_summary = 100% PASS` y `0` violaciones arquitectónicas.

## [CONEXIÓN E INFRAESTRUCTURA]
- **Herramienta Core:** Utilizar las skills de `mcp_server_sintel.py` (ej. `expert_e2e_auditor`) para interactuar con los servicios Docker y el sistema de archivos.
- **Entorno:** Los tests se ejecutan dentro del contenedor `django_app` o `celery_worker` según corresponda.
- **Observabilidad:** - Terminal: `pytest path/to/app/` / `python manage.py test`.
    - Logs Docker: `docker logs -f sintel_app`.
    - DOM/Network: Verificar respuestas HTMX (OOB Swaps, HX-Triggers) y el payload JSON capturado por el DOM Shield.

## [FASE 1: SMOKE TESTS & COMPILACIÓN (Regla 0 y Direct Gateway)]
1. **Validación [CRITICAL] 0:** Ejecutar `python -m py_compile` en los archivos modificados. Si falla por caracteres especiales (emojis), abortar y corregir inmediatamente.
2. **Health Check Direct Gateway:** Verificar que los endpoints directos de la app (ej. `/tenant/<app_name>/api/`) respondan correctamente (200/403 según auth). **PROHIBIDO** testear a través de `/api/v1/...` (Facade legacy).

## [FASE 2: TESTING DE BACKEND Y SERVICE LAYER (E2E Arquitectónico)]
1. **Aislamiento Multi-Tenant (Zero-Trust):** Probar mediante tests automatizados que un usuario de la `Empresa A` recibe un 403 o 404 al intentar acceder/mutar un ID de la `Empresa B` (Regla SaaS-DEFENSE 13).
2. **Auditoria Service Layer:** - Verificar que los `ViewSets` no contengan logica de negocio (solo enrutamiento).
    - Ejecutar tests unitarios aislados contra `services/crud_service.py` y `services/business_service.py`.
    - Confirmar que las mutaciones Maestro-Detalle usen `@transaction.atomic`.
3. **Double Semantic Verification (Anti-IDOR):** Intentar un `POST/PATCH` enviando un `empresa_id` malicioso en el payload y confirmar que el `BusinessService` lo rechaza o lo sobrescribe de forma segura con `request.user.perfil.empresa`.
4. **Optimizacion de Queries (Zero Waste):** Escanear el codigo del `crud_service.py` para asegurar que no existan llamadas a `.all()` o `.filter()` sin encadenar explicitamente `.only()` o `.defer()`.
5. **IsTenantMember Obligatorio (Regla 15):** Verificar que TODOS los ViewSets que hereden de `BaseTenantViewSet` incluyan `IsTenantMember` en su `permission_classes`. Sin excepciones. Usar `audit_security` del MCP server para validacion automatizada.
6. **Aislamiento de Esquema Publico (Regla 17 - Bridge Isolation):**
    - Escanear imports en TODOS los archivos `.py` de apps tenant (excepto `core` y `api`).
    - **PROHIBIDO:** Cualquier `from apps.public` o `import apps.public` fuera de `apps/tenant/core/` y `apps/tenant/api/`.
    - **CORRECTO:** Usar `from apps.tenant.core.services.membership import ...` para acceder a datos del esquema publico.
    - Usar el tool `audit_bridge_isolation` del MCP server para deteccion automatizada.
    - Toda PR debe pasar con cero violaciones de bridge.

## [FASE 3: TESTING DE FRONTEND & INTEGRACIÓN (FSD y DOM Shield)]
1. **Validación de Rutas FSD:** Auditar que todos los estáticos y templates estén ubicados estrictamente en `apps/tenant/<app_name>/static/<app_name>/js/` y `apps/tenant/<app_name>/templates/<app_name>/`.
2. **DOM Shield Check:** Simular/verificar que el script `<modelo>_form.js` recolecta los datos correctamente, asegurando que los atributos `name` de los selectores visibles estén removidos y el payload use los inputs ocultos (previene mutación visual a texto).
3. **Reactividad HTMX y Tabulator:** Verificar que las respuestas exitosas del backend (200/201) emitan un encabezado `HX-Trigger` o un bloque `hx-swap-oob="true"` que actualice la tabla `#tabla-<modelo>` vía `table.replaceData()`.
4. **Normalización (Si aplica):** Enviar datos ruidosos o desnormalizados vía API y verificar que el backend o los mixins los guarden limpios (ej. mayúsculas, numéricos sin `NaN`).

## [FASE 4: CICLO DE CORRECCIÓN AUTÓNOMA (Loop)]
- **Si un Test o Regla falla:**
    1. Leer el Traceback desde el log de Docker o el error de sintaxis vía MCP.
    2. Clasificar el error (Violación de `AGENTS.md` vs Error Lógico de Python/JS).
    3. Aplicar la corrección usando las reglas SSoT (ej. si falta herencia, aplicar `SintelTenantBaseModel`).
    4. **NO REINICIAR DOCKER** a menos que implique cambios en variables de entorno o migraciones de BD (`makemigrations`/`migrate`); preferir la recarga en caliente (`hot-reload`).
    5. Re-ejecutar test.

## [FASE 5: REPORTE Y TRAZABILIDAD DOCUMENTAL]
Actualizar obligatoriamente el archivo central `AUDITORIA_FLUJO_COMPLETO.md` de la app modificada (`apps/tenant/<app_name>/AUDITORIA_FLUJO_COMPLETO.md`) con las siguientes secciones:
- `[PASSED]` Listado de tests unitarios, de integración y E2E exitosos.
- `[ARCH-CHECK]` Confirmación de que el flujo respeta el Service Layer y Gateway Directo.
- `[COVERAGE]` Confirmación de validación Anti-IDOR (Double Semantic Verification) aplicada a los endpoints evaluados.

## [CRITICAL] Regla 0: Validación de Caracteres Especiales

**PRIMERA VERIFICACIÓN OBLIGATORIA:**
```bash
# Validar compilación antes de cualquier test
python -m py_compile apps/tenant/<app_name>/models.py
python -m py_compile apps/tenant/<app_name>/services/*.py
python -m py_compile apps/tenant/<app_name>/api/*.py
```

- **ABORTAR** inmediatamente si hay emojis en archivos `.py`
- **ALCANCE**: `/apps/`, `/config/`, `/tests/`, `/tools/`, `/scripts/`
- **RAZÓN**: Los emojis causan `SyntaxError` y `500 Internal Server Error`

## [PHASE-1] Testing de Arquitectura Backend

### 1.1. **Verificación de Modelos (CORE-DB)**
```python
def test_modelo_herencia_sintel():
    """Verificar herencia de SintelTenantBaseModel"""
    from apps.tenant.<app_name>.models import <Modelo>
    from apps.tenant.core.models import SintelTenantBaseModel
    
    assert issubclass(<Modelo>, SintelTenantBaseModel)
    assert hasattr(<Modelo>, 'empresa_id')
```

### 1.2. **Testing de Service Layer Modular**
```python
def test_service_layer_estructura():
    """Verificar estructura modular obligatoria"""
    import os
    services_path = 'apps/tenant/<app_name>/services/'
    
    assert os.path.exists(f'{services_path}__init__.py')
    assert os.path.exists(f'{services_path}crud_service.py')
    assert os.path.exists(f'{services_path}business_service.py')
    assert os.path.exists(f'{services_path}services.py')

def test_business_service_stateless():
    """Verificar métodos stateless en business service"""
    from apps.tenant.<app_name>.services import <Modelo>Service
    
    # Todos los métodos deben ser @staticmethod o @classmethod
    for method_name in dir(<Modelo>Service):
        if not method_name.startswith('_'):
            method = getattr(<Modelo>Service, method_name)
            assert isinstance(method, (staticmethod, classmethod))
```

### 1.3. **Testing Zero-Trust y Multi-Tenant**
```python
def test_empresa_resolution_standard():
    """Verificar resolución estándar de empresa"""
    from django.test import RequestFactory
    from apps.tenant.<app_name>.api.viewsets import <Modelo>ViewSet
    
    factory = RequestFactory()
    request = factory.get('/')
    request.empresa = empresa_a
    
    viewset = <Modelo>ViewSet()
    empresa = viewset._resolve_empresa(request)
    
    assert empresa == empresa_a

def test_tenant_isolation():
    """Verificar aislamiento por tenant (Anti-IDOR)"""
    # Usuario de Empresa A intenta acceder a datos de Empresa B
    response = client_empresa_a.get(f'/api/v1/<app_name>/{objeto_empresa_b.id}/')
    assert response.status_code in [403, 404]

def test_double_semantic_verification():
    """Verificar DSV en mutaciones"""
    payload = {'nombre': 'test', 'empresa_id': empresa_b.id}  # Malicioso
    response = client_empresa_a.post('/api/v1/<app_name>/', payload)
    
    # El objeto debe crearse con empresa_a, no empresa_b
    objeto = <Modelo>.objects.get(nombre='test')
    assert objeto.empresa_id == empresa_a.id
```

### 1.4. **Testing de Queries Optimizadas (Zero Waste)**
```python
def test_queries_optimizadas():
    """Verificar uso obligatorio de .only() o .defer()"""
    from django.test.utils import override_settings
    from django.db import connection
    
    with override_settings(DEBUG=True):
        connection.queries_log.clear()
        
        # Ejecutar endpoint que debe usar .only()
        response = client.get('/api/v1/<app_name>/')
        
        # Verificar que las queries usen SELECT específico, no SELECT *
        for query in connection.queries:
            if '<tabla>' in query['sql']:
                assert 'SELECT *' not in query['sql']
```

## [PHASE-2] Testing de Gateway Directo

### 2.1. **Endpoints Directos por App**
```python
def test_gateway_directo():
    """Verificar endpoints directos sin facades"""
    # CORRECTO: Endpoint directo de la app
    response = client.get('/api/v1/<app_name>/')
    assert response.status_code == 200
    
    # PROHIBIDO: No debe existir facade centralizada
    # Los endpoints deben estar en la propia app

def test_basetenanviewset_herencia():
    """Verificar herencia de BaseTenantViewSet"""
    from apps.tenant.<app_name>.api.viewsets import <Modelo>ViewSet
    from apps.tenant.api.base import BaseTenantViewSet
    
    assert issubclass(<Modelo>ViewSet, BaseTenantViewSet)
```

### 2.2. **Testing de Paginación Estándar**
```python
def test_paginacion_standard():
    """Verificar StandardResultsSetPagination"""
    response = client.get('/api/v1/<app_name>/')
    data = response.json()
    
    assert 'results' in data
    assert 'count' in data
    assert 'next' in data
    assert 'previous' in data
```

## [PHASE-3] Testing de Frontend (Feature-Sliced Design)

### 3.1. **Verificación de Estructura FSD**
```python
def test_templates_fsd():
    """Verificar templates en ubicación correcta"""
    import os
    
    template_path = 'apps/tenant/<app_name>/templates/<app_name>/'
    assert os.path.exists(f'{template_path}list.html')
    assert os.path.exists(f'{template_path}offcanvas_crear_{modelo}.html')
    assert os.path.exists(f'{template_path}offcanvas_editar_{modelo}.html')
    assert os.path.exists(f'{template_path}offcanvas_detalle_{modelo}.html')

def test_javascript_namespace():
    """Verificar namespace JavaScript"""
    js_path = 'apps/tenant/<app_name>/static/<app_name>/js/'
    
    # Verificar archivos modulares
    assert os.path.exists(f'{js_path}<app_name>.main.js')
    assert os.path.exists(f'{js_path}<app_name>.api.js')
    assert os.path.exists(f'{js_path}<app_name>.table.js')
    assert os.path.exists(f'{js_path}<app_name>.ui.js')
```

### 3.2. **Testing DOM Shield**
```javascript
// Test en navegador/Selenium
function testDOMShield() {
    // Verificar que inputs visibles NO tengan atributo name
    const visibleInputs = document.querySelectorAll('input:not([type="hidden"])');
    visibleInputs.forEach(input => {
        assert(!input.hasAttribute('name'), 'Input visible tiene atributo name');
    });
    
    // Verificar que ForeignKeys viajen en hidden inputs
    const hiddenInputs = document.querySelectorAll('input[type="hidden"]');
    assert(hiddenInputs.length > 0, 'Faltan hidden inputs para ForeignKeys');
}
```

### 3.3. **Testing HTMX y Reactividad**
```python
def test_htmx_oob_swaps():
    """Verificar Out of Band Swaps"""
    response = client.post('/api/v1/<app_name>/', data, 
                          HTTP_HX_REQUEST='true')
    
    # Verificar headers HTMX
    assert 'HX-Trigger' in response or 'hx-swap-oob' in response.content.decode()

def test_tabulator_integration():
    """Verificar integración con Tabulator"""
    # Verificar que endpoint retorna formato esperado por Tabulator
    response = client.get('/api/v1/<app_name>/')
    data = response.json()
    
    assert 'results' in data
    # Verificar campos necesarios para tabla
    if data['results']:
        required_fields = ['id', 'nombre']  # Campos específicos
        for field in required_fields:
            assert field in data['results'][0]
```

## [PHASE-4] Testing de Seguridad Avanzada

### 4.1. **Ciberseguridad Defensiva (SaaS-DEFENSE)**
```python
def test_idor_prevention():
    """Testing exhaustivo Anti-IDOR"""
    # Crear objetos en diferentes empresas
    obj_a = <Modelo>.objects.create(empresa=empresa_a, nombre='test_a')
    obj_b = <Modelo>.objects.create(empresa=empresa_b, nombre='test_b')
    
    # Usuario A intenta acceder/modificar objeto B
    client.force_authenticate(user=user_empresa_a)
    
    # GET: Debe fallar
    response = client.get(f'/api/v1/<app_name>/{obj_b.id}/')
    assert response.status_code in [403, 404]
    
    # PUT: Debe fallar
    response = client.put(f'/api/v1/<app_name>/{obj_b.id}/', {'nombre': 'hack'})
    assert response.status_code in [403, 404]
    
    # DELETE: Debe fallar
    response = client.delete(f'/api/v1/<app_name>/{obj_b.id}/')
    assert response.status_code in [403, 404]

def test_payload_injection():
    """Testing inyección maliciosa en payload"""
    malicious_payload = {
        'nombre': 'test',
        'empresa_id': empresa_b.id,  # Intento de cambiar empresa
        'empresa': empresa_b.id      # Variante alternativa
    }
    
    response = client_empresa_a.post('/api/v1/<app_name>/', malicious_payload)
    
    if response.status_code == 201:
        obj = <Modelo>.objects.get(nombre='test')
        # Debe pertenecer a empresa_a, no empresa_b
        assert obj.empresa_id == empresa_a.id
```

### 4.2. **Testing de Transacciones Atómicas**
```python
def test_atomic_transactions():
    """Verificar @transaction.atomic en mutaciones"""
    from unittest.mock import patch
    
    # Simular fallo en medio de transacción
    with patch('<app_name>.services.crud_service.create_item', side_effect=Exception):
        with pytest.raises(Exception):
            <Modelo>Service.crear_con_items(empresa_a, data_with_items)
        
        # Verificar rollback: no debe existir objeto parcial
        assert <Modelo>.objects.filter(empresa=empresa_a).count() == 0
```

## [PHASE-5] Ciclo de Corrección Autónoma

### 5.1. **Detección y Clasificación de Errores**
```python
def classify_error(error_message):
    """Clasificar tipo de error para corrección automática"""
    if 'emoji' in error_message or 'SyntaxError' in error_message:
        return 'CRITICAL_RULE_0'
    elif 'SintelTenantBaseModel' in error_message:
        return 'MODEL_INHERITANCE'
    elif 'empresa_id' in error_message:
        return 'TENANT_ISOLATION'
    elif '.all()' in error_message or 'SELECT *' in error_message:
        return 'QUERY_OPTIMIZATION'
    else:
        return 'LOGIC_ERROR'
```

### 5.2. **Corrección Automática por Tipo**
```python
def auto_fix_by_type(error_type, file_path):
    """Aplicar corrección automática según tipo de error"""
    if error_type == 'MODEL_INHERITANCE':
        # Cambiar models.Model por SintelTenantBaseModel
        fix_model_inheritance(file_path)
    elif error_type == 'QUERY_OPTIMIZATION':
        # Agregar .only() a queries
        fix_query_optimization(file_path)
    # ... más correcciones automáticas
```

## [PHASE-6] Reporte y Documentación

### 6.1. **Actualización de Auditoría**
```markdown
# Estructura requerida en AUDITORIA_FLUJO_COMPLETO.md

## [TESTING-RESULTS] - Fecha: YYYY-MM-DD

### Backend Tests
- [✓] Herencia SintelTenantBaseModel
- [✓] Service Layer modular
- [✓] Zero-Trust Multi-Tenant
- [✓] Queries optimizadas (.only/.defer)
- [✓] Transacciones atómicas

### Frontend Tests  
- [✓] Feature-Sliced Design
- [✓] JavaScript namespace
- [✓] DOM Shield implementado
- [✓] HTMX integración

### Security Tests
- [✓] Anti-IDOR verificado
- [✓] Double Semantic Verification
- [✓] Tenant isolation confirmado

### Performance Tests
- [✓] Query optimization
- [✓] Pagination standard
- [✓] Asset loading optimized
```

## [CHECKLIST] Conformidad de Testing

### Compilación y Sintaxis
- [ ] Zero emojis en archivos `.py`
- [ ] `python -m py_compile` exitoso en todos los archivos
- [ ] Sin caracteres Unicode/multibyte en código

### Arquitectura Backend
- [ ] Modelos heredan de `SintelTenantBaseModel`
- [ ] Service Layer modular (mínimo 3 archivos)
- [ ] ViewSets con `_resolve_empresa()` estándar
- [ ] Queries con `.only()` o `.defer()`
- [ ] Transacciones atómicas en mutaciones

### Seguridad
- [ ] Anti-IDOR verificado exhaustivamente
- [ ] Double Semantic Verification implementada
- [ ] Tenant isolation confirmado
- [ ] Payload injection resistente
- [ ] IsTenantMember en TODOS los ViewSets (Regla 15)
- [ ] Bridge isolation: cero imports directos a `apps.public` fuera de `core/api` (Regla 17)

### Frontend
- [ ] Templates en ubicación FSD correcta
- [ ] JavaScript bajo namespace correcto
- [ ] DOM Shield funcionando
- [ ] HTMX OOB Swaps operativos

### Documentación
- [ ] `AUDITORIA_FLUJO_COMPLETO.md` actualizada
- [ ] Tests documentados con resultados
- [ ] Cobertura de seguridad confirmada

---

## [GOVERNANCE] Protocolo de Autorización

Para testing en `apps/tenant/`:
1. **Lectura previa** de `apps/tenant/<app_name>/AUDITORIA_INVENTARIO.md`
2. **Validación arquitectónica** antes de testing funcional
3. **Reporte obligatorio** de resultados en auditoría

---

*Referencia Suprema: AGENTS.md | SINTEL v2.61.8 | Testing SSoT*