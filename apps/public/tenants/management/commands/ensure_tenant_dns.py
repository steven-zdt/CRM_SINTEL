"""
Comando MANUAL para registrar A records DNS de tenants activos en Windows Server DNS.

Ejecutar desde el HOST Windows (NO desde Docker) al crear un nuevo tenant privado.
NO tiene ejecucion automatica programada — se invoca manualmente cuando se necesite.

Uso:
    python manage.py ensure_tenant_dns                          # Todos los tenants activos
    python manage.py ensure_tenant_dns --dry-run                # Vista previa sin ejecutar
    python manage.py ensure_tenant_dns --schema <schema_name>  # Un tenant especifico
    python manage.py ensure_tenant_dns --ip <server_ip>        # IP destino personalizada

NOTA: Al agregar un nuevo tenant, ejecutar este comando y tambien agregar manualmente
la linea correspondiente en docker-compose.yaml bajo extra_hosts:
    - "{schema_name}.sintel.net.co:<server_ip>"
Y reiniciar los contenedores: docker compose restart web celery

WARNING [2026-08-05]: Si SOLO estas desarrollando desde una unica maquina (sin necesitar
que otras PCs de la red accedan), es mas simple registrar el hosts file local de Windows
en vez de usar Windows DNS Server + este comando. El archivo hosts mapea IP -> hostname,
NUNCA hostname -> hostname:
    127.0.0.1   home.sintel.net.co          # CORRECTO
    localhost   home.sintel.net.co          # INCORRECTO -- Windows ignora esta linea en
                                             # silencio (sin error visible) porque
                                             # "localhost" no es una IP valida en la
                                             # primera columna. Sintoma: el navegador falla
                                             # con "no se puede resolver el nombre remoto" y
                                             # el log del contenedor no muestra NADA porque
                                             # la request nunca sale de la maquina cliente.
Ver documentacion/INFRA_RED_LOCAL_MULTI_TENANT.md, seccion "Troubleshooting", para el caso
completo de diagnostico. Verificar tambien que SERVER_IP (default abajo) siga siendo la IP
real de la maquina -- el DHCP puede reasignarla (confirmado: cambio de 192.168.2.15 a
192.168.2.200 en este entorno sin que ningun archivo de config se actualizara).
"""
import logging
import subprocess
from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

SERVER_IP: str = getattr(settings, "SERVER_IP", "192.168.2.15")
DNS_ZONE: str = getattr(settings, "TENANT_DOMAIN_BASE", "sintel.net.co")


def _dns_record_exists(subdomain: str, zone: str) -> bool:
    """Verifica si ya existe un A record en Windows DNS."""
    try:
        result = subprocess.run(
            [
                "powershell", "-NoProfile", "-NonInteractive", "-Command",
                f"Get-DnsServerResourceRecord -ZoneName '{zone}' -Name '{subdomain}'"
                f" -RRType A -ErrorAction SilentlyContinue",
            ],
            capture_output=True, text=True, timeout=10,
        )
        return bool(result.stdout.strip())
    except Exception as exc:
        logger.warning("DNS check failed for %s: %s", subdomain, exc)
        return False


def _add_dns_record(subdomain: str, zone: str, ip: str) -> bool:
    """Agrega un A record en Windows DNS via PowerShell."""
    try:
        result = subprocess.run(
            [
                "powershell", "-NoProfile", "-NonInteractive", "-Command",
                f"Add-DnsServerResourceRecordA -ZoneName '{zone}' -Name '{subdomain}'"
                f" -IPv4Address '{ip}' -TimeToLive 01:00:00 -ErrorAction Stop",
            ],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            logger.error("DNS add failed %s.%s: %s", subdomain, zone, result.stderr)
            return False
        return True
    except Exception as exc:
        logger.error("DNS add exception %s.%s: %s", subdomain, zone, exc)
        return False


class Command(BaseCommand):
    help = "Registra A records DNS en Windows Server para todos los tenants activos"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Mostrar que se crearia sin ejecutar nada",
        )
        parser.add_argument(
            "--schema", type=str, default=None,
            help="Procesar solo el tenant con este schema_name. "
                 "Omitir para procesar todos los tenants activos.",
        )
        parser.add_argument(
            "--ip", type=str, default=None,
            help=f"IP destino del A record (default: {SERVER_IP})",
        )
        parser.add_argument(
            "--force", action="store_true",
            help="Agregar aunque el registro ya exista",
        )

    def handle(self, *args, **options):
        from apps.public.tenants.models import Client, Domain

        dry_run: bool = options["dry_run"]
        schema_filter: str | None = options["schema"]
        target_ip: str = options["ip"] or SERVER_IP

        self.stdout.write(f"DNS Zone  : {DNS_ZONE}")
        self.stdout.write(f"Target IP : {target_ip}")
        self.stdout.write(f"Dry-run   : {dry_run}")
        self.stdout.write("-" * 50)

        # EXCEPCION: schema_name="public" es el dominio raiz de la plataforma (sintel.net.co).
        # Su registro DNS se gestiona de forma independiente en el servidor DNS de Windows
        # y NO debe ser modificado por este comando — solo aplica a tenants privados.
        qs = Client.objects.exclude(schema_name="public").filter(is_active=True)
        if schema_filter:
            qs = qs.filter(schema_name=schema_filter)

        created = skipped = errors = 0
        compose_hints = []

        for client in qs:
            domains = Domain.objects.filter(tenant=client, is_primary=True).values_list("domain", flat=True)
            for fqdn in domains:
                if not fqdn.endswith(f".{DNS_ZONE}"):
                    self.stdout.write(self.style.WARNING(f"  SKIP {fqdn} — no es subdominio de {DNS_ZONE}"))
                    continue

                subdomain = fqdn[: -(len(DNS_ZONE) + 1)]

                if not options["force"] and _dns_record_exists(subdomain, DNS_ZONE):
                    self.stdout.write(f"  OK   {fqdn} ya existe")
                    skipped += 1
                    continue

                if dry_run:
                    self.stdout.write(self.style.WARNING(f"  DRY  {fqdn} -> {target_ip}"))
                    created += 1
                    compose_hints.append(fqdn)
                    continue

                if _add_dns_record(subdomain, DNS_ZONE, target_ip):
                    self.stdout.write(self.style.SUCCESS(f"  ADD  {fqdn} -> {target_ip}"))
                    created += 1
                    compose_hints.append(fqdn)
                else:
                    self.stdout.write(self.style.ERROR(f"  ERR  {fqdn}"))
                    errors += 1

        self.stdout.write("-" * 50)
        self.stdout.write(
            f"DNS: {created} {'creados' if not dry_run else 'pendientes'}"
            f" | {skipped} ya existian | {errors} errores"
        )

        if compose_hints:
            self.stdout.write(self.style.WARNING(
                "\nAgregar en docker-compose.yaml extra_hosts y reiniciar:"
            ))
            for fqdn in compose_hints:
                self.stdout.write(f'    - "{fqdn}:{target_ip}"')
            self.stdout.write("Luego: docker compose restart web celery")
