"""
Admin Site aislado para Tenants Privados.

Este módulo crea un Admin Site personalizado que SOLO muestra modelos
pertenecientes a TENANT_APPS, eliminando cualquier rastro de la administración pública.

# WARNING: IMPORTANTE: Este admin site es completamente independiente del admin global.
Los modelos del esquema público (Client, Domain, etc.) NO aparecerán aquí.
"""
from django.apps import apps
from django.conf import settings
from django.contrib import admin


class TenantAdminSite(admin.AdminSite):
    """
    Admin Site personalizado para tenants privados.
    
    Solo muestra modelos pertenecientes a TENANT_APPS, garantizando
    el aislamiento completo de la administración pública.
    """
    site_header = "Administración de la Empresa"
    site_title = "Portal de Empresa"
    index_title = "Gestión del Tenant"
    
    def has_permission(self, request):
        """
        Validación extra: Solo usuarios activos y staff pueden acceder.
        
        # WARNING: IMPORTANTE: Esta validación es adicional a la verificación de membresía
        que se hace en el middleware o en las vistas del dashboard.
        """
        return request.user.is_active and request.user.is_staff
    
    def index(self, request, extra_context=None):
        """
        # WARNING: v3.3: Sobrescribir index para manejar ProgrammingError cuando se intenta
        contar objetos de modelos de tenant en el esquema público.
        """
        from django.db import connection
        from django.db.utils import OperationalError, ProgrammingError
        from django_tenants.utils import get_public_schema_name
        
        try:
            return super().index(request, extra_context)
        except (ProgrammingError, OperationalError) as e:
            # Si hay error de tabla no existente, filtrar modelos problemáticos
            error_msg = str(e).lower()
            if 'does not exist' in error_msg or 'relation' in error_msg:
                # Estamos en el esquema público y hay modelos de tenant registrados
                # Filtrar modelos de tenant del contexto
                current_schema = getattr(connection, 'schema_name', None)
                public_schema = get_public_schema_name()
                
                if current_schema == public_schema:
                    # Reintentar sin modelos de tenant
                    context = self.each_context(request)
                    context.update(extra_context or {})
                    
                    # Filtrar modelos que no deberían estar en el esquema público
                    app_list = []
                    for app_config in apps.get_app_configs():
                        app_label = app_config.label
                        # Solo incluir apps que NO están en TENANT_APPS
                        if app_label not in [app.split('.')[-1] for app in settings.TENANT_APPS]:
                            models = []
                            for model in app_config.get_models():
                                if model in self._registry:
                                    model_admin = self._registry[model]
                                    if model_admin.has_module_permission(request):
                                        try:
                                            # Intentar obtener el conteo de forma segura
                                            count = model_admin.get_queryset(request).count()
                                        except (ProgrammingError, OperationalError):
                                            # Si falla, omitir este modelo
                                            continue
                                        except Exception:
                                            # Si hay otro error, omitir este modelo
                                            continue
                                        
                                        models.append({
                                            'name': model.__name__,
                                            'object_name': model.__name__,
                                            'perms': {
                                                'add': model_admin.has_add_permission(request),
                                                'change': model_admin.has_change_permission(request),
                                                'delete': model_admin.has_delete_permission(request),
                                                'view': model_admin.has_view_permission(request),
                                            },
                                            'admin_url': None,
                                            'add_url': None,
                                            'view_only': False,
                                        })
                            
                            if models:
                                app_list.append({
                                    'name': app_config.verbose_name,
                                    'app_label': app_label,
                                    'app_url': None,
                                    'has_module_permission': True,
                                    'models': models,
                                })
                    
                    context['app_list'] = app_list
                    return self.template_response(request, self.index_template or 'admin/index.html', context)
            
            # Si no es el esquema público, re-lanzar el error
            raise


# Instancia aislada del Admin para Tenants
tenant_admin_site = TenantAdminSite(name='tenant_admin')


def register_tenant_apps():
    """
    Copia los modelos registrados en el admin global (admin.site)
    hacia tenant_admin_site, PERO SOLO si pertenecen a una app de TENANT_APPS.
    
    # WARNING: IMPORTANTE: Esta función se ejecuta al importar este módulo.
    Filtra automáticamente los modelos del esquema público (Client, Domain, etc.)
    y solo registra modelos de apps de tenant (Empresa, Factura, AsientoContable, etc.).
    """
    # 1. Obtener etiquetas de apps permitidas
    # settings.TENANT_APPS tiene formato: ['apps.tenant.empresa', 'apps.tenant.facturas', ...]
    tenant_app_labels = set()
    
    for app_path in settings.TENANT_APPS:
        # Extraer el label de la app (última parte del path)
        # Ej: 'apps.tenant.empresa' -> 'empresa'
        app_label = app_path.split('.')[-1]
        tenant_app_labels.add(app_label)
    
    # También agregar apps de Django contrib que están en TENANT_APPS
    # (aunque normalmente no hay, por si acaso)
    for app_path in settings.TENANT_APPS:
        if app_path.startswith('django.contrib.'):
            # Para apps de Django contrib, el label es diferente
            # Ej: 'django.contrib.admin' -> 'admin'
            parts = app_path.split('.')
            if len(parts) >= 3:
                tenant_app_labels.add(parts[-1])
    
    # 2. Iterar sobre el registro global del admin
    registered_count = 0
    for model, model_admin in admin.site._registry.items():
        # 3. Filtrar: ¿El modelo pertenece a una app de tenant?
        app_label = model._meta.app_label
        
        if app_label in tenant_app_labels:
            # 4. Registrar en nuestro sitio aislado (si no está ya registrado)
            if not tenant_admin_site.is_registered(model):
                # Usamos la misma clase ModelAdmin que ya se definió
                # Esto copia la configuración (list_display, fieldsets, etc.)
                try:
                    # Crear una nueva instancia del ModelAdmin para evitar problemas
                    # con la instancia compartida del admin global
                    admin_class = model_admin.__class__
                    tenant_admin_site.register(model, admin_class)
                    registered_count += 1
                except admin.sites.AlreadyRegistered:
                    # Si ya está registrado, ignorar (no debería pasar)
                    pass
                except Exception as e:
                    # Loggear errores pero continuar
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Error al registrar {model.__name__} en tenant_admin_site: {e}")
    
    return registered_count


def ensure_tenant_apps_registered():
    """
    Asegura que los modelos de tenant estén registrados en tenant_admin_site.
    
    Esta función puede ser llamada múltiples veces de forma segura.
    Útil para ejecutar después de que todos los admin.py se hayan cargado.
    """
    try:
        register_tenant_apps()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error al registrar apps de tenant en admin aislado: {e}")


# Ejecutar el filtrado al importar este módulo
# # WARNING: IMPORTANTE: Esto se ejecuta cuando Django carga este módulo.
# Si algunos modelos aún no están registrados en admin.site, se registrarán
# cuando se importen sus respectivos admin.py.
# 
# Para asegurar que todos los modelos se registren, también podemos usar
# AppConfig.ready() en apps/tenant/core/apps.py
ensure_tenant_apps_registered()


def _is_tenant_model(model):
    """
    # WARNING: v3.3: Helper para verificar si un modelo pertenece a TENANT_APPS.
    
    Esta función es crítica para el monkey patch: solo filtra modelos de tenant,
    NO silencia errores legítimos en tablas que sí deberían estar en el esquema público.
    """
    app_label = model._meta.app_label
    tenant_app_labels = {app.split('.')[-1] for app in settings.TENANT_APPS}
    return app_label in tenant_app_labels


# # WARNING: v3.3: Monkey patch para el AdminSite global
# Esto previene ProgrammingError cuando se intenta contar objetos de modelos de tenant
# en el esquema público, PERO solo filtra modelos de TENANT_APPS para no silenciar errores legítimos
def _safe_index(self, request, extra_context=None):
    """
    # WARNING: v3.3: Versión segura de index() que captura ProgrammingError
    cuando se intenta contar objetos de modelos de tenant en el esquema público.
    
    SEGURIDAD: Solo filtra modelos de TENANT_APPS. No silencia errores legítimos
    en tablas que sí deberían estar en el esquema público (como Client/Tenant).
    """
    from django.db import connection
    from django.db.utils import OperationalError, ProgrammingError
    from django_tenants.utils import get_public_schema_name
    
    try:
        # Intentar ejecutar el método original
        return admin.AdminSite.index(self, request, extra_context)
    except (ProgrammingError, OperationalError) as e:
        # Si hay error de tabla no existente, verificar si estamos en el esquema público
        error_msg = str(e).lower()
        if 'does not exist' in error_msg or 'relation' in error_msg:
            current_schema = getattr(connection, 'schema_name', None)
            public_schema = get_public_schema_name()
            
            if current_schema == public_schema:
                # Estamos en el esquema público y hay modelos de tenant registrados
                # Filtrar SOLO modelos de tenant del contexto (no silenciar errores legítimos)
                context = self.each_context(request)
                context.update(extra_context or {})
                
                # # WARNING: CRÍTICO: Filtrar SOLO modelos de TENANT_APPS
                # Esto previene silenciar errores legítimos en tablas públicas (Client, Domain, etc.)
                app_list = []
                tenant_app_labels = {app.split('.')[-1] for app in settings.TENANT_APPS}
                
                for app_config in apps.get_app_configs():
                    app_label = app_config.label
                    # Solo incluir apps que NO están en TENANT_APPS
                    if app_label not in tenant_app_labels:
                        models = []
                        for model in app_config.get_models():
                            if model in self._registry:
                                model_admin = self._registry[model]
                                
                                # # WARNING: VALIDACIÓN ADICIONAL: Verificar que NO es un modelo de tenant
                                # Esto es una doble verificación de seguridad
                                if _is_tenant_model(model):
                                    # Si es un modelo de tenant, omitirlo (no debería estar aquí)
                                    continue
                                
                                if model_admin.has_module_permission(request):
                                    try:
                                        # Intentar obtener el conteo de forma segura
                                        count = model_admin.get_queryset(request).count()
                                    except (ProgrammingError, OperationalError) as inner_e:
                                        # # WARNING: Si falla, verificar si es un modelo de tenant
                                        # Si NO es de tenant, re-lanzar el error (no silenciar errores legítimos)
                                        if _is_tenant_model(model):
                                            # Es un modelo de tenant, omitirlo
                                            continue
                                        else:
                                            # NO es un modelo de tenant, re-lanzar el error
                                            raise inner_e
                                    except Exception:
                                        # Si hay otro error, omitir este modelo (fallback seguro)
                                        continue
                                    
                                    models.append({
                                        'name': model.__name__,
                                        'object_name': model.__name__,
                                        'perms': {
                                            'add': model_admin.has_add_permission(request),
                                            'change': model_admin.has_change_permission(request),
                                            'delete': model_admin.has_delete_permission(request),
                                            'view': model_admin.has_view_permission(request),
                                        },
                                        'admin_url': None,
                                        'add_url': None,
                                        'view_only': False,
                                    })
                        
                        if models:
                            app_list.append({
                                'name': app_config.verbose_name,
                                'app_label': app_label,
                                'app_url': None,
                                'has_module_permission': True,
                                'models': models,
                            })
                
                context['app_list'] = app_list
                return self.template_response(request, self.index_template or 'admin/index.html', context)
        
        # Si no es el esquema público, re-lanzar el error (no silenciar errores legítimos)
        raise

# # WARNING: v3.3: Aplicar el monkey patch solo si no se ha aplicado ya
if not hasattr(admin.site, '_safe_index_applied'):
    admin.site.index = _safe_index.__get__(admin.site, admin.AdminSite)
    admin.site._safe_index_applied = True
