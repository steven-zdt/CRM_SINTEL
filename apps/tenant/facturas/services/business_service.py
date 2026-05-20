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
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from apps.tenant.empresa.models import Empresa
from apps.tenant.facturas.models import Factura, ItemFactura, NotaCredito, MANUAL_EDITABLE_FIELDS, XML_IMMUTABLE_FIELDS
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


class FacturaBusinessService:
    """
    Servicio de lógica de negocio para Facturas.
    """

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
    def guardar_desde_dto(
        dto: dict[str, Any], 
        xml_text: str = None,
        file_bytes: bytes = None,
        file_type: str = 'xml'
    ) -> tuple[dict[str, Any], int]:
        """
        Persiste factura desde DTO canonico (v3.5).

        Soporta el DTO del pipeline universal (nested: emisor.nit, totales.subtotal, etc.)
        y el DTO legacy (flat: emisor_nit, subtotal, etc.).
        """
        try:
            empresa_config = get_empresa_emisor_data()
        except EmpresaNotConfiguredError as ex:
            return {"error": "empresa_no_configurada", "message": str(ex)}, 422

        # --- Helpers para leer nested O flat ---
        emisor = dto.get("emisor", {}) if isinstance(dto.get("emisor"), dict) else {}
        receptor = dto.get("receptor", {}) if isinstance(dto.get("receptor"), dict) else {}
        totales = dto.get("totales", {}) if isinstance(dto.get("totales"), dict) else {}
        identificadores = dto.get("identificadores", {}) if isinstance(dto.get("identificadores"), dict) else {}
        autorizacion = dto.get("autorizacion", {}) if isinstance(dto.get("autorizacion"), dict) else {}

        # Extraer y normalizar
        numero = FacturaBusinessService.normalize_document_number(dto.get("numero"))
        emisor_nit = FacturaBusinessService.normalize_document_number(
            emisor.get("nit") or dto.get("emisor_nit", "")
        )
        receptor_nit = FacturaBusinessService.normalize_document_number(
            receptor.get("nit") or dto.get("receptor_nit", "")
        )

        # Validacion de campos obligatorios
        if not numero or not emisor_nit or not receptor_nit:
            return {"error": "missing_required_fields", "message": "Numero, NIT Emisor y NIT Receptor son obligatorios."}, 422

        # Determinar naturaleza
        naturaleza = FacturaBusinessService._resolver_naturaleza(emisor_nit, empresa_config.get("nit"))

        # Cascading Security
        if naturaleza == Factura.Naturaleza.COMPRA:
            nit_tenant = FacturaBusinessService.normalize_document_number(empresa_config.get("nit"))
            if receptor_nit != nit_tenant:
                return {
                    "error": "document_not_for_tenant",
                    "message": f"Documento dirigido a tercero (NIT receptor: {receptor_nit}). No pertenece a este tenant."
                }, 422

        # Empresa instance
        try:
            empresa_instance = Empresa.objects.get(
                nit=FacturaBusinessService.normalize_document_number(empresa_config.get("nit"))
            )
        except Empresa.DoesNotExist:
            return {"error": "empresa_not_found", "message": "La empresa no existe."}, 404

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
            factura_existente = Factura.objects.filter(
                cufe=cufe, empresa=empresa_instance
            ).only('id', 'uuid', 'numero', 'naturaleza', 'cufe').first()
            if factura_existente:
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
        doc_type = dto.get("document_type", "")
        if "creditnote" in doc_type.lower():
            tipo = Factura.TipoFactura.NC
        elif "debitnote" in doc_type.lower():
            tipo = Factura.TipoFactura.ND
        else:
            tipo = Factura.TipoFactura.FE

        # Estado: importadas se marcan como ACEPTADA
        estado = dto.get("estado") or Factura.Estado.ACEPTADA

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

        # v3.7.1: Persistir retenciones en Contabilidad.Retencion (Pull Model)
        from apps.tenant.contabilidad.services.retenciones_service import RetencionesService
        for tipo, clave in [('RETEFUENTE', 'retefuente'), ('RETEICA', 'reteica'), ('RETEIVA', 'reteiva')]:
            monto_raw = totales.get(clave) or dto.get(clave, 0)
            monto = Decimal(str(monto_raw)) if monto_raw else Decimal('0')
            if monto > Decimal('0'):
                RetencionesService.crear_retencion(
                    empresa=empresa_instance,
                    tipo=tipo,
                    monto=monto,
                    documento_origen_app='facturas',
                    documento_origen_modelo='Factura',
                    documento_origen_id=factura.id,
                )

        # # WARNING: SINTEL v2.62: Persistencia delegada de Nota de Crédito
        if tipo == Factura.TipoFactura.NC:
            referencia_dto = dto.get("referencia", {})
            ref_cufe = referencia_dto.get("cufe") or dto.get("ref_factura_cufe")
            
            # Intentar localizar la factura original para referencia informativa
            factura_original = None
            if ref_cufe:
                factura_original = Factura.objects.filter(cufe=ref_cufe, empresa=empresa_instance).first()
            
            if not factura_original and dto.get("ref_factura_numero"):
                factura_original = Factura.objects.filter(numero=dto.get("ref_factura_numero"), empresa=empresa_instance).first()

            # [VALIDACIÓN] Idempotencia: No permitir dos NCs para la misma factura si ya existe el vínculo
            if factura_original and NotaCredito.objects.filter(ref_factura_cufe=factura_original.cufe).exists():
                 logger.warning(f"[facturas:nc] Intento de duplicar NC para factura {factura_original.numero}")
                 # Opcional: Podríamos retornar error aquí si queremos ser estrictos 1:1
            
            # Crear registro de extensión NotaCredito vinculado al documento 'factura' (que es la NC)
            NotaCredito.objects.create(
                empresa=empresa_instance,
                factura=factura, # Vínculo OneToOne con el documento NC
                cude=cufe, 
                motivo=dto.get("motivo") or referencia_dto.get("motivo") or "Anulación/Ajuste de factura",
                ref_factura_numero=factura_original.numero if factura_original else (dto.get("ref_factura_numero") or ""),
                ref_factura_cufe=factura_original.cufe if factura_original else (ref_cufe or ""),
                retefuente=Decimal(str(totales.get("retefuente") or 0)),
                reteica=Decimal(str(totales.get("reteica") or 0)),
                reteiva=Decimal(str(totales.get("reteiva") or 0)),
            )
            logger.info(f"[facturas:nc] Nota de Crédito {factura.numero} persistida y vinculada a referencia {ref_cufe}")

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
    def actualizar_factura_limitado(factura: Factura, data: dict[str, Any], empresa_id: int) -> Factura:
        """
        Actualizacion parcial segura de factura (Limited Edit).

        - DSV: rechaza si factura no pertenece a empresa_id.
        - Rechaza con 400 cualquier campo XML inmutable.
        - Sanitiza "" a None para fechas y UUID.
        - Usa MANUAL_EDITABLE_FIELDS (SSoT en models.py).
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
            if field in {'fecha_vencimiento', 'payment_due_date', 'cuenta_contable_uuid'} and val == "":
                val = None

            # DSV para cuenta contable
            if field == 'cuenta_contable_uuid' and val:
                from apps.tenant.contabilidad.services.selectors import CuentaContableSelector
                if not CuentaContableSelector.exists_by_uuid(val, empresa_id):
                    raise ValidationError({
                        "cuenta_contable_uuid": "La cuenta contable no existe o no pertenece a la empresa."
                    })

            update_data[field] = val

        if not update_data:
            return factura

        return FacturaCRUDService.actualizar(factura, update_data)



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
