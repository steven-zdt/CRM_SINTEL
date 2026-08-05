"""
Comando de management para corregir dominios sin TLD a <schema>.<TENANT_DOMAIN_BASE> (FQDN).

Uso:
    python manage.py fix_tenant_domains

Este comando:
- Identifica dominios sin TLD o con formato incorrecto
- Los corrige al formato <schema>.<TENANT_DOMAIN_BASE> (ej: cliente.sintel.net.co)
- Normaliza y valida el FQDN antes de guardar
- Muestra un resumen de cambios realizados
"""

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.public.tenants.models import Domain
from apps.public.tenants.utils import normalize_domain, validate_fqdn


class Command(BaseCommand):
    help = "Corrige dominios sin TLD a <schema>.<TENANT_DOMAIN_BASE> (FQDN)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simular cambios sin guardar en la base de datos",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Forzar corrección incluso si el dominio parece válido",
        )

    def handle(self, *args, **options):
        base = getattr(settings, "TENANT_DOMAIN_BASE", "sintel.net.co")
        dry_run = options["dry_run"]
        force = options["force"]

        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("🔧 CORRECCIÓN DE DOMINIOS A FQDN"))
        self.stdout.write("=" * 60)
        self.stdout.write("\n📋 Configuración:")
        self.stdout.write(f"   TENANT_DOMAIN_BASE: {base}")
        self.stdout.write(f"   Modo: {'DRY RUN (simulación)' if dry_run else 'EJECUCIÓN REAL'}")
        self.stdout.write(f"   Forzar: {'Sí' if force else 'No'}")

        changed = 0
        errors = 0

        with transaction.atomic():
            domains = Domain.objects.select_related("tenant").all()
            total = domains.count()

            self.stdout.write(f"\n🔍 Analizando {total} dominio(s)...\n")

            for d in domains:
                dom = (d.domain or "").strip().lower()
                schema = d.tenant.schema_name
                desired = normalize_domain(f"{schema}.{base}")

                # Heurística: detectar dominios que necesitan corrección
                needs_fix = False
                reason = ""

                if not dom:
                    needs_fix = True
                    reason = "dominio vacío"
                elif "." not in dom:
                    needs_fix = True
                    reason = "sin punto (no es FQDN)"
                elif not validate_fqdn(dom):
                    needs_fix = True
                    reason = "FQDN inválido"
                elif dom.endswith(f".{base.split('.')[0]}"):  # ej: termina en ".sintel" sin TLD
                    needs_fix = True
                    reason = f"termina en '.{base.split('.')[0]}' (sin TLD)"
                elif force and dom != desired:
                    needs_fix = True
                    reason = "forzado (diferente al formato esperado)"

                if needs_fix:
                    # Validar el dominio deseado
                    try:
                        if not validate_fqdn(desired):
                            self.stdout.write(
                                self.style.ERROR(
                                    f"  ERROR: {dom} -> {desired} (ERROR: FQDN inválido)"
                                )
                            )
                            errors += 1
                            continue
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"  ERROR: {dom} -> {desired} (ERROR: {e})")
                        )
                        errors += 1
                        continue

                    # Verificar que no haya conflicto
                    existing = Domain.objects.filter(domain=desired).exclude(pk=d.pk).first()
                    if existing:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  WARNING:  {dom} -> {desired} (OMITIDO: ya existe para tenant '{existing.tenant.schema_name}')"
                            )
                        )
                        errors += 1
                        continue

                    # Mostrar cambio
                    self.stdout.write(self.style.WARNING(f"  🔄 {dom} -> {desired} ({reason})"))

                    if not dry_run:
                        d.domain = desired
                        d.save(update_fields=["domain"])

                    changed += 1
                else:
                    # Dominio ya está correcto
                    if force or options.get("verbosity", 1) >= 2:
                        self.stdout.write(self.style.SUCCESS(f"  OK: {dom} (correcto)"))

        # Resumen
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("📋 RESUMEN"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"  Total de dominios analizados: {total}")
        self.stdout.write(f"  Dominios corregidos: {changed}")
        self.stdout.write(f"  Errores/conflictos: {errors}")
        self.stdout.write(f"  Sin cambios: {total - changed - errors}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\nWARNING:  MODO DRY RUN: No se guardaron cambios. "
                    "Ejecuta sin --dry-run para aplicar los cambios."
                )
            )
        elif changed > 0:
            self.stdout.write(
                self.style.SUCCESS(f"\nOK: {changed} dominio(s) corregido(s) exitosamente")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("\nOK: Todos los dominios ya están en el formato correcto")
            )

        if errors > 0:
            self.stdout.write(
                self.style.ERROR(
                    f"\nWARNING:  {errors} dominio(s) tuvieron errores o conflictos. "
                    "Revisa los mensajes arriba."
                )
            )
