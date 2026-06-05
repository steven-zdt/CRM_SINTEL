from django.core.management.base import BaseCommand
from django.db import transaction

from apps.tenant.facturas.models import Factura
from apps.tenant.facturas.services.crud_service import FacturaCRUDService
from apps.tenant.proveedores.services.business_service import ProveedorBusinessService


class Command(BaseCommand):
    help = "Vincula proveedores a facturas de compra existentes usando emisor_nit."

    def add_arguments(self, parser):
        parser.add_argument(
            "--empresa-id",
            type=int,
            default=None,
            help="Limita el backfill a una empresa_id dentro del schema actual.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra que se haria sin escribir cambios.",
        )

    def handle(self, *args, **options):
        empresa_id = options.get("empresa_id")
        dry_run = options.get("dry_run")

        qs = Factura.objects.filter(
            naturaleza=Factura.Naturaleza.COMPRA,
            proveedor_uuid__isnull=True,
        ).only(
            "id",
            "uuid",
            "numero",
            "empresa_id",
            "naturaleza",
            "proveedor_uuid",
            "emisor_nit",
            "emisor_razon_social",
            "emisor_email",
            "emisor_telefono",
            "emisor_direccion",
            "emisor_actividad_ciiu",
        ).order_by("empresa_id", "id")

        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)

        vinculadas = 0
        proveedores_creados = 0
        omitidas = 0
        errores = []

        for factura in qs.iterator(chunk_size=200):
            try:
                if dry_run:
                    omitidas += 1
                    continue

                with transaction.atomic():
                    proveedor, created = ProveedorBusinessService.resolver_o_crear_desde_factura_compra(
                        empresa_id=factura.empresa_id,
                        emisor_nit=factura.emisor_nit,
                        emisor_razon_social=factura.emisor_razon_social,
                        emisor_email=factura.emisor_email,
                        emisor_telefono=factura.emisor_telefono,
                        emisor_direccion=factura.emisor_direccion,
                        emisor_actividad_ciiu=factura.emisor_actividad_ciiu,
                    )
                    FacturaCRUDService.actualizar(factura, {"proveedor_uuid": proveedor.uuid})

                vinculadas += 1
                if created:
                    proveedores_creados += 1
            except Exception as exc:
                errores.append({"factura": factura.numero, "error": str(exc)})

        self.stdout.write(
            self.style.SUCCESS(
                "Backfill proveedores facturas compra: "
                f"vinculadas={vinculadas}, "
                f"proveedores_creados={proveedores_creados}, "
                f"omitidas={omitidas}, "
                f"errores={len(errores)}"
            )
        )

        for error in errores[:20]:
            self.stdout.write(f"- {error['factura']}: {error['error']}")

        if len(errores) > 20:
            self.stdout.write(f"... {len(errores) - 20} errores adicionales omitidos")
