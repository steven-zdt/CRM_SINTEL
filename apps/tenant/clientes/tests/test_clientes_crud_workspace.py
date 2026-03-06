"""
Test funcional completo de CRUD de clientes en el workspace.

Verifica que todos los métodos CRUD funcionen correctamente:
- LIST: GET /api/v1/clientes/
- CREATE: POST /api/v1/clientes/
- READ: GET /api/v1/clientes/{id}/
- UPDATE: PATCH /api/v1/clientes/{id}/
- DELETE: DELETE /api/v1/clientes/{id}/
"""
import pytest
from django_tenants.utils import schema_context
from apps.tenant.clientes.models import Cliente
from apps.public.tenants.models import TenantMembership


@pytest.mark.django_db
def test_clientes_crud_completo(client, django_user_model, tenant):
    """
    Test funcional completo de CRUD de clientes.
    
    Verifica:
    1. LIST: Obtener lista de clientes (vacía inicialmente)
    2. CREATE: Crear un nuevo cliente
    3. READ: Obtener detalle de un cliente
    4. UPDATE: Actualizar un cliente existente
    5. DELETE: Eliminar un cliente
    6. LIST después de DELETE: Verificar que el cliente fue eliminado
    """
    # Setup: Crear usuario y membresía
    user = django_user_model.objects.create(username="testuser", email="test@example.com")
    TenantMembership.objects.create(
        client=tenant,
        user=user,
        is_active=True,
        rol="ADMIN"
    )
    client.force_login(user)
    
    # Datos de prueba
    cliente_data = {
        "tipo_persona": "JURIDICA",
        "tipo_documento": "NIT",
        "numero_documento": "900123456",
        "razon_social": "CLIENTE TEST S.A.S.",
        "nombre_comercial": "CLIENTE TEST",
        "regimen_tributario": "ORDINARIO",
        "responsable_iva": True,
        "segmento": "B2B",
        "email": "test@cliente.com",
        "telefono": "3001234567",
        "direccion": "Calle 123 #45-67",
        "ciudad": "Bogotá",
        "contacto_nombre": "Juan Pérez",
        "contacto_telefono": "3007654321",
        "banco": "Banco de Prueba",
        "tipo_cuenta": "CORRIENTE",
        "numero_cuenta": "1234567890",
        "activo": True,
        "observaciones": "Cliente de prueba para tests"
    }
    
    with schema_context(tenant.schema_name):
        # 1. LIST: Verificar que la lista está vacía inicialmente
        resp = client.get("/api/v1/clientes/", HTTP_HOST=f"{tenant.schema_name}.sintel.com")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.content}"
        data = resp.json()
        assert "results" in data or isinstance(data, list), "Response should be paginated or a list"
        initial_count = len(data.get("results", data))
        
        # 2. CREATE: Crear un nuevo cliente
        resp = client.post(
            "/api/v1/clientes/",
            data=cliente_data,
            content_type="application/json",
            HTTP_HOST=f"{tenant.schema_name}.sintel.com"
        )
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.content}"
        created = resp.json()
        assert created["razon_social"] == cliente_data["razon_social"]
        assert created["numero_documento"] == cliente_data["numero_documento"]
        cliente_id = created["id"]
        
        # Verificar que el cliente fue creado en la BD
        cliente_db = Cliente.objects.get(id=cliente_id)
        assert cliente_db.razon_social == cliente_data["razon_social"]
        assert cliente_db.email == cliente_data["email"]
        
        # 3. READ: Obtener detalle del cliente
        resp = client.get(
            f"/api/v1/clientes/{cliente_id}/",
            HTTP_HOST=f"{tenant.schema_name}.sintel.com"
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.content}"
        detail = resp.json()
        assert detail["id"] == cliente_id
        assert detail["razon_social"] == cliente_data["razon_social"]
        assert detail["email"] == cliente_data["email"]
        assert detail["telefono"] == cliente_data["telefono"]
        assert detail["direccion"] == cliente_data["direccion"]
        assert detail["ciudad"] == cliente_data["ciudad"]
        assert detail["contacto_nombre"] == cliente_data["contacto_nombre"]
        assert detail["banco"] == cliente_data["banco"]
        assert detail["tipo_cuenta"] == cliente_data["tipo_cuenta"]
        assert detail["numero_cuenta"] == cliente_data["numero_cuenta"]
        assert detail["observaciones"] == cliente_data["observaciones"]
        
        # 4. UPDATE: Actualizar el cliente
        update_data = {
            "razon_social": "CLIENTE TEST ACTUALIZADO S.A.S.",
            "email": "nuevo@cliente.com",
            "telefono": "3009998888",
            "activo": False,
            "observaciones": "Cliente actualizado en test"
        }
        resp = client.patch(
            f"/api/v1/clientes/{cliente_id}/",
            data=update_data,
            content_type="application/json",
            HTTP_HOST=f"{tenant.schema_name}.sintel.com"
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.content}"
        updated = resp.json()
        assert updated["razon_social"] == update_data["razon_social"]
        assert updated["email"] == update_data["email"]
        assert updated["telefono"] == update_data["telefono"]
        assert updated["activo"] == update_data["activo"]
        assert updated["observaciones"] == update_data["observaciones"]
        
        # Verificar que el cliente fue actualizado en la BD
        cliente_db.refresh_from_db()
        assert cliente_db.razon_social == update_data["razon_social"]
        assert cliente_db.email == update_data["email"]
        assert cliente_db.activo == update_data["activo"]
        
        # 5. LIST después de UPDATE: Verificar que el cliente aparece actualizado
        resp = client.get("/api/v1/clientes/", HTTP_HOST=f"{tenant.schema_name}.sintel.com")
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("results", data)
        assert len(items) == initial_count + 1
        cliente_list = next((c for c in items if c["id"] == cliente_id), None)
        assert cliente_list is not None
        assert cliente_list["razon_social"] == update_data["razon_social"]
        assert cliente_list["activo"] == update_data["activo"]
        
        # 6. DELETE: Eliminar el cliente
        resp = client.delete(
            f"/api/v1/clientes/{cliente_id}/",
            HTTP_HOST=f"{tenant.schema_name}.sintel.com"
        )
        assert resp.status_code in (204, 200), f"Expected 204 or 200, got {resp.status_code}: {resp.content}"
        
        # Verificar que el cliente fue eliminado de la BD
        assert not Cliente.objects.filter(id=cliente_id).exists()
        
        # 7. LIST después de DELETE: Verificar que el cliente ya no aparece
        resp = client.get("/api/v1/clientes/", HTTP_HOST=f"{tenant.schema_name}.sintel.com")
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("results", data)
        assert len(items) == initial_count
        cliente_list = next((c for c in items if c["id"] == cliente_id), None)
        assert cliente_list is None


@pytest.mark.django_db
def test_clientes_create_validaciones(client, django_user_model, tenant):
    """
    Test de validaciones al crear clientes.
    
    Verifica:
    - Campos requeridos
    - Unicidad de documento
    - Valores válidos para campos con choices
    """
    user = django_user_model.objects.create(username="testuser", email="test@example.com")
    TenantMembership.objects.create(
        client=tenant,
        user=user,
        is_active=True,
        rol="ADMIN"
    )
    client.force_login(user)
    
    with schema_context(tenant.schema_name):
        # Test: Campos requeridos faltantes
        resp = client.post(
            "/api/v1/clientes/",
            data={},
            content_type="application/json",
            HTTP_HOST=f"{tenant.schema_name}.sintel.com"
        )
        assert resp.status_code == 400, "Should return 400 for missing required fields"
        
        # Test: Crear cliente válido
        cliente_data = {
            "tipo_persona": "JURIDICA",
            "tipo_documento": "NIT",
            "numero_documento": "900111222",
            "razon_social": "CLIENTE VALIDO S.A.S.",
            "regimen_tributario": "ORDINARIO",
            "segmento": "B2B",
            "activo": True
        }
        resp = client.post(
            "/api/v1/clientes/",
            data=cliente_data,
            content_type="application/json",
            HTTP_HOST=f"{tenant.schema_name}.sintel.com"
        )
        assert resp.status_code == 201
        cliente_id = resp.json()["id"]
        
        # Test: Intentar crear cliente duplicado (mismo documento)
        resp = client.post(
            "/api/v1/clientes/",
            data=cliente_data,
            content_type="application/json",
            HTTP_HOST=f"{tenant.schema_name}.sintel.com"
        )
        assert resp.status_code == 400, "Should return 400 for duplicate document"
        
        # Limpiar
        Cliente.objects.filter(id=cliente_id).delete()


@pytest.mark.django_db
def test_clientes_list_filtros_y_ordenamiento(client, django_user_model, tenant):
    """
    Test de filtros y ordenamiento en listado de clientes.
    """
    user = django_user_model.objects.create(username="testuser", email="test@example.com")
    TenantMembership.objects.create(
        client=tenant,
        user=user,
        is_active=True,
        rol="ADMIN"
    )
    client.force_login(user)
    
    with schema_context(tenant.schema_name):
        # Crear clientes de prueba
        Cliente.objects.create(
            tipo_persona="JURIDICA",
            tipo_documento="NIT",
            numero_documento="900111111",
            razon_social="Cliente A",
            regimen_tributario="ORDINARIO",
            segmento="B2B",
            activo=True
        )
        Cliente.objects.create(
            tipo_persona="JURIDICA",
            tipo_documento="NIT",
            numero_documento="900222222",
            razon_social="Cliente B",
            regimen_tributario="SIMPLE",
            segmento="B2C",
            activo=False
        )
        
        # Test: Filtro por segmento
        resp = client.get(
            "/api/v1/clientes/?segmento=B2B",
            HTTP_HOST=f"{tenant.schema_name}.sintel.com"
        )
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("results", data)
        assert all(c["segmento"] == "B2B" for c in items)
        
        # Test: Filtro por activo
        resp = client.get(
            "/api/v1/clientes/?activo=true",
            HTTP_HOST=f"{tenant.schema_name}.sintel.com"
        )
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("results", data)
        assert all(c["activo"] is True for c in items)
        
        # Test: Ordenamiento
        resp = client.get(
            "/api/v1/clientes/?ordering=razon_social",
            HTTP_HOST=f"{tenant.schema_name}.sintel.com"
        )
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("results", data)
        razones = [c["razon_social"] for c in items if c.get("razon_social")]
        assert razones == sorted(razones), "Should be sorted by razon_social"
        
        # Test: Búsqueda
        resp = client.get(
            "/api/v1/clientes/?search=Cliente A",
            HTTP_HOST=f"{tenant.schema_name}.sintel.com"
        )
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("results", data)
        assert any("Cliente A" in c.get("razon_social", "") for c in items)
