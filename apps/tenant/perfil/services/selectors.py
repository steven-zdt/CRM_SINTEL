from django.db.models import Q

from apps.tenant.perfil.models import TenantProfile, Departamento


DEPARTAMENTO_LIST_FIELDS = (
    "id",
    "uuid",
    "nombre",
    "descripcion",
    "activo",
    "empresa_id",
    "created_at",
    "updated_at",
)


LIST_FIELDS = (
    "id",
    "uuid",
    "user__id",
    "user__email",
    "user__username",
    "user__first_name",
    "user__last_name",
    "empresa_id",
    "cargo",
    "departamento__id",
    "departamento__uuid",
    "departamento__nombre",
    "telefono_corporativo",
    "avatar",
    "configuracion",
    "rol",
    "created_at",
    "updated_at",
)

DETAIL_FIELDS = (
    "id",
    "uuid",
    "user__id",
    "user__email",
    "user__username",
    "user__first_name",
    "user__last_name",
    "empresa_id",
    "cargo",
    "departamento__id",
    "departamento__uuid",
    "departamento__nombre",
    "telefono_corporativo",
    "avatar",
    "configuracion",
    "rol",
    "created_at",
    "updated_at",
)


class DepartamentoSelector:
    """Selector para modelo Departamento."""

    @staticmethod
    def get_list(empresa_id, search=None):
        """Retorna listado optimizado de departamentos."""
        qs = Departamento.objects.filter(
            empresa_id=empresa_id
        ).only(*DEPARTAMENTO_LIST_FIELDS)
        
        if search:
            qs = qs.filter(
                Q(nombre__icontains=search) |
                Q(descripcion__icontains=search)
            )
        return qs

    @staticmethod
    def get_detail(uuid, empresa_id):
        """Retorna detalle de un departamento por su UUID."""
        return Departamento.objects.filter(
            uuid=uuid,
            empresa_id=empresa_id
        ).only(*DEPARTAMENTO_LIST_FIELDS).first()


class PerfilSelector:
    """Selector para modelo TenantProfile."""

    @staticmethod
    def get_list(empresa_id, search=None):
        """Retorna listado optimizado de perfiles."""
        qs = TenantProfile.objects.filter(
            empresa_id=empresa_id
        ).select_related('user', 'departamento').prefetch_related('sedes_asignadas', 'areas_asignadas').only(*LIST_FIELDS)
        
        if search:
            qs = qs.filter(
                Q(user__email__icontains=search) |
                Q(user__username__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(cargo__icontains=search) |
                Q(departamento__nombre__icontains=search)
            )
        
        return qs

    @staticmethod
    def get_detail(uuid, empresa_id):
        """Retorna detalle de un perfil por su UUID."""
        return TenantProfile.objects.filter(
            uuid=uuid,
            empresa_id=empresa_id
        ).select_related('user', 'departamento').prefetch_related('sedes_asignadas', 'areas_asignadas').only(*DETAIL_FIELDS).first()

    @staticmethod
    def get_by_user(user_id, empresa_id):
        """Retorna perfil por usuario y empresa."""
        return TenantProfile.objects.filter(
            user_id=user_id,
            empresa_id=empresa_id
        ).select_related('user', 'departamento').prefetch_related('sedes_asignadas', 'areas_asignadas').only(*DETAIL_FIELDS).first()
