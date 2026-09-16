import logging
from decimal import Decimal
from typing import Any, Dict, Tuple, Optional

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.tenant.gastos.models import DocumentoSoporte, ResolucionDIAN
from apps.tenant.gastos.services.crud_service import DocumentoCRUDService, ResolucionCRUDService

# Lazy imports for cross-domain dependencies (proveedores, inventario, contabilidad)
# kept inside def blocks to avoid circular imports at module load time
HAS_ACCOUNTING = False

logger = logging.getLogger(__name__)


class GastoBusinessService:
    """
    Logica de negocio centralizada para Gastos.
    SSoT para calculos, validaciones y orquestacion de procesos.
    """

    # [REMOVED v3.7.1] calcular_retenciones moved to contabilidad.RetencionesService

    @staticmethod
    @transaction.atomic
    def anular_gasto(gasto_id: int, motivo: str, usuario: Any, empresa_id: int = None) -> Tuple[bool, Dict[str, Any], int]:
        """Orquesta la anulacion de un gasto (Inmutabilidad legal)."""
        try:
            qs = DocumentoSoporte.objects.filter(id=gasto_id)
            if empresa_id:
                qs = qs.filter(empresa_id=empresa_id)
                
            documento = qs.first()
            if not documento:
                return False, {"detail": "Documento no encontrado o no pertenece a la empresa."}, 404

            if documento.anulado:
                return False, {"detail": "El documento ya se encuentra anulado."}, 400

            # REM P0-02 (docs/remediation/REM-P0-02.md): PeriodoContable.__doc__
            # afirma "Bloquea edicion/anulacion de Facturas y Gastos en
            # periodos cerrados", pero verificar_periodo_cerrado() nunca se
            # invocaba desde gastos -- un documento podia anularse libremente
            # con fecha dentro de un periodo ya cerrado, descuadrando
            # reportes ya emitidos de ese periodo.
            from apps.tenant.contabilidad.services.selectors import verificar_periodo_cerrado
            cerrado, periodo_nombre = verificar_periodo_cerrado(documento.fecha, empresa_id or documento.empresa_id)
            if cerrado:
                return False, {
                    "detail": (
                        f"No se puede anular este documento: su fecha "
                        f"({documento.fecha}) pertenece al periodo contable "
                        f"'{periodo_nombre}', que ya esta CERRADO."
                    )
                }, 400

            # Logica de negocio: Anulacion es irreversible. v2.62: Trazabilidad
            DocumentoCRUDService.anular_documento(documento, motivo, usuario)
            
            return True, {"message": "Gasto anulado correctamente."}, 200
        except ValidationError as e:
            return False, e.detail, 400
        except Exception as e:
            logger.error(f"Error en anular_gasto: {e}", exc_info=True)
            return False, {"detail": f"Error interno: {str(e)}"}, 500

    @staticmethod
    @transaction.atomic
    def desactivar_gasto(gasto_id: int, empresa_id: int = None) -> Dict[str, Any]:
        """Desactiva un gasto (Soft Delete)."""
        qs = DocumentoSoporte.objects.filter(id=gasto_id)
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)
            
        documento = qs.first()
        if not documento:
            raise ValidationError("Documento no encontrado.")

        DocumentoCRUDService.desactivar_documento(documento)
        return {"message": "Gasto desactivado correctamente."}

    @staticmethod
    @transaction.atomic
    def eliminar_gasto(gasto_id: int, empresa_id: int = None) -> Tuple[bool, Dict[str, Any], int]:
        """
        Elimina un gasto (Sigue el estandar de Clientes: Bloqueo si activo, Fisico si inactivo).
        En Gastos, 'Inactivo' para borrado significa anulado=True.
        """
        try:
            qs = DocumentoSoporte.objects.filter(id=gasto_id)
            if empresa_id:
                qs = qs.filter(empresa_id=empresa_id)
                
            documento = qs.first()
            if not documento:
                return False, {"detail": "Documento no encontrado."}, 404

            # [STANDARDIZATION] Bloquear si no esta anulado
            if not documento.anulado:
                return False, {
                    "detail": "No se puede eliminar un gasto activo. Debe anularlo primero para poder borrar el registro permanentemente."
                }, 400

            # [STANDARDIZATION] Borrado fisico de registros inactivos
            DocumentoCRUDService.eliminar_documento(documento)
            return True, {"message": "Gasto eliminado permanentemente."}, 204
            
        except Exception as e:
            logger.error(f"Error en eliminar_gasto: {e}", exc_info=True)
            return False, {"detail": f"Error al procesar borrado: {str(e)}"}, 500

    # [REMOVED v3.7.1] calcular_y_validar_totales deprecated. Retentions are Pull Model.

    @staticmethod
    @transaction.atomic
    def procesar_gasto(empresa: Any, data: Dict[str, Any]) -> Tuple[bool, Any, int]:
        """
        Orquesta la creacion de un DocumentoSoporte (Gasto v3.7.1).
        Realiza Double Semantic Verification (DSV) e integra con Contabilidad (Pull Model).
        """
        logger.info(f"[GastoBusinessService:procesar_gasto] Iniciando proceso para empresa={empresa.id}")
        try:
            # Normalizacion de datos
            ds_data = data.get('documento_soporte', data) if 'documento_soporte' in data else data
            
            # SINTEL v3.7.1 - Asegurar que descripcion se capture (si viene afuera o adentro)
            if 'descripcion' in data and 'descripcion' not in ds_data:
                ds_data['descripcion'] = data['descripcion']
            
            # Limpieza de campos obsoletos (v3.7.1)
            for legacy_field in ['retefuente_porcentaje', 'reteica_porcentaje', 'retefuente', 'reteica']:
                ds_data.pop(legacy_field, None)

            # Handle both field names for backward compatibility
            resolucion_id = ds_data.pop('resolucion_dian', None) or ds_data.pop('resolucion', None)
            if not resolucion_id:
                return False, {"error": "resolucion_requerida", "message": "Debe especificar una resolucion DIAN."}, 400

            # DSV: Resolucion
            resolucion = ResolucionDIAN.objects.filter(id=resolucion_id, empresa=empresa).first()
            if not resolucion:
                return False, {"error": "resolucion_invalida", "message": "La resolucion no es valida."}, 404

            # DSV: Proveedor (SINTEL v3.7.1 - Resiliencia ID/UUID)
            proveedor_id = ds_data.get('proveedor')
            from apps.tenant.proveedores.models import Proveedor
            import uuid as uuid_lib

            proveedor = None
            if proveedor_id:
                # 1. Intentar como UUID
                is_uuid = False
                try:
                    if isinstance(proveedor_id, str) and len(proveedor_id) >= 32:
                        uuid_lib.UUID(str(proveedor_id))
                        is_uuid = True
                except (ValueError, TypeError):
                    pass

                if is_uuid:
                    proveedor = Proveedor.objects.filter(uuid=proveedor_id, empresa=empresa).first()
                else:
                    # 2. Fallback a ID numerico
                    try:
                        proveedor = Proveedor.objects.filter(id=int(proveedor_id), empresa=empresa).first()
                    except (ValueError, TypeError, ValueError):
                        pass

            if not proveedor:
                return False, {"error": "proveedor_invalido", "message": f"El proveedor '{proveedor_id}' no es valido o no pertenece a su empresa."}, 404
            
            ds_data['proveedor'] = proveedor

            # DSV: Vinculacion transaccional al Kardex de Inventario (Pull Model)
            movimiento_uuid = ds_data.pop('movimiento_inventario_uuid', None)
            if movimiento_uuid:
                try:
                    uuid_lib.UUID(str(movimiento_uuid))
                except (ValueError, TypeError):
                    raise ValidationError({
                        "movimiento_inventario_uuid": "El formato del UUID de movimiento de inventario no es valido."
                    })
                
                from apps.tenant.inventario.services.selectors import MovimientoInventarioSelector
                mov = MovimientoInventarioSelector.get_detail(
                    empresa_id=empresa.id,
                    movimiento_uuid=movimiento_uuid
                )
                if not mov:
                    raise ValidationError({
                        "movimiento_inventario_uuid": f"El movimiento de inventario especificado '{movimiento_uuid}' no es valido o no pertenece a la empresa."
                    })
                ds_data['movimiento_inventario_uuid'] = movimiento_uuid

            # 1. Preparar Totales (v3.7.1 Pull Model)
            # NOTA: La fecha del documento (fecha_doc) corresponde a la fecha de la factura
            # del proveedor y NO debe ser restringida por el rango de vigencia de la resolucion
            # DIAN. La resolucion solo controla la numeracion consecutiva del documento soporte.
            subtotal = Decimal(str(ds_data.get('subtotal', 0)))
            ds_data['subtotal'] = subtotal
            
            # [SSoT] Obtener retenciones configuradas para el proveedor
            from apps.tenant.contabilidad.services.retenciones_service import RetencionesService
            config_ret = RetencionesService.obtener_retenciones_desde_tercero(
                nit=proveedor.numero_documento,
                tipo_tercero='PROVEEDOR',
                naturaleza='COMPRA',
                empresa_id=empresa.id
            )
            
            # Calcular retenciones iniciales para determinar el TOTAL neto
            monto_retefuente = RetencionesService.calcular_monto_retencion('RETEFUENTE', config_ret['retefuente_porcentaje'], subtotal)
            monto_reteica = RetencionesService.calcular_monto_retencion('RETEICA', config_ret['reteica_porcentaje'], subtotal)
            monto_reteiva = RetencionesService.calcular_monto_retencion('RETEIVA', config_ret['reteiva_porcentaje'], subtotal)
            
            total_neto = (subtotal - monto_retefuente - monto_reteica - monto_reteiva).quantize(Decimal('0.01'))
            ds_data['total'] = total_neto

            # 3. Persistencia via CRUD
            documento = DocumentoCRUDService.crear_documento(ds_data, empresa, resolucion)
            
            # 4. Registrar Retenciones en Contabilidad (v3.7.1)
            for tipo in ['RETEFUENTE', 'RETEICA', 'RETEIVA']:
                pct = config_ret.get(f'{tipo.lower()}_porcentaje', Decimal('0.00'))
                if pct > 0:
                    RetencionesService.crear_retencion(
                        empresa=empresa,
                        tipo=tipo,
                        porcentaje=pct,
                        base=subtotal,
                        documento_origen_app='gastos',
                        documento_origen_modelo='DocumentoSoporte',
                        documento_origen_id=documento.id,
                        notas=f"Auto-generada desde Gasto #{documento.consecutivo}"
                    )
            
            logger.info(f"[GastoBusinessService:procesar_gasto] Exito! ID={documento.id}, Total Neto={total_neto}")
            return True, documento, 201
            
        except ValidationError as e:
            # Error de DRF
            transaction.set_rollback(True)
            logger.warning(f"[GastoBusinessService:procesar_gasto] Error de validacion API: {e.detail}")
            return False, {"error": "validacion_api", "message": e.detail}, 400

        except DjangoValidationError as e:
            # Error de Modelo (full_clean)
            transaction.set_rollback(True)
            error_dict = e.message_dict if hasattr(e, 'message_dict') else {"non_field_errors": str(e)}
            logger.warning(f"[GastoBusinessService:procesar_gasto] Error de validacion Django: {error_dict}")
            logger.warning(f"[GastoBusinessService:procesar_gasto] Documento data al fallar: {ds_data}")
            return False, {"error": "validacion", "message": error_dict}, 400

        except Exception as e:
            transaction.set_rollback(True)
            logger.error(f"[GastoBusinessService:procesar_gasto] Error critico: {str(e)}", exc_info=True)
            return False, {"error": "error_interno", "message": str(e)}, 500




class ResolucionBusinessService:
    """Logica de negocio para ResolucionDIAN."""

    @staticmethod
    def validar_fechas_y_rangos(data: Dict[str, Any]):
        """Valida coherencia de fechas y rangos de la resolucion."""
        rango_desde = data.get('rango_desde')
        rango_hasta = data.get('rango_hasta')
        fecha_inicio = data.get('fecha_inicio')
        fecha_fin = data.get('fecha_fin')
        fecha_resolucion = data.get('fecha_resolucion')

        if rango_desde and rango_hasta and rango_hasta <= rango_desde:
            raise ValidationError({'rango_hasta': 'El numero final debe ser mayor al inicial.'})
        
        if fecha_inicio and fecha_fin and fecha_fin <= fecha_inicio:
            raise ValidationError({'fecha_fin': 'La fecha de fin debe ser posterior a la de inicio.'})
        
        if fecha_inicio and fecha_resolucion and fecha_inicio < fecha_resolucion:
            raise ValidationError({'fecha_inicio': 'La aplicacion no puede iniciar antes de la emision de la resolucion.'})

    @staticmethod
    @transaction.atomic
    def crear_resolucion(empresa: Any, data: dict[str, Any]) -> ResolucionDIAN:
        """Crea una nueva resolucion DIAN orchestrando validaciones."""
        data = data.copy()
        if 'fecha_resolucion' in data and 'fecha_inicio' not in data:
            data['fecha_inicio'] = data['fecha_resolucion']
            
        ResolucionBusinessService.validar_fechas_y_rangos(data)
        
        vigente = data.get('vigente', True)
        if vigente:
            ResolucionDIAN.objects.filter(empresa=empresa, vigente=True).update(vigente=False)
        
        return ResolucionCRUDService.crear_resolucion(data, empresa)

    @staticmethod
    @transaction.atomic
    def desactivar_resolucion(empresa_id: int, resolucion_id: int) -> ResolucionDIAN:
        """Desactiva una resolucion DIAN."""
        try:
            resolucion = ResolucionDIAN.objects.get(id=resolucion_id, empresa_id=empresa_id)
            return ResolucionCRUDService.desactivar_resolucion(resolucion)
        except ResolucionDIAN.DoesNotExist:
            raise ValidationError("Resolucion no encontrada o no pertenece a la empresa.")

    @staticmethod
    def puede_eliminar(empresa_id: int, resolucion_id: int) -> Tuple[bool, str]:
        """Verifica si una resolucion puede ser eliminada."""
        try:
            resolucion = ResolucionDIAN.objects.get(id=resolucion_id, empresa_id=empresa_id)
            if resolucion.vigente:
                return False, "No se puede eliminar una resolucion vigente."
            
            if not ResolucionCRUDService.puede_eliminar(resolucion):
                return False, "La resolucion tiene documentos asociados."
            
            return True, "La resolucion puede ser eliminada."
        except ResolucionDIAN.DoesNotExist:
            return False, "Resolucion no encontrada."


@transaction.atomic
def materializar_gasto_desde_dto(dto: dict) -> Tuple[dict, int]:
    """
    Materializa un gasto (DocumentoSoporte) a partir de un DTO canonico.
    Cumple con:
    - Idempotencia por numero (para el mismo proveedor/empresa)
    - Transaccionalidad atomica
    - Estricto aislamiento Multi-tenant
    """
    from django.core.exceptions import ValidationError
    from decimal import Decimal, InvalidOperation
    from django.utils.dateparse import parse_datetime

    # 1. Validaciones del DTO
    if not dto or not isinstance(dto, dict):
        raise ValidationError("El DTO no es un diccionario valido.")
        
    numero = dto.get("numero")
    if not numero:
        raise ValidationError("El campo 'numero' es obligatorio.")
        
    fecha_emision_str = dto.get("fecha_emision")
    if not fecha_emision_str:
        raise ValidationError("El campo 'fecha_emision' es obligatorio.")
        
    emisor = dto.get("emisor")
    if not emisor or not isinstance(emisor, dict):
        raise ValidationError("El campo 'emisor' es obligatorio y debe ser un diccionario.")
        
    emisor_nit = emisor.get("nit")
    if not emisor_nit:
        raise ValidationError("El NIT del emisor es obligatorio.")
        
    totales = dto.get("totales")
    if not totales or not isinstance(totales, dict) or "total" not in totales:
        raise ValidationError("El campo 'totales' con subcampo 'total' es obligatorio.")
        
    # 2. Parseo de datos
    try:
        dt = parse_datetime(fecha_emision_str)
        if not dt:
            from django.utils.dateparse import parse_date
            fecha_doc = parse_date(fecha_emision_str)
            if not fecha_doc:
                raise ValidationError("La fecha de emision no tiene un formato valido.")
        else:
            fecha_doc = dt.date()
    except Exception:
        raise ValidationError("La fecha de emision no tiene un formato valido.")
        
    try:
        total_val = Decimal(str(totales["total"]))
    except (ValueError, TypeError, KeyError, InvalidOperation):
        raise ValidationError("El total no es un valor decimal valido.")
        
    # 3. Obtener contexto del Tenant activo (Empresa SSoT)
    # GASTOS-01 (mision UI/UX): este materializador corre sin supervision
    # humana desde el pipeline de ingesta de correo (document_router.py).
    # Antes fabricaba silenciosamente una Empresa/ResolucionDIAN falsa
    # (NIT "123456789", resolucion "999999") y las usaba para crear un
    # DocumentoSoporte real -- un dato fiscal legalmente significativo no
    # puede depender de datos inventados. Ahora falla explicito: el
    # document_router ya distingue ValidationError (esperado, ver su
    # except dedicado) de un error inesperado.
    from apps.tenant.empresa.models import Empresa
    empresa = Empresa.objects.first()
    if not empresa:
        raise ValidationError(
            "No se puede materializar el gasto: la Empresa del tenant aun no esta configurada."
        )
        
    # 4. Obtener/Crear Proveedor (NIT es numero_documento en Proveedor)
    from apps.tenant.proveedores.models import Proveedor
    
    # Clean / parse NIT
    def parse_nit(nit_str: str):
        if '-' in nit_str:
            num, dv = nit_str.rsplit('-', 1)
            return num.strip(), dv.strip()
        return nit_str.strip(), None
        
    doc_num, dv = parse_nit(emisor_nit)
    
    proveedor = Proveedor.objects.filter(
        empresa=empresa,
        numero_documento=doc_num
    ).first()
    
    if not proveedor:
        razon_social = emisor.get("razon_social") or f"Proveedor {doc_num}"
        proveedor = Proveedor.objects.create(
            empresa=empresa,
            numero_documento=doc_num,
            digito_verificacion=dv,
            razon_social=razon_social,
            tipo_persona="JURIDICA",
            tipo_documento="NIT",
            regimen_tributario="ORDINARIO",
            activo=True
        )
        
    # 5. Idempotencia: Verificar si el gasto ya fue materializado
    from apps.tenant.gastos.models import DocumentoSoporte, ResolucionDIAN
    existing = DocumentoSoporte.objects.filter(
        empresa=empresa,
        proveedor=proveedor,
        numero_documento_proveedor=numero,
        anulado=False
    ).first()
    
    if existing:
        return {
            "id": existing.id,
            "numero": numero,
            "created": False
        }, 200
        
    # 6. Obtener Resolucion DIAN vigente (GASTOS-01: ya no se fabrica una
    # falsa -- una resolucion DIAN es un rango numerico real registrado
    # ante la autoridad tributaria, no un dato que el sistema pueda inventar).
    resolucion = ResolucionDIAN.objects.filter(empresa=empresa, vigente=True).first()
    if not resolucion:
        raise ValidationError(
            "No se puede materializar el gasto: la empresa no tiene una Resolucion DIAN vigente configurada."
        )
        
    # 7. Persistir DocumentoSoporte usando CRUDService
    categoria = dto.get("categoria") or "OTROS_GASTOS"
    
    ds_data = {
        "proveedor": proveedor,
        "numero_documento_proveedor": numero,
        "fecha": fecha_doc,
        "subtotal": total_val,
        "total": total_val,
        "descripcion": f"Materializado desde DTO - {categoria}",
        "categoria_contable": None
    }
    
    documento = DocumentoCRUDService.crear_documento(ds_data, empresa, resolucion)
    
    return {
        "id": documento.id,
        "numero": numero,
        "created": True
    }, 201





