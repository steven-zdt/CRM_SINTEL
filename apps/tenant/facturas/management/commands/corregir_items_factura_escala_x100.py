"""
Backfill: corrige ItemFactura cuya cantidad/valor_unitario quedaron
divididos por 100 (o 10000) por un bug real del parser XML universal
(apps/services/document_parser/xml_parser/parser.py -- ya corregido,
ver _decimal_desde_xml()).

Causa raiz (2026-09-18): `normalize_numeric_to_decimal_string()`
(apps/services/document_parser/normalizers.py) hacia
`value.replace('.', '')` y LUEGO comprobaba `'.' not in value` para
decidir si dividir por 100 -- esa condicion era SIEMPRE verdadera (el
punto ya se habia eliminado), asi que CUALQUIER valor XML sin separadores
de miles (es decir, cualquier numero UBL/DIAN valido: "1", "582992", ...)
se dividia por 100 sin condicion real. cantidad y valor_unitario se veian
afectados cada uno por separado -- si solo uno de los dos tenia punto
decimal en el XML original, solo ese sobrevivia (ratio final x100); si
ninguno tenia punto, ambos se corrompian (ratio final x10000, porque
subtotal = cantidad_corrupta * valor_unitario_corrupto).

Este comando:
    1. Recorre Factura (VENTA y COMPRA) con FacturaAnexos.ubl_xml
       disponible.
    2. Detecta sospecha de corrupcion: suma(item.subtotal) vs
       Factura.subtotal, ratio > 50 (los casos reales observados son
       exactamente ~100 o ~10000 -- nunca valores "normales" de
       redondeo/descuentos, que estarian cerca de 1).
    3. Re-parsea el XML original YA guardado (nunca lo reconstruye ni lo
       vuelve a descargar) con el parser corregido y compara.
    4. Si el resultado re-parseado SI cuadra con Factura.subtotal (con
       tolerancia de redondeo), actualiza los ItemFactura afectados.
    5. Si no cuadra (o no hay XML guardado), lo deja intacto y lo reporta
       como no corregible automaticamente -- nunca inventa un valor.

DRY RUN por defecto (--apply para escribir), mismo criterio de seguridad
que migrar_facturas_a_ventas.py. NO toca Factura.subtotal/impuestos/total
(la evidencia indica que esos ya eran correctos) ni ningun campo fiscal
mas alla de los montos por item (cantidad/valor_unitario/valor_iva/
subtotal/total de ItemFactura).

Uso:
    python manage.py corregir_items_factura_escala_x100
    python manage.py corregir_items_factura_escala_x100 --schema=admin --apply
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import get_tenant_model, schema_context

from apps.services.document_parser.xml_parser.parser import parse_to_dto
from apps.tenant.facturas.models import Factura, ItemFactura

TOLERANCIA = Decimal("1.00")  # redondeo aceptable en pesos


class Command(BaseCommand):
    help = (
        "Corrige ItemFactura con cantidad/valor_unitario divididos por 100 (o 10000) "
        "por el bug historico del parser XML universal (ya corregido). DRY RUN por "
        "defecto -- requiere --apply para escribir."
    )

    def add_arguments(self, parser):
        parser.add_argument("--schema", type=str, default=None)
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        schema_name = options.get("schema")
        apply_changes = options.get("apply")
        schemas = [schema_name] if schema_name else list(
            get_tenant_model().objects.values_list("schema_name", flat=True)
        )

        modo = "APLICANDO CAMBIOS" if apply_changes else "DRY RUN (solo reporte)"
        self.stdout.write(self.style.WARNING(f"Modo: {modo}"))

        total = {"revisadas": 0, "sospechosas": 0, "corregidas": 0, "sin_xml": 0, "no_reconciliable": 0}

        for schema in schemas:
            try:
                with schema_context(schema):
                    stats = self._corregir_schema(schema, apply_changes)
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f"[{schema}] omitido: {exc}"))
                continue
            for k, v in stats.items():
                total[k] = total.get(k, 0) + v

        self.stdout.write(self.style.SUCCESS("\n=== TOTAL ==="))
        for k, v in total.items():
            self.stdout.write(f"  {k}: {v}")

    def _corregir_schema(self, schema, apply_changes):
        stats = {"revisadas": 0, "sospechosas": 0, "corregidas": 0, "sin_xml": 0, "no_reconciliable": 0}

        facturas = Factura.objects.filter(
            naturaleza__in=[Factura.Naturaleza.VENTA, Factura.Naturaleza.COMPRA],
        ).prefetch_related("items", "anexos")

        for factura in facturas.iterator(chunk_size=100):
            items = list(factura.items.all())
            if not items or not factura.subtotal:
                continue
            stats["revisadas"] += 1

            suma_items = sum((it.subtotal for it in items), Decimal("0"))
            if suma_items <= 0:
                continue
            ratio = factura.subtotal / suma_items
            if ratio <= Decimal("50"):
                continue

            stats["sospechosas"] += 1
            anexos = getattr(factura, "anexos", None)
            xml_content = getattr(anexos, "ubl_xml", None) if anexos else None
            if not xml_content:
                stats["sin_xml"] += 1
                self.stdout.write(self.style.WARNING(
                    f"[{schema}] Factura {factura.numero} (id={factura.id}): sospechosa "
                    f"(ratio={ratio:.2f}) pero sin XML guardado -- no se puede reconciliar."
                ))
                continue

            try:
                dto = parse_to_dto(xml_content.encode("utf-8"), filename=f"{factura.numero}.xml")
            except Exception as exc:
                stats["no_reconciliable"] += 1
                self.stdout.write(self.style.ERROR(
                    f"[{schema}] Factura {factura.numero} (id={factura.id}): error re-parseando XML: {exc}"
                ))
                continue

            items_dto = dto.get("items", [])
            suma_reparseada = sum((Decimal(str(it.get("subtotal", 0))) for it in items_dto), Decimal("0"))
            if abs(suma_reparseada - factura.subtotal) > TOLERANCIA:
                stats["no_reconciliable"] += 1
                self.stdout.write(self.style.ERROR(
                    f"[{schema}] Factura {factura.numero} (id={factura.id}): el re-parseo "
                    f"({suma_reparseada}) tampoco cuadra con Factura.subtotal ({factura.subtotal}) "
                    f"-- no se corrige automaticamente."
                ))
                continue

            if len(items_dto) != len(items):
                stats["no_reconciliable"] += 1
                self.stdout.write(self.style.ERROR(
                    f"[{schema}] Factura {factura.numero} (id={factura.id}): numero de items "
                    f"distinto (BD={len(items)} vs XML={len(items_dto)}) -- no se corrige "
                    f"automaticamente, requiere revision manual."
                ))
                continue

            self.stdout.write(self.style.SUCCESS(
                f"[{schema}] Factura {factura.numero} (id={factura.id}): CORREGIBLE "
                f"(ratio={ratio:.2f}, {len(items)} item(s))."
            ))
            if not apply_changes:
                stats["corregidas"] += 1
                continue

            with transaction.atomic():
                for item_db, item_dto in zip(items, items_dto):
                    cantidad = Decimal(str(item_dto["cantidad"]))
                    valor_unitario = Decimal(str(item_dto["valor_unitario"]))
                    porcentaje_iva = Decimal(str(item_dto["porcentaje_iva"]))
                    subtotal = Decimal(str(item_dto["subtotal"]))
                    total_item = Decimal(str(item_dto["total"]))
                    valor_iva = total_item - subtotal

                    ItemFactura.objects.filter(pk=item_db.pk).update(
                        cantidad=cantidad,
                        valor_unitario=valor_unitario,
                        porcentaje_iva=porcentaje_iva,
                        valor_iva=valor_iva,
                        subtotal=subtotal,
                        total=total_item,
                    )
            stats["corregidas"] += 1

        return stats
