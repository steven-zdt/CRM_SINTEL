"""
Middlewares para seguridad y autorización de tenants.

WARNING: IMPORTANTE: Estos middlewares validan seguridad y membresía del tenant.
"""

from django.http import HttpResponse
from django.shortcuts import redirect

from apps.public.tenants.models import TenantMembership


class TenantSecurityMiddleware:
    """
    Middleware que bloquea el acceso a tenants suspendidos (is_active=False).

    WARNING: SEGURIDAD: Este middleware debe ir DESPUÉS de TenantMainMiddleware
    para tener acceso a request.tenant.

    WARNING: REGLA DE NEGOCIO:
    - Si el tenant está suspendido (is_active=False):
      → Bloquear acceso (excepto rutas públicas como /login/)
      → Retornar 403 o redirección apropiada

    WARNING: EXCEPCIONES:
    - Rutas públicas: /login/, /logout/ (permitir acceso incluso si está suspendido)
    - Sin tenant activo: No se valida (dominio público)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Obtener tenant
        tenant = getattr(request, "tenant", None)

        # Solo validar si hay tenant activo
        if tenant and not tenant.is_active:
            # Rutas públicas que se permiten incluso si el tenant está suspendido
            public_paths = ["/login/", "/logout/"]
            if request.path not in public_paths:
                # Tenant suspendido: bloquear acceso
                return HttpResponse(
                    "Este tenant está suspendido. Por favor, contacta al administrador.", status=403
                )

        # Continuar con el siguiente middleware/view
        return self.get_response(request)


def require_tenant_membership(get_response):
    """
    Middleware que valida membresía del tenant para usuarios autenticados.

    WARNING: REGLA DE NEGOCIO:
    - Si el usuario está autenticado Y hay un tenant activo (request.tenant):
      → Verificar que existe TenantMembership activa
      → Si no existe: 403 Forbidden o redirigir a /login/?no_tenant_access=1

    WARNING: EXCEPCIONES:
    - Usuarios anónimos: No se valida (pueden ver landing page)
    - Sin tenant activo: No se valida (dominio público)
    - Rutas públicas: No se valida (/, /login/, /logout/)

    Args:
        get_response: Función que obtiene la respuesta del siguiente middleware/view

    Returns:
        HttpResponse: Respuesta HTTP (403 o redirección si no hay membresía)
    """

    def middleware(request):
        # Obtener tenant y usuario
        tenant = getattr(request, "tenant", None)
        user = getattr(request, "user", None)

        # Solo validar si hay tenant activo y usuario autenticado
        if tenant and user and user.is_authenticated:
            # Rutas públicas que no requieren membresía
            public_paths = ["/", "/login/", "/logout/"]
            if request.path in public_paths:
                return get_response(request)

            # Verificar membresía activa
            has_membership = TenantMembership.objects.filter(
                client=tenant, user=user, is_active=True
            ).exists()

            if not has_membership:
                # Usuario autenticado pero sin membresía en este tenant
                # Opción 1: 403 Forbidden (más estricto)
                # return HttpResponseForbidden("No tienes acceso a este tenant.")

                # Opción 2: Redirigir a login con mensaje (más amigable)
                # WARNING: v2.30: tenant_landing:login eliminado (API-First completo)
                # Usar URL directa ya que las vistas HTML fueron eliminadas
                login_url = "/login/"

                return redirect(f"{login_url}?no_tenant_access=1")

        # Continuar con el siguiente middleware/view
        return get_response(request)

    return middleware
