"""
Selectores para Perfil v3.5 - Zero Waste Queries.
"""
from django.db.models import Q

from apps.tenant.perfil.models import TenantProfile


LIST_FIELDS = (
    "id",
    "user__id",
    "user__email",
    "user__username",
    "user__first_name",
    "user__last_name",
    "empresa_id",
    "cargo",
    "departamento",
    "telefono_corporativo",
    "avatar",
    "configuracion",
    "rol",
    "created_at",
    "updated_at",
)

DETAIL_FIELDS = (
    "id",
    "user__id",
    "user__email",
    "user__username",
    "user__first_name",
    "user__last_name",
    "empresa_id",
    "cargo",
    "departamento",
    "telefono_corporativo",
    "avatar",
    "configuracion",
    "rol",
    "created_at",
    "updated_at",
)


class PerfilSelector:
    """Selector para modelo TenantProfile."""

    @staticmethod
    def get_list(empresa_id, search=None):
        """Retorna listado optimizado de perfiles."""
        qs = TenantProfile.objects.filter(
            empresa_id=empresa_id
        ).select_related('user').only(*LIST_FIELDS)
        
        if search:
            qs = qs.filter(
                Q(user__email__icontains=search) |
                Q(user__username__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(cargo__icontains=search) |
                Q(departamento__icontains=search)
            )
        
        return qs

    @staticmethod
    def get_detail(profile_id, empresa_id):
        """Retorna detalle de un perfil."""
        return TenantProfile.objects.filter(
            id=profile_id,
            empresa_id=empresa_id
        ).select_related('user').only(*DETAIL_FIELDS).first()

    @staticmethod
    def get_by_user(user_id, empresa_id):
        """Retorna perfil por usuario y empresa."""
        return TenantProfile.objects.filter(
            user_id=user_id,
            empresa_id=empresa_id
        ).select_related('user').only(*DETAIL_FIELDS).first()
