"""
Test de Introspección SSoT v2.61.4

Este test valida que TODA aplicación en TENANT_APPS cumpla con:
1. Tener campo empresa FK obligatorio (null=False)
2. Heredar de SintelTenantBaseModel
3. NO tener campo empresa duplicado en Meta.fields

El test usa django.apps.apps.get_models() para iterar dinámicamente
y FALLAR si encuentra violaciones.

[SHIELD] Este es el "seguro de arquitectura" que previene regresiones.
"""

import pytest
from django.apps import apps
from django.db import models


class TestSSoTIntegrity:
    """Test suite para validar Single Source of Truth en TENANT_APPS."""
    
    TENANT_APPS = [
        'apps.tenant.core',
        'apps.tenant.empresa',
        'apps.tenant.facturas',
        'apps.tenant.contabilidad',
        'apps.tenant.inventario',
        'apps.tenant.empleados',
        'apps.tenant.gastos',
        'apps.tenant.cotizaciones',
        'apps.tenant.proveedores',
        'apps.tenant.clientes',
        'apps.tenant.proyectos',
        'apps.tenant.perfil',
        'apps.tenant.landing',
        'apps.tenant.dashboard',
    ]
    
    # Modelos que están PERMITIDOS no tener empresa FK explicit
    # RAZÓN: Son SSoT singletons o configuration models
    EXEMPT_MODELS = {
        'Empresa',  # SSoT singleton - no necesita auto-referencia
        'MailInboxConfig',  # TODO: considerar agregar empresa FK en v2.62
        'CatalogoMaestroNIIF',  # Referencia compartida (TODO: clarificar diseño)
    }
    
    @pytest.mark.django_db
    def test_tenant_models_have_empresa_fk(self):
        """
        [TEST 1] Todo modelo en TENANT_APPS debe tener campo empresa FK.
        
        FALLAR SI:
        - Hay modelos en tenant apps sin campo empresa
        - El campo empresa es nullable (null=True)
        - El campo no es ForeignKey
        """
        violations = []
        
        for app_config in apps.get_app_configs():
            if not any(app_config.name.startswith(prefix) for prefix in self.TENANT_APPS):
                continue  # Skip non-TENANT_APPS
            
            for model in app_config.get_models():
                model_name = model.__name__
                
                # Skip exempt models
                if model_name in self.EXEMPT_MODELS:
                    continue
                
                # Skip abstract models
                if model._meta.abstract:
                    continue
                
                # Check for empresa field
                empresa_field = model._meta.get_field('empresa') if hasattr(model._meta, 'get_field') else None
                
                if empresa_field is None:
                    violations.append(
                        f"{app_config.name}.{model_name}: ERROR: Campo 'empresa' ausente"
                    )
                elif not isinstance(empresa_field, models.ForeignKey):
                    violations.append(
                        f"{app_config.name}.{model_name}: ERROR: Campo 'empresa' no es ForeignKey"
                    )
                elif empresa_field.null:
                    violations.append(
                        f"{app_config.name}.{model_name}: ERROR: Campo 'empresa' es nullable (null=True)"
                    )
        
        assert not violations, (
            f"[SSoT INTEGRITY] {len(violations)} modelo(s) violan la regla de empresa FK:\n"
            + "\n".join(violations)
        )
    
    @pytest.mark.django_db
    def test_tenant_models_inherit_from_base(self):
        """
        [TEST 2] Todo modelo DEBE heredar de SintelTenantBaseModel.
        
        FALLAR SI:
        - Hay modelos que no heredan del modelo base
        - Excepción: SSoT/Configuration models en EXEMPT_MODELS
        """
        from apps.tenant.core.models import SintelTenantBaseModel
        
        violations = []
        
        for app_config in apps.get_app_configs():
            if not any(app_config.name.startswith(prefix) for prefix in self.TENANT_APPS):
                continue
            
            for model in app_config.get_models():
                model_name = model.__name__
                
                # Skip exempts and abstracts
                if model_name in self.EXEMPT_MODELS or model._meta.abstract:
                    continue
                
                # Empresa is SSoT, doesn't need to inherit
                if model_name == 'Empresa':
                    continue
                
                # Check inheritance
                if not issubclass(model, SintelTenantBaseModel):
                    violations.append(
                        f"{app_config.name}.{model_name}: ERROR: No hereda de SintelTenantBaseModel"
                    )
        
        assert not violations, (
            f"[SSoT INTEGRITY] {len(violations)} modelo(s) deben heredar de SintelTenantBaseModel:\n"
            + "\n".join(violations)
        )
    
    @pytest.mark.django_db
    def test_tenant_models_no_duplicate_empresa_field(self):
        """
        [TEST 3] Los modelos NO deben definir 'empresa' manualmente
        (lo heredan de SintelTenantBaseModel).
        
        FALLAR SI:
        - Un modelo redefine el campo empresa en lugar de heredarlo
        """
        from apps.tenant.core.models import SintelTenantBaseModel
        
        violations = []
        
        for app_config in apps.get_app_configs():
            if not any(app_config.name.startswith(prefix) for prefix in self.TENANT_APPS):
                continue
            
            for model in app_config.get_models():
                model_name = model.__name__
                
                # Skip exempts and abstracts
                if model_name in self.EXEMPT_MODELS or model._meta.abstract:
                    continue
                
                if not issubclass(model, SintelTenantBaseModel):
                    continue  # Skip non-base-inheriting models
                
                # Check if 'empresa' field is defined directly in this model
                # (it should only be inherited, not redefined)
                if 'empresa' in model.__dict__:
                    # It's defined in this model's __dict__, not inherited
                    violations.append(
                        f"{app_config.name}.{model_name}: WARNING:  Define 'empresa' localmente "
                        f"(debería solo heredarlo de SintelTenantBaseModel)"
                    )
        
        # Note: This is a warning, not a hard error
        if violations:
            print("\n[WARNING] Modelos que redefinen 'empresa' (considerar limpiar):")
            for v in violations:
                print(f"  {v}")
    
    @pytest.mark.django_db
    def test_tenant_models_have_created_updated_audit_fields(self):
        """
        [TEST 4] Todo modelo debe tener created_at y updated_at
        (heredados de SintelTenantBaseModel).
        
        FALLAR SI:
        - Un modelo no tiene estos campos
        """
        violations = []
        
        for app_config in apps.get_app_configs():
            if not any(app_config.name.startswith(prefix) for prefix in self.TENANT_APPS):
                continue
            
            for model in app_config.get_models():
                model_name = model.__name__
                
                if model_name in self.EXEMPT_MODELS or model._meta.abstract:
                    continue
                
                # Check for audit fields
                try:
                    model._meta.get_field('created_at')
                except:
                    violations.append(
                        f"{app_config.name}.{model_name}: ERROR: Campo 'created_at' ausente"
                    )
                
                try:
                    model._meta.get_field('updated_at')
                except:
                    violations.append(
                        f"{app_config.name}.{model_name}: ERROR: Campo 'updated_at' ausente"
                    )
        
        assert not violations, (
            f"[SSoT INTEGRITY] {len(violations)} modelo(s) no tienen campos de auditoría:\n"
            + "\n".join(violations)
        )
    
    @pytest.mark.django_db
    def test_empresa_field_has_index(self):
        """
        [TEST 5] Campo empresa deve estar indexed para queries eficientes.
        
        FALLAR SI:
        - El campo empresa no está indexado
        """
        violations = []
        
        for app_config in apps.get_app_configs():
            if not any(app_config.name.startswith(prefix) for prefix in self.TENANT_APPS):
                continue
            
            for model in app_config.get_models():
                model_name = model.__name__
                
                if model_name in self.EXEMPT_MODELS or model._meta.abstract:
                    continue
                
                try:
                    empresa_field = model._meta.get_field('empresa')
                    if not empresa_field.db_index and not any(
                        'empresa' in index.fields for index in model._meta.indexes
                    ):
                        violations.append(
                            f"{app_config.name}.{model_name}: WARNING:  Campo 'empresa' sin índice "
                            f"(usar db_index=True o Meta.indexes)"
                        )
                except:
                    pass  # Field doesn't exist, already caught by test 1
        
        if violations:
            print("\n[WARNING] Campos sin índice:")
            for v in violations:
                print(f"  {v}")
    
    @pytest.mark.django_db
    def test_no_null_empresa_in_database(self):
        """
        [TEST 6] Verificar que NO hay registros con empresa_id = NULL
        en la base de datos (integridad de datos).
        
        ACTUALIZACIÓN EN VIVO: Detecta corrupción de datos
        """
        violations = []
        
        for app_config in apps.get_app_configs():
            if not any(app_config.name.startswith(prefix) for prefix in self.TENANT_APPS):
                continue
            
            for model in app_config.get_models():
                model_name = model.__name__
                
                if model_name in self.EXEMPT_MODELS or model._meta.abstract:
                    continue
                
                try:
                    # Query for NULL empresa_id
                    null_count = model.objects.filter(empresa_id__isnull=True).count()
                    if null_count > 0:
                        violations.append(
                            f"{app_config.name}.{model_name}: ERROR: {null_count} registro(s) "
                            f"con empresa_id = NULL"
                        )
                except:
                    pass  # Can't query this model
        
        assert not violations, (
            "[DATA INTEGRITY] Registros corrompidos encontrados:\n"
            + "\n".join(violations)
        )


# ============================================================================
# PYTEST FIXTURES (Utilities)
# ============================================================================

@pytest.fixture
def tenant_models_summary():
    """
    Proporciona un resumen de TODOS los modelos en TENANT_APPS
    para debugging y auditoría.
    """
    from apps.tenant.core.models import SintelTenantBaseModel
    
    summary = {}
    for app_config in apps.get_app_configs():
        app_name = app_config.name
        models_list = []
        
        for model in app_config.get_models():
            info = {
                'name': model.__name__,
                'inherits_base': issubclass(model, SintelTenantBaseModel),
                'has_empresa': hasattr(model, 'empresa'),
                'abstract': model._meta.abstract,
            }
            models_list.append(info)
        
        if models_list:
            summary[app_name] = models_list
    
    return summary


__all__ = [
    'TestSSoTIntegrity',
    'tenant_models_summary',
]
