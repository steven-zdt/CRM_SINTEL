"""
FacturaBusinessService — Logica de negocio avanzada para Facturas.

Responsabilidad única: Orquestar ingesta UBL/PDF, validación de naturaleza y snapshots.
SSoT para reglas de negocio fiscales y contables del tenant.

Reglas SINTEL v3.5:
- Todos los métodos son @staticmethod.
- Double Semantic Verification (DSV): empresa_id obligatorio.
- Snapshot Pattern: captura datos de terceros al momento de la transacción.
"""

import logging
import re
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura, ItemFactura, ItemNotaCredito, NotaCredito, MANUAL_EDITABLE_FIELDS, XML_IMMUTABLE_FIELDS
from apps.tenant.facturas.services.crud_service import FacturaCRUDService

# Importación segura para Document Ingest Pipeline Universal
try:
    from apps.services.document_ingest.ingest_service import ingest_document
    HAS_DOCUMENT_INGEST = True
except ImportError:
    ingest_document = None
    HAS_DOCUMENT_INGEST = False

from apps.tenant.empresa.services import (
    EmpresaNotConfiguredError,
    get_empresa_emisor_data,
)

logger = logging.getLogger(__name__)


def clean_nit(nit_str):
    if not nit_str:
        return ""
    nit_str = str(nit_str).strip()
    nit_str = nit_str.replace(".", "")
    if "-" in nit_str:
        nit_str = nit_str.split("-")[0]
    return re.sub(r'[^a-zA-Z0-9]', '', nit_str)


class FacturaBusinessService:
    """
    Servicio de logica de negocio para Facturas.
    """

    @staticmethod
    @transaction.atomic
    def crear_factura_desde_venta(empresa, dto: dict):
        """
        Crea una Factura de Venta electronica a partir del DTO canonico generado
        por VentaBusinessService._construir_dto_factura().

        El DTO debe contener:
          - emisor.nit / emisor.razon_social (snapshot empresa)
          - receptor.nit / receptor.razon_social (snapshot cliente)
          - totales.subtotal, totales.impuestos, totales.total
          - fecha_emision, lineas[], cliente_uuid, venta_uuid

        Genera un numero de factura provisional BORR-VTA-{uuid8} hasta que
        la DIAN asigne el numero definitivo en el proceso de firma y envio.
        Retorna la instancia de Factura creada.
        """
        from django.db.models import Max
        import uuid as uuid_lib

        emisor = dto.get("emisor", {})
        receptor = dto.get("receptor", {})
        totales = dto.get("totales", {})
        lineas = dto.get("lineas", [])

        # Numero provisional unico
        venta_uuid_str = dto.get("venta_uuid", str(uuid_lib.uuid4()))
        numero_provisional = "BORR-VTA-" + venta_uuid_str.replace("-", "").upper()[:12]

        # Consecutivo dentro de facturas VENTA de la empresa.
        # WARNING: [PERF-C2] select_for_update() sobre la fila Empresa (singleton por
        # tenant) serializa la asignacion de consecutivo entre transacciones concurrentes,
        # sin bloquear la tabla Factura (que crece sin limite). Mismo patron de lock sobre
        # entidad "contenedora" que ResolucionDIAN en gastos/services/crud_service.py.
        empresa_locked = Empresa.objects.select_for_update().get(pk=empresa.pk)
        max_consec = (
            Factura.objects.filter(empresa=empresa_locked, naturaleza=Factura.Naturaleza.VENTA)
            .aggregate(m=Max("consecutivo"))["m"]
        ) or 0
        consecutivo = max_consec + 1

        # Resolucion DIAN para poblar campos de autorizacion
        resol = dto.get("resolucion", {})
        num_definitivo = dto.get("numero_externo") or dto.get("num_fac") or numero_provisional

        # [OSF Fase F10] `sede_id` viaja en el DTO como dato plano (nunca
        # una FK directa Ventas->Facturas, ver VentaBusinessService.
        # _construir_dto_factura()). DSV anti-IDOR: solo se asigna si la
        # Sede realmente pertenece a esta empresa - un id ajeno/invalido se
        # ignora silenciosamente (degrada a sede=None) en vez de romper la
        # creacion de la Factura por un dato de contexto secundario.
        sede = None
        sede_id_dto = dto.get("sede_id")
        if sede_id_dto:
            from apps.tenant.empresa.models import Sede
            sede = Sede.objects.filter(id=sede_id_dto, empresa_id=empresa.id).first()

        factura_data = {
            "empresa": empresa,
            "numero": num_definitivo,
            "consecutivo": consecutivo,
            "tipo": Factura.TipoFactura.FE,
            "estado": Factura.Estado.BORRADOR,
            "naturaleza": Factura.Naturaleza.VENTA,
            "fecha_emision": timezone.now(),
            "fecha_vencimiento": dto.get("fecha_vencimiento") or None,
            "emisor_nit": emisor.get("nit", ""),
            "emisor_razon_social": emisor.get("razon_social", ""),
            "emisor_direccion": emisor.get("direccion", ""),
            "emisor_email": emisor.get("email", ""),
            "emisor_telefono": emisor.get("telefono", ""),
            "receptor_nit": receptor.get("nit", ""),
            "receptor_razon_social": receptor.get("razon_social", ""),
            "receptor_email": receptor.get("email", ""),
            "subtotal": Decimal(str(totales.get("subtotal", "0"))),
            "impuestos": Decimal(str(totales.get("impuestos", "0"))),
            "total": Decimal(str(totales.get("total", "0"))),
            "moneda": dto.get("moneda", "COP"),
            "cliente_uuid": dto.get("cliente_uuid"),
            "sede": sede,
            # Campos DIAN generados en Fase 5 (None en vez de "" para campos unique/integer)
            "cufe": dto.get("cufe") or None,
            "qr_url": dto.get("qr_string") or None,
            "xml_content": dto.get("xml_content") or None,
            "dian_response_xml": dto.get("dian_response_xml") or None,
            # Datos de autorizacion de la resolucion
            "autorizacion_numero": resol.get("numero_autorizacion") or None,
            "autorizacion_prefijo": resol.get("prefijo") or None,
            "autorizacion_rango_desde": int(resol["desde"]) if resol.get("desde") else None,
            "autorizacion_rango_hasta": int(resol["hasta"]) if resol.get("hasta") else None,
            "autorizacion_vigencia_inicio": resol.get("fecha_inicio") or None,
            "autorizacion_vigencia_fin": resol.get("fecha_fin") or None,
        }

        factura = FacturaCRUDService.crear(factura_data)

        # Crear ItemFactura por cada linea del DTO
        from apps.tenant.facturas.models import ItemFactura
        items_a_crear = []
        for idx, linea in enumerate(lineas):
            cant = Decimal(str(linea.get("cantidad", "1")))
            pu = Decimal(str(linea.get("valor_unitario", "0")))
            pct_iva = Decimal(str(linea.get("porcentaje_iva", "0")))
            sub = cant * pu
            iva_val = sub * (pct_iva / Decimal("100"))
            items_a_crear.append(
                ItemFactura(
                    empresa=empresa,
                    factura=factura,
                    linea_id=str(idx + 1),
                    descripcion=linea.get("descripcion", ""),
                    cantidad=cant,
                    valor_unitario=pu,
                    porcentaje_iva=pct_iva,
                    valor_iva=iva_val,
                    subtotal=sub,
                    total=sub + iva_val,
                )
            )
        if items_a_crear:
            ItemFactura.objects.bulk_create(items_a_crear)

        logger.info(
            "[FacturaBS] Factura creada desde Venta: numero=%s id=%s",
            factura.numero,
            factura.id,
        )
        return factura

    @staticmethod
    def normalize_document_number(value: str | None) -> str:
        """
        Normaliza números de documento eliminando espacios y caracteres no imprimibles.
        """
        if not value:
            return ""
        normalized = str(value).strip()
        normalized = re.sub(r'[^\w\-\.]', '', normalized)
        # Si es un NIT, estandarizar eliminando guiones y puntos
        if re.match(r'^[\d\-\.]+$', normalized) and not re.search(r'[A-Za-z]', normalized):
            normalized = normalized.replace('-', '').replace('.', '')
        return normalized

    @staticmethod
    def _resolver_naturaleza(emisor_nit: str | None, empresa_nit: str | None) -> str:
        """
        Resuelve si la factura es VENTA o COMPRA (SSoT).
        """
        nit_dto = FacturaBusinessService.normalize_document_number(emisor_nit)
        nit_tenant = FacturaBusinessService.normalize_document_number(empresa_nit)

        if nit_dto and nit_tenant and nit_dto == nit_tenant:
            return Factura.Naturaleza.VENTA
        return Factura.Naturaleza.COMPRA

    @staticmethod
    def obtener_retenciones_desde_cliente(cliente_nit: str | None, empresa_id: int | None = None) -> dict[str, Any]:
        """
        [v3.7.1 ENDPOINT PUENTE] Extrae retenciones desde Contabilidad API (Pull Model).

        Delega a GET /api/v1/contabilidad/retenciones/obtener-por-tercero/
        para mantener SSoT en la app Contabilidad en lugar de leer directo desde Cliente.
        """
        if not cliente_nit:
            return {
                "aplica_retefuente": False,
                "retefuente_porcentaje": Decimal('0.00'),
                "aplica_reteica": False,
                "reteica_porcentaje": Decimal('0.00'),
                "aplica_reteiva": False,
                "reteiva_porcentaje": Decimal('0.00'),
            }

        try:
            from apps.tenant.contabilidad.services.retenciones_service import RetencionesService

            cliente_nit_normalized = FacturaBusinessService.normalize_document_number(cliente_nit)
            retenciones = RetencionesService.obtener_retenciones_desde_tercero(
                nit=cliente_nit_normalized,
                tipo_tercero='CLIENTE',
                naturaleza='VENTA',
                empresa_id=empresa_id,
            )

            return {
                "aplica_retefuente": retenciones.get('aplica_retefuente', False),
                "retefuente_porcentaje": retenciones.get('retefuente_porcentaje', Decimal('0.00')),
                "aplica_reteica": retenciones.get('aplica_reteica', False),
                "reteica_porcentaje": retenciones.get('reteica_porcentaje', Decimal('0.00')),
                "aplica_reteiva": retenciones.get('aplica_reteiva', False),
                "reteiva_porcentaje": retenciones.get('reteiva_porcentaje', Decimal('0.00')),
            }
        except Exception as e:
            logger.warning(f"Error extrayendo retenciones de cliente {cliente_nit}: {e}")
            return {
                "aplica_retefuente": False,
                "retefuente_porcentaje": Decimal('0.00'),
                "aplica_reteica": False,
                "reteica_porcentaje": Decimal('0.00'),
                "aplica_reteiva": False,
                "reteiva_porcentaje": Decimal('0.00'),
            }

    @staticmethod
    def obtener_retenciones_desde_proveedor(proveedor_nit: str | None, empresa_id: int | None = None) -> dict[str, Any]:
        """
        [v3.7.1 ENDPOINT PUENTE — DEPRECATED] Extrae retenciones desde Contabilidad API.

        Nota: Para facturas COMPRA, las retenciones ya están en el XML — este método
        NO se usa. Se mantiene para compatibilidad futura si se requiere.
        """
        if not proveedor_nit:
            return {
                "aplica_retefuente": False,
                "retefuente_porcentaje": Decimal('0.00'),
                "aplica_reteica": False,
                "reteica_porcentaje": Decimal('0.00'),
                "aplica_reteiva": False,
                "reteiva_porcentaje": Decimal('0.00'),
            }

        try:
            from apps.tenant.contabilidad.services.retenciones_service import RetencionesService

            proveedor_nit_normalized = FacturaBusinessService.normalize_document_number(proveedor_nit)
            retenciones = RetencionesService.obtener_retenciones_desde_tercero(
                nit=proveedor_nit_normalized,
                tipo_tercero='PROVEEDOR',
                naturaleza='COMPRA',
                empresa_id=empresa_id,
            )

            return {
                "aplica_retefuente": retenciones.get('aplica_retefuente', False),
                "retefuente_porcentaje": retenciones.get('retefuente_porcentaje', Decimal('0.00')),
                "aplica_reteica": retenciones.get('aplica_reteica', False),
                "reteica_porcentaje": retenciones.get('reteica_porcentaje', Decimal('0.00')),
                "aplica_reteiva": retenciones.get('aplica_reteiva', False),
                "reteiva_porcentaje": retenciones.get('reteiva_porcentaje', Decimal('0.00')),
            }
        except Exception as e:
            logger.warning(f"Error extrayendo retenciones de proveedor {proveedor_nit}: {e}")
            return {
                "aplica_retefuente": False,
                "retefuente_porcentaje": Decimal('0.00'),
                "aplica_reteica": False,
                "reteica_porcentaje": Decimal('0.00'),
                "aplica_reteiva": False,
                "reteiva_porcentaje": Decimal('0.00'),
            }

    @staticmethod
    @transaction.atomic
    def guardar_desde_dto(
        dto: dict[str, Any], 
        xml_text: str = None,
        file_bytes: bytes = None,
        file_type: str = 'xml',
        empresa_id: int = None
    ) -> tuple[dict[str, Any], int]:
        """
        Persiste factura desde DTO canonico (v3.5).

        Soporta el DTO del pipeline universal (nested: emisor.nit, totales.subtotal, etc.)
        y el DTO legacy (flat: emisor_nit, subtotal, etc.).
        """
        while isinstance(dto.get("dto"), dict):
            dto = dto["dto"]

        # Obtener instancia de empresa
        if empresa_id:
            try:
                empresa_instance = Empresa.objects.get(id=empresa_id)
            except Empresa.DoesNotExist:
                return {"error": "empresa_not_found", "message": "La empresa no existe."}, 404
        else:
            try:
                empresa_config = get_empresa_emisor_data()
                empresa_instance = Empresa.objects.get(
                    nit=FacturaBusinessService.normalize_document_number(empresa_config.get("nit"))
                )
            except (EmpresaNotConfiguredError, Empresa.DoesNotExist):
                empresa_instance = Empresa.objects.first()
                if not empresa_instance:
                    return {"error": "empresa_no_configurada", "message": "No hay ninguna empresa configurada."}, 422

        # --- Helpers para leer nested O flat ---
        emisor = dto.get("emisor", {}) if isinstance(dto.get("emisor"), dict) else {}
        receptor = dto.get("receptor", {}) if isinstance(dto.get("receptor"), dict) else {}
        totales = dto.get("totales", {}) if isinstance(dto.get("totales"), dict) else {}
        identificadores = dto.get("identificadores", {}) if isinstance(dto.get("identificadores"), dict) else {}
        autorizacion = dto.get("autorizacion", {}) if isinstance(dto.get("autorizacion"), dict) else {}
        doc_type = dto.get("document_type") or dto.get("type") or dto.get("tipo") or ""
        doc_type_normalized = str(doc_type).lower()
        is_credit_note = "creditnote" in doc_type_normalized or doc_type_normalized in {"nc", "nota_credito"}

        # Extraer y normalizar
        numero = FacturaBusinessService.normalize_document_number(dto.get("numero"))
        emisor_nit = FacturaBusinessService.normalize_document_number(
            emisor.get("nit") or dto.get("emisor_nit", "")
        )
        receptor_nit = FacturaBusinessService.normalize_document_number(
            receptor.get("nit") or dto.get("receptor_nit", "")
        )

        # Validacion de campos obligatorios
        if not numero or (not is_credit_note and (not emisor_nit or not receptor_nit)):
            return {"error": "missing_required_fields", "message": "Numero, NIT Emisor y NIT Receptor son obligatorios."}, 422

        # Validar pertenencia del NIT (DIAN) - Fase 1
        nit_empresa_limpio = clean_nit(empresa_instance.nit)
        emisor_nit_limpio = clean_nit(emisor_nit)
        receptor_nit_limpio = clean_nit(receptor_nit)

        if nit_empresa_limpio != emisor_nit_limpio and nit_empresa_limpio != receptor_nit_limpio:
            from django.core.exceptions import ValidationError as DjangoValidationError
            raise DjangoValidationError("El NIT de la empresa actual no coincide con el emisor ni con el receptor del documento.")

        # Determinar naturaleza usando empresa_instance.nit
        naturaleza = FacturaBusinessService._resolver_naturaleza(emisor_nit, empresa_instance.nit)

        # Cascading Security
        if naturaleza == Factura.Naturaleza.COMPRA and not is_credit_note:
            nit_tenant = FacturaBusinessService.normalize_document_number(empresa_instance.nit)
            if receptor_nit != nit_tenant:
                return {
                    "error": "document_not_for_tenant",
                    "message": f"Documento dirigido a tercero (NIT receptor: {receptor_nit}). No pertenece a este tenant."
                }, 422

        cliente_uuid = None
        proveedor_uuid = None
        emisor_razon_social = emisor.get("razon_social") or dto.get("emisor_razon_social", "")
        emisor_direccion = emisor.get("direccion") or dto.get("emisor_direccion", "")
        emisor_email = emisor.get("email") or dto.get("emisor_email", "")
        emisor_telefono = emisor.get("telefono") or dto.get("emisor_telefono", "")
        emisor_actividad_ciiu = emisor.get("actividad_ciiu") or dto.get("emisor_actividad_ciiu", "")
        receptor_razon_social = receptor.get("razon_social") or dto.get("receptor_razon_social", "")
        receptor_direccion = receptor.get("direccion") or dto.get("receptor_direccion", "")
        receptor_email = receptor.get("email") or dto.get("receptor_email", "")
        receptor_telefono = receptor.get("telefono") or dto.get("receptor_telefono", "")

        cufe = (
            identificadores.get("cufe")
            or identificadores.get("cude")
            or identificadores.get("uuid")
            or dto.get("cufe", "")
        )
        # --- VINCULACIÓN DE NOTA DE CRÉDITO (Fase 7) ---
        if dto.get("tipo") == "NC":
            ref_cufe = dto.get("ref_factura_cufe")
            ref_numero = dto.get("ref_factura_numero")
            
            # Buscar factura original para el vínculo 1:1
            factura_original = None
            if ref_cufe:
                factura_original = Factura.objects.filter(empresa=empresa_instance, cufe=ref_cufe).first()
            
            if not factura_original and ref_numero:
                factura_original = Factura.objects.filter(empresa=empresa_instance, numero=ref_numero).first()

            if factura_original:
                # [VALIDACIÓN] Evitar duplicados (Idempotencia de Negocio)
                if NotaCredito.objects.filter(factura=factura_original).exists():
                    logger.warning(f"[facturas:nc] Intento de duplicar NC para factura {factura_original.numero}")
                    return {"error": "Ya existe una Nota de Crédito asociada a esta factura."}, 422
                
                # Inyectar factura_id en el DTO para el CRUDService
                dto["factura_id"] = factura_original.id
                logger.info(f"[facturas:nc] Vinculando NC {dto.get('numero')} con factura {factura_original.numero}")
            else:
                logger.warning(f"[facturas:nc] NC {dto.get('numero')} sin factura de referencia encontrada (CUFE: {ref_cufe})")

        # Idempotencia por CUFE
        if cufe:
            if is_credit_note:
                nota_existente = NotaCredito.objects.filter(
                    cude=cufe, empresa=empresa_instance
                ).only("id", "uuid", "numero", "cude", "empresa_id").first()
                if nota_existente:
                    return {
                        "id": nota_existente.id,
                        "uuid": str(nota_existente.uuid),
                        "numero": nota_existente.numero,
                        "cude": nota_existente.cude,
                        "created": False,
                        "error": "duplicate",
                        "message": "Nota credito ya existe.",
                    }, 200

            factura_existente = Factura.objects.filter(
                cufe=cufe, empresa=empresa_instance
            ).only('id', 'uuid', 'numero', 'naturaleza', 'cufe', 'empresa_id', 'cliente_uuid', 'proveedor_uuid').first()
            if factura_existente:
                if factura_existente.naturaleza == Factura.Naturaleza.VENTA and not factura_existente.cliente_uuid:
                    from apps.tenant.clientes.services.business_service import ClienteBusinessService
                    try:
                        cliente, _ = ClienteBusinessService.resolver_o_crear_desde_factura_venta(
                            empresa_id=empresa_instance.id,
                            receptor_nit=receptor_nit,
                            receptor_razon_social=receptor_razon_social,
                            receptor_email=receptor_email,
                            receptor_telefono=receptor_telefono,
                            receptor_direccion=receptor_direccion,
                        )
                    except DRFValidationError as exc:
                        return {"error": "cliente_required", "message": str(exc.detail)}, 422
                    FacturaCRUDService.actualizar(factura_existente, {"cliente_uuid": cliente.uuid})

                if factura_existente.naturaleza == Factura.Naturaleza.COMPRA and not factura_existente.proveedor_uuid:
                    from apps.tenant.proveedores.services.business_service import ProveedorBusinessService
                    try:
                        proveedor, _ = ProveedorBusinessService.resolver_o_crear_desde_factura_compra(
                            empresa_id=empresa_instance.id,
                            emisor_nit=emisor_nit,
                            emisor_razon_social=emisor_razon_social,
                            emisor_email=emisor_email,
                            emisor_telefono=emisor_telefono,
                            emisor_direccion=emisor_direccion,
                            emisor_actividad_ciiu=emisor_actividad_ciiu,
                        )
                    except DRFValidationError as exc:
                        return {"error": "proveedor_required", "message": str(exc.detail)}, 422
                    FacturaCRUDService.actualizar(factura_existente, {"proveedor_uuid": proveedor.uuid})

                return {
                    "id": factura_existente.id,
                    "uuid": str(factura_existente.uuid),
                    "numero": factura_existente.numero,
                    "naturaleza": factura_existente.naturaleza,
                    "cufe": factura_existente.cufe,
                    "created": False,
                    "message": "Factura ya existe.",
                }, 200

        # Fecha emision
        fecha_emision_raw = dto.get("fecha_emision")
        if isinstance(fecha_emision_raw, str):
            fecha_emision = parse_datetime(fecha_emision_raw) or timezone.now()
        elif hasattr(fecha_emision_raw, 'tzinfo'):
            fecha_emision = fecha_emision_raw
        else:
            fecha_emision = timezone.now()

        # Fecha vencimiento
        fecha_vencimiento_raw = dto.get("fecha_vencimiento")
        fecha_vencimiento = parse_date(fecha_vencimiento_raw) if isinstance(fecha_vencimiento_raw, str) else fecha_vencimiento_raw

        # Determinar tipo de factura
        if is_credit_note:
            tipo = Factura.TipoFactura.NC
        elif "debitnote" in doc_type.lower():
            tipo = Factura.TipoFactura.ND
        else:
            tipo = Factura.TipoFactura.FE

        # Estado: importadas se marcan como ACEPTADA
        estado = dto.get("estado") or Factura.Estado.ACEPTADA

        factura_original_para_nc = None
        if tipo == Factura.TipoFactura.NC:
            referencia_dto = dto.get("referencia", {})
            ref_cufe = referencia_dto.get("cufe") or dto.get("ref_factura_cufe")
            ref_numero = referencia_dto.get("numero") or dto.get("ref_factura_numero")

            if ref_cufe:
                factura_original_para_nc = Factura.objects.filter(
                    cufe=ref_cufe, empresa=empresa_instance
                ).only("id", "numero", "cufe", "empresa_id").first()

            if not factura_original_para_nc and ref_numero:
                factura_original_para_nc = Factura.objects.filter(
                    numero=ref_numero, empresa=empresa_instance
                ).only("id", "numero", "cufe", "empresa_id").first()

            if not factura_original_para_nc:
                return {"error": "missing_invoice", "message": "Factura original no encontrada."}, 422

            if NotaCredito.objects.filter(factura=factura_original_para_nc, empresa=empresa_instance).exists():
                logger.warning(f"[facturas:nc] Intento de duplicar NC para factura {factura_original_para_nc.numero}")
                return {"error": "already_has_nc", "message": "La factura ya tiene nota credito."}, 422

        if naturaleza == Factura.Naturaleza.VENTA:
            from apps.tenant.clientes.services.business_service import ClienteBusinessService
            try:
                cliente, _ = ClienteBusinessService.resolver_o_crear_desde_factura_venta(
                    empresa_id=empresa_instance.id,
                    receptor_nit=receptor_nit,
                    receptor_razon_social=receptor_razon_social,
                    receptor_email=receptor_email,
                    receptor_telefono=receptor_telefono,
                    receptor_direccion=receptor_direccion,
                )
            except DRFValidationError as exc:
                return {"error": "cliente_required", "message": str(exc.detail)}, 422
            cliente_uuid = cliente.uuid
        elif naturaleza == Factura.Naturaleza.COMPRA:
            from apps.tenant.proveedores.services.business_service import ProveedorBusinessService
            try:
                proveedor, _ = ProveedorBusinessService.resolver_o_crear_desde_factura_compra(
                    empresa_id=empresa_instance.id,
                    emisor_nit=emisor_nit,
                    emisor_razon_social=emisor_razon_social,
                    emisor_email=emisor_email,
                    emisor_telefono=emisor_telefono,
                    emisor_direccion=emisor_direccion,
                    emisor_actividad_ciiu=emisor_actividad_ciiu,
                )
            except DRFValidationError as exc:
                return {"error": "proveedor_required", "message": str(exc.detail)}, 422
            proveedor_uuid = proveedor.uuid

        # Construir factura_data con TODOS los campos del modelo
        factura_data = {
            "empresa": empresa_instance,
            "numero": numero,
            "prefijo": dto.get("prefijo", ""),
            "consecutivo": dto.get("consecutivo", 0),
            "tipo": tipo,
            "estado": estado,
            "naturaleza": naturaleza,
            # UBL metadata
            "ubl_version": dto.get("ubl_version", ""),
            "customization_id": dto.get("customization_id", ""),
            "profile_id": dto.get("profile_id", ""),
            "profile_execution_id": dto.get("profile_execution_id", ""),
            "invoice_type_code": dto.get("invoice_type_code", ""),
            # Fechas
            "fecha_emision": fecha_emision,
            "fecha_vencimiento": fecha_vencimiento,
            # Emisor snapshot
            "emisor_nit": emisor_nit,
            "emisor_razon_social": emisor.get("razon_social") or dto.get("emisor_razon_social", ""),
            "emisor_direccion": emisor.get("direccion") or dto.get("emisor_direccion", ""),
            "emisor_email": emisor.get("email") or dto.get("emisor_email", ""),
            "emisor_telefono": emisor.get("telefono") or dto.get("emisor_telefono", ""),
            "emisor_actividad_ciiu": emisor.get("actividad_ciiu") or dto.get("emisor_actividad_ciiu", ""),
            # Receptor snapshot
            "receptor_nit": receptor_nit,
            "receptor_razon_social": receptor.get("razon_social") or dto.get("receptor_razon_social", ""),
            "receptor_direccion": receptor.get("direccion") or dto.get("receptor_direccion", ""),
            "receptor_email": receptor.get("email") or dto.get("receptor_email", ""),
            "receptor_telefono": receptor.get("telefono") or dto.get("receptor_telefono", ""),
            "cliente_uuid": cliente_uuid,
            "proveedor_uuid": proveedor_uuid,
            # Totales
            "moneda": totales.get("moneda") or dto.get("moneda", "COP"),
            "subtotal": totales.get("subtotal") or dto.get("subtotal", 0),
            "impuestos": totales.get("impuestos") or dto.get("impuestos", 0),
            "total": totales.get("total") or dto.get("total", 0),
            # Pago
            "forma_pago": dto.get("forma_pago", ""),
            "medio_pago_codigo": dto.get("medio_pago_codigo", ""),
            "payment_due_date": parse_date(dto.get("payment_due_date")) if isinstance(dto.get("payment_due_date"), str) else dto.get("payment_due_date"),
            # CUFE / identificadores
            "cufe": cufe,
            "qr_code": dto.get("qr_code", ""),
            "qr_url": dto.get("qr_url", ""),
            # Autorizacion DIAN
            "autorizacion_numero": autorizacion.get("numero") or dto.get("autorizacion_numero", ""),
            "autorizacion_prefijo": autorizacion.get("prefijo") or dto.get("autorizacion_prefijo", ""),
            "autorizacion_rango_desde": autorizacion.get("rango_desde") or dto.get("autorizacion_rango_desde", 0),
            "autorizacion_rango_hasta": autorizacion.get("rango_hasta") or dto.get("autorizacion_rango_hasta", 0),
            "autorizacion_vigencia_inicio": parse_date(autorizacion.get("vigencia_inicio")) if isinstance(autorizacion.get("vigencia_inicio"), str) else autorizacion.get("vigencia_inicio") or dto.get("autorizacion_vigencia_inicio"),
            "autorizacion_vigencia_fin": parse_date(autorizacion.get("vigencia_fin")) if isinstance(autorizacion.get("vigencia_fin"), str) else autorizacion.get("vigencia_fin") or dto.get("autorizacion_vigencia_fin"),
            # DIAN validation
            "dian_validation_code": dto.get("dian_validation_code", ""),
            "dian_validation_desc": dto.get("dian_validation_desc", ""),
            "dian_validation_fecha": parse_date(dto.get("dian_validation_fecha")) if isinstance(dto.get("dian_validation_fecha"), str) else dto.get("dian_validation_fecha"),
            "dian_validation_hora": dto.get("dian_validation_hora"),
            "dian_response_xml": dto.get("dian_response_xml", ""),
        }

        # Anexos
        anexos_data = {
            "ubl_xml": xml_text or (file_bytes.decode('utf-8', errors='ignore') if file_bytes and file_type == 'xml' else ""),
        }

        factura = FacturaCRUDService.crear(factura_data, anexos_data)

        # Guardar impuestos desglosados - Fase 2
        from apps.tenant.facturas.models import FacturaImpuesto
        for imp_dto in dto.get("impuestos_desglosados", []):
            FacturaImpuesto.objects.create(
                factura=factura,
                empresa=empresa_instance,
                tipo_impuesto=imp_dto.get("tipo_impuesto"),
                porcentaje=Decimal(str(imp_dto.get("porcentaje") or 0)),
                base_imponible=Decimal(str(imp_dto.get("base_imponible") or 0)),
                valor_impuesto=Decimal(str(imp_dto.get("valor_impuesto") or 0))
            )

        # v3.7.1: Persistir retenciones en Contabilidad.Retencion (Pull Model)
        from apps.tenant.contabilidad.services.retenciones_service import RetencionesService
        for tipo_retencion, clave in [('RETEFUENTE', 'retefuente'), ('RETEICA', 'reteica'), ('RETEIVA', 'reteiva')]:
            monto_raw = totales.get(clave) or dto.get(clave, 0)
            monto = Decimal(str(monto_raw)) if monto_raw else Decimal('0')
            if monto > Decimal('0'):
                RetencionesService.crear_retencion(
                    empresa=empresa_instance,
                    tipo=tipo_retencion,
                    monto=monto,
                    documento_origen_app='facturas',
                    documento_origen_modelo='Factura',
                    documento_origen_id=factura.id,
                )

        # # WARNING: SINTEL v2.62: Persistencia delegada de Nota de Crédito
        if tipo == Factura.TipoFactura.NC:
            referencia_dto = dto.get("referencia", {})
            ref_cufe = referencia_dto.get("cufe") or dto.get("ref_factura_cufe")
            factura_original = factura_original_para_nc
            
            nota = NotaCredito.objects.create(
                empresa=empresa_instance,
                factura=factura_original,
                numero=numero,
                cude=cufe,
                fecha_emision=fecha_emision,
                moneda=totales.get("moneda") or dto.get("moneda", "COP"),
                subtotal=Decimal(str(totales.get("subtotal") or dto.get("subtotal") or 0)),
                impuestos=Decimal(str(totales.get("impuestos") or dto.get("impuestos") or 0)),
                total=Decimal(str(totales.get("total") or dto.get("total") or 0)),
                motivo=dto.get("motivo") or referencia_dto.get("motivo") or "Anulación/Ajuste de factura",
                ref_factura_numero=factura_original.numero,
                ref_factura_cufe=factura_original.cufe,
                retefuente=Decimal(str(totales.get("retefuente") or 0)),
                reteica=Decimal(str(totales.get("reteica") or 0)),
                reteiva=Decimal(str(totales.get("reteiva") or 0)),
                xml_content=xml_text or "",
            )
            logger.info(f"[facturas:nc] Nota de Crédito {factura.numero} persistida y vinculada a referencia {ref_cufe}")

            # v3.27: Items de la NC (CreditNoteLine, ya parseados por el pipeline
            # universal en dto["items"] -- mismo shape que los items de Factura)
            # + disparo real de ENTRADA_DEVOLUCION (Pull hacia Contabilidad se
            # resuelve solo via ExtractorInventario, F22, sin cambios).
            for idx, item in enumerate(dto.get("items", []), start=1):
                cantidad = Decimal(str(item.get("cantidad") or "0"))
                if cantidad <= 0:
                    continue
                valor_unitario = Decimal(str(item.get("valor_unitario") or "0"))
                porcentaje_iva = Decimal(str(item.get("porcentaje_iva") or "0"))
                subtotal_item = Decimal(str(item.get("subtotal") or (cantidad * valor_unitario)))
                total_item = Decimal(str(item.get("total") or subtotal_item))
                valor_iva = total_item - subtotal_item

                item_inventario_uuid = None
                item_inventario_tipo = None
                item_inventario_codigo = None
                codigo_item = (item.get("codigo") or "").strip()
                if codigo_item:
                    from apps.tenant.inventario.models import Producto
                    producto_resuelto = Producto.objects.filter(
                        empresa=empresa_instance, codigo=codigo_item, activo=True,
                    ).only("id", "uuid").first()
                    if producto_resuelto:
                        item_inventario_uuid = producto_resuelto.uuid
                        item_inventario_tipo = ItemNotaCredito.TipoItemInventario.PRODUCTO
                        item_inventario_codigo = codigo_item

                ItemNotaCredito.objects.create(
                    empresa=empresa_instance,
                    nota_credito=nota,
                    linea_id=item.get("linea_id") or "",
                    codigo=codigo_item,
                    descripcion=item.get("descripcion") or "",
                    item_inventario_uuid=item_inventario_uuid,
                    item_inventario_tipo=item_inventario_tipo,
                    item_inventario_codigo=item_inventario_codigo,
                    cantidad=cantidad,
                    unidad_medida=item.get("unidad_medida") or "UND",
                    valor_unitario=valor_unitario,
                    porcentaje_iva=porcentaje_iva,
                    valor_iva=valor_iva,
                    subtotal=subtotal_item,
                    total=total_item,
                    orden=idx,
                )

            FacturaBusinessService._generar_entrada_devolucion(
                nota=nota, empresa_id=empresa_instance.id, sede_id=factura_original.sede_id,
            )

            return {
                "id": nota.id,
                "uuid": str(nota.uuid),
                "numero": nota.numero,
                "cude": nota.cude,
                "created": True,
                "message": "Nota credito creada exitosamente.",
            }, 201

        # Crear items
        for item in dto.get("items", []):
            ItemFactura.objects.create(
                factura=factura,
                empresa=empresa_instance,
                linea_id=item.get("linea_id", ""),
                codigo=item.get("codigo", ""),
                descripcion=item.get("descripcion", ""),
                cantidad=item.get("cantidad", 1),
                unidad_medida=item.get("unidad_medida", "UND"),
                valor_unitario=item.get("valor_unitario", 0),
                porcentaje_iva=item.get("porcentaje_iva", 0),
                valor_iva=item.get("valor_iva", 0),
                porcentaje_retefuente=item.get("porcentaje_retefuente", 0),
                valor_retefuente=item.get("valor_retefuente", 0),
                porcentaje_reteiva=item.get("porcentaje_reteiva", 0),
                valor_reteiva=item.get("valor_reteiva", 0),
                porcentaje_reteica=item.get("porcentaje_reteica", 0),
                valor_reteica=item.get("valor_reteica", 0),
                subtotal=item.get("subtotal", 0),
                total=item.get("total", 0),
                es_servicio=item.get("es_servicio", False),
                orden=item.get("orden", 1),
            )

        return {
            "id": factura.id,
            "uuid": str(factura.uuid),
            "numero": factura.numero,
            "naturaleza": factura.naturaleza,
            "cufe": factura.cufe,
            "created": True,
            "message": "Factura creada exitosamente.",
        }, 201

    # ------------------------------------------------------------------
    # v3.27: entrada de inventario real por devolucion (Nota Credito)
    # ------------------------------------------------------------------

    @staticmethod
    def _generar_entrada_devolucion(nota: NotaCredito, empresa_id: int, sede_id: int | None) -> None:
        """
        Genera MovimientoInventario(ENTRADA_DEVOLUCION) por cada ItemNotaCredito
        con producto real resuelto (item_inventario_uuid no nulo). Reutiliza
        KardexService.registrar_movimiento() -- no se crea un servicio de
        inventario nuevo. Costo desde Producto.costo_promedio (mismo criterio
        que SALIDA_VENTA, nunca precio_unitario/valor_unitario del documento).
        Idempotente via el mismo UniqueConstraint que ya usa MovimientoInventario
        (documento_origen = ItemNotaCredito, mismo criterio de granularidad que
        ItemVenta/RecepcionCompraItem). Items sin producto resoluble (servicios,
        o codigo sin match en el catalogo) se omiten sin bloquear la NC -- mismo
        patron de omision elegante que RecepcionCompraBusinessService.confirmar_recepcion().
        """
        from apps.tenant.inventario.models import MovimientoInventario, Producto
        from apps.tenant.inventario.services.business_service import KardexService

        items_con_producto = (
            nota.items
            .filter(item_inventario_uuid__isnull=False)
            .only("id", "cantidad", "item_inventario_uuid")
        )
        for item in items_con_producto:
            producto = Producto.objects.filter(
                uuid=item.item_inventario_uuid, empresa_id=empresa_id, activo=True,
            ).only("id", "costo_promedio").first()
            if producto is None:
                logger.info(
                    "[FacturaBS] ItemNotaCredito id=%s referencia producto uuid=%s ya no "
                    "resoluble -- se omite ENTRADA_DEVOLUCION.",
                    item.id, item.item_inventario_uuid,
                )
                continue
            KardexService.registrar_movimiento(
                empresa_id=empresa_id,
                producto_id=producto.id,
                tipo=MovimientoInventario.TipoMovimiento.ENTRADA_DEVOLUCION,
                cantidad=item.cantidad,
                costo_unitario=producto.costo_promedio,
                origen_referencia=f"NC {nota.numero}",
                sede_id=sede_id,
                documento_origen_app='facturas',
                documento_origen_modelo='ItemNotaCredito',
                documento_origen_id=item.id,
            )

    @staticmethod
    def importar_documento(file_bytes, filename='ubl.xml', preview=False, async_mode=False, **kwargs):
        """
        Inicia el proceso de importacion de un documento.

        Flujo:
        1. Delega parseo a ingest_document (pipeline universal).
        2. Si preview=True, retorna DTO sin persistir.
        3. Si preview=False, persiste via guardar_desde_dto.
        """
        if HAS_DOCUMENT_INGEST and getattr(settings, 'FEATURE_DOCUMENT_PIPELINE', False):
            result, code = ingest_document(
                content=file_bytes, filename=filename,
                preview=preview, async_mode=async_mode,
            )
            # Si el parseo fallo o es preview, retornar tal cual
            if code >= 400 or preview:
                return result, code

            # Persistir el DTO parseado
            dto = result.get("dto", {})
            if not dto:
                return {"error": "empty_dto", "message": "El pipeline no produjo un DTO valido."}, 422

            xml_text = file_bytes.decode('utf-8', errors='ignore') if isinstance(file_bytes, bytes) else str(file_bytes)
            return FacturaBusinessService.guardar_desde_dto(
                dto, xml_text=xml_text, file_bytes=file_bytes,
            )

        # Fallback legacy
        from apps.tenant.facturas.utils.ubl_parser import parse_ubl_to_dict, _parse_xml
        try:
            xml_str = file_bytes.decode('utf-8') if isinstance(file_bytes, bytes) else file_bytes
            root = _parse_xml(xml_str)
            dto = parse_ubl_to_dict(root, xml_bytes=file_bytes)
            if preview:
                return {"persisted": False, "dto": dto}, 200
            xml_text = xml_str if isinstance(xml_str, str) else xml_str.decode('utf-8', errors='ignore')
            return FacturaBusinessService.guardar_desde_dto(
                dto, xml_text=xml_text, file_bytes=file_bytes,
            )
        except Exception as e:
            return {"error": "parse_error", "message": str(e)}, 422

    @staticmethod
    def materializar_desde_result(result, empresa_id=None):
        """
        Confirma la creación de una factura desde un resultado de preview.
        """
        dto = result.get("dto")
        if not dto:
            return {"error": "invalid_result", "message": "Resultado de pipeline inválido."}, 400
        
        return FacturaBusinessService.guardar_desde_dto(dto)

    @staticmethod
    def resumen(empresa_id=None):
        """Retorna el resumen financiero (vía Selectors)."""
        from apps.tenant.facturas.services.selectors import FacturaSelectors
        return FacturaSelectors.get_summary(empresa_id=empresa_id)

    @staticmethod
    def obtener_xml(factura, tipo='ubl'):
        """Retorna el XML de un anexo (vía Selectors)."""
        from apps.tenant.facturas.services.selectors import FacturaSelectors
        return FacturaSelectors.obtener_anexo_xml(factura, tipo)

    @staticmethod
    def actualizar_factura_limitado(
        factura: Factura, data: dict[str, Any], empresa_id: int, sede_ids=None,
    ) -> Factura:
        """
        Actualizacion parcial segura de factura (Limited Edit).

        - DSV: rechaza si factura no pertenece a empresa_id.
        - Rechaza con 400 cualquier campo XML inmutable.
        - Sanitiza "" a None para fechas y UUID.
        - Usa MANUAL_EDITABLE_FIELDS (SSoT en models.py).

        [OSF Fase F9] `sede_ids` (opcional, conjunto de sedes del
        OrganizationalScope de quien hace la peticion) se propaga a
        CotizacionBridge al vincular `cotizacion_uuid`: un perfil con
        alcance SEDE/AREA no debe poder vincular una Factura a una
        Cotizacion de una sede fuera de su alcance, aunque pertenezca a la
        misma empresa. `None` (default) no restringe - comportamiento
        identico al de antes de esta fase.

        [OSF Fase F11] `sede_ids` tambien restringe ahora la propia
        asignacion del campo `sede` de la Factura: solo se puede asignar una
        sede que pertenezca a la empresa Y este dentro del alcance
        organizacional de quien edita (mismo `sede_ids`, verificacion
        estricta - no NULL-safe, porque aqui se valida la sede DESTINO, no
        si un registro existente sin sede es visible).
        """
        from rest_framework.exceptions import ValidationError

        # DSV: verificar propiedad del tenant
        if factura.empresa_id != empresa_id:
            raise ValidationError({"detail": "La factura no pertenece a la empresa activa."})

        # Rechazar campos XML inmutables con 400 explicito
        attempted_xml = XML_IMMUTABLE_FIELDS & set(data.keys())
        if attempted_xml:
            raise ValidationError({
                field: f"Campo inmutable: '{field}' proviene del XML y no puede modificarse."
                for field in attempted_xml
            })

        update_data = {}

        for field in MANUAL_EDITABLE_FIELDS:
            if field not in data:
                continue
            val = data[field]

            # Sanitizar "" -> None para fechas y UUID
            if val == "":
                val = None

            # DSV para cotizacion + auto-sync snapshot (v3.10.1)
            if field == 'cotizacion_uuid' and val:
                from apps.tenant.facturas.services.selectors import CotizacionBridge
                if not CotizacionBridge.exists_by_uuid(val, empresa_id, sede_ids=sede_ids):
                    raise ValidationError({
                        "cotizacion_uuid": "La cotización no existe, no pertenece a la empresa, "
                                           "o esta fuera de su alcance organizacional."
                    })
                # Auto-sync snapshot: obtener numero y guardarlo
                cot = CotizacionBridge.obtener_cotizacion_por_uuid(val, empresa_id, sede_ids=sede_ids)
                if cot:
                    update_data['cotizacion_numero'] = cot.get('numero_cotizacion')
            elif field == 'cotizacion_uuid' and not val:
                # Desvincular: limpiar snapshot también
                update_data['cotizacion_numero'] = None

            # [OSF Fase F11] `sede` deja de ser meramente informativa: se
            # vuelve editable via el unico camino de escritura realmente
            # alcanzable hoy (Limited Edit) - antes de esta fase el DSV de
            # alcance ya existia en FacturaDetailSerializer.validate() (F8)
            # pero era codigo muerto (ese serializer nunca se usa para
            # escritura aqui, ver auditoria de F8). Resuelve UUID o PK
            # (mismo patron que UUIDOrPKRelatedField), anti-IDOR por
            # empresa_id y verificacion de alcance organizacional.
            elif field == 'sede':
                if val:
                    from apps.tenant.empresa.models import Sede
                    data_str = str(val)
                    sede_obj = (
                        Sede.objects.filter(id=val, empresa_id=empresa_id).first()
                        if data_str.isdigit()
                        else Sede.objects.filter(uuid=val, empresa_id=empresa_id).first()
                    )
                    if sede_obj is None:
                        raise ValidationError({
                            "sede": "La sede no existe o no pertenece a la empresa."
                        })
                    if sede_ids is not None and sede_obj.id not in sede_ids:
                        raise ValidationError({
                            "sede": "No tiene permiso para asignar esta sede "
                                    "(fuera de su alcance organizacional)."
                        })
                    val = sede_obj
                else:
                    val = None

            update_data[field] = val

        if not update_data:
            return factura

        # ── Validacion de estado_pago vs conciliacion bancaria (v3.11.0) ────────
        nuevo_estado_pago = update_data.get('estado_pago')
        if nuevo_estado_pago:
            medio = update_data.get('medio_pago_codigo', factura.medio_pago_codigo)
            es_efectivo = (medio == '10')  # DIAN codigo '10' = Efectivo

            if not es_efectivo:
                total_bancos  = factura.total_pagado_bancos
                saldo_pend    = factura.saldo_pendiente

                if nuevo_estado_pago == 'PAGADA' and saldo_pend > 0:
                    raise ValidationError({
                        "estado_pago": (
                            f"La factura no esta 100% conciliada en bancos. "
                            f"Solo puede marcarse como PAGO_PARCIAL. "
                            f"Diferencia pendiente: ${saldo_pend:,.2f}"
                        )
                    })

                if nuevo_estado_pago in ('PAGADA', 'PAGO_PARCIAL') and total_bancos == 0:
                    raise ValidationError({
                        "estado_pago": (
                            "No hay conciliaciones bancarias asociadas a esta factura. "
                            "El estado debe ser NO_PAGADA."
                        )
                    })

        return FacturaCRUDService.actualizar(factura, update_data)

    @staticmethod
    def vincular_cliente(factura: Factura, cliente_uuid: str | None, empresa_id: int) -> Factura:
        """Vincula un cliente existente a una factura de venta."""
        from rest_framework.exceptions import ValidationError
        from apps.tenant.facturas.services.selectors import ClienteBridge

        if factura.empresa_id != empresa_id:
            raise ValidationError({"detail": "La factura no pertenece a la empresa activa."})

        if factura.naturaleza != Factura.Naturaleza.VENTA:
            raise ValidationError({"cliente_uuid": "Solo las facturas de venta pueden vincularse a clientes."})

        if not cliente_uuid:
            raise ValidationError({"cliente_uuid": "Una factura de venta debe tener un cliente vinculado."})

        if not ClienteBridge.exists_by_uuid(cliente_uuid, empresa_id):
            raise ValidationError({"cliente_uuid": "El cliente no existe o no pertenece a la empresa."})

        return FacturaCRUDService.actualizar(factura, {"cliente_uuid": cliente_uuid})

    @staticmethod
    def vincular_proveedor(factura: Factura, proveedor_uuid: str | None, empresa_id: int) -> Factura:
        """Vincula un proveedor existente a una factura de compra."""
        from rest_framework.exceptions import ValidationError
        from apps.tenant.facturas.services.selectors import ProveedorBridge

        if factura.empresa_id != empresa_id:
            raise ValidationError({"detail": "La factura no pertenece a la empresa activa."})

        if factura.naturaleza != Factura.Naturaleza.COMPRA:
            raise ValidationError({"proveedor_uuid": "Solo las facturas de compra pueden vincularse a proveedores."})

        if not proveedor_uuid:
            raise ValidationError({"proveedor_uuid": "Una factura de compra debe tener un proveedor vinculado."})

        if not ProveedorBridge.exists_by_uuid(proveedor_uuid, empresa_id):
            raise ValidationError({"proveedor_uuid": "El proveedor no existe o no pertenece a la empresa."})

        return FacturaCRUDService.actualizar(factura, {"proveedor_uuid": proveedor_uuid})



class FacturaInterAppAPI:
    """
    [v3.10.0] ABIERTO PARA APPS DE NEGOCIO.

    Contrato de acceso sin restriccion empresa_id para lectura.
    Usada por: Contabilidad, Proyectos, Gastos, Empleados, Proveedores, etc.

    Reglas:
    - LECTURA sin filtro empresa_id (permite acceso a todas las facturas del tenant)
    - ESCRITURA: usar FacturaBusinessService + empresa_id (DSV obligatorio)
    - Llamadas desde servicios internos SOLO — no exponible como API HTTP
    """

    @staticmethod
    def list_all(search: str | None = None, order_by: str = '-fecha_emision'):
        """
        [ABIERTO] QuerySet de TODAS las facturas sin filtro empresa_id.
        Llamable desde apps de negocio para integracion.

        Params:
          search: filtro por numero/cufe/receptor/emisor
          order_by: campo de ordenamiento (default -fecha_emision)

        Returns:
          Django QuerySet — compatible con iteracion, agregacion, etc.
        """
        from apps.tenant.facturas.services.selectors import FacturaSelectors
        qs = FacturaSelectors.qs_list(empresa_id=None, search=search)
        if order_by:
            qs = qs.order_by(order_by)
        return qs

    @staticmethod
    def get_by_id(factura_id: int | None = None, factura_uuid: str | None = None):
        """
        [ABIERTO] Obtiene una factura por id o uuid sin validar empresa_id.
        Llamable desde apps de negocio.
        """
        try:
            if factura_uuid:
                return Factura.objects.get(uuid=factura_uuid)
            elif factura_id:
                return Factura.objects.get(id=factura_id)
        except Factura.DoesNotExist:
            return None
        return None

    @staticmethod
    def summary_all() -> dict:
        """
        [ABIERTO] Resumen financiero consolidado (TODAS las empresas).
        Usa agregacion django, no filtra empresa_id.
        """
        from apps.tenant.facturas.services.selectors import FacturaSelectors
        return FacturaSelectors.get_summary(empresa_id=None)

    @staticmethod
    def get_by_cufe(cufe: str):
        """[ABIERTO] Busca factura por CUFE."""
        try:
            return Factura.objects.get(cufe=cufe)
        except Factura.DoesNotExist:
            return None

    @staticmethod
    def get_by_numero(numero: str):
        """[ABIERTO] Busca factura por número."""
        try:
            return Factura.objects.get(numero=numero)
        except Factura.DoesNotExist:
            return None

    @staticmethod
    def resolve_cotizacion(factura_uuid: str | None = None, factura_id: int | None = None) -> dict | None:
        """
        [ABIERTO] Resuelve Cotizacion vinculada a una Factura.
        Importa desde servicio Cotizaciones usando CotizacionBridge.

        Params:
          factura_uuid o factura_id: identifica la factura

        Returns:
          dict con datos de Cotizacion o None
        """
        factura = None
        if factura_uuid:
            factura = FacturaInterAppAPI.get_by_id(factura_uuid=factura_uuid)
        elif factura_id:
            factura = FacturaInterAppAPI.get_by_id(factura_id=factura_id)

        if not factura or not factura.cotizacion_uuid:
            return None

        from apps.tenant.facturas.services.selectors import CotizacionBridge
        return CotizacionBridge.obtener_cotizacion_por_uuid(
            cotizacion_uuid=str(factura.cotizacion_uuid),
            empresa_id=None  # Sin empresa_id para acceso abierto
        )

    @staticmethod
    def recalcular_estado_pago_automatico(factura_uuid) -> bool:
        """
        [v3.11.0] Disparo cross-app desde Bancos tras conciliar una transaccion.

        Reglas:
        - Solo actua si medio_pago_codigo != '10' (no Efectivo).
        - saldo_pendiente == 0  → PAGADA
        - total_pagado_bancos > 0 pero saldo_pendiente > 0 → PAGO_PARCIAL
        - total_pagado_bancos == 0 → NO_PAGADA

        Returns True si el estado fue modificado, False si no cambio o es efectivo.
        """
        import logging
        log = logging.getLogger(__name__)

        try:
            factura = Factura.objects.only(
                'id', 'uuid', 'empresa_id', 'estado_pago',
                'medio_pago_codigo', 'total',
            ).get(uuid=factura_uuid)
        except Factura.DoesNotExist:
            log.warning("[BancosIntegracion] factura_uuid=%s no encontrada", factura_uuid)
            return False

        if factura.medio_pago_codigo == '10':
            return False  # Efectivo: el usuario controla el estado manualmente

        total_bancos = factura.total_pagado_bancos
        saldo        = factura.saldo_pendiente

        if saldo <= 0 and total_bancos > 0:
            nuevo = 'PAGADA'
        elif total_bancos > 0 and saldo > 0:
            nuevo = 'PAGO_PARCIAL'
        else:
            nuevo = 'NO_PAGADA'

        if factura.estado_pago == nuevo:
            return False

        factura.estado_pago = nuevo
        factura.save(update_fields=['estado_pago'])
        log.info(
            "[BancosIntegracion] Factura uuid=%s estado_pago actualizado a %s",
            factura_uuid, nuevo
        )
        return True


class FacturaService:
    """
    Facade de alto nivel para integraciones externas (Celery, management commands).
    No usar desde ViewSets — usar FacturaBusinessService directamente.
    """

    @staticmethod
    def crear_desde_xml(xml_content, empresa_id, usuario_id):
        """
        Procesamiento de factura XML UBL 2.1 desde Celery Task o integracion externa.
        """
        return FacturaBusinessService.importar_documento(
            xml_content,
            empresa_id=empresa_id,
            usuario_id=usuario_id
        )
