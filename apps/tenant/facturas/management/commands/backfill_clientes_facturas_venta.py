from django.core.management.base import BaseCommand
from django.db import transaction

from apps.tenant.clientes.services.business_service import ClienteBusinessService
from apps.tenant.facturas.models import Factura
from apps.tenant.facturas.services.crud_service import FacturaCRUDService


class Command(BaseCommand):
    help = "Vincula clientes a facturas de venta existentes usando receptor_nit."

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
            naturaleza=Factura.Naturaleza.VENTA,
            cliente_uuid__isnull=True,
        ).only(
            "id",
            "uuid",
            "numero",
            "empresa_id",
            "naturaleza",
            "cliente_uuid",
            "receptor_nit",
            "receptor_razon_social",
            "receptor_email",
            "receptor_telefono",
            "receptor_direccion",
        ).order_by("empresa_id", "id")

        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)

        vinculadas = 0
        clientes_creados = 0
        omitidas = 0
        errores = []

        for factura in qs.iterator(chunk_size=200):
            try:
                if dry_run:
                    omitidas += 1
                    continue

                with transaction.atomic():
                    cliente, created = ClienteBusinessService.resolver_o_crear_desde_factura_venta(
                        empresa_id=factura.empresa_id,
                        receptor_nit=factura.receptor_nit,
                        receptor_razon_social=factura.receptor_razon_social,
                        receptor_email=factura.receptor_email,
                        receptor_telefono=factura.receptor_telefono,
                        receptor_direccion=factura.receptor_direccion,
                    )
                    FacturaCRUDService.actualizar(factura, {"cliente_uuid": cliente.uuid})

                vinculadas += 1
                if created:
                    clientes_creados += 1
            except Exception as exc:
                errores.append({"factura": factura.numero, "error": str(exc)})

        self.stdout.write(
            self.style.SUCCESS(
                "Backfill clientes facturas venta: "
                f"vinculadas={vinculadas}, "
                f"clientes_creados={clientes_creados}, "
                f"omitidas={omitidas}, "
                f"errores={len(errores)}"
            )
        )

        for error in errores[:20]:
            self.stdout.write(f"- {error['factura']}: {error['error']}")

        if len(errores) > 20:
            self.stdout.write(f"... {len(errores) - 20} errores adicionales omitidos")
