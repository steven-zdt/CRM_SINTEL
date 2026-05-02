"""
Middleware funcional para autorización por membresía del tenant.

WARNING: IMPORTANTE: Este middleware valida que el usuario autenticado tenga
membresía activa en el tenant activo (derivado del hostname) SOLO en rutas PRIVADAS.

Debe ir DESPUÉS de:
- TenantMainMiddleware (para tener request.tenant)
- SessionMiddleware (para tener request.user)
- AuthenticationMiddleware (para tener request.user.is_authenticated)
"""

from django.http import HttpResponseForbidden
from django_tenants.utils import get_public_schema_name

# Prefijos PRIVADOS: aquí defines exactamente qué segmentos requieren membresía
# Puedes añadir '/app', '/secure', '/intranet', '/api/tenant/', etc.
# WARNING: v2.30: /workspace/ es ruta privada que requiere membresía
PRIVATE_PREFIXES = ("/dashboard", "/workspace", "/miapp", "/api/tenant/")

# Nombre del esquema público (obtenido dinámicamente de django-tenants)
PUBLIC_SCHEMA_NAME = get_public_schema_name()


def require_tenant_membership(get_response):
    """
    Enforce de membresía SOLO en rutas PRIVADAS de tenants NO públicos.

    Cualquier ruta que NO empiece por PRIVATE_PREFIXES se considera pública
    a efectos de este middleware y NO se verifica membresía (p.ej. '/', '/login/').

    WARNING: REGLA DE NEGOCIO:
    - Si el usuario está autenticado Y hay un tenant activo (request.tenant):
      → Verificar que existe TenantMembership activa SOLO en rutas privadas
      → Si no existe: 403 Forbidden

    WARNING: EXCEPCIONES:
    - Usuarios anónimos: No se valida (pueden ver landing page y rutas públicas)
    - Sin tenant activo: No se valida (dominio público)
    - Tenant público: No se valida (schema_name == "public")
    - Rutas NO privadas: No se valida (/, /login/, /logout/, estáticos, etc.)

    Args:
        get_response: Función que obtiene la respuesta del siguiente middleware/view

    Returns:
        HttpResponse: Respuesta HTTP (403 si no hay membresía en ruta privada, o continúa normalmente)
    """

    def middleware(request):
        tenant = getattr(request, "tenant", None)  # fijado por TenantMainMiddleware
        path = request.path

        # 0) Tenants públicos: nunca verificar membresía
        if tenant and getattr(tenant, "schema_name", "") == PUBLIC_SCHEMA_NAME:
            return get_response(request)

        # 1) ¿Es una ruta privada?
        is_private = any(path.startswith(pfx) for pfx in PRIVATE_PREFIXES)
        if not is_private:
            # Rutas NO privadas: pasar sin validar membresía
            # (La protección de login la gestionan tus vistas con @login_required si la necesitan)
            return get_response(request)

        # 2) Rutas privadas: solo aplica si el usuario YA está autenticado
        user = getattr(request, "user", None)
        if tenant and user and user.is_authenticated:
            from apps.public.tenants.models import TenantMembership

            ok = TenantMembership.objects.filter(client=tenant, user=user, is_active=True).exists()
            if not ok:
                # Puedes renderizar una plantilla propia en lugar de 403 si lo deseas
                return HttpResponseForbidden("No tienes acceso a este tenant.")
            return get_response(request)

        # 3) Si llega aquí y no está autenticado, deja que la vista aplique @login_required
        # (redireccionará a LOGIN_URL="/login/" según settings)
        return get_response(request)

    return middleware
