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
from django.db.models import OuterRef, QuerySet, Subquery
from django.utils.timezone import now
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.public.tenants.models import Client, Domain
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
        # Anotar primary_domain con Subquery para obtener el dominio primario
        primary_domain_sq = Subquery(
            Domain.objects.filter(tenant=OuterRef("pk"), is_primary=True).values("domain")[:1]
        )

        # Excluir el tenant público (schema_name='public') para que los
        # listados administrativos muestren solo tenants reales.
        base_qs: QuerySet = (
            Client.objects.exclude(schema_name="public")
            .only("id", "nombre", "schema_name", "is_active", "on_trial", "paid_until", "created_on")
            .annotate(primary_domain=primary_domain_sq)
        )

        # DEBUG: log current tenants snapshot to trace unexpected extra tenants in tests
        logger = logging.getLogger(__name__)
        try:
            tenant_snapshot = list(
                base_qs.values("id", "schema_name", "nombre")
            )
            logger.info("TenantsDataTableView: base_qs_count=%s tenants=%s", len(tenant_snapshot), tenant_snapshot)
        except Exception:
            logger.exception("TenantsDataTableView: fallo al obtener snapshot de tenants")

        spec = DataTableSpec(
            fields_map={
                0: "id",
                1: "schema_name",
                2: "nombre",
                3: "primary_domain",  # nueva columna
                4: "is_active",
                5: "created_on",
            },
            search_fields=[
                "nombre",
                "schema_name",
                "domains__domain",
            ],  # buscar también por dominio
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
        """POST /api/admin/v1/console/dt/users/ - Listar o Crear"""
        # Si es DataTables request (tiene draw, start, length)
        if "draw" in request.data:
            base_qs = User.objects.only(
                "id",
                "email",
                "first_name",
                "last_name",
                "is_active",
                "is_staff",
                "date_joined",
                "telefono",
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

        # Si es crear usuario
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
        """DELETE /api/admin/v1/console/dt/users/{id}/ - Eliminar usuario"""
        if not user_id:
            return Response({"error": "user_id requerido"}, status=400)

        try:
            user = User.objects.get(pk=user_id)
            email = user.email

            # Clean up tenant profiles and use raw delete to bypass cascade check
            try:
                from django.db import connections
                from django_tenants.utils import get_tenant_model

                Tenant = get_tenant_model()
                for tenant in Tenant.objects.all():
                    try:
                        with connections[tenant.schema_name].cursor() as cursor:
                            cursor.execute(
                                'DELETE FROM perfil_tenantprofile WHERE user_id = %s',
                                [user_id]
                            )
                    except Exception:
                        pass
            except Exception:
                pass

            # Delete using raw SQL to bypass Django's cascade checks
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute('DELETE FROM accounts_user WHERE id = %s', [user_id])

            return Response({"mensaje": f"Usuario {email} eliminado correctamente"})
        except User.DoesNotExist:
            return Response({"error": "Usuario no encontrado"}, status=404)
        except Exception as e:
            logger.exception(f"Error eliminando usuario {user_id}: {e}")
            return Response({"error": f"Error al eliminar usuario: {str(e)}"}, status=400)


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
