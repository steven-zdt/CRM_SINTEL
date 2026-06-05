"""
Comando de management para asegurar que los dominios del tenant público existan.

Este comando es idempotente y no destructivo:
- Crea dominios que no existen
- Marca sintel.com como primario si está en la lista
- NO elimina dominios existentes
- NO modifica dominios que ya están correctamente configurados

Uso:
    python manage.py ensure_public_domains

Variables de entorno:
    PUBLIC_TENANT_DOMAINS: Lista de dominios separados por coma (default: sintel.com,localhost,127.0.0.1)
    PUBLIC_DOMAIN_PROTECT: Si es True, no modifica dominios existentes (default: False)
"""

import os
import re

from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import schema_context

from apps.public.tenants.models import Client, Domain
from apps.public.tenants.utils import normalize_domain, validate_fqdn


def _is_valid_ipv4(host: str) -> bool:
    if not re.match(r'^(\d{1,3}\.){3}\d{1,3}$', host):
        return False
    return all(0 <= int(p) <= 255 for p in host.split('.'))


class Command(BaseCommand):
    help = "Asegura que los dominios del tenant público existan (idempotente y no destructivo)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--domains",
            type=str,
            help="Lista de dominios separados por coma (sobrescribe PUBLIC_TENANT_DOMAINS)",
        )
        parser.add_argument(
            "--primary",
            type=str,
            help="Dominio que debe ser primario (sobrescribe el primero de la lista)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simular cambios sin guardar en la base de datos",
        )

    def handle(self, *args, **options):
        # Obtener lista de dominios desde variables de entorno o argumento
        domains_str = options.get("domains") or os.getenv(
            "PUBLIC_TENANT_DOMAINS", "sintel.com,localhost,127.0.0.1"
        )
        protect = os.getenv("PUBLIC_DOMAIN_PROTECT", "False").lower() == "true"
        dry_run = options.get("dry_run", False)
        primary_domain = options.get("primary") or domains_str.split(",")[0].strip()

        # Parsear lista de dominios
        domains = [d.strip() for d in domains_str.split(",") if d.strip()]

        if not domains:
            self.stdout.write(self.style.ERROR("ERROR: No se proporcionaron dominios"))
            return 1

        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("🛡️ GARANTIZANDO DOMINIOS DEL TENANT PÚBLICO"))
        self.stdout.write("=" * 60)
        self.stdout.write("\n📋 Configuración:")
        self.stdout.write(f"   Dominios requeridos: {', '.join(domains)}")
        self.stdout.write(f"   Dominio primario: {primary_domain}")
        self.stdout.write(f"   Modo protección: {'Activado' if protect else 'Desactivado'}")
        self.stdout.write(f"   Modo: {'DRY RUN (simulación)' if dry_run else 'EJECUCIÓN REAL'}")

        with schema_context("public"):
            # Obtener tenant público
            try:
                public = Client.objects.get(schema_name="public")
                self.stdout.write(f"\nOK: Tenant público encontrado: {public.nombre}")
            except Client.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(
                        "\nERROR: ERROR: Tenant público (schema_name='public') no encontrado"
                    )
                )
                self.stdout.write("   Ejecuta primero: python manage.py setup_public_tenant")
                return 1

            created = 0
            updated = 0
            skipped = 0
            errors = 0

            with transaction.atomic():
                # Procesar cada dominio
                for domain_str in domains:
                    domain_str = domain_str.strip()
                    if not domain_str:
                        continue

                    # Normalizar dominio
                    normalized = normalize_domain(domain_str)

                    # Validar FQDN (permitir localhost, IPs locales y 127.0.0.1 para desarrollo)
                    if (
                        normalized not in ("localhost", "127.0.0.1")
                        and not _is_valid_ipv4(normalized)
                        and not validate_fqdn(normalized)
                    ):
                        self.stdout.write(
                            self.style.WARNING(
                                f"  WARNING:  {domain_str} → {normalized} (FQDN inválido, omitiendo)"
                            )
                        )
                        errors += 1
                        continue

                    # Verificar si existe
                    domain_obj = Domain.objects.filter(domain=normalized, tenant=public).first()

                    if domain_obj:
                        # Dominio existe
                        is_primary = domain_obj.is_primary
                        should_be_primary = normalized == normalize_domain(primary_domain)

                        if should_be_primary and not is_primary:
                            # Debe ser primario pero no lo es
                            if protect:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"  WARNING:  {normalized} (existe, debería ser primario pero modo protección activado)"
                                    )
                                )
                                skipped += 1
                            else:
                                # Desactivar otros primarios primero
                                Domain.objects.filter(tenant=public, is_primary=True).exclude(
                                    pk=domain_obj.pk
                                ).update(is_primary=False)

                                if not dry_run:
                                    domain_obj.is_primary = True
                                    domain_obj.save(update_fields=["is_primary"])

                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f"  🔄 {normalized} (actualizado a primario)"
                                    )
                                )
                                updated += 1
                        else:
                            # Ya está correcto
                            status = "⭐ PRIMARIO" if is_primary else "  "
                            self.stdout.write(
                                self.style.SUCCESS(f"  {status} {normalized} (ya existe)")
                            )
                            skipped += 1
                    else:
                        # Dominio no existe, crearlo
                        should_be_primary = normalized == normalize_domain(primary_domain)

                        # Si va a ser primario, desactivar otros primero
                        if should_be_primary:
                            Domain.objects.filter(tenant=public, is_primary=True).update(
                                is_primary=False
                            )

                        if not dry_run:
                            Domain.objects.create(
                                tenant=public,
                                domain=normalized,
                                is_primary=should_be_primary,
                            )

                        status = "⭐ PRIMARIO" if should_be_primary else "  "
                        self.stdout.write(self.style.SUCCESS(f"  {status} {normalized} (creado)"))
                        created += 1

            # Resumen
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write(self.style.SUCCESS("📋 RESUMEN"))
            self.stdout.write("=" * 60)
            self.stdout.write(f"  Dominios creados: {created}")
            self.stdout.write(f"  Dominios actualizados: {updated}")
            self.stdout.write(f"  Dominios sin cambios: {skipped}")
            self.stdout.write(f"  Errores/omitidos: {errors}")

            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        "\nWARNING:  MODO DRY RUN: No se guardaron cambios. "
                        "Ejecuta sin --dry-run para aplicar los cambios."
                    )
                )
            elif created > 0 or updated > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nOK: {created + updated} dominio(s) procesado(s) exitosamente"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        "\nOK: Todos los dominios ya están configurados correctamente"
                    )
                )

            # Verificación final
            self.stdout.write("\n📋 Dominios finales del tenant público:")
            final_domains = Domain.objects.filter(tenant=public).order_by("-is_primary", "domain")
            for d in final_domains:
                status = "⭐ PRIMARIO" if d.is_primary else "  "
                self.stdout.write(f"  {status} {d.domain}")

            return 0
