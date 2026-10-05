"""
Management command (PLAN_PROYECTOS_FASE_2_COTIZACION_RECURSOS_PRESUPUESTO,
Fase 2 "Migracion de datos historicos"): resuelve `Proyecto.cotizacion`
(vinculo directo, nuevo SSoT de Planeacion) a partir del vinculo indirecto
historico `Proyecto.factura_costo -> Factura.cotizacion_uuid`, para los
Proyectos que ya tenian una Factura de centro de costos asignada ANTES de
que existiera la FK directa.

No modifica `factura_costo` (se preserva intacto, Fase 2 del plan: "No
modificar factura_costo"). Nunca sobrescribe un `Proyecto.cotizacion` ya
asignado. Casos no migrables (Factura sin cotizacion, Cotizacion inexistente
o de otro tenant, Cotizacion ya vinculada a otro Proyecto como principal)
se reportan explicitamente -- "No corregir silenciosamente estos casos."

Uso:
    python manage.py backfill_proyecto_cotizacion_desde_factura
    python manage.py backfill_proyecto_cotizacion_desde_factura --tenants=1,2
    python manage.py backfill_proyecto_cotizacion_desde_factura --dry-run
"""

from django.core.management.base import BaseCommand
from django_tenants.utils import get_tenant_model, schema_context

Tenant = get_tenant_model()


class Command(BaseCommand):
    help = (
        "Backfill: Proyecto.cotizacion desde Proyecto.factura_costo.cotizacion_uuid "
        "(vinculo indirecto historico -> vinculo directo)."
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
                from apps.tenant.cotizaciones.models import Cotizacion
                from apps.tenant.facturas.models import Factura
                from apps.tenant.proyectos.models import Proyecto

                candidatos = (
                    Proyecto.objects.filter(
                        factura_costo_id__isnull=False, cotizacion_id__isnull=True
                    )
                    .only("id", "uuid", "nombre", "empresa_id", "factura_costo_id")
                    .order_by("id")
                )

                if not candidatos.exists():
                    self.stdout.write("  Sin proyectos candidatos, se omite.")
                    continue

                omitidos_tenant = []
                for proyecto in candidatos.iterator(chunk_size=200):
                    factura = (
                        Factura.objects.filter(
                            pk=proyecto.factura_costo_id, empresa_id=proyecto.empresa_id
                        )
                        .only("id", "cotizacion_uuid")
                        .first()
                    )
                    if not factura or not factura.cotizacion_uuid:
                        omitidos_tenant.append((proyecto.nombre, "Factura sin cotizacion vinculada"))
                        continue

                    cotizacion = (
                        Cotizacion.objects.filter(
                            uuid=factura.cotizacion_uuid, empresa_id=proyecto.empresa_id
                        )
                        .only("id")
                        .first()
                    )
                    if not cotizacion:
                        omitidos_tenant.append(
                            (
                                proyecto.nombre,
                                f"Cotizacion {factura.cotizacion_uuid} inexistente o de otro tenant",
                            )
                        )
                        continue

                    # Regla de unicidad (Fase 1 del plan): nunca dejar una
                    # Cotizacion como principal de 2 Proyectos -- si otro
                    # Proyecto ya la tiene (dato historico inconsistente real,
                    # no hipotetico), se reporta en vez de romper el
                    # UniqueConstraint silenciosamente.
                    ya_vinculada = (
                        Proyecto.objects.filter(cotizacion_id=cotizacion.id)
                        .exclude(pk=proyecto.pk)
                        .exists()
                    )
                    if ya_vinculada:
                        omitidos_tenant.append(
                            (proyecto.nombre, "Cotizacion ya vinculada a otro proyecto como principal")
                        )
                        continue

                    if dry_run:
                        self.stdout.write(f"  [DRY RUN] migraria: {proyecto.nombre}")
                        totales["migrados"] += 1
                        continue

                    Proyecto.objects.filter(pk=proyecto.pk).update(cotizacion_id=cotizacion.id)
                    self.stdout.write(f"  Migrado: {proyecto.nombre}")
                    totales["migrados"] += 1

                for nombre, motivo in omitidos_tenant:
                    self.stdout.write(self.style.WARNING(f"  Omitido: {nombre} -- {motivo}"))
                totales["omitidos"] += len(omitidos_tenant)

        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill completo: migrados={totales['migrados']}, omitidos={totales['omitidos']}"
                + (" (dry-run, sin escribir)" if dry_run else "")
            )
        )
