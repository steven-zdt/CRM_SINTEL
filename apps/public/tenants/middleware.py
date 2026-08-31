"""
Middlewares para seguridad y autorización de tenants.

WARNING: IMPORTANTE: Estos middlewares validan seguridad y membresía del tenant.
"""

from django.http import HttpResponse
from django.shortcuts import redirect

from apps.public.tenants.models import TenantMembership


class TenantSecurityMiddleware:
    """
    Middleware que bloquea el acceso a tenants suspendidos (is_active=False)
    y a tenants cuyo periodo de prueba vencio.

    WARNING: SEGURIDAD: Este middleware debe ir DESPUÉS de TenantMainMiddleware
    para tener acceso a request.tenant.

    WARNING: REGLA DE NEGOCIO:
    - Si el tenant está suspendido (is_active=False):
      → Bloquear acceso (excepto rutas públicas como /login/)
      → Retornar 403 o redirección apropiada

    WARNING: EXCEPCIONES:
    - Rutas públicas: /login/, /logout/ (permitir acceso incluso si está suspendido)
    - Sin tenant activo: No se valida (dominio público)

    CONSOLE_TENANTS_CRUD (docs/console/TENANT_LIFECYCLE.md): antes de esta
    correccion, `on_trial`/`paid_until` no tenian NINGUN enforcement --
    campos guardados sin consecuencia funcional (confirmado por auditoria,
    cero referencias en este archivo). Se reconcilia el lifecycle EN CADA
    REQUEST, antes del chequeo de is_active -- garantiza que el bloqueo por
    trial vencido sea efectivo de inmediato, sin depender de que la tarea
    periodica de Celery haya corrido (regla explicita: el runtime protege
    el acceso, Celery solo refleja el estado para el admin). Costo en el
    caso comun (trial vigente): cero queries adicionales -- solo comparacion
    en memoria sobre el objeto `tenant` ya resuelto por TenantMainMiddleware.
    Un UPDATE solo ocurre la primera vez que se detecta la expiracion.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Obtener tenant
        tenant = getattr(request, "tenant", None)

        if tenant:
            from apps.public.tenants.services.lifecycle import (
                is_trial_expired,
                reconcile_tenant_lifecycle,
            )

            trial_expired = is_trial_expired(tenant)
            if trial_expired:
                reconcile_tenant_lifecycle(tenant)

            # Solo validar si el tenant quedo inactivo (por expiracion de
            # trial recien reconciliada arriba, o por suspension manual
            # previa -- is_active ya refleja ambos casos).
            if not tenant.is_active:
                # Rutas públicas que se permiten incluso si el tenant está suspendido
                public_paths = ["/login/", "/logout/"]
                if request.path not in public_paths:
                    if trial_expired:
                        message = (
                            "El periodo de prueba de este tenant ha vencido. "
                            "Contacta al administrador para reactivar el acceso."
                        )
                    else:
                        message = (
                            "Este tenant está suspendido. Por favor, contacta al administrador."
                        )
                    return HttpResponse(message, status=403)

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
