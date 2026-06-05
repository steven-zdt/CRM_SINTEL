import logging
import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.models import Field
from django_tenants.utils import get_public_schema_name

from apps.tenant.core.services.membership import check_membership_by_schema, check_primary_admin
from apps.tenant.empresa.models import Area, Empresa, Sede
from apps.tenant.perfil.models import Departamento, RolTenant
from .crud_service import PerfilCRUDService

logger = logging.getLogger(__name__)


class PerfilBusinessService:
    def __init__(self):
        self.crud = PerfilCRUDService()

    @staticmethod
    def _is_tenant_primary_admin(user) -> bool:
        """[RULE 13] Verifica si el usuario es el admin primario de este tenant.

        Tier 1 (rapido, intra-schema): consulta Empresa.owner_email en el schema
        activo. Cero latencia cross-schema. Poblado durante onboarding.

        Tier 2 (fallback, cross-schema): consulta TenantMembership en el esquema
        public via search_path para tenants donde owner_email aun no fue poblado.

        DSV: el schema_name del tenant activo se usa para aislar el fallback
        (anti-IDOR horizontal entre tenants).

        Args:
            user: Usuario global (auth model) autenticado.

        Returns:
            True si el usuario es el admin primario, False en cualquier otro caso.
        """
        try:
            # Tier 1: intra-schema via Empresa.owner_email (fast path)
            if (
                user.email
                and Empresa.objects.filter(owner_email=user.email).only('id').exists()
            ):
                return True
        except Exception:
            pass

        try:
            # Tier 2: cross-schema fallback via Core Membership Bridge (REGLA 2)
            return check_primary_admin(user.pk)
        except Exception:
            return False

    @staticmethod
    def _verify_user_membership(user):
        """[SEG-1] Verifica que el usuario tenga TenantMembership activa
        en el tenant actual. Defense-in-depth: bloquea creacion de perfiles
        para usuarios sin membresia, incluso si la capa HTTP falla.

        Returns:
            True si tiene membresia activa, False en caso contrario.
        """
        # En schema public no aplica la validacion de membership
        if connection.schema_name == get_public_schema_name():
            return True
        try:
            return check_membership_by_schema(user.id)
        except Exception:
            logger.warning(
                "[perfil:membership] No se pudo verificar membership: user=%s schema=%s",
                getattr(user, 'email', '?'),
                _conn.schema_name,
            )
            return False

    def get_or_initialize_profile(self, user, empresa):
        """Obtiene el perfil existente o lo crea con Auto-Admin Onboarding.

        [SEG-1] Antes de crear un perfil nuevo, verifica que el usuario
        tenga TenantMembership activa en el tenant actual (defense-in-depth).

        [AUTO-ADMIN] Si el perfil se crea por primera vez y el usuario es el
        admin primario del tenant (is_primary_admin=True en TenantMembership),
        se asigna automaticamente rol='ADMIN' sin intervencion manual.

        Si el perfil ya existe pero tiene rol != 'ADMIN' y el usuario ES el
        admin primario, se corrige automaticamente (Auto-Admin Elevation).
        Esto cubre el caso de perfiles creados durante onboarding seed sin rol.

        DSV: la verificacion de TenantMembership usa connection.schema_name
        para garantizar aislamiento total entre tenants (anti-IDOR).
        """
        profile = self.crud.get_profile_by_user_and_tenant(user.id, empresa.id)
        if not profile:
            # [SEG-1] Verificar membership antes de crear perfil
            if not self._verify_user_membership(user):
                logger.warning(
                    "[perfil:create] BLOQUEADO: usuario sin membership intento crear perfil "
                    "| user=%s schema=%s",
                    user.email,
                    connection.schema_name,
                )
                raise ValidationError(
                    "El usuario no tiene membresia activa en este tenant."
                )
            is_owner = self._is_tenant_primary_admin(user)
            defaults = {'rol': 'ADMIN'} if is_owner else {}
            profile = self.crud.create_profile(user, empresa, defaults=defaults)
        elif profile.rol != 'ADMIN' and self._is_tenant_primary_admin(user):
            # Auto-Admin Elevation: corregir perfiles existentes creados antes
            # de que el seed de onboarding incluyera rol='ADMIN'.
            profile.rol = 'ADMIN'
            profile.save(update_fields=['rol', 'updated_at'])
        return profile

    def list_profiles(self, empresa):
        """Lista todos los perfiles del tenant actual."""
        return self.crud.list_profiles(empresa.id)

    def create_profile_for_user(self, empresa, data):
        """Crea un perfil (y opcionalmente un usuario nuevo) en el tenant.

        Flujo:
        1. Busca User existente por email/username.
        2. Si no existe, crea un User nuevo en el esquema public con
           set_unusable_password() (el usuario se activa via invitacion).
        3. Valida idempotencia (perfil duplicado).
        4. Crea TenantProfile con datos corporativos y rol.

        [RULE 17] Usa get_user_model() (API estandar Django) en lugar de
        importar directamente desde apps.public.
        """
        User = get_user_model()

        email = (data.get("email") or "").strip().lower()
        username = (data.get("username") or "").strip()

        if not email and not username:
            raise ValidationError(
                "Se requiere email o username para identificar al usuario."
            )

        # 1. Buscar usuario global existente
        user = None
        if email:
            user = User.objects.filter(email=email).only(
                "id", "email", "username"
            ).first()
        if not user and username:
            user = User.objects.filter(username=username).only(
                "id", "email", "username"
            ).first()

        # 2. Si no existe, crear usuario nuevo en public schema
        if not user:
            if not email:
                raise ValidationError(
                    "Se requiere email para crear un usuario nuevo."
                )

            first_name = (data.get("first_name") or "").strip()
            last_name = (data.get("last_name") or "").strip()

            if not first_name:
                raise ValidationError(
                    "Se requiere nombre (first_name) para crear un usuario nuevo."
                )

            # Generar username unico a partir del email (inline, sin import cross-schema)
            def _gen_username(em):
                base = (em.split("@")[0] if em else "user").strip().replace(" ", "").lower() or "user"
                candidate = base[:150]
                if not User.objects.filter(username=candidate).exists():
                    return candidate
                i = 1
                while True:
                    cand = f"{base}-{i}"[:150]
                    if not User.objects.filter(username=cand).exists():
                        return cand
                    i += 1

            user_kwargs = {
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "is_staff": False,
                "is_active": True,
            }

            # Generar username si el modelo lo soporta
            has_username = any(
                isinstance(f, Field) and f.name == "username"
                for f in User._meta.get_fields()
            )
            if has_username:
                user_kwargs["username"] = _gen_username(email)

            try:
                user = User(**user_kwargs)
                user.set_unusable_password()
                user.save()
                logger.info(
                    "[perfil:create] Usuario creado en public: %s (username=%s, unusable password) | schema=%s",
                    email,
                    user_kwargs.get("username", "N/A"),
                    connection.schema_name,
                )
            except IntegrityError:
                # Email o username duplicado: reintentar busqueda
                user = User.objects.filter(email=email).only(
                    "id", "email", "username"
                ).first()
                if not user:
                    raise ValidationError(
                        "No se pudo crear el usuario: email o username ya existente."
                    )
                logger.info(
                    "[perfil:create] Usuario obtenido tras conflicto de unicidad: %s | schema=%s",
                    email,
                    connection.schema_name,
                )

        # 3. [SEG-4 REVISADO] La verificacion de membership del usuario destino
        #    se elimina de create_profile_for_user. Razon:
        #    - Crear un perfil ES el acto de agregar un usuario al tenant.
        #    - Usuarios nuevos (user_is_new) no tienen TenantMembership aun.
        #    - Usuarios pre-existentes que se agregan a un nuevo tenant tampoco
        #      tienen TenantMembership para ese tenant todavia.
        #    - La autorizacion del ADMIN solicitante ya fue validada por
        #      IsTenantProfileAdmin en el ViewSet (Capa 3 - Defense-in-Depth).
        #    - SEG-1 (get_or_initialize_profile) conserva su membership guard
        #      porque ese flujo es para el usuario PROPIO, no para creacion admin.

        # 4. Idempotencia: verificar si ya existe perfil para este user+empresa
        existing = self.crud.get_profile_by_user_and_tenant(
            user.id, empresa.id
        )
        if existing:
            raise ValidationError(
                "Ya existe un perfil para este usuario en esta empresa."
            )

        # 4. Construir defaults con datos corporativos
        defaults = {}
        if data.get("cargo"):
            defaults["cargo"] = str(data["cargo"]).strip()
        if data.get("telefono_corporativo"):
            defaults["telefono_corporativo"] = str(data["telefono_corporativo"]).strip()

        # Resolver departamento_uuid -> instancia Departamento con DSV
        departamento_uuid = (data.get("departamento_uuid") or data.get("departamento") or "").strip()
        if departamento_uuid:
            dept = Departamento.objects.filter(
                uuid=departamento_uuid, empresa=empresa
            ).only("id", "uuid").first()
            if not dept:
                raise ValidationError(
                    "El departamento no pertenece a la empresa activa del tenant (DSV)."
                )
            defaults["departamento"] = dept

        # Rol inicial: ADMIN puede asignar rol en la creacion (DSV: valor valido de RolTenant)
        if data.get("rol"):
            valid_roles = [c[0] for c in RolTenant.choices]
            if data["rol"] in valid_roles:
                defaults["rol"] = data["rol"]

        profile = self.crud.create_profile(user, empresa, defaults=defaults)
        self._sync_sedes_y_areas(profile, data, empresa)
        return profile

    def _sync_sedes_y_areas(self, profile, data, empresa):
        """
        Sincroniza las M2M sedes_asignadas y areas_asignadas con DSV.
        Tambien valida que el departamento FK pertenezca al tenant activo.
        """
        if not isinstance(data, dict):
            return

        sedes_uuids = data.pop("sedes_uuids", None)
        areas_uuids = data.pop("areas_uuids", None)

        # DSV: validar que el departamento pertenezca al tenant activo
        # El SlugRelatedField puede haberlo resuelto como instancia ya
        departamento = data.get("departamento", None)
        if departamento is not None:
            dept_id = getattr(departamento, 'id', None) or departamento
            if not Departamento.objects.filter(id=dept_id, empresa=empresa).exists():
                raise ValidationError(
                    "El departamento no pertenece a la empresa activa del tenant (DSV)."
                )

        with transaction.atomic():
            if sedes_uuids is not None:
                # Cast a str para compatibilidad con filter(uuid__in=...)
                sedes_uuids_str = [str(u) for u in sedes_uuids if u]
                sedes = list(Sede.objects.filter(uuid__in=sedes_uuids_str, empresa=empresa))
                if len(sedes) != len(sedes_uuids_str):
                    raise ValidationError("Una o mas sedes no pertenecen a la empresa actual (DSV).")
                profile.sedes_asignadas.set(sedes)

            if areas_uuids is not None:
                # Cast a str para compatibilidad con filter(uuid__in=...)
                areas_uuids_str = [str(u) for u in areas_uuids if u]
                areas = list(Area.objects.filter(uuid__in=areas_uuids_str, empresa=empresa))
                if len(areas) != len(areas_uuids_str):
                    raise ValidationError("Una o mas areas no pertenecen a la empresa actual (DSV).")
                profile.areas_asignadas.set(areas)

    def update_user_profile(self, user, empresa, data):
        # Double Semantic Verification (anti-IDOR): ensure payload does not attempt to reassign FK to other tenant/user
        if isinstance(data, dict):
            if "empresa_id" in data or "empresa" in data:
                incoming_empresa = data.get("empresa_id") or data.get("empresa")
                if incoming_empresa is not None and int(incoming_empresa) != int(empresa.id):
                    raise ValidationError("Foreign key 'empresa' in payload does not belong to tenant (anti-IDOR)")
            if "user_id" in data or "user" in data:
                incoming_user = data.get("user_id") or data.get("user")
                if incoming_user is not None and int(incoming_user) != int(user.id):
                    raise ValidationError("Foreign key 'user' in payload does not belong to authenticated user (anti-IDOR)")

        profile = self.get_or_initialize_profile(user, empresa)
        self._sync_sedes_y_areas(profile, data, empresa)
        return self.crud.update_profile(profile, data)

    def get_profile(self, profile_id, empresa):
        """Obtiene un perfil especifico, validando pertenencia al tenant, soportando UUID e ID."""
        is_uuid = False
        if isinstance(profile_id, str):
            try:
                uuid.UUID(profile_id)
                is_uuid = True
            except ValueError:
                pass
        
        if is_uuid:
            profile = self.crud.get_profile_by_uuid_and_tenant(profile_id, empresa.id)
        else:
            profile = self.crud.get_profile_by_id_and_tenant(profile_id, empresa.id)
            
        if not profile:
            raise ValidationError("Perfil no encontrado o no pertenece a la empresa actual.")
        return profile

    def update_profile_by_id(self, profile_id, empresa, data):
        """Actualiza un perfil por ID/UUID (para administradores del tenant) con DSV y sync de M2M."""
        if isinstance(data, dict):
            if "empresa_id" in data or "empresa" in data:
                incoming_empresa = data.get("empresa_id") or data.get("empresa")
                if incoming_empresa is not None and int(incoming_empresa) != int(empresa.id):
                    raise ValidationError("Foreign key 'empresa' in payload does not belong to tenant (anti-IDOR)")
                    
        profile = self.get_profile(profile_id, empresa)
        self._sync_sedes_y_areas(profile, data, empresa)
        return self.crud.update_profile(profile, data)

    def delete_profile(self, profile_id, empresa):
        """Elimina un perfil del tenant."""
        profile = self.get_profile(profile_id, empresa)
        return self.crud.delete_profile(profile)

    def assign_rol(self, profile_id, empresa, new_rol: str):
        """[RULE 13] Asigna un rol a un perfil con Double Semantic Verification."""
        # DSV Paso 1: valor de rol valido
        valid_roles = [choice[0] for choice in RolTenant.choices]
        if new_rol not in valid_roles:
            raise ValidationError(
                f"Rol invalido: '{new_rol}'. Opciones validas: {valid_roles}"
            )

        # DSV Paso 2: perfil pertenece al tenant actual
        profile = self.get_profile(profile_id, empresa)

        # Persistencia atomica
        return self.crud.assign_rol(profile, new_rol)
