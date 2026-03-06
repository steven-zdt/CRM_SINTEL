import sys
from typing import Optional

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection
from django.urls import get_resolver

from django_tenants.utils import get_public_schema_name

from apps.public.tenants.models import Client, Domain


class Command(BaseCommand):
    help = "Diagnóstico de errores 404 / resolución de tenants para un hostname dado."

    def add_arguments(self, parser):
        parser.add_argument(
            "--host",
            type=str,
            default="home.localhost:8000",
            help="Hostname a diagnosticar (por defecto: home.localhost:8000)",
        )

    def handle(self, *args, **options):
        host = options["host"]
        self.stdout.write(self.style.MIGRATE_HEADING("=== DIAGNÓSTICO 404 TENANTS ==="))
        self.stdout.write(f"Host a diagnosticar: {host}")
        self.stdout.write("")

        self._print_clients_and_domains()

        self.stdout.write("")
        self._simulate_resolution(host)

    # ------------------------------------------------------------------
    # 1) Listar Clients y Domains
    # ------------------------------------------------------------------
    def _print_clients_and_domains(self):
        self.stdout.write(self.style.MIGRATE_LABEL("-> Tenants registrados (Client + Domain):"))

        clients = Client.objects.all().order_by("schema_name")
        if not clients.exists():
            self.stdout.write("  (no hay tenants registrados)")
            return

        for client in clients:
            self.stdout.write(
                f"  - Client: schema='{client.schema_name}', nombre='{client.nombre}', "
                f"is_active={getattr(client, 'is_active', True)}"
            )
            domains = Domain.objects.filter(tenant=client).order_by("-is_primary", "domain")
            if not domains.exists():
                self.stdout.write("      (sin dominios asociados)")
            else:
                for d in domains:
                    self.stdout.write(
                        f"      · Domain: '{d.domain}' "
                        f"(is_primary={d.is_primary})"
                    )

    # ------------------------------------------------------------------
    # 2) Simular resolución para un host dado
    # ------------------------------------------------------------------
    def _simulate_resolution(self, host: str):
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_LABEL("-> Simulación de resolución de tenant para host:"))

        # Emular lógica típica de django-tenants: quitar puerto del host
        hostname = host.split(":", 1)[0].strip().lower()
        self.stdout.write(f"  Host completo recibido : {host}")
        self.stdout.write(f"  Hostname sin puerto    : {hostname}")

        domain_obj: Optional[Domain] = Domain.objects.filter(domain=hostname).first()
        if not domain_obj:
            self.stdout.write(self.style.ERROR(f"  ✗ No se encontró Domain.domain='{hostname}' en BD."))
            return

        tenant = domain_obj.tenant
        self.stdout.write(self.style.SUCCESS("  ✓ Dominio encontrado en BD."))
        self.stdout.write(
            f"    -> Domain: '{domain_obj.domain}' (is_primary={domain_obj.is_primary})"
        )
        self.stdout.write(
            f"    -> Tenant: schema='{tenant.schema_name}', nombre='{tenant.nombre}', "
            f"is_active={getattr(tenant, 'is_active', True)}"
        )

        # Determinar qué URLConf usaría django-tenants para este tenant
        public_schema = get_public_schema_name()
        if tenant.schema_name == public_schema:
            effective_urlconf = settings.ROOT_URLCONF
            scope = "PÚBLICO"
        else:
            effective_urlconf = settings.TENANT_URLCONF
            scope = "TENANT PRIVADO"

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_LABEL("-> URLConf efectivo para este tenant:"))
        self.stdout.write(f"  Esquema               : {tenant.schema_name} ({scope})")
        self.stdout.write(f"  settings.ROOT_URLCONF : {settings.ROOT_URLCONF}")
        self.stdout.write(f"  settings.TENANT_URLCONF: {settings.TENANT_URLCONF}")
        self.stdout.write(f"  URLConf efectivo       : {effective_urlconf}")

        # Forzar el schema en la conexión para emular el contexto del tenant
        try:
            if tenant.schema_name == public_schema:
                connection.set_schema_to_public()
            else:
                connection.set_schema(tenant.schema_name)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Error al cambiar de esquema: {e}"))

        # Listar patrones de URL para la raíz ('')
        self.stdout.write("")
        self._list_root_urls(effective_urlconf)

    # ------------------------------------------------------------------
    # 3) Listar URLs raíz para un URLConf dado
    # ------------------------------------------------------------------
    def _list_root_urls(self, urlconf: str):
        self.stdout.write(self.style.MIGRATE_LABEL("-> Rutas registradas en la raíz ('') para este URLConf:"))
        try:
            resolver = get_resolver(urlconf)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ No se pudo obtener resolver para '{urlconf}': {e}"))
            return

        found_any = False
        for pattern in resolver.url_patterns:
            route = self._pattern_to_string(pattern)
            if route in ("", "^$", "^$?"):
                found_any = True
                name = getattr(pattern, "name", None)
                callback = getattr(pattern, "callback", None)
                callback_name = getattr(callback, "__name__", str(callback)) if callback else "N/A"
                self.stdout.write(
                    f"  - pattern='' name='{name}' view='{callback_name}'"
                )

        if not found_any:
            self.stdout.write("  (no se encontró ninguna ruta explícita para la raíz '')")

    def _pattern_to_string(self, pattern) -> str:
        """
        Convierte un objeto URLPattern / URLResolver a un string de ruta simple.
        Maneja tanto path() (RoutePattern) como re_path() (RegexPattern).
        """
        pat = getattr(pattern, "pattern", None)
        if pat is None:
            return ""

        # Django 2+ RoutePattern
        route = getattr(pat, "_route", None)
        if route is not None:
            return route

        # RegexPattern
        regex = getattr(pat, "regex", None)
        if regex is not None:
            return regex.pattern

        return str(pat)

