import logging

from django.contrib import admin
from django.db import transaction
from django_tenants.utils import get_public_schema_name

from apps.public.tenants.forms import ClientAdminForm
from apps.public.tenants.services.deletion_service import hard_delete_tenant

from .models import Client, Domain, TenantMembership


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    """
    Admin personalizado para el modelo Client (Tenant).

    [WARNING] APROVISIONAMIENTO AUTOMÁTICO:
    - Permite seleccionar un usuario propietario al crear el tenant
    - Crea automáticamente la TenantMembership con rol ADMIN
    - Asigna is_primary_admin=True al usuario seleccionado
    """

    form = ClientAdminForm

    list_display = (
        "nombre",
        "schema_name",
        "get_owner",
        "paid_until",
        "on_trial",
        "is_active",
        "created_on",
    )
    list_filter = ("on_trial", "is_active", "created_on")
    search_fields = ("nombre", "schema_name")

    fieldsets = (
        (
            "Información del Tenant",
            {
                "fields": (
                    "nombre",
                    "schema_name",
                    "is_active",
                    "on_trial",
                    "paid_until",
                    "created_on",
                )
            },
        ),
        (
            "Aprovisionamiento",
            {
                "fields": ("admin_user",),
                "description": "Seleccione el usuario global que será el administrador principal de este tenant. "
                "Este usuario tendrá acceso completo al tenant con rol ADMIN.",
            },
        ),
    )

    readonly_fields = ("created_on",)

    def get_owner(self, obj):
        """
        Muestra el email del usuario propietario (admin principal) del tenant.

        Busca la TenantMembership con is_primary_admin=True para este cliente
        y retorna el email del usuario, o un guion "-" si no existe.
        """
        try:
            membership = TenantMembership.objects.filter(client=obj, is_primary_admin=True).first()

            if membership:
                return membership.user.email
            else:
                return "-"
        except Exception:
            return "-"

    get_owner.short_description = "Usuario Propietario"
    get_owner.admin_order_field = "memberships__user__email"

    def save_model(self, request, obj, form, change):
        """
        Guarda el modelo Client y crea automáticamente la TenantMembership.

        [WARNING] APROVISIONAMIENTO ATÓMICO:
        - Usa transaction.atomic() para garantizar que si falla la creación de Membership,
          el Client también se revierte (rollback completo).
        - Esto previene tenants "huérfanos" sin administrador.

        [WARNING] FLUJO CRÍTICO:
        1. Si es creación nueva (change=False):
           - Transacción atómica: Client + Domain (señal) + TenantMembership
           - Si falla cualquier paso, TODO se revierte
        2. Si es edición (change=True):
           - Actualiza Client y Membership sin transacción (ya existe)

        Args:
            request: HttpRequest del admin
            obj: Instancia del modelo Client
            form: Formulario ClientAdminForm
            change: Boolean indicando si es edición (True) o creación (False)
        """
        if change:
            # EDICIÓN: No necesita transacción atómica (el tenant ya existe)
            super().save_model(request, obj, form, change)

            # Obtener el usuario seleccionado desde el formulario
            admin_user = form.cleaned_data.get("admin_user")

            # Si hay un usuario seleccionado, actualizar/crear la membresía.
            # El lookup debe ser (client, user) — la clave única del modelo.
            # Buscar por is_primary_admin=True causaría IntegrityError si el usuario
            # ya tiene una membresía con is_primary_admin=False.
            if admin_user:
                TenantMembership.objects.update_or_create(
                    client=obj,
                    user=admin_user,
                    defaults={
                        "rol": "ADMIN",
                        "is_primary_admin": True,
                        "is_active": True,
                    },
                )

                # Desmarcar cualquier otro primary_admin en este tenant
                TenantMembership.objects.filter(client=obj, is_primary_admin=True).exclude(
                    user=admin_user
                ).update(is_primary_admin=False)
        else:
            # CREACIÓN: Transacción atómica para prevenir tenants huérfanos
            try:
                with transaction.atomic():
                    # Paso 1: Guardar el Client (esto crea el esquema en la BD)
                    # La señal post_save creará automáticamente el Domain
                    super().save_model(request, obj, form, change)

                    # Paso 2: Obtener el usuario seleccionado desde el formulario
                    admin_user = form.cleaned_data.get("admin_user")

                    # Paso 3: CRÍTICO - Crear la TenantMembership inmediatamente
                    # Si esto falla, la transacción se revierte y el Client NO se crea
                    if admin_user:
                        TenantMembership.objects.create(
                            client=obj,
                            user=admin_user,
                            rol="ADMIN",
                            is_primary_admin=True,
                            is_active=True,
                        )
                    else:
                        # Esto no debería pasar porque el formulario valida admin_user en clean()
                        # Pero por seguridad, lanzamos un error si no hay usuario
                        raise ValueError(
                            "No se puede crear un tenant sin usuario administrador. "
                            "El formulario debería haber validado esto."
                        )
            except Exception as e:
                # Si falla la creación de Membership, la transacción se revierte automáticamente
                # El Client NO se crea, evitando tenants huérfanos
                self.message_user(
                    request,
                    f"[ERROR] Error al crear tenant: {str(e)}. "
                    f"El tenant no fue creado para evitar estados inconsistentes.",
                    level="error",
                )
                raise  # Re-lanzar para que Django Admin muestre el error

    def has_delete_permission(self, request, obj=None):
        """
        Bloquea la eliminación del tenant público en la UI del Admin.

        [WARNING] PROTECCIÓN DEL TENANT PÚBLICO:
        - Si obj.schema_name == 'public', retorna False (oculta botón de eliminar)
        - Para otros tenants, valida is_active=False
        """
        if obj is None:
            # Permite mostrar la acción de eliminar en la lista (se validará en delete_model)
            return super().has_delete_permission(request, obj)

        # BLOQUEO ABSOLUTO DEL TENANT PÚBLICO
        public_schema = get_public_schema_name()
        if obj.schema_name == public_schema:
            return False  # Oculta el botón de eliminar en la UI

        # Para otros tenants, validar is_active=False
        if obj.is_active:
            return False  # No permitir eliminar tenants activos

        return super().has_delete_permission(request, obj)

    def delete_model(self, request, obj):
        """
        Sobrescribe delete_model para delegar la eliminacion al servicio hard_delete_tenant.

        [WARNING] HARD DELETE CON PRECONDICION:
        - La validacion de is_active=False y el bloqueo del tenant publico los realiza
          hard_delete_tenant() como SSoT (defense in depth en el servicio).
        - Este metodo solo actua como capa de feedback UI para el admin.

        Raises:
            ValidationError: Propagada desde hard_delete_tenant si el tenant esta activo o es publico.
        """
        logger = logging.getLogger("security.tenants")
        actor_user_id = request.user.id if request.user.is_authenticated else None

        try:
            hard_delete_tenant(client_id=obj.id, actor_user_id=actor_user_id)
            self.message_user(
                request,
                f'[OK] Tenant "{obj.nombre}" eliminado permanentemente (esquema y datos).',
                level="success",
            )
        except Exception as e:
            logger.error(f"Error en delete_model (Admin): {str(e)}", exc_info=True)
            self.message_user(request, f"[ERROR] {str(e)}", level="error")
            raise


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ("domain", "tenant", "is_primary")
    list_filter = ("is_primary",)
    search_fields = ("domain",)


@admin.register(TenantMembership)
class TenantMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "client", "rol", "is_primary_admin", "created_at")
    list_filter = ("rol", "is_primary_admin", "created_at")
    search_fields = ("user__email", "client__nombre")
