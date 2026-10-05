"""
Management command (PLAN_AJUSTE_CICLO_PROYECTOS_FASE_1_VIABILIDAD_
APROBACION, Seccion 61 "Backfill propuesto para facturas"): crea el
vinculo explicito `ProyectoFacturaVenta` para Proyectos que ya tenian un
`factura_costo` asignado ANTES de que existiera esta Fase 1, cuando esa
Factura es realmente una Factura de Venta ACEPTADA (unico criterio
valido, Decision 03). Nunca toca `factura_costo` (se conserva intacto,
Seccion 9: "NO repurposear factura_costo"). Nunca "corrige" en silencio
un caso no migrable -- se reporta explicitamente (Seccion 61.5).

Uso:
    python manage.py backfill_proyecto_facturas_venta
    python manage.py backfill_proyecto_facturas_venta --tenants=1,2
    python manage.py backfill_proyecto_facturas_venta --dry-run
"""

from django.core.management.base import BaseCommand
from django_tenants.utils import get_tenant_model, schema_context

Tenant = get_tenant_model()


class Command(BaseCommand):
    help = (
        "Backfill: crea ProyectoFacturaVenta desde Proyecto.factura_costo "
        "para Proyectos existentes, cuando esa Factura es VENTA+ACEPTADA."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenants",
            type=str,
            default=None,
            help="Comma-separated tenant IDs. Por defecto, todos los tenants.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Solo reporta que se migraria, sin escribir cambios.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if options["tenants"]:
            tenant_ids = [int(t.strip()) for t in options["tenants"].split(",")]
            tenants = Tenant.objects.filter(pk__in=tenant_ids).exclude(schema_name="public")
        else:
            tenants = Tenant.objects.exclude(schema_name="public")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: no se escribira ningun cambio."))

        totales = {"migrados": 0, "omitidos": 0}

        for tenant in tenants:
            self.stdout.write(f"Tenant: {tenant.schema_name} (id={tenant.pk})")
            with schema_context(tenant.schema_name):
                from apps.tenant.facturas.models import Factura
                from apps.tenant.proyectos.models import Proyecto, ProyectoFacturaVenta

                candidatos = (
                    Proyecto.objects.filter(factura_costo_id__isnull=False)
                    .only("id", "uuid", "nombre", "empresa_id", "factura_costo_id")
                    .order_by("id")
                )

                if not candidatos.exists():
                    self.stdout.write("  Sin proyectos candidatos, se omite.")
                    continue

                omitidos_tenant = []
                migrados_tenant = 0
                for proyecto in candidatos.iterator(chunk_size=200):
                    factura = (
                        Factura.objects.filter(
                            pk=proyecto.factura_costo_id, empresa_id=proyecto.empresa_id
                        )
                        .only("id", "uuid", "numero", "naturaleza", "estado")
                        .first()
                    )
                    if not factura:
                        omitidos_tenant.append(
                            (proyecto.nombre, "factura_costo no existe o es de otro tenant")
                        )
                        continue
                    if factura.naturaleza != Factura.Naturaleza.VENTA:
                        omitidos_tenant.append(
                            (proyecto.nombre, f"factura_costo no es de VENTA (naturaleza={factura.naturaleza})")
                        )
                        continue
                    if factura.estado != Factura.Estado.ACEPTADA:
                        omitidos_tenant.append(
                            (proyecto.nombre, f"factura_costo no esta ACEPTADA (estado={factura.estado})")
                        )
                        continue

                    if ProyectoFacturaVenta.objects.filter(
                        proyecto_id=proyecto.id, factura_uuid=factura.uuid
                    ).exists():
                        omitidos_tenant.append((proyecto.nombre, "ya tenia el vinculo (idempotente)"))
                        continue

                    if dry_run:
                        self.stdout.write(f"  [DRY RUN] migraria: {proyecto.nombre} -> Factura {factura.numero}")
                        migrados_tenant += 1
                        continue

                    ProyectoFacturaVenta.objects.create(
                        empresa_id=proyecto.empresa_id,
                        proyecto_id=proyecto.id,
                        factura_uuid=factura.uuid,
                        factura_numero=factura.numero,
                        vinculado_por=None,
                    )
                    self.stdout.write(f"  Migrado: {proyecto.nombre} -> Factura {factura.numero}")
                    migrados_tenant += 1

                for nombre, motivo in omitidos_tenant:
                    self.stdout.write(self.style.WARNING(f"  Omitido: {nombre} -- {motivo}"))

                totales["migrados"] += migrados_tenant
                totales["omitidos"] += len(omitidos_tenant)

        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill completo: migrados={totales['migrados']}, omitidos={totales['omitidos']}"
                + (" (dry-run, sin escribir)" if dry_run else "")
            )
        )
