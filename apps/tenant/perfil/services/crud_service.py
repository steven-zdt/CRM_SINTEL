from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from apps.tenant.perfil.models import TenantProfile


class PerfilCRUDService:
    @staticmethod
    def list_profiles(empresa_id):
        """Retorna todos los perfiles de un tenant filtrados por empresa_id."""
        return TenantProfile.objects.filter(
            empresa_id=empresa_id
        ).order_by('-created_at').select_related('user').only(
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

    @staticmethod
    def get_profile_by_user_and_tenant(user_id, empresa_id):
        # Zero Waste: request only the fields we need
        qs = TenantProfile.objects.filter(user_id=user_id, empresa_id=empresa_id).only(
            "id",
            "user_id",
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
        return qs.first()

    @staticmethod
    def create_profile(user, empresa, defaults=None):
        if defaults is None:
            defaults = {}
        profile, _ = TenantProfile.objects.get_or_create(
            user=user, empresa=empresa, defaults=defaults
        )
        return profile

    # [SEG-3] Allowlist de campos mutables via update_profile.
    # Rechaza silenciosamente campos protegidos (user, empresa, rol, id).
    MUTABLE_FIELDS = frozenset({
        'cargo', 'departamento', 'telefono_corporativo',
        'avatar', 'configuracion',
    })

    @staticmethod
    def update_profile(profile, validated_data):
        # [SEG-3] Apply only ALLOWED fields — ignore protected fields
        update_fields = []
        for attr, value in validated_data.items():
            if attr not in PerfilCRUDService.MUTABLE_FIELDS:
                continue
            setattr(profile, attr, value)
            update_fields.append(attr)

        if update_fields:
            update_fields.append("updated_at")
            profile.save(update_fields=update_fields)
        return profile

    @staticmethod
    def get_profile_by_id_and_tenant(profile_id, empresa_id):
        # Zero Waste: request only the fields we need
        qs = TenantProfile.objects.filter(id=profile_id, empresa_id=empresa_id).only(
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
        ).select_related("user")
        return qs.first()

    @staticmethod
    @transaction.atomic
    def assign_rol(profile, new_rol: str):
        """[RULE 5.4] Persiste el nuevo rol en el perfil, operacion atomica."""
        profile.rol = new_rol
        profile.save(update_fields=['rol', 'updated_at'])
        return profile

    @staticmethod
    def delete_profile(profile):
        profile.delete()
        return True
