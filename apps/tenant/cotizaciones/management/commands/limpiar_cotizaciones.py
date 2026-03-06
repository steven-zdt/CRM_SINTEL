"""
Comando de gestión para limpiar todos los datos de la app cotizaciones.

⚠️ ADVERTENCIA: Este comando elimina TODOS los datos de las tablas de cotizaciones.
Incluye:
- CotizacionItem (ítems de cotizaciones)
- Cotizacion (cotizaciones)
- Producto (catálogo de productos)
- Servicio (catálogo de servicios)
- ConfiguracionCotizacion (perfiles de configuración)

Uso (Local):
    python manage.py tenant_command limpiar_cotizaciones --schema=tenant_name --confirm
    python manage.py all_tenants_command limpiar_cotizaciones --confirm

Uso (Docker - Comandos directos):
    # Para un tenant específico:
    docker compose -f infra/compose/docker-compose.yml exec -T app python manage.py tenant_command limpiar_cotizaciones --schema=tenant_name --confirm
    
    # Para todos los tenants:
    docker compose -f infra/compose/docker-compose.yml exec -T app python manage.py all_tenants_command limpiar_cotizaciones --confirm
    
    # Modo simulación (ver qué se eliminaría):
    docker compose -f infra/compose/docker-compose.yml exec -T app python manage.py tenant_command limpiar_cotizaciones --schema=tenant_name --dry-run

Uso (Docker - Scripts helper):
    # Linux/Mac:
    ./scripts/limpiar_cotizaciones.sh tenant_name --confirm
    ./scripts/limpiar_cotizaciones.sh all --confirm
    
    # Windows (PowerShell):
    .\scripts\limpiar_cotizaciones.ps1 tenant_name -Confirm
    .\scripts\limpiar_cotizaciones.ps1 all -Confirm
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count

from apps.tenant.cotizaciones.models import (
    CotizacionItem,
    Cotizacion,
    Producto,
    Servicio
)
from apps.tenant.cotizaciones.configuracion.models import ConfiguracionCotizacion


class Command(BaseCommand):
    help = "Elimina todos los datos de las tablas de cotizaciones (⚠️ DESTRUCTIVO)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirmar eliminación (requerido para ejecutar)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular sin eliminar (muestra conteos)'
        )

    def handle(self, *args, **options):
        confirm = options.get('confirm', False)
        dry_run = options.get('dry_run', False)

        if not confirm and not dry_run:
            raise CommandError(
                "⚠️ ADVERTENCIA: Este comando eliminará TODOS los datos de cotizaciones.\n"
                "Use --confirm para confirmar o --dry-run para ver qué se eliminaría.\n\n"
                "Uso en Docker:\n"
                "  # Comando directo:\n"
                "  docker compose -f infra/compose/docker-compose.yml exec -T app python manage.py tenant_command limpiar_cotizaciones --schema=tenant_name --confirm\n\n"
                "  # Script helper (Linux/Mac):\n"
                "  ./scripts/limpiar_cotizaciones.sh tenant_name --confirm\n\n"
                "  # Script helper (Windows PowerShell):\n"
                "  .\\scripts\\limpiar_cotizaciones.ps1 tenant_name -Confirm"
            )

        # Obtener información del schema actual (si está disponible)
        from django.db import connection
        schema_name = getattr(connection, 'schema_name', 'unknown')
        
        # Obtener conteos antes de eliminar
        conteos = {
            'cotizacion_items': CotizacionItem.objects.count(),
            'cotizaciones': Cotizacion.objects.count(),
            'productos': Producto.objects.count(),
            'servicios': Servicio.objects.count(),
            'configuraciones': ConfiguracionCotizacion.objects.count(),
        }

        self.stdout.write(self.style.WARNING("\n" + "="*60))
        self.stdout.write(self.style.WARNING("⚠️  LIMPIEZA DE BASE DE DATOS - APP COTIZACIONES"))
        self.stdout.write(self.style.WARNING("="*60 + "\n"))
        
        if schema_name != 'unknown':
            self.stdout.write(f"Schema: {schema_name}\n")

        self.stdout.write("Conteos actuales:")
        for modelo, count in conteos.items():
            self.stdout.write(f"  - {modelo}: {count} registros")

        total = sum(conteos.values())
        self.stdout.write(f"\n  TOTAL: {total} registros a eliminar\n")

        if dry_run:
            self.stdout.write(self.style.SUCCESS("✓ Modo DRY-RUN: No se eliminó nada."))
            return

        if not confirm:
            raise CommandError("Use --confirm para confirmar la eliminación.")

        # Confirmación final
        self.stdout.write(self.style.ERROR("⚠️  ADVERTENCIA FINAL:"))
        self.stdout.write(self.style.ERROR("   Se eliminarán TODOS los datos de:"))
        self.stdout.write(self.style.ERROR("   - CotizacionItem"))
        self.stdout.write(self.style.ERROR("   - Cotizacion"))
        self.stdout.write(self.style.ERROR("   - Producto"))
        self.stdout.write(self.style.ERROR("   - Servicio"))
        self.stdout.write(self.style.ERROR("   - ConfiguracionCotizacion"))
        self.stdout.write(self.style.ERROR("\n   Esta acción NO se puede deshacer.\n"))

        # Proceder con la eliminación en orden (respetando foreign keys)
        try:
            with transaction.atomic():
                self.stdout.write("Eliminando datos...")

                # 1. Eliminar ítems de cotizaciones primero (dependen de Cotizacion)
                deleted_items = CotizacionItem.objects.all().delete()
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Eliminados {deleted_items[0]} CotizacionItem")
                )

                # 2. Eliminar cotizaciones
                deleted_cotizaciones = Cotizacion.objects.all().delete()
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Eliminadas {deleted_cotizaciones[0]} Cotizacion")
                )

                # 3. Eliminar productos del catálogo
                deleted_productos = Producto.objects.all().delete()
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Eliminados {deleted_productos[0]} Producto")
                )

                # 4. Eliminar servicios del catálogo
                deleted_servicios = Servicio.objects.all().delete()
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Eliminados {deleted_servicios[0]} Servicio")
                )

                # 5. Eliminar configuraciones
                deleted_configs = ConfiguracionCotizacion.objects.all().delete()
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Eliminadas {deleted_configs[0]} ConfiguracionCotizacion")
                )

                self.stdout.write(self.style.SUCCESS("\n" + "="*60))
                self.stdout.write(self.style.SUCCESS("✓ LIMPIEZA COMPLETADA EXITOSAMENTE"))
                self.stdout.write(self.style.SUCCESS("="*60 + "\n"))

        except Exception as e:
            raise CommandError(f"Error al eliminar datos: {str(e)}")
