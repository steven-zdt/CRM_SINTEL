import logging
from decimal import Decimal
from typing import Any, Dict, Tuple, Optional

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.tenant.gastos.models import DocumentoSoporte, ResolucionDIAN

# Lazy imports for related domains to avoid circularity at runtime
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
        from apps.tenant.gastos.services.crud_service import DocumentoCRUDService
        
        try:
            qs = DocumentoSoporte.objects.filter(id=gasto_id)
            if empresa_id:
                qs = qs.filter(empresa_id=empresa_id)
                
            documento = qs.first()
            if not documento:
                return False, {"detail": "Documento no encontrado o no pertenece a la empresa."}, 404

            if documento.anulado:
                return False, {"detail": "El documento ya se encuentra anulado."}, 400

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
        from apps.tenant.gastos.services.crud_service import DocumentoCRUDService
        
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
        from apps.tenant.gastos.services.crud_service import DocumentoCRUDService
        
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

            # DSV: Relaciones Opcionales a Inventario (FASE 2)
            from apps.tenant.inventario.models import Producto, Servicio, ActivoFijo

            def resolver_item_inventario(model_class, item_id, model_name):
                if not item_id:
                    return None
                if isinstance(item_id, model_class):
                    if item_id.empresa_id != empresa.id:
                        raise ValidationError({
                            f"{model_name}_relacionado": f"El {model_name} especificado no pertenece a la empresa."
                        })
                    return item_id
                
                is_item_uuid = False
                try:
                    if isinstance(item_id, str) and len(item_id) >= 32:
                        uuid_lib.UUID(str(item_id))
                        is_item_uuid = True
                except (ValueError, TypeError):
                    pass

                item = None
                if is_item_uuid:
                    item = model_class.objects.filter(uuid=item_id, empresa=empresa).first()
                else:
                    try:
                        item = model_class.objects.filter(id=int(item_id), empresa=empresa).first()
                    except (ValueError, TypeError):
                        pass

                if not item:
                    raise ValidationError({
                        f"{model_name}_relacionado": f"El {model_name} especificado '{item_id}' no es valido o no pertenece a la empresa."
                    })
                return item

            producto_rel_id = ds_data.pop('producto_relacionado', None) or ds_data.pop('producto_relacionado_id', None)
            servicio_rel_id = ds_data.pop('servicio_relacionado', None) or ds_data.pop('servicio_relacionado_id', None)
            activo_rel_id = ds_data.pop('activo_relacionado', None) or ds_data.pop('activo_relacionado_id', None)

            if producto_rel_id:
                ds_data['producto_relacionado'] = resolver_item_inventario(Producto, producto_rel_id, 'producto')
            if servicio_rel_id:
                ds_data['servicio_relacionado'] = resolver_item_inventario(Servicio, servicio_rel_id, 'servicio')
            if activo_rel_id:
                ds_data['activo_relacionado'] = resolver_item_inventario(ActivoFijo, activo_rel_id, 'activo')

            # 1. Validar DIAN
            fecha_doc = ds_data.get('fecha')
            if not resolucion.esta_dentro_de_fecha(fecha_doc):
                return False, {"error": "resolucion_vencida", "message": "Fecha fuera de rango de resolucion."}, 400

            # 2. Preparar Totales (v3.7.1 Pull Model)
            subtotal = Decimal(str(ds_data.get('subtotal', 0)))
            ds_data['subtotal'] = subtotal
            
            # [SSoT] Obtener retenciones configuradas para el proveedor
            from apps.tenant.contabilidad.services.retenciones_service import RetencionesService
            config_ret = RetencionesService.obtener_retenciones_desde_tercero(
                nit=proveedor.numero_documento,
                tipo_tercero='PROVEEDOR',
                naturaleza='COMPRA'
            )
            
            # Calcular retenciones iniciales para determinar el TOTAL neto
            monto_retefuente = RetencionesService.calcular_monto_retencion('RETEFUENTE', config_ret['retefuente_porcentaje'], subtotal)
            monto_reteica = RetencionesService.calcular_monto_retencion('RETEICA', config_ret['reteica_porcentaje'], subtotal)
            monto_reteiva = RetencionesService.calcular_monto_retencion('RETEIVA', config_ret['reteiva_porcentaje'], subtotal)
            
            total_neto = (subtotal - monto_retefuente - monto_reteica - monto_reteiva).quantize(Decimal('0.01'))
            ds_data['total'] = total_neto

            # 3. Persistencia via CRUD
            from apps.tenant.gastos.services.crud_service import DocumentoCRUDService
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
            logger.warning(f"[GastoBusinessService:procesar_gasto] Error de validacion API: {e.detail}")
            return False, {"error": "validacion_api", "message": e.detail}, 400
            
        except DjangoValidationError as e:
            # Error de Modelo (full_clean)
            error_dict = e.message_dict if hasattr(e, 'message_dict') else {"non_field_errors": str(e)}
            logger.warning(f"[GastoBusinessService:procesar_gasto] Error de validacion Django: {error_dict}")
            logger.warning(f"[GastoBusinessService:procesar_gasto] Documento data al fallar: {ds_data}")
            return False, {"error": "validacion", "message": error_dict}, 400
            
        except Exception as e:
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
        from apps.tenant.gastos.services.crud_service import ResolucionCRUDService
        
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
        from apps.tenant.gastos.services.crud_service import ResolucionCRUDService
        
        try:
            resolucion = ResolucionDIAN.objects.get(id=resolucion_id, empresa_id=empresa_id)
            return ResolucionCRUDService.desactivar_resolucion(resolucion)
        except ResolucionDIAN.DoesNotExist:
            raise ValidationError("Resolucion no encontrada o no pertenece a la empresa.")

    @staticmethod
    def puede_eliminar(empresa_id: int, resolucion_id: int) -> Tuple[bool, str]:
        """Verifica si una resolucion puede ser eliminada."""
        from apps.tenant.gastos.services.crud_service import ResolucionCRUDService
        
        try:
            resolucion = ResolucionDIAN.objects.get(id=resolucion_id, empresa_id=empresa_id)
            if resolucion.vigente:
                return False, "No se puede eliminar una resolucion vigente."
            
            if not ResolucionCRUDService.puede_eliminar(resolucion):
                return False, "La resolucion tiene documentos asociados."
            
            return True, "La resolucion puede ser eliminada."
        except ResolucionDIAN.DoesNotExist:
            return False, "Resolucion no encontrada."




