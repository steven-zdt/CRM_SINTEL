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

    @staticmethod
    def calcular_retenciones(subtotal: Decimal, retefuente_porcentaje: str, reteica_porcentaje: str) -> Dict[str, Decimal]:
        """Calcula valores de retenciones basados en el subtotal (v2.40)."""
        # Convertir a Decimal para calculo exacto
        pct_fuente = Decimal(str(retefuente_porcentaje or '0.00'))
        pct_ica = Decimal(str(reteica_porcentaje or '0.00'))

        # Calculo: Redondeo a 2 decimales para pesos colombianos
        retefuente = (subtotal * pct_fuente).quantize(Decimal('0.01'))
        reteica = (subtotal * pct_ica).quantize(Decimal('0.01'))
        total = (subtotal - retefuente - reteica).quantize(Decimal('0.01'))

        return {
            'retefuente': retefuente,
            'reteica': reteica,
            'total': total
        }

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
        Elimina un gasto (Sigue el estandar de Clientes: Bloqueo si activo, Físico si inactivo).
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

            # [STANDARDIZATION] Bloquear si no está anulado
            if not documento.anulado:
                return False, {
                    "detail": "No se puede eliminar un gasto activo. Debe anularlo primero para poder borrar el registro permanentemente."
                }, 400

            # [STANDARDIZATION] Borrado físico de registros inactivos
            DocumentoCRUDService.eliminar_documento(documento)
            return True, {"message": "Gasto eliminado permanentemente."}, 204
            
        except Exception as e:
            logger.error(f"Error en eliminar_gasto: {e}", exc_info=True)
            return False, {"detail": f"Error al procesar borrado: {str(e)}"}, 500

    @staticmethod
    def calcular_y_validar_totales(data: Dict[str, Any], resolucion: Any = None) -> Dict[str, Any]:
        """
        Realiza calculos de retenciones y valida el total.
        v2.62: Tolerancia unificada a 0.01. Asegura tipos Decimal.
        """
        subtotal = Decimal(str(data.get('subtotal', 0)))
        retefuente_pct = data.get('retefuente_porcentaje', '0.00')
        reteica_pct = data.get('reteica_porcentaje', '0.00')
        total_enviado = data.get('total')

        retenciones = GastoBusinessService.calcular_retenciones(subtotal, retefuente_pct, reteica_pct)
        
        if total_enviado is not None:
            d_total_enviado = Decimal(str(total_enviado))
            diferencia = abs(d_total_enviado - retenciones['total'])
            if diferencia > Decimal('0.01'):
                raise ValidationError({
                    'total': f"Inconsistencia en el total. Esperado: {retenciones['total']}, Recibido: {d_total_enviado}"
                })

        return {
            'subtotal': subtotal,
            'retefuente': retenciones['retefuente'],
            'reteica': retenciones['reteica'],
            'total': retenciones['total']
        }

    @staticmethod
    @transaction.atomic
    def procesar_gasto(empresa: Any, data: Dict[str, Any]) -> Tuple[bool, Any, int]:
        """
        Orquesta la creacion de un DocumentoSoporte (Gasto v2.62).
        Realiza Double Semantic Verification (DSV) para prevenir IDOR.
        """
        logger.info(f"[GastoBusinessService:procesar_gasto] Iniciando proceso para empresa={empresa.id}")
        try:
            # En v2.62, el payload puede venir anidado en 'documento_soporte' o plano.
            if 'documento_soporte' in data:
                ds_data = data.pop('documento_soporte')
                # Mezclar campos extra (descripcion, observaciones, categoria_contable, etc)
                for key, value in data.items():
                    if key not in ds_data:
                        ds_data[key] = value
            else:
                ds_data = data

            logger.debug(f"[GastoBusinessService:procesar_gasto] Data normalizada: {ds_data}")

            # Normalizar porcentajes para evitar errores de validacion de choices (v2.62.1)
            for pct_field in ['retefuente_porcentaje', 'reteica_porcentaje']:
                val = ds_data.get(pct_field)
                if val is not None:
                    try:
                        d_val = Decimal(str(val))
                        if d_val == Decimal('0'):
                            ds_data[pct_field] = '0.00'
                        else:
                            # Asegurar que sea string para el CharField
                            ds_data[pct_field] = str(val)
                    except Exception:
                        pass

            resolucion_id = ds_data.pop('resolucion', None)
            
            if not resolucion_id:
                return False, {
                    "error": "resolucion_requerida", 
                    "message": "Debe especificar una resolucion DIAN."
                }, 400

            # DSV: Verificar que la resolucion pertenezca a la empresa
            resolucion = ResolucionDIAN.objects.filter(id=resolucion_id, empresa=empresa).first()
            if not resolucion:
                logger.warning(f"[SECURITY:IDOR] Intento de uso de resolucion {resolucion_id} por empresa {empresa.id}")
                return False, {
                    "error": "resolucion_invalida", 
                    "message": "La resolucion especificada no es valida o no pertenece a su empresa."
                }, 404

            # DSV: Verificar que el proveedor pertenezca a la empresa
            proveedor_id = ds_data.get('proveedor')
            if not proveedor_id:
                return False, {
                    "error": "proveedor_requerido",
                    "message": "Debe especificar un proveedor."
                }, 400
            
            from apps.tenant.proveedores.models import Proveedor
            proveedor = Proveedor.objects.filter(id=proveedor_id, empresa=empresa).first()
            if not proveedor:
                logger.warning(f"[SECURITY:IDOR] Intento de uso de proveedor {proveedor_id} por empresa {empresa.id}")
                return False, {
                    "error": "proveedor_invalido",
                    "message": "El proveedor especificado no es valido o no pertenece a su empresa."
                }, 404
            
            # Asignar objeto proveedor para persistencia
            ds_data['proveedor'] = proveedor

            # 1. Validar cumplimiento DIAN (Vigencia de fecha)
            fecha_doc = ds_data.get('fecha')
            if not resolucion.esta_dentro_de_fecha(fecha_doc):
                return False, {
                    "error": "resolucion_vencida",
                    "message": f"La fecha {fecha_doc} esta fuera del rango de vigencia de la resolucion ({resolucion.fecha_inicio} a {resolucion.fecha_fin})."
                }, 400

            # 2. Preparar datos de DocumentoSoporte con calculos de negocio
            calculos = GastoBusinessService.calcular_y_validar_totales(ds_data, resolucion)
            ds_data.update(calculos)
            
            # 3. Persistencia Atomica via CRUD
            from apps.tenant.gastos.services.crud_service import DocumentoCRUDService
            documento = DocumentoCRUDService.crear_documento(ds_data, empresa, resolucion)
            
            logger.info(f"[GastoBusinessService:procesar_gasto] Exito! ID={documento.id}")
            return True, documento, 201
            
        except ValidationError as e:
            logger.warning(f"[GastoBusinessService:procesar_gasto] Error de validacion: {e.detail}")
            return False, e.detail, 400
        except DjangoValidationError as e:
            logger.warning(f"[GastoBusinessService:procesar_gasto] Error de validacion Django: {e}")
            return False, {"error": "validacion", "message": str(e)}, 400
        except Exception as e:
            logger.error(f"Error en procesar_gasto: {e}", exc_info=True)
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




