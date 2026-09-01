"""
Tests para CSRFTrustedOriginMiddleware.

[WARNING] REGLA 0: Cero caracteres especiales o emojis. Solo ASCII.

Cubre el hallazgo de la mision LAN_MULTI_TENANT (2026-08-31, "Hallazgo 3",
docs/network/LAN_MULTI_TENANT_FINAL_REPORT.md): cuando el navegador NO envia
un header Origin real, el middleware no debe sintetizar
request.META["HTTP_ORIGIN"], porque ese valor queda visible en la fase de
respuesta para cualquier middleware posterior -- incluido
corsheaders.middleware.CorsMiddleware -- y terminaba reflejandose en
"access-control-allow-origin" filtrando el puerto interno del contenedor
Django (p.ej. ":8000") incluso para requests que llegaron por Nginx en 80/443.
"""

from django.conf import settings
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings

from corsheaders.middleware import CorsMiddleware

from apps.public.core.middleware import CSRFTrustedOriginMiddleware


def _view(request):
    return HttpResponse("ok")


class CSRFTrustedOriginMiddlewareTests(TestCase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    @override_settings(DEBUG=True, CSRF_TRUSTED_ORIGINS=[])
    def test_real_browser_origin_is_preserved_and_trusted(self):
        """Si el navegador manda un Origin real, el middleware lo respeta tal cual."""
        request = self.factory.get(
            "/",
            HTTP_HOST="tenant1.sintel.net.co:8000",
            HTTP_ORIGIN="http://tenant1.sintel.net.co:8000",
        )

        CSRFTrustedOriginMiddleware(_view)(request)

        self.assertEqual(request.META["HTTP_ORIGIN"], "http://tenant1.sintel.net.co:8000")
        self.assertIn("http://tenant1.sintel.net.co:8000", settings.CSRF_TRUSTED_ORIGINS)
        self.assertIn("http://tenant1.sintel.net.co", settings.CSRF_TRUSTED_ORIGINS)

    @override_settings(DEBUG=True, CSRF_TRUSTED_ORIGINS=[])
    def test_missing_origin_is_not_synthesized(self):
        """
        Regresion del fix: sin Origin real (navegacion de pagina completa, curl
        sin -H Origin), el middleware NO debe inventar request.META["HTTP_ORIGIN"].
        Antes del fix, esto sintetizaba "http://admin.sintel.net.co:8000".
        """
        request = self.factory.get("/", HTTP_HOST="admin.sintel.net.co", SERVER_PORT="8000")
        request.META.pop("HTTP_ORIGIN", None)

        CSRFTrustedOriginMiddleware(_view)(request)

        self.assertNotIn("HTTP_ORIGIN", request.META)
        # El proposito real del middleware (poblar CSRF_TRUSTED_ORIGINS) sigue intacto.
        self.assertIn("http://admin.sintel.net.co", settings.CSRF_TRUSTED_ORIGINS)
        self.assertIn("http://admin.sintel.net.co:8000", settings.CSRF_TRUSTED_ORIGINS)

    @override_settings(
        DEBUG=True,
        CSRF_TRUSTED_ORIGINS=[],
        CORS_ALLOWED_ORIGIN_REGEXES=[r"^http://.*\.sintel\.net\.co(:\d+)?$"],
        CORS_ALLOW_CREDENTIALS=True,
    )
    def test_missing_origin_does_not_leak_internal_port_via_cors(self):
        """
        Hallazgo 3 (LAN_MULTI_TENANT): sin Origin real, CorsMiddleware no debe
        reflejar ningun access-control-allow-origin sintetico con el puerto
        interno del contenedor Django.
        """
        request = self.factory.get("/", HTTP_HOST="admin.sintel.net.co", SERVER_PORT="8000")
        request.META.pop("HTTP_ORIGIN", None)

        # Reproduce el orden real de MIDDLEWARE (config/settings.py): CorsMiddleware
        # va antes en la lista, por lo que envuelve a CSRFTrustedOriginMiddleware.
        chain = CorsMiddleware(CSRFTrustedOriginMiddleware(_view))
        response = chain(request)

        headers = {k.lower() for k in response.headers.keys()}
        self.assertNotIn("access-control-allow-origin", headers)

    @override_settings(
        DEBUG=True,
        CSRF_TRUSTED_ORIGINS=[],
        CORS_ALLOWED_ORIGIN_REGEXES=[r"^http://.*\.sintel\.net\.co(:\d+)?$"],
        CORS_ALLOW_CREDENTIALS=True,
    )
    def test_real_origin_is_still_correctly_reflected_by_cors(self):
        """
        Control: un Origin real de navegador (fetch/XHR cross-origin entre tenants)
        debe seguir siendo reflejado normalmente por CorsMiddleware -- el fix no
        debe romper CORS legitimo.
        """
        request = self.factory.get(
            "/",
            HTTP_HOST="admin.sintel.net.co",
            HTTP_ORIGIN="http://tenant1.sintel.net.co",
        )

        chain = CorsMiddleware(CSRFTrustedOriginMiddleware(_view))
        response = chain(request)

        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://tenant1.sintel.net.co")

    @override_settings(DEBUG=False, CSRF_TRUSTED_ORIGINS=["http://sintel.net.co"])
    def test_middleware_is_noop_outside_debug(self):
        """En produccion (DEBUG=False) el middleware no debe tocar nada."""
        request = self.factory.get("/", HTTP_HOST="admin.sintel.net.co", SERVER_PORT="8000")
        request.META.pop("HTTP_ORIGIN", None)
        original_trusted = list(settings.CSRF_TRUSTED_ORIGINS)

        CSRFTrustedOriginMiddleware(_view)(request)

        self.assertNotIn("HTTP_ORIGIN", request.META)
        self.assertEqual(settings.CSRF_TRUSTED_ORIGINS, original_trusted)
