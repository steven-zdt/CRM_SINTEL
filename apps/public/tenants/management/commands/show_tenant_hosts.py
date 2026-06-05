"""
Management command: show_tenant_hosts

Muestra las entradas exactas para agregar al archivo hosts del sistema
cuando los subdominios de tenants no resuelven en red local.

Uso:
    python manage.py show_tenant_hosts
    python manage.py show_tenant_hosts --ip 192.168.2.15
    python manage.py show_tenant_hosts --server   # para el servidor (127.0.0.1)
    python manage.py show_tenant_hosts --powershell  # comando PowerShell listo
"""

from django.core.management.base import BaseCommand

from apps.public.tenants.models import Domain


class Command(BaseCommand):
    help = "Muestra entradas hosts para todos los dominios de tenants"

    def add_arguments(self, parser):
        parser.add_argument(
            "--ip",
            default=None,
            help="IP a usar (defecto: 127.0.0.1 para servidor, o especifica la IP del servidor)",
        )
        parser.add_argument(
            "--server",
            action="store_true",
            default=False,
            help="Usar 127.0.0.1 (modo servidor local)",
        )
        parser.add_argument(
            "--powershell",
            action="store_true",
            default=False,
            help="Generar script PowerShell para agregar automaticamente",
        )

    def handle(self, *args, **options):
        ip = options.get("ip")
        server_mode = options.get("server")
        powershell_mode = options.get("powershell")

        if ip:
            target_ip = ip
        elif server_mode:
            target_ip = "127.0.0.1"
        else:
            target_ip = "192.168.2.15"

        domains = (
            Domain.objects.exclude(tenant__schema_name="public")
            .select_related("tenant")
            .values_list("domain", "tenant__schema_name")
            .order_by("tenant__schema_name")
        )

        if not domains:
            self.stdout.write(self.style.WARNING("No hay dominios de tenants registrados."))
            return

        domain_list = [d[0] for d in domains]

        if powershell_mode:
            self._print_powershell(target_ip, domain_list)
        else:
            self._print_plain(target_ip, domain_list, domains)

    def _print_plain(self, ip, domain_list, domains):
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Entradas para agregar al archivo hosts (IP: {ip}):"
            )
        )
        self.stdout.write("")
        self.stdout.write("  Ruta Windows: C:\\Windows\\System32\\drivers\\etc\\hosts")
        self.stdout.write("  Ruta Linux/Mac: /etc/hosts")
        self.stdout.write("")
        self.stdout.write("  --- COPIAR ESTAS LINEAS ---")
        for domain, schema in domains:
            self.stdout.write(f"  {ip:<16} {domain}")
        self.stdout.write("  --- FIN ---")
        self.stdout.write("")
        self.stdout.write(
            self.style.WARNING(
                "  NOTA: En el servidor usa 127.0.0.1. Desde otras maquinas en red usa la IP del servidor."
            )
        )
        self.stdout.write(
            "  Para generar script PowerShell: python manage.py show_tenant_hosts --powershell"
        )
        self.stdout.write("")

    def _print_powershell(self, ip, domain_list):
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS("Script PowerShell (ejecutar como Administrador):")
        )
        self.stdout.write("")
        self.stdout.write('  $hostsPath = "C:\\Windows\\System32\\drivers\\etc\\hosts"')
        self.stdout.write("  $entries = @(")
        for domain in domain_list:
            self.stdout.write(f'      "{ip}   {domain}"')
        self.stdout.write("  )")
        self.stdout.write("  foreach ($entry in $entries) {")
        self.stdout.write(
            "      $hostname = $entry.Split(' ', [System.StringSplitOptions]::RemoveEmptyEntries)[-1]"
        )
        self.stdout.write(
            "      if (-not (Select-String -Path $hostsPath -Pattern ([regex]::Escape($hostname)) -Quiet)) {"
        )
        self.stdout.write(
            '          Add-Content -Path $hostsPath -Value $entry -Encoding UTF8'
        )
        self.stdout.write('          Write-Host "Agregado: $entry" -ForegroundColor Green')
        self.stdout.write("      } else {")
        self.stdout.write(
            '          Write-Host "Ya existe: $hostname" -ForegroundColor Yellow'
        )
        self.stdout.write("      }")
        self.stdout.write("  }")
        self.stdout.write("")
