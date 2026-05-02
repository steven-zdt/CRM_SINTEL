"""
Vistas del dashboard de ingesta.

UI server-rendered que consume la API DRF existente.
"""

import requests
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import TemplateView

from apps.public.impuestos.models import DocumentoFuente

API_BASE = "/api/public/v1/impuestos"


class StaffRequired(UserPassesTestMixin):
    """Mixin para requerir permisos de staff."""

    def test_func(self):
        return self.request.user.is_staff


class HomeImpuestosView(LoginRequiredMixin, StaffRequired, TemplateView):
    """Vista de entrada al módulo de Catálogo DIAN."""

    template_name = "impuestos_dashboard/home.html"


class IngestaListView(LoginRequiredMixin, StaffRequired, TemplateView):
    """Lista de documentos de ingesta con filtros."""

    template_name = "impuestos_dashboard/ingesta_list.html"

    def get(self, request, *args, **kwargs):
        qs = DocumentoFuente.objects.all().order_by("-created_at")

        # Filtros básicos por querystring
        estado = request.GET.get("estado")
        fuente = request.GET.get("fuente")

        if estado:
            qs = qs.filter(estado=estado)
        if fuente:
            qs = qs.filter(fuente__icontains=fuente)

        ctx = {
            "docs": qs[:200],  # Limitar a 200 para performance
            "filtro_estado": estado,
            "filtro_fuente": fuente,
        }
        return render(request, self.template_name, ctx)


class IngestaCreateView(LoginRequiredMixin, StaffRequired, TemplateView):
    """Vista para crear nueva ingesta (archivo o URL)."""

    template_name = "impuestos_dashboard/ingesta_create.html"

    def post(self, request, *args, **kwargs):
        """Procesar creación de documento vía API DRF."""
        # Detectar si viene archivo o URL
        endpoint = f"{API_BASE}/ingesta/"
        headers = {
            "X-Requested-From": "dashboard",
            "Authorization": f"Token {request.session.get('auth_token', '')}"
            if request.session.get("auth_token")
            else None,
        }
        # Remover None del dict
        headers = {k: v for k, v in headers.items() if v is not None}

        files = None
        data = {}

        # Preparar datos según el tipo de request
        if "archivo" in request.FILES:
            # Multipart: archivo + metadata
            files = {"archivo": request.FILES["archivo"]}
            data = {
                "fuente": request.POST.get("fuente", "DIAN"),
                "tipo": request.POST.get("tipo", "PDF"),
            }
            if request.POST.get("fecha_publicacion"):
                data["fecha_publicacion"] = request.POST.get("fecha_publicacion")
        else:
            # JSON: URL + metadata
            data = {
                "url_origen": request.POST.get("url_origen"),
                "fuente": request.POST.get("fuente", "DIAN"),
                "tipo": request.POST.get("tipo", "PDF"),
            }
            if request.POST.get("fecha_publicacion"):
                data["fecha_publicacion"] = request.POST.get("fecha_publicacion")

        try:
            # Construir URL absoluta
            absolute_url = request.build_absolute_uri(endpoint)

            # Preparar cookies de sesión para autenticación
            cookies = {}
            if request.user.is_authenticated:
                # Usar sesión de Django para autenticación
                cookies = request.COOKIES

            if files:
                # POST multipart hacia API DRF
                r = requests.post(
                    absolute_url,
                    files=files,
                    data=data,
                    headers=headers,
                    cookies=cookies,
                    timeout=300,  # Timeout largo para archivos grandes
                )
            else:
                # POST JSON hacia API DRF
                r = requests.post(
                    absolute_url,
                    json=data,
                    headers=headers,
                    cookies=cookies,
                    timeout=60,
                )

            if r.status_code in (201, 202):
                messages.success(request, "Documento creado exitosamente. Procesamiento iniciado.")
                return redirect("impuestos_dashboard:ingesta_list")

            if r.status_code == 429:
                # Throttling: mostrar Retry-After
                retry_after = r.headers.get("Retry-After", "unos segundos")
                error_msg = f"Has alcanzado el límite de requests. Intenta de nuevo en {retry_after} segundos."
                return render(
                    request,
                    self.template_name,
                    {"error": error_msg, "retry_after": retry_after},
                    status=429,
                )

            # Otros errores
            error_data = (
                r.json()
                if r.headers.get("content-type", "").startswith("application/json")
                else r.text
            )
            return render(
                request,
                self.template_name,
                {"error": f"Error {r.status_code}: {error_data}"},
                status=r.status_code,
            )

        except requests.exceptions.Timeout:
            return render(
                request,
                self.template_name,
                {"error": "Timeout al comunicarse con la API. Intenta de nuevo."},
                status=500,
            )
        except Exception as ex:
            return render(
                request, self.template_name, {"error": f"Error inesperado: {str(ex)}"}, status=500
            )


class IngestaDetailView(LoginRequiredMixin, StaffRequired, TemplateView):
    """Detalle de documento con logs."""

    template_name = "impuestos_dashboard/ingesta_detail.html"

    def get(self, request, pk, *args, **kwargs):
        doc = get_object_or_404(DocumentoFuente, pk=pk)
        return render(request, self.template_name, {"doc": doc})


# --- HTMX fragments ---


def htmx_refresh_row(request, pk):
    """Fragmento HTMX para refrescar una fila de la tabla."""
    if not (request.user.is_authenticated and request.user.is_staff):
        return HttpResponse(status=403)

    doc = get_object_or_404(DocumentoFuente, pk=pk)
    return render(request, "console/pages/impuestos/fragments/ingesta_row.html", {"doc": doc})


def htmx_logs_fragment(request, pk):
    """Fragmento HTMX para mostrar logs de un documento."""
    if not (request.user.is_authenticated and request.user.is_staff):
        return HttpResponse(status=403)

    doc = get_object_or_404(DocumentoFuente, pk=pk)
    logs = doc.logs.order_by("-ts")[:200]
    return render(
        request, "console/pages/impuestos/fragments/logs.html", {"doc": doc, "logs": logs}
    )


# --- Acciones ---


def action_reintentar_descarga(request, pk):
    """Reencolar tarea de descarga."""
    if not (request.user.is_authenticated and request.user.is_staff):
        return HttpResponse(status=403)

    from apps.public.impuestos.tasks import descargar_fuente

    doc = get_object_or_404(DocumentoFuente, pk=pk)

    # Reencolar descarga (Celery)
    descargar_fuente.delay(doc.id)

    # Actualizar estado
    doc.estado = "RECIBIDO"
    doc.save(update_fields=["estado"])

    # Retornar fila actualizada
    return htmx_refresh_row(request, pk)


def action_reintentar_procesar(request, pk):
    """Reencolar tarea de procesamiento."""
    if not (request.user.is_authenticated and request.user.is_staff):
        return HttpResponse(status=403)

    from apps.public.impuestos.tasks import procesar_fuente

    doc = get_object_or_404(DocumentoFuente, pk=pk)

    # Reencolar procesamiento (Celery)
    procesar_fuente.delay(doc.id)

    # Actualizar estado
    doc.estado = "EN_PROCESO"
    doc.save(update_fields=["estado"])

    # Retornar fila actualizada
    return htmx_refresh_row(request, pk)
