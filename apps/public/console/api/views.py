"""
APIViews para la consola de administración (API-First).

Todas las vistas usan POST para DataTables (server-side) con CSRF,
y requieren permisos IsAdminUser.

WARNING: AUTENTICACIÓN:
- Usa SessionAuthentication para permitir autenticación por cookies de sesión
- La UI (HTML/JS) usa sesiones de Django, no JWT
"""

import logging

from django.contrib.auth import get_user_model
from django.db.models import Exists, OuterRef, Q, QuerySet, Subquery
from django.utils.timezone import now
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.public.accounts.services.delete_user_service import delete_user_service
from apps.public.tenants.models import Client, Domain, TenantMembership
from apps.shared.datatable import DataTableServer, DataTableSpec

from .serializers import (
    ConsoleUserDetailSerializer,
    ConsoleUserListSerializer,
    TenantDomainSerializer,
    TenantListSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


class TenantsDataTableView(APIView):
    """
    Endpoint DataTables para listado de tenants.

    POST /api/admin/v1/console/dt/tenants/

    Requiere: IsAdminUser
    Autenticación: SessionAuthentication (cookies de sesión)
    Contrato: DataTables estándar (draw, recordsTotal, recordsFiltered, data)
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        _base_membership = TenantMembership.objects.filter(
            client=OuterRef("pk"), is_primary_admin=True, is_active=True
        )

        base_qs: QuerySet = (
            Client.objects.exclude(schema_name="public")
            .only("id", "nombre", "schema_name", "is_active", "on_trial", "paid_until", "created_on")
            .annotate(
                primary_domain=Subquery(
                    Domain.objects.filter(tenant=OuterRef("pk"), is_primary=True).values("domain")[:1]
                ),
                owner_email=Subquery(_base_membership.values("user__email")[:1]),
                owner_password=Subquery(_base_membership.values("user__password")[:1]),
            )
        )

        spec = DataTableSpec(
            fields_map={
                0: "id",
                1: "schema_name",
                2: "nombre",
                3: "primary_domain",
                4: "is_active",
                5: "created_on",
            },
            search_fields=["nombre", "schema_name", "domains__domain", "owner_email"],
            base_qs=base_qs,
            serializer=TenantListSerializer,
        )

        return DataTableServer(spec).handle(request)


class TenantDomainsDataTableView(APIView):
    """
    Endpoint DataTables para dominios de tenants.

    POST /api/admin/v1/console/dt/tenant-domains/

    Requiere: IsAdminUser
    Autenticación: SessionAuthentication (cookies de sesión)
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        base_qs = Domain.objects.only("id", "domain", "is_primary", "tenant_id").select_related(
            "tenant"
        )

        spec = DataTableSpec(
            fields_map={
                0: "id",
                1: "domain",
                2: "is_primary",
            },
            search_fields=["domain"],
            base_qs=base_qs,
            serializer=TenantDomainSerializer,
        )

        return DataTableServer(spec).handle(request)


class UsersDataTableView(APIView):
    """
    Endpoint CRUD para usuarios globales.

    POST /api/admin/v1/console/dt/users/ → Listar (DataTables)
    GET /api/admin/v1/console/dt/users/{id}/ → Obtener usuario
    POST /api/admin/v1/console/dt/users/ (con data) → Crear usuario
    PATCH /api/admin/v1/console/dt/users/{id}/ → Actualizar usuario
    DELETE /api/admin/v1/console/dt/users/{id}/ → Eliminar usuario

    Requiere: IsAdminUser
    Autenticación: SessionAuthentication (cookies de sesión)
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request, user_id=None, *args, **kwargs):
        """GET /api/admin/v1/console/dt/users/{id}/ - Obtener usuario específico"""
        if not user_id:
            return Response({"error": "user_id requerido"}, status=400)

        try:
            user = User.objects.get(pk=user_id)
            serializer = ConsoleUserDetailSerializer(user)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response({"error": "Usuario no encontrado"}, status=404)

    def post(self, request, *args, **kwargs):
        """POST /api/admin/v1/console/dt/users/ - Listar (DataTables) o Crear usuario"""
        if "draw" in request.data:
            from django.db.models import Exists, Prefetch, Q

            # Solo mostrar: system admins (staff+superuser) O owners de tenants (primary_admin)
            # Los empleados/miembros de tenants (OPERADOR, VISOR) no deben aparecer aqui
            _has_primary_admin = TenantMembership.objects.filter(
                user=OuterRef("pk"),
                is_primary_admin=True,
                is_active=True,
            )
            memberships_qs = TenantMembership.objects.filter(
                is_active=True
            ).select_related("client").only(
                "user_id", "client_id", "rol", "is_primary_admin", "is_active",
                "client__id", "client__nombre", "client__schema_name",
            )
            base_qs = (
                User.objects.filter(
                    Q(is_staff=True, is_superuser=True) |  # Admins del sistema
                    Q(Exists(_has_primary_admin))           # Owners de tenants privados
                )
                .distinct()
                .only(
                    "id", "email", "first_name", "last_name",
                    "is_active", "is_staff", "is_superuser", "date_joined", "telefono",
                )
                .prefetch_related(
                    Prefetch("tenant_memberships", queryset=memberships_qs, to_attr="_tenant_memberships")
                )
            )

            spec = DataTableSpec(
                fields_map={
                    0: "id",
                    1: "email",
                    2: "first_name",
                    3: "last_name",
                    4: "is_active",
                    5: "is_staff",
                    6: "date_joined",
                },
                search_fields=["email", "first_name", "last_name"],
                base_qs=base_qs,
                serializer=ConsoleUserListSerializer,
            )
            return DataTableServer(spec).handle(request)

        # Crear usuario
        serializer = ConsoleUserDetailSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    def patch(self, request, user_id=None, *args, **kwargs):
        """PATCH /api/admin/v1/console/dt/users/{id}/ - Actualizar usuario"""
        if not user_id:
            return Response({"error": "user_id requerido"}, status=400)

        try:
            user = User.objects.get(pk=user_id)
            serializer = ConsoleUserDetailSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        except User.DoesNotExist:
            return Response({"error": "Usuario no encontrado"}, status=404)

    def delete(self, request, user_id=None, *args, **kwargs):
        """DELETE /api/admin/v1/console/dt/users/{id}/ - Eliminar usuario via delete_user_service"""
        if not user_id:
            return Response({"error": "user_id requerido"}, status=400)

        try:
            user = User.objects.only("id", "email").get(pk=user_id)
            email = user.email
        except User.DoesNotExist:
            return Response({"error": "Usuario no encontrado"}, status=404)

        try:
            deleted_by_id = request.user.id if request.user.is_authenticated else None
            delete_user_service(
                user_id=user_id,
                cascade=True,
                deleted_by_id=deleted_by_id,
            )
            return Response({"mensaje": f"Usuario {email} eliminado correctamente"})
        except Exception as e:
            logger.exception(f"Error eliminando usuario {user_id}: {e}")
            return Response({"error": f"Error al eliminar usuario: {str(e)}"}, status=400)


class OrphanTenantsView(APIView):
    """
    Tenants sin administrador primario activo (huerfanos).

    GET /api/admin/v1/console/orphan-tenants/

    Devuelve lista de Clients sin TenantMembership is_primary_admin=True + is_active=True,
    para permitir asignacion de un usuario como owner desde la consola.
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        from django.db.models import Subquery, OuterRef, Exists

        has_primary_admin = TenantMembership.objects.filter(
            client=OuterRef("pk"),
            is_primary_admin=True,
            is_active=True,
        )
        orphans = (
            Client.objects.exclude(schema_name="public")
            .filter(is_active=True)
            .annotate(has_primary=Exists(has_primary_admin))
            .filter(has_primary=False)
            .only("id", "nombre", "schema_name")
            .annotate(
                primary_domain=Subquery(
                    Domain.objects.filter(tenant=OuterRef("pk"), is_primary=True).values("domain")[:1]
                )
            )
        )
        data = [
            {
                "id": t.id,
                "nombre": t.nombre,
                "schema_name": t.schema_name,
                "primary_domain": t.primary_domain,
            }
            for t in orphans
        ]
        return Response({"count": len(data), "results": data})


class AssignTenantView(APIView):
    """
    Asigna un usuario a un tenant como administrador primario.

    POST /api/admin/v1/console/dt/users/{user_id}/assign-tenant/
    Body: {
        "tenant_id": int,
        "rol": "ADMIN"|"STAFF"|"USER",       (default: "ADMIN")
        "is_primary_admin": bool              (default: true)
    }

    Si el usuario ya tenia una membresia en ese tenant, la actualiza.
    Si is_primary_admin=True, desvincula el admin primario anterior.
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def post(self, request, user_id=None, *args, **kwargs):
        if not user_id:
            return Response({"error": "user_id requerido"}, status=400)

        try:
            user = User.objects.get(pk=user_id, is_active=True)
        except User.DoesNotExist:
            return Response({"error": "Usuario no encontrado o inactivo"}, status=404)

        tenant_id = request.data.get("tenant_id")
        if not tenant_id:
            return Response({"error": "tenant_id requerido"}, status=400)

        try:
            tenant = Client.objects.get(pk=tenant_id, is_active=True)
        except Client.DoesNotExist:
            return Response({"error": "Tenant no encontrado o inactivo"}, status=404)

        rol = request.data.get("rol", "ADMIN")
        is_primary = bool(request.data.get("is_primary_admin", True))

        # Si va a ser primary_admin, desmarcar al anterior
        if is_primary:
            TenantMembership.objects.filter(
                client=tenant, is_primary_admin=True
            ).update(is_primary_admin=False)

        membership, created = TenantMembership.objects.update_or_create(
            client=tenant,
            user=user,
            defaults={
                "rol": rol,
                "is_primary_admin": is_primary,
                "is_active": True,
            },
        )

        return Response(
            {
                "mensaje": f"Usuario {user.email} asignado a {tenant.nombre} como {rol}.",
                "membership_id": membership.pk,
                "tenant_nombre": tenant.nombre,
                "tenant_schema": tenant.schema_name,
                "created": created,
            },
            status=201 if created else 200,
        )


class UserTenantsView(APIView):
    """
    Devuelve las membresías del usuario indicado.

    GET /api/admin/v1/console/dt/users/{user_id}/tenants/
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request, user_id=None, *args, **kwargs):
        if not user_id:
            return Response({"error": "user_id requerido"}, status=400)
        try:
            User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"error": "Usuario no encontrado"}, status=404)

        memberships = (
            TenantMembership.objects.filter(user_id=user_id)
            .select_related("client")
            .only(
                "id", "rol", "is_primary_admin", "is_active",
                "client__id", "client__nombre", "client__schema_name",
            )
        )
        data = [
            {
                "membership_id": m.pk,
                "tenant_id": m.client_id,
                "nombre": m.client.nombre,
                "schema_name": m.client.schema_name,
                "rol": m.rol,
                "is_primary_admin": m.is_primary_admin,
                "is_active": m.is_active,
            }
            for m in memberships
        ]
        return Response({"count": len(data), "results": data})


class ConsoleHealthView(APIView):
    """
    Endpoint de salud/estado de la consola.

    GET /api/admin/v1/console/health/

    Requiere: IsAdminUser
    Autenticación: SessionAuthentication (cookies de sesión)
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        return Response(
            {
                "status": "ok",
                "time": now().isoformat(),
                "features": {
                    "api_first": True,
                    "datatables_post": True,
                    "jwt_admin": True,
                },
            }
        )
