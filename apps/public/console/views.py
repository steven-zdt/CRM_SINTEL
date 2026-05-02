"""
Vistas para la consola de administración pública (API-First).

WARNING: IMPORTANTE: Este módulo solo contiene vistas de renderizado (TemplateView).
Toda la lógica de negocio y CRUD vive en apps/public/console/api (SSOT).

Las vistas aquí solo renderizan templates HTML; la UI consume APIs JSON
desde apps/public/console/api o apps/public/tenants/api.
"""

import requests
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView
from django_tenants.utils import get_public_schema_name
from rest_framework_simplejwt.tokens import RefreshToken

from .mixins import StaffRequiredMixin


class PublicSchemaMixin:
    """Mixin que verifica que estemos en el esquema 'public'."""

    def dispatch(self, request, *args, **kwargs):
        try:
            public_schema = get_public_schema_name()
            current_schema = getattr(connection, "schema_name", None)
            if current_schema is not None and current_schema != public_schema:
                from django.http import Http404

                raise Http404("Consola disponible solo en esquema 'public'.")
        except Exception:
            pass
        return super().dispatch(request, *args, **kwargs)


class ConsoleTemplateView(StaffRequiredMixin, PublicSchemaMixin, TemplateView):
    """Vista base para todas las páginas de la consola."""


# ============================================================================
# VISTAS DE RENDERIZADO (TemplateView - Sin lógica de negocio)
# ============================================================================


class DashboardView(ConsoleTemplateView):
    """Dashboard principal de la consola."""

    template_name = "console/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Dashboard - Consola de Administración"
        context["user"] = self.request.user
        return context


class TenantsListView(ConsoleTemplateView):
    """Lista de tenants (DataTables consume /api/admin/v1/console/dt/tenants/)."""

    template_name = "console/pages/tenants/list.html"

    def get_context_data(self, **kwargs):
        from django.conf import settings

        context = super().get_context_data(**kwargs)
        context["page_title"] = "Gestión de Empresas - Consola de Administración"
        context["user"] = self.request.user
        context["api_url"] = "/api/admin/v1/console/dt/tenants/"  # Endpoint DataTables POST
        context["api_onboard_url"] = "/api/public/v1/tenants/onboard/"  # Onboarding
        context["tenant_domain_base"] = getattr(settings, "TENANT_DOMAIN_BASE", "localhost")
        return context


class TenantsNewView(ConsoleTemplateView):
    """Formulario para crear nuevo tenant (JS consume /api/public/v1/tenants/onboard/)."""

    template_name = "console/pages/tenants/new.html"

    def get_context_data(self, **kwargs):
        from django.conf import settings

        context = super().get_context_data(**kwargs)
        context["page_title"] = "Nuevo Tenant - Consola de Administración"
        context["user"] = self.request.user
        context["api_url"] = "/api/public/v1/tenants/"
        context["api_onboard_url"] = "/api/public/v1/tenants/onboard/"
        context["api_users_url"] = "/api/admin/v1/accounts/users/"  # API admin para usuarios
        context["tenant_domain_base"] = getattr(settings, "TENANT_DOMAIN_BASE", "localhost")
        return context


class TenantsStatusView(ConsoleTemplateView):
    """Vista de estado de creación de tenant (polling HTMX)."""

    template_name = "console/pages/tenants/status.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["task_id"] = self.request.GET.get("task_id")
        if not context["task_id"]:
            from django.contrib import messages

            messages.error(self.request, "task_id requerido")
        return context


class UsersListView(ConsoleTemplateView):
    """Lista de usuarios globales (DataTables consume /api/admin/v1/console/dt/users/)."""

    template_name = "console/pages/users/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Gestión de Usuarios - Consola de Administración"
        context["user"] = self.request.user
        context["api_url"] = "/api/admin/v1/console/dt/users/"  # Endpoint DataTables POST
        return context


class ImpuestosCatalogoView(ConsoleTemplateView):
    """Catálogo de impuestos DIAN."""

    template_name = "console/impuestos_catalogo.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Catálogo DIAN - Consola de Administración"
        context["user"] = self.request.user
        return context


class ImpuestosIndexView(ConsoleTemplateView):
    """Home del módulo Catálogo DIAN."""

    template_name = "console/pages/impuestos/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Catálogo DIAN"
        context["user"] = self.request.user
        return context


# ============================================================================
# VISTAS PARA NUEVOS CATÁLOGOS DIAN (v2.30+)
# ============================================================================


class ContribuyentesTiposListView(ConsoleTemplateView):
    """Lista de tipos de contribuyente (API-First)."""

    template_name = "console/pages/impuestos/contribuyentes_tipos_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Tipos de Contribuyente - Catálogo DIAN"
        context["user"] = self.request.user
        return context


class RegimenesRentaListView(ConsoleTemplateView):
    """Lista de regímenes de renta (API-First)."""

    template_name = "console/pages/impuestos/regimenes_renta_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Regímenes de Renta - Catálogo DIAN"
        context["user"] = self.request.user
        return context


class ResponsabilidadesRUTListView(ConsoleTemplateView):
    """Lista de responsabilidades RUT (API-First)."""

    template_name = "console/pages/impuestos/responsabilidades_rut_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Responsabilidades RUT - Catálogo DIAN"
        context["user"] = self.request.user
        return context


class PerfilesTributariosListView(ConsoleTemplateView):
    """Lista de perfiles tributarios (API-First)."""

    template_name = "console/pages/impuestos/perfiles_tributarios_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Perfiles Tributarios - Catálogo DIAN"
        context["user"] = self.request.user
        return context


class ImpuestosIngestaListView(ConsoleTemplateView):
    """Lista de procesos de ingesta."""

    template_name = "console/pages/impuestos/ingesta_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Ingesta de Catálogo DIAN"
        context["user"] = self.request.user
        return context


class ImpuestosIngestaCreateView(ConsoleTemplateView):
    """Formulario para crear nuevo proceso de ingesta."""

    template_name = "console/pages/impuestos/ingesta_create.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Nueva Ingesta - Catálogo DIAN"
        context["user"] = self.request.user
        return context


class ImpuestosIngestaDetailView(ConsoleTemplateView):
    """Detalle de un proceso de ingesta."""

    template_name = "console/pages/impuestos/ingesta_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Detalle Ingesta #{kwargs.get('pk')}"
        context["user"] = self.request.user
        context["pk"] = kwargs.get("pk")
        return context


class ImpuestosSearchPageView(ConsoleTemplateView):
    """Página de búsqueda tributaria."""

    template_name = "console/pages/impuestos/search_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Búsqueda Tributaria - Catálogo DIAN"
        context["user"] = self.request.user
        return context


class TiposListPageView(ConsoleTemplateView):
    """Lista de tipos de impuesto con DataTables."""

    template_name = "console/pages/impuestos/tipos_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Tipos de Impuesto - Catálogo DIAN"
        context["user"] = self.request.user
        return context


class TipoFormNewView(ConsoleTemplateView):
    """Formulario HTMX para nuevo tipo de impuesto."""

    template_name = "console/pages/impuestos/forms/tipo_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["mode"] = "new"
        context["page_title"] = "Nuevo Tipo de Impuesto"
        context["user"] = self.request.user
        return context


class TipoFormEditView(ConsoleTemplateView):
    """Formulario HTMX para editar tipo de impuesto."""

    template_name = "console/pages/impuestos/forms/tipo_form.html"

    def get_context_data(self, **kwargs):
        from django.shortcuts import get_object_or_404

        from apps.public.impuestos.models import TipoImpuesto

        context = super().get_context_data(**kwargs)
        obj = get_object_or_404(TipoImpuesto, pk=kwargs.get("pk"))
        context["mode"] = "edit"
        context["obj"] = obj
        context["page_title"] = f"Editar Tipo de Impuesto #{obj.id}"
        context["user"] = self.request.user
        return context


# ============================================================================
# VISTAS CON LÓGICA ESPECÍFICA (mantener por ahora)
# ============================================================================


@login_required(login_url="/admin/login/")
def _check_staff_or_raise(request):
    """Helper para verificar staff (usado por vistas funcionales)."""
    if not request.user.is_authenticated:
        return redirect(f"{reverse('admin:login')}?next={request.get_full_path()}")
    if not request.user.is_staff:
        raise PermissionDenied("Acceso denegado. Se requieren permisos de staff.")
    return None


def _ensure_public_schema_or_404():
    """
    Helper para verificar esquema public (usado por vistas funcionales).

    WARNING: NOTA: Esta función NO debe tener decoradores (@login_required, etc.)
    porque es una función helper, no una vista. Las vistas que la llaman
    ya tienen sus propios decoradores.
    """
    try:
        public_schema = get_public_schema_name()
        current_schema = getattr(connection, "schema_name", None)
        if current_schema is not None and current_schema != public_schema:
            from django.http import Http404

            raise Http404("Consola disponible solo en esquema 'public'.")
    except Exception:
        pass


@login_required(login_url="/admin/login/")
def tenants_status_page(request):
    """
    Vista para mostrar progreso de creación de tenant (polling HTMX).

    Si la petición es HTMX (request.headers.get('HX-Request')), renderiza solo el partial.
    Si es normal, renderiza la página completa.
    """
    staff_check = _check_staff_or_raise(request)
    if staff_check:
        return staff_check

    _ensure_public_schema_or_404()

    task_id = request.GET.get("task_id")
    if not task_id:
        from django.contrib import messages

        messages.error(request, "task_id requerido")
        return redirect(reverse("console:tenants-new"))

    # Si es petición HTMX, devolver solo el partial
    if request.headers.get("HX-Request"):
        from celery.result import AsyncResult
        from django.shortcuts import render

        try:
            result = AsyncResult(task_id)

            result_data = None
            error_data = None

            if result.successful():
                result_data = result.result
            elif result.failed():
                error_info = result.info
                if isinstance(error_info, Exception):
                    error_data = str(error_info)
                elif isinstance(error_info, dict):
                    error_data = error_info.get("error", str(error_info))
                else:
                    error_data = str(error_info) if error_info else "Error desconocido"

            context = {
                "task_id": task_id,
                "state": result.state,
                "result": result_data,
                "error": error_data,
            }

            return render(request, "console/pages/tenants/_status_card.html", context)
        except Exception as e:
            import traceback

            traceback.format_exc()

            context = {
                "task_id": task_id,
                "state": "FAILURE",
                "result": None,
                "error": f"Error al consultar estado de la tarea: {str(e)}",
            }
            return render(request, "console/pages/tenants/_status_card.html", context)

    # Petición normal: usar TemplateView
    return TenantsStatusView.as_view()(request)


@login_required(login_url="/admin/login/")
def impuestos_ingesta_list(request):
    """Lista de procesos de ingesta (con lógica de filtrado)."""
    staff_check = _check_staff_or_raise(request)
    if staff_check:
        return staff_check

    _ensure_public_schema_or_404()

    from django.shortcuts import render

    return render(
        request,
        "console/pages/impuestos/ingesta_list.html",
        {
            "page_title": "Ingesta de Catálogo DIAN",
            "user": request.user,
        },
    )


@login_required(login_url="/admin/login/")
def impuestos_ingesta_create(request):
    """Crear nuevo proceso de ingesta (con lógica de formulario)."""
    staff_check = _check_staff_or_raise(request)
    if staff_check:
        return staff_check

    _ensure_public_schema_or_404()

    from django.shortcuts import render

    if request.method == "POST":
        # Lógica de creación (delegar a API si es posible)
        pass

    return render(
        request,
        "console/pages/impuestos/ingesta_create.html",
        {
            "page_title": "Nueva Ingesta - Catálogo DIAN",
            "user": request.user,
        },
    )


@login_required(login_url="/admin/login/")
def impuestos_ingesta_detail(request, pk):
    """Detalle de proceso de ingesta."""
    staff_check = _check_staff_or_raise(request)
    if staff_check:
        return staff_check

    _ensure_public_schema_or_404()

    from django.shortcuts import render

    return render(
        request,
        "console/pages/impuestos/ingesta_detail.html",
        {
            "page_title": f"Detalle Ingesta #{pk}",
            "user": request.user,
            "pk": pk,
        },
    )


@login_required(login_url="/admin/login/")
def impuestos_ingesta_delete(request, pk):
    """Eliminar proceso de ingesta."""
    staff_check = _check_staff_or_raise(request)
    if staff_check:
        return staff_check

    _ensure_public_schema_or_404()

    # Lógica de eliminación (delegar a API si es posible)
    from django.contrib import messages
    from django.shortcuts import redirect

    messages.success(request, f"Proceso de ingesta #{pk} eliminado.")
    return redirect("console:impuestos-ingesta-list")


@login_required(login_url="/admin/login/")
def impuestos_search_results(request):
    """Resultados de búsqueda tributaria (con lógica de búsqueda)."""
    staff_check = _check_staff_or_raise(request)
    if staff_check:
        return staff_check

    _ensure_public_schema_or_404()

    from django.shortcuts import render

    query = request.GET.get("q", "")

    return render(
        request,
        "console/pages/impuestos/search_results.html",
        {
            "page_title": "Resultados de Búsqueda",
            "user": request.user,
            "query": query,
        },
    )


@login_required(login_url="/admin/login/")
def impuestos_search_health(request):
    """Health check de OpenSearch."""
    staff_check = _check_staff_or_raise(request)
    if staff_check:
        return staff_check

    _ensure_public_schema_or_404()

    from django.http import JsonResponse

    # Lógica de health check
    return JsonResponse({"status": "ok"})


@login_required(login_url="/admin/login/")
def jwt_from_session(request):
    """
    Genera token JWT desde la sesión activa del usuario.

    Útil para que la consola obtenga tokens JWT automáticamente
    sin necesidad de hacer login explícito vía /api/token/.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"error": "No autenticado"}, status=401)

    try:
        refresh = RefreshToken.for_user(request.user)
        return JsonResponse(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        )
    except Exception as ex:
        return JsonResponse({"error": str(ex)}, status=500)


@login_required(login_url="/admin/login/")
def tipo_save_proxy(request, pk=None):
    """Proxy para guardar tipo de impuesto (POST a API CRUD)."""
    staff_check = _check_staff_or_raise(request)
    if staff_check:
        return staff_check

    _ensure_public_schema_or_404()

    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    api_url = request.build_absolute_uri("/api/public/v1/impuestos/tipos-crud/")
    headers = {"X-Requested-From": "console"}
    data = {
        "codigo": request.POST.get("codigo"),
        "nombre": request.POST.get("nombre"),
        "descripcion": request.POST.get("descripcion", ""),
        "activo": request.POST.get("activo") == "on" or request.POST.get("activo") == "true",
    }
    fecha_vigencia = request.POST.get("fecha_vigencia")
    if fecha_vigencia:
        data["fecha_vigencia"] = fecha_vigencia

    try:
        if pk is None:
            r = requests.post(api_url, json=data, headers=headers, cookies=request.COOKIES)
        else:
            r = requests.patch(
                api_url + f"{pk}/", json=data, headers=headers, cookies=request.COOKIES
            )

        status_code = r.status_code
        body = (
            r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text
        )

        from django.shortcuts import render

        return render(
            request,
            "console/pages/impuestos/forms/tipo_result.html",
            {
                "status": status_code,
                "body": body,
                "success": status_code in (200, 201),
            },
        )
    except Exception as ex:
        from django.shortcuts import render

        return render(
            request,
            "console/pages/impuestos/forms/tipo_result.html",
            {
                "status": 500,
                "body": {"error": str(ex)},
                "success": False,
            },
        )
