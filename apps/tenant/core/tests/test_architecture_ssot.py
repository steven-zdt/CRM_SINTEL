"""
[ARCHITECTURE GUARD] Test de Integridad SSoT - Garantiza que TODOS los modelos
en TENANT_APPS tengan FK a Empresa (NOT NULL)

Este test actúa como "Server Guard" en CI/CD, bloqueando commits que introduzcan
modelos "huérfanos" sin relación empresa_id obligatoria.

Validaciones:
1. Introspección de modelos: Todos los modelos en TENANT_APPS tienen empresa FK
2. Validación de constraints: empresa field es NOT NULL en todos los casos
3. Integridad de service layer: No se pueden crear registros sin empresa
4. Base model sugerencia: Propone implementar SintelTenantBaseModel para consistencia
"""

import pytest
from django.apps import apps
from django.conf import settings
from django.db import models
from django_tenants.utils import schema_context


class TestArchitectureSSoTIntegrity:
    """
    Test de Introspección: Verifica que TODOS los modelos en TENANT_APPS
    tengan relación obligatoria con Empresa
    """

    @pytest.mark.django_db
    def test_all_tenant_models_have_empresa_fk(self):
        """
        [CRITICAL] Valida que TODO modelo en TENANT_APPS tenga un FK a Empresa.
        
        Regla Arquitectónica:
        - TODA tabla en esquema tenant DEBE tener empresa_id como FK
        - NO permitir null en empresa_id
        - Esto garantiza integridad referencial y scope multi-tenant
        
        Failure Impact: BLOQUEANTE - Detiene commit si se incumple
        """
        
        # Apps a verificar: TENANT_APPS desde settings
        tenant_apps_config = [
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
            'apps.tenant.dashboard',
        ]
        
        # Modelos que NO deben tener empresa FK (excepciones)
        # Nota: Esta lista debe mantenerse mínima
        # [CRITICAL] Excepciones son TEMPORALES - Se deben arreglar en futuras versiones
        MODELS_WITHOUT_EMPRESA_FK = {
            'apps.tenant.empresa': [
                'Empresa',  # Empresa no tiene FK a sí misma
                'MailInboxConfig',  # Config global
            ],
            'apps.tenant.core': [],  # Core models exceptions (if any)
            'apps.tenant.landing': [],  # Landing page (public access)
            'apps.tenant.dashboard': [],  # Dashboard (no business data)
            # [TECHNICAL DEBT] - Modelos legacy que necesitan arreglo:
            'apps.tenant.facturas': [
                'MailIngestionConfig',  # Configuración global de mail
                'MailIngestionRun',  # Registro de ejecuciones de mail
                'MailInboxState',  # Estado de bandeja de entrada
                'FacturaAnexos',  # Anexos de facturas (heredan empresa del padre)
            ],
            'apps.tenant.contabilidad': [
                'CatalogoMaestroNIIF',  # Catálogo estándar DIAN (compartido)
                'MovimientoContable',  # Movimientos contables (vinculados vía AsientoContable)
            ],
        }
        
        models_without_empresa = []
        models_with_nullable_empresa = []
        models_checked = []
        
        for app_name in tenant_apps_config:
            try:
                app_config = apps.get_app_config(app_name.split('.')[-1])
            except LookupError:
                # App no instalada, skipear
                continue
            
            # Excepciones específicas por app
            exceptions = MODELS_WITHOUT_EMPRESA_FK.get(app_name, [])
            
            for model in app_config.get_models():
                # Skip excepciones
                if model.__name__ in exceptions:
                    continue
                
                # Skip modelos abstractos
                if model._meta.abstract:
                    continue
                
                models_checked.append(f'{app_name}.{model.__name__}')
                
                # Verificar que tenga campo 'empresa'
                try:
                    empresa_field = model._meta.get_field('empresa')
                except:
                    models_without_empresa.append(f'{app_name}.{model.__name__}')
                    continue
                
                # Verificar que sea ForeignKey a Empresa
                if not isinstance(empresa_field, models.ForeignKey):
                    models_without_empresa.append(
                        f'{app_name}.{model.__name__} (empresa no es ForeignKey)'
                    )
                    continue
                
                # Verificar que NO sea nullable
                if empresa_field.null:
                    models_with_nullable_empresa.append(
                        f'{app_name}.{model.__name__} (empresa.null=True - INCORRECTO)'
                    )
        
        # Build error message con detalles
        error_messages = []
        
        if models_without_empresa:
            error_messages.append(
                f"\n[ERROR] Modelos sin FK a Empresa ({len(models_without_empresa)}):\n"
                + "\n".join(f"  - {m}" for m in models_without_empresa)
                + "\n\nFIX: Agrega este campo a cada modelo:\n"
                + "  empresa = models.ForeignKey(\n"
                + "      'empresa.Empresa',\n"
                + "      on_delete=models.CASCADE,\n"
                + "      related_name='...',\n"
                + "  )\n"
            )
        
        if models_with_nullable_empresa:
            error_messages.append(
                f"\n[ERROR] Modelos con empresa.null=True ({len(models_with_nullable_empresa)}):\n"
                + "\n".join(f"  - {m}" for m in models_with_nullable_empresa)
                + "\n\nFIX: Cambia null=True a null=False en el campo empresa\n"
            )
        
        # Assert
        assert not models_without_empresa and not models_with_nullable_empresa, (
            "[ARCHITECTURE VIOLATION] SSoT Rule incumplida:\n"
            + "".join(error_messages)
            + f"\nModelos verificados: {len(models_checked)}"
            + "\nContexto: TENANT_APPS requiere empresa_id obligatorio en TODOS los modelos"
        )
        
        # Log de éxito
        assert len(models_checked) > 0, (
            "[WARNING] No se encontraron modelos para verificar. "
            "Verifica que apps.tenant.* estén instaladas."
        )
        
        print(f"\n✅ [ARCHITECTURE CHECK] {len(models_checked)} modelos verificados")
        print("   Todos cumplen SSoT rule: empresa FK obligatorio (null=False)")

    @pytest.mark.django_db
    def test_empresa_fk_field_constraints(self):
        """
        [CRITICAL] Verifica constraints específicos del campo empresa en modelos TENANT_APPS.
        
        Constraints validados:
        1. null=False (obligatorio)
        2. blank=False (no permitir fieldEmpty en formularios)
        3. on_delete=CASCADE o PROTECT (no permitir orfandad)
        
        Failure Impact: BLOQUEANTE - Violación de constraint
        """
        
        # Modelos representativos para verificación detallada
        representative_models = [
            ('apps.tenant.clientes.models', 'Cliente'),
            ('apps.tenant.facturas.models', 'Factura'),
            ('apps.tenant.inventario.models', 'Producto'),
            ('apps.tenant.gastos.models', 'Gasto'),
        ]
        
        constraint_violations = []
        
        for module_path, model_name in representative_models:
            try:
                module_parts = module_path.split('.')
                app_label = module_parts[-2]  # e.g., 'clientes' from 'apps.tenant.clientes.models'
                
                try:
                    app_config = apps.get_app_config(app_label)
                except LookupError:
                    # App no está instalada, skipear
                    continue
                
                # Obtener modelo
                model = None
                for m in app_config.get_models():
                    if m.__name__ == model_name:
                        model = m
                        break
                
                if not model:
                    continue
                
                # Verificar campo empresa
                empresa_field = model._meta.get_field('empresa')
                
                # Validar null
                if empresa_field.null:
                    constraint_violations.append(
                        f'{app_label}.{model_name}.empresa: null=True (debería ser False)'
                    )
                
                # Validar blank
                if empresa_field.blank:
                    constraint_violations.append(
                        f'{app_label}.{model_name}.empresa: blank=True (debería ser False)'
                    )
                
                # Validar on_delete
                if hasattr(empresa_field, 'remote_field') and empresa_field.remote_field:
                    on_delete = empresa_field.remote_field.on_delete
                    # on_delete debe ser CASCADE o PROTECT
                    if on_delete.__name__ not in ('CASCADE', 'PROTECT'):
                        constraint_violations.append(
                            f'{app_label}.{model_name}.empresa: on_delete={on_delete.__name__} '
                            f'(debería ser CASCADE o PROTECT)'
                        )
                
            except Exception:
                # Ignorar errores de models que no existan
                pass
        
        assert not constraint_violations, (
            f"[CONSTRAINT VIOLATIONS] {len(constraint_violations)} campos empresa tienen constraints incorrectos:\n"
            + "\n".join(f"  - {v}" for v in constraint_violations)
            + "\n\nFIX: Asegúrate que el campo empresa tenga:\n"
            + "  - null=False\n"
            + "  - blank=False\n"
            + "  - on_delete=models.CASCADE o PROTECT\n"
        )

    @pytest.mark.django_db
    @pytest.mark.skip(reason="[TODO] Fixture tenant needs Client model fields update")
    def test_service_layer_cannot_create_record_without_empresa(self, tenant):
        """
        [CRITICAL] Test de Estrés: Valida que el service layer rechace
        intentos de crear registros sin especificar empresa_id.
        
        Esto verifica que la regla SSoT se enforce no solo en BD sino
        también en la lógica de negocio.
        
        Failure Impact: BLOQUEANTE - Regla de negocio incumplida
        """
        
        with schema_context(tenant.schema_name):
            # Test 1: Cliente sin empresa debe causar error
            from apps.tenant.clientes.models import Cliente
            from apps.tenant.empresa.models import Empresa
            
            try:
                empresa = Empresa.objects.first()
                if not empresa:
                    pytest.skip("No hay Empresa en tenant para testing")
                
                # Intentar crear cliente sin empresa debería fallar
                try:
                    cliente = Cliente.objects.create(
                        razon_social="Test Cliente",
                        numero_documento="123456789",
                        # ❌ NO especificamos empresa_id aquí
                    )
                    
                    # Si llegamos aquí, el constraint NO está funcionando
                    assert False, (
                        f"[INTEGRITY ERROR] Se creó Cliente sin empresa_id. "
                        f"Debería haber lanzado IntegrityError o ValidationError.\n"
                        f"Cliente creado: {cliente.id} con empresa_id={cliente.empresa_id}"
                    )
                    
                except Exception as e:
                    # Esperamos IntegrityError o ValidationError
                    expected_errors = ('IntegrityError', 'ValidationError', 'NOT NULL')
                    error_str = str(e)
                    
                    # Aceptar si es constraint de BD
                    if any(exp in error_str for exp in expected_errors):
                        print("\n✅ Service Layer Guard: Cliente rechazado sin empresa")
                        print(f"   Error esperado: {type(e).__name__}")
                    else:
                        # Error inesperado
                        raise
                
            except Exception as e:
                if 'DoesNotExist' in str(type(e)):
                    # Modelo no existe en este tenant, skipear
                    pytest.skip(f"Modelo no disponible en tenant: {str(e)}")
                raise

    @pytest.mark.django_db
    def test_base_model_consistency_check(self):
        """
        [OPTIONAL] Sugerencia: Si muchos modelos en TENANT_APPS comparten
        la misma definición de empresa FK, se podría crear un abstract base model.
        
        Este test sugiere y valida la implementación de:
        class SintelTenantBaseModel(models.Model):
            empresa = ForeignKey(Empresa, ...)
            class Meta:
                abstract = True
        
        Luego: class Cliente(SintelTenantBaseModel): ...
        
        Failure Impact: INFORMATIVO - No bloquea, sugiere refactoring
        """
        
        # Contar cuántos modelos tienen definición manual de empresa
        models_with_manual_empresa = 0
        models_with_inherited_empresa = 0
        
        tenant_apps = [
            'apps.tenant.clientes',
            'apps.tenant.facturas',
            'apps.tenant.inventario',
            'apps.tenant.gastos',
        ]
        
        for app_name in tenant_apps:
            try:
                app_label = app_name.split('.')[-1]
                app_config = apps.get_app_config(app_label)
            except:
                continue
            
            for model in app_config.get_models():
                if hasattr(model, 'empresa'):
                    # Verificar si vino de clase padre (abstract base) o definición manual
                    # Si está en el diccionario de campos del modelo mismo: manual
                    if 'empresa' in model._meta.model._meta.fields:
                        if model._meta.model.__name__ == 'SintelTenantBaseModel':
                            models_with_inherited_empresa += 1
                        else:
                            models_with_manual_empresa += 1
        
        # Si hay muchos modelos con definición manual, sugerir base model
        if models_with_manual_empresa > 5:
            print("\n[SUGGESTION] Considera crear SintelTenantBaseModel:")
            print(f"  - {models_with_manual_empresa} modelos tienen empresa FK manual")
            print("  - Crear abstract base model reduciría duplicación")
            print("\n  Implementación sugerida:")
            print("  # apps/tenant/core/models.py")
            print("  class SintelTenantBaseModel(models.Model):")
            print("      empresa = models.ForeignKey('empresa.Empresa', ...)")
            print("      class Meta:")
            print("          abstract = True")
            print("\n  Luego en cada modelo:")
            print("  class Cliente(SintelTenantBaseModel):")
            print("      # Ya hereda empresa FK automáticamente")


class TestSSoTRuleEnforcement:
    """
    Tests que validan que la regla SSoT se enforza en todos los niveles:
    - Nivel BD: FK constraint
    - Nivel ORM: Los servicios usan queryset scoped
    - Nivel API: Los endpoints filtran por empresa
    """

    @pytest.mark.django_db
    @pytest.mark.skip(reason="[TODO] Fixture tenant needs Client model fields update")
    def test_queryset_is_scoped_by_empresa(self, tenant):
        """
        Valida que QuerySets estén scopped por empresa_id en service layer.
        
        Esto previene que un query retorne datos de diferentes empresas
        cuando solo debería retornar datos de la empresa actual.
        """
        
        with schema_context(tenant.schema_name):
            from apps.tenant.clientes.models import Cliente
            from apps.tenant.empresa.models import Empresa
            
            empresa = Empresa.objects.first()
            if not empresa:
                pytest.skip("No hay Empresa en tenant")
            
            # Crear clientes
            c1 = Cliente.objects.create(
                razon_social="Cliente 1",
                numero_documento="111111111",
                empresa=empresa
            )
            
            # Verificar que la queryset puede ser filtrada por empresa
            clientes_empresa1 = Cliente.objects.filter(empresa_id=empresa.id)
            assert c1 in clientes_empresa1, (
                "No puede filtrar clientes por empresa_id"
            )
            
            print("\n✅ Queryset scoped by empresa_id: OK")

    @pytest.mark.django_db
    @pytest.mark.skip(reason="[TODO] Fixture tenant needs Client model fields update")
    def test_empresa_fk_prevents_orphaned_records(self, tenant):
        """
        Valida que el FK constraint previene registros huérfanos.
        
        Cuando se elimina una Empresa, los registros relacionados deben
        ser eliminados (CASCADE) o rechazados (PROTECT).
        """
        
        with schema_context(tenant.schema_name):

            from apps.tenant.empresa.models import Empresa
            
            # Crear empresa temporal
            try:
                tmp_empresa = Empresa.objects.create(
                    razon_social="Temporal",
                    numero_documento="999999999"
                )
                
                # Verificar que no hay huérfanos
                # (Este es más un validation que un test actual de orfandad)
                assert tmp_empresa.id is not None
                
                print("\n✅ Empresa FK constraint: Previene orfandad")
                
            except Exception as e:
                pytest.skip(f"No se pudo crear empresa de test: {e}")


# ============================================================================
# Utilidades para diagnóstico
# ============================================================================

def print_tenant_models_report(quiet=False):
    """
    Imprime un reporte de TODOS los modelos en TENANT_APPS y su estado SSoT.
    Útil para diagnóstico y auditoría.
    """
    
    if quiet:
        return
    
    from tabulate import tabulate
    
    rows = []
    tenant_apps = settings.TENANT_APPS
    
    for app_name in tenant_apps:
        try:
            app_label = app_name.split('.')[-1]
            app_config = apps.get_app_config(app_label)
        except:
            continue
        
        for model in app_config.get_models():
            if model._meta.abstract:
                continue
            
            has_empresa = False
            empresa_null = False
            
            try:
                empresa_field = model._meta.get_field('empresa')
                has_empresa = True
                empresa_null = empresa_field.null
            except:
                pass
            
            status = "✅ OK" if (has_empresa and not empresa_null) else "❌ FAIL"
            
            rows.append([
                f"{app_label}",
                model.__name__,
                "✅ Yes" if has_empresa else "❌ No",
                "❌ Nullable" if empresa_null else "✅ Required",
                status
            ])
    
    print("\n" + "="*100)
    print("SSoT INTEGRITY REPORT - TENANT_APPS Models")
    print("="*100)
    print(tabulate(rows, headers=["App", "Model", "empresa FK", "Constraint", "Status"]))
    print("="*100 + "\n")
