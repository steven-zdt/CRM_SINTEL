"""
Reconciliacion masiva Facturas -> Ventas (FST-375 secc. 16-18, 35-39, 45.4).

"Migrar las facturas existentes a Ventas" NO significa duplicar facturas ni
crear una segunda factura fiscal -- Facturas sigue siendo el unico SSoT
fiscal (CUFE/XML/autorizacion/consecutivo). Este comando solo actua del
lado comercial (Venta, propiedad de Ventas), reutilizando integramente los
servicios ya existentes y probados:

    - VentaBusinessService.vincular_factura_existente() (naturaleza, DSV,
      idempotencia 409 en duplicado) cuando ya existe una Venta candidata.
    - VentaBusinessService.crear_venta_desde_factura() (compone
      VentaCRUDService.crear_venta()/vincular_factura(), ya usados por el
      flujo manual) cuando ninguna Venta reclama la factura.

Criterio de match (secc. 18, deliberadamente estricto): NO se usa total,
cliente o fecha por si solos. Un candidato solo es valido si:
    (a) ya existe vinculo directo (Factura.venta_origen) -- se omite, ya
        esta resuelto; o
    (b) existe una Venta sin factura_asociada cuyo numero_factura coincide
        exactamente con Factura.numero, dentro de la misma empresa.
Si hay mas de un candidato (b), la factura se marca AMBIGUA y no se toca --
nunca se vincula automaticamente con evidencia insuficiente.

Uso (reporte, no escribe nada -- default seguro):
    python manage.py migrar_facturas_a_ventas
    python manage.py migrar_facturas_a_ventas --schema=acme

Para ejecutar de verdad (escribe en BD), requiere el flag explicito --apply:
    python manage.py migrar_facturas_a_ventas --apply
    python manage.py migrar_facturas_a_ventas --schema=acme --apply

A diferencia de otros comandos de este mismo directorio (backfill_*.py,
donde --dry-run es opt-in y por defecto SI escriben), aqui se invierte la
seguridad por defecto: esto crea registros comerciales nuevos (Venta) a
partir de historial fiscal real, y el propio encargo exige "antes de migrar
ejecutar DRY RUN" -- por eso el modo seguro (solo reporte) es el default,
y escribir requiere una decision explicita (--apply).

Idempotente (secc. 36): correrlo dos veces sobre el mismo estado no crea
duplicados -- la segunda corrida solo encuentra facturas ya_vinculadas.
Concurrencia (secc. 37): select_for_update() sobre la Factura durante el
vinculo/creacion: dos ejecuciones simultaneas no pueden vincular la misma
factura a dos Ventas distintas (la segunda pierde la carrera con
IntegrityError, capturado y contado como error, no crashea el comando).
"""
from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction
from django_tenants.utils import get_tenant_model, schema_context
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura
from apps.tenant.ventas.models import Venta
from apps.tenant.ventas.services.business_service import VentaBusinessService


class Command(BaseCommand):
    help = (
        "Reconcilia Facturas de naturaleza VENTA sin Venta vinculada: vincula "
        "una Venta existente que coincida por numero_factura, o crea una Venta "
        "comercial nueva y la vincula. Reporte solo por defecto -- requiere "
        "--apply para escribir. NUNCA crea una segunda factura fiscal."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--schema", type=str, default=None,
            help="Schema especifico (opcional; si no se da, se procesan todos los tenants).",
        )
        parser.add_argument(
            "--apply", action="store_true",
            help="Ejecuta de verdad (escribe en BD). Sin este flag, solo reporta (DRY RUN).",
        )
        parser.add_argument(
            "--limit-detalle", type=int, default=20,
            help="Maximo de facturas a listar por categoria en el detalle (default: 20).",
        )

    def handle(self, *args, **options):
        schema_name = options.get("schema")
        apply_changes = options.get("apply")
        limit_detalle = options.get("limit_detalle", 20)

        schemas = [schema_name] if schema_name else list(
            get_tenant_model().objects.values_list("schema_name", flat=True)
        )

        modo = "APLICANDO CAMBIOS" if apply_changes else "DRY RUN (solo reporte, nada se escribe)"
        self.stdout.write(self.style.WARNING(f"Modo: {modo}"))

        total_global = {}

        for schema in schemas:
            try:
                with schema_context(schema):
                    stats = self._reconciliar_schema(schema, apply_changes, limit_detalle)
            except Exception as exc:
                # Defensivo: schemas especiales (ej. 'public', el schema
                # compartido) o tenants incompletos no tienen las tablas de
                # apps tenant (empresa/facturas/ventas) -- se omiten con
                # warning en vez de abortar la reconciliacion de los demas
                # tenants reales.
                self.stdout.write(self.style.WARNING(
                    f"[{schema}] omitido -- no parece ser un tenant de negocio real: {exc}"
                ))
                continue
            for k, v in stats.items():
                total_global[k] = total_global.get(k, 0) + v

        self.stdout.write(self.style.SUCCESS("\n=== TOTAL (todos los schemas procesados) ==="))
        for k, v in total_global.items():
            self.stdout.write(f"  {k}: {v}")

    def _reconciliar_schema(self, schema, apply_changes, limit_detalle):
        empresa = Empresa.objects.only("id").first()
        if not empresa:
            self.stdout.write(self.style.WARNING(f"[{schema}] Sin Empresa configurada -- omitido."))
            return {}

        stats = {
            "facturas_naturaleza_venta_total": 0,
            "facturas_naturaleza_compra": Factura.objects.filter(naturaleza=Factura.Naturaleza.COMPRA).count(),
            "notas_credito": Factura.objects.filter(tipo=Factura.TipoFactura.NC).count(),
            "notas_debito": Factura.objects.filter(tipo=Factura.TipoFactura.ND).count(),
            "ya_vinculadas": 0,
            "vinculadas_a_venta_existente": 0,
            "ventas_creadas": 0,
            "ambiguas": 0,
            "omitidas_sin_items": 0,
            "errores": 0,
        }
        detalle_ambiguas = []
        detalle_errores = []

        qs = Factura.objects.filter(
            naturaleza=Factura.Naturaleza.VENTA,
            tipo=Factura.TipoFactura.FE,
        ).prefetch_related("items").order_by("id")
        stats["facturas_naturaleza_venta_total"] = qs.count()

        for factura in qs.iterator(chunk_size=100):
            if hasattr(factura, "venta_origen"):
                stats["ya_vinculadas"] += 1
                continue

            candidatas = list(
                Venta.objects.filter(
                    empresa_id=factura.empresa_id,
                    numero_factura=factura.numero,
                    factura_asociada__isnull=True,
                ).only("id", "uuid")
            ) if factura.numero else []

            if len(candidatas) > 1:
                stats["ambiguas"] += 1
                detalle_ambiguas.append(factura.numero)
                continue

            if not candidatas and not list(factura.items.all()):
                # factura.items.all() ya viene resuelto por el
                # prefetch_related() del queryset -- list() reutiliza el
                # cache en vez de disparar un .exists() adicional por fila.
                stats["omitidas_sin_items"] += 1
                continue

            if not apply_changes:
                if candidatas:
                    stats["vinculadas_a_venta_existente"] += 1
                else:
                    stats["ventas_creadas"] += 1
                continue

            try:
                with transaction.atomic():
                    factura_lock = Factura.objects.select_for_update().get(pk=factura.pk)
                    if hasattr(factura_lock, "venta_origen"):
                        # Otra ejecucion concurrente ya la vinculo entre el
                        # conteo y este punto -- no es un error, es la
                        # garantia de concurrencia (secc. 37) funcionando.
                        stats["ya_vinculadas"] += 1
                        continue

                    if candidatas:
                        ok, resultado, _status = VentaBusinessService.vincular_factura_existente(
                            candidatas[0], str(factura.uuid), factura.empresa_id
                        )
                        if not ok:
                            stats["errores"] += 1
                            detalle_errores.append({"factura": factura.numero, "error": resultado})
                            continue
                        stats["vinculadas_a_venta_existente"] += 1
                    else:
                        VentaBusinessService.crear_venta_desde_factura(factura_lock, empresa)
                        stats["ventas_creadas"] += 1
            except (ValueError, DRFValidationError) as exc:
                stats["errores"] += 1
                detalle_errores.append({"factura": factura.numero, "error": str(exc)})
            except IntegrityError as exc:
                stats["errores"] += 1
                detalle_errores.append({"factura": factura.numero, "error": f"race/integridad: {exc}"})

        self.stdout.write(self.style.SUCCESS(f"\n=== [{schema}] ==="))
        for k, v in stats.items():
            self.stdout.write(f"  {k}: {v}")
        if detalle_ambiguas:
            self.stdout.write(self.style.WARNING(f"  Ambiguas (numero_factura con >1 Venta candidata):"))
            for numero in detalle_ambiguas[:limit_detalle]:
                self.stdout.write(f"    - {numero}")
            if len(detalle_ambiguas) > limit_detalle:
                self.stdout.write(f"    ... {len(detalle_ambiguas) - limit_detalle} adicionales omitidas")
        if detalle_errores:
            self.stdout.write(self.style.ERROR(f"  Errores:"))
            for err in detalle_errores[:limit_detalle]:
                self.stdout.write(f"    - {err['factura']}: {err['error']}")
            if len(detalle_errores) > limit_detalle:
                self.stdout.write(f"    ... {len(detalle_errores) - limit_detalle} adicionales omitidos")

        return stats
