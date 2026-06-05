"""
Business Service for Proveedores v3.5 - Business Logic & orchestration.
"""
import re

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from django.apps import apps
from django.db import transaction, IntegrityError
from rest_framework.exceptions import ValidationError
from .crud_service import ProveedorCRUDService
from .selectors import ProveedorSelector
from apps.tenant.empresa.models import Empresa

class ProveedorBusinessService:
    """
    Orchestration layer for Proveedor v3.5.
    Handles business rules, validations, financial calculations and complex flows.
    """
    def __init__(self):
        self.crud = ProveedorCRUDService()

    # ==============================================================================
    # 1. HELPERS & NORMALIZATION
    # ==============================================================================

    @staticmethod
    def normalize_document_number(value) -> str:
        """Normaliza documentos legales para emparejar XML importados."""
        if value is None:
            return ""
        raw = str(value).strip()
        return re.sub(r"[\s\.\-]", "", raw).upper()

    @staticmethod
    @transaction.atomic
    def resolver_o_crear_desde_factura_compra(
        empresa_id: int,
        emisor_nit: str,
        emisor_razon_social: str,
        emisor_email: str | None = None,
        emisor_telefono: str | None = None,
        emisor_direccion: str | None = None,
        emisor_actividad_ciiu: str | None = None,
    ):
        """Resuelve o crea el proveedor requerido por una factura de compra."""
        numero_documento = ProveedorBusinessService.normalize_document_number(emisor_nit)
        razon_social = str(emisor_razon_social or "").strip()

        if not numero_documento:
            raise ValidationError({"emisor_nit": "La factura de compra requiere NIT de emisor para vincular proveedor."})
        if not razon_social:
            raise ValidationError({"emisor_razon_social": "La factura de compra requiere razon social de emisor para vincular proveedor."})

        existing = ProveedorSelector.get_by_documento(
            empresa_id=empresa_id,
            tipo_documento="NIT",
            numero_documento=numero_documento,
        )
        if existing:
            return existing, False

        service = ProveedorBusinessService()
        proveedor = service.crear_proveedor(
            empresa_id=empresa_id,
            data={
                "tipo_persona": "JURIDICA",
                "tipo_documento": "NIT",
                "numero_documento": numero_documento,
                "razon_social": razon_social,
                "nombre_comercial": "",
                "regimen_tributario": "ORDINARIO",
                "actividad_economica_ciiu": str(emisor_actividad_ciiu or "").strip(),
                "email_contacto": str(emisor_email or "").strip(),
                "telefono_contacto": str(emisor_telefono or "").strip(),
                "direccion": str(emisor_direccion or "").strip(),
                "ciudad": "",
                "activo": True,
                "observaciones": "Creado automaticamente desde factura XML de compra.",
            },
        )
        return proveedor, True

    @staticmethod
    def _to_decimal(value, field_name):
        try:
            return Decimal(str(value or 0))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValidationError({field_name: [f"Valor numerico invalido para {field_name}."]}) from exc

    @staticmethod
    def _normalize_percentage_for_calculation(value):
        dec = ProveedorBusinessService._to_decimal(value, "porcentaje")
        # Compatibilidad con payloads de gastos que usan base-1 (0.04 => 4%).
        if Decimal("0") < dec < Decimal("0.5"):
            return (dec * Decimal("100")).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        return dec

    @staticmethod
    def _format_percentage_choice(value):
        dec = ProveedorBusinessService._to_decimal(value, "porcentaje")
        if dec == Decimal("0"):
            return "0.00"
        text = format(dec.normalize(), "f")
        return text.rstrip("0").rstrip(".") if "." in text else text

    @staticmethod
    def _get_contacto_proveedor_model():
        """Return ContactoProveedor model if it exists after refactors."""
        try:
            return apps.get_model("tenant_proveedores", "ContactoProveedor")
        except (LookupError, ValueError):
            return None

    def _sanitize_retenciones(self, payload: dict) -> dict:
        """
        Zero Trust: Limpia flags y porcentajes de retención si el proveedor no es retenedor.
        """
        es_retenedor = payload.get("es_retenedor", False)
        
        if not es_retenedor:
            payload["aplica_retefuente"] = False
            payload["retefuente_porcentaje"] = 0
            payload["aplica_reteica"] = False
            payload["reteica_porcentaje"] = 0
            payload["aplica_reteiva"] = False
            payload["reteiva_porcentaje"] = 0
        else:
            # Sanitización fina: si la flag individual es False, el porcentaje debe ser 0
            if not payload.get("aplica_retefuente", False):
                payload["retefuente_porcentaje"] = 0
            if not payload.get("aplica_reteica", False):
                payload["reteica_porcentaje"] = 0
            if not payload.get("aplica_reteiva", False):
                payload["reteiva_porcentaje"] = 0
                
        return payload

    # ==============================================================================

    # 2. FINANCIAL CALCULATIONS (SSoT)
    # ==============================================================================

    @staticmethod
    def calcular_neto_gasto(subtotal, porcentaje_retencion):
        """
        Fuente unica de verdad matematica para gastos.
        Formula: neto = subtotal - (subtotal * porcentaje_retencion / 100)
        """
        subtotal_dec = ProveedorBusinessService._to_decimal(subtotal, "subtotal")
        porcentaje_retencion_dec = ProveedorBusinessService._to_decimal(porcentaje_retencion, "porcentaje_retencion")

        if subtotal_dec < Decimal("0"):
            raise ValidationError({"subtotal": ["El subtotal no puede ser negativo."]})
        if porcentaje_retencion_dec < Decimal("0") or porcentaje_retencion_dec > Decimal("100"):
            raise ValidationError({"porcentaje_retencion": ["El porcentaje de retencion debe estar entre 0 y 100."]})

        descuento = (subtotal_dec * (porcentaje_retencion_dec / Decimal("100"))).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        return (subtotal_dec - descuento).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def obtener_configuracion_retenciones(proveedor):
        """Configuracion base de retenciones por proveedor (v2.61.4)."""
        retefuente_porcentaje = Decimal("0")
        reteica_porcentaje = Decimal("0")

        if not proveedor:
            return {
                "retefuente_porcentaje": retefuente_porcentaje,
                "reteica_porcentaje": reteica_porcentaje,
                "porcentaje_retencion_total": Decimal("0"),
            }

        if not bool(getattr(proveedor, "autoretenedor", False)):
            retefuente_porcentaje = Decimal("4")

        if str(getattr(proveedor, "tipo_persona", "")).upper() == "NATURAL":
            reteica_porcentaje = Decimal("0.966")

        return {
            "retefuente_porcentaje": retefuente_porcentaje,
            "reteica_porcentaje": reteica_porcentaje,
            "porcentaje_retencion_total": retefuente_porcentaje + reteica_porcentaje,
        }

    @staticmethod
    def calcular_componentes_retencion(subtotal, retefuente_porcentaje=0, reteica_porcentaje=0):
        subtotal_dec = ProveedorBusinessService._to_decimal(subtotal, "subtotal")
        retefuente_pct = ProveedorBusinessService._normalize_percentage_for_calculation(retefuente_porcentaje)
        reteica_pct = ProveedorBusinessService._normalize_percentage_for_calculation(reteica_porcentaje)

        retefuente = (subtotal_dec * (retefuente_pct / Decimal("100"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        reteica = (subtotal_dec * (reteica_pct / Decimal("100"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        porcentaje_total = retefuente_pct + reteica_pct
        total_neto = ProveedorBusinessService.calcular_neto_gasto(subtotal_dec, porcentaje_total)

        return {
            "subtotal": subtotal_dec,
            "retefuente": retefuente,
            "reteica": reteica,
            "retefuente_porcentaje": retefuente_pct,
            "reteica_porcentaje": reteica_pct,
            "porcentaje_retencion_total": porcentaje_total,
            "total": total_neto,
        }

    # ==============================================================================
    # 3. CRUD ORCHESTRATION
    # ==============================================================================

    def crear_proveedor(self, empresa_id, data):
        """Orquesta la creación de un proveedor con validaciones."""
        if not Empresa.objects.filter(id=empresa_id).exists():
            raise ValidationError({"empresa": ["La empresa no existe."]})
        data = self._sanitize_retenciones(data)

        # Defensa-en-profundidad (FASE 3): valida ANTES del CRUD para error claro
        num_doc  = ProveedorBusinessService.normalize_document_number(data.get("numero_documento", ""))
        tipo_doc = data.get("tipo_documento", "")
        if num_doc and tipo_doc and ProveedorSelector.existe_documento(empresa_id, tipo_doc, num_doc):
            raise ValidationError({
                "numero_documento": [
                    f"Ya existe un Proveedor registrado con el documento "
                    f"{tipo_doc} {num_doc} en su organización."
                ]
            })

        return self.crud.create(empresa_id, data)

    def actualizar_proveedor(self, proveedor, data):
        """Orquesta la actualización de un proveedor con validaciones."""
        data = self._sanitize_retenciones(data)

        # Defensa-en-profundidad (FASE 3): excluye el UUID actual para evitar falso positivo
        num_doc  = ProveedorBusinessService.normalize_document_number(
            data.get("numero_documento", str(proveedor.numero_documento))
        )
        tipo_doc = data.get("tipo_documento", proveedor.tipo_documento)
        if num_doc and tipo_doc and ProveedorSelector.existe_documento(
            proveedor.empresa_id, tipo_doc, num_doc, exclude_uuid=str(proveedor.uuid)
        ):
            raise ValidationError({
                "numero_documento": [
                    f"Ya existe un Proveedor registrado con el documento "
                    f"{tipo_doc} {num_doc} en su organización."
                ]
            })

        return self.crud.update(proveedor, data)


    def inactivar_proveedor(self, proveedor):
        """Cambia el estado del proveedor a inactivo."""
        return self.crud.update(proveedor, {'activo': False})

    def eliminar_proveedor(self, proveedor):
        """
        Elimina el proveedor de forma segura (hard delete con cascada automática).

        Comportamiento:
        - Si el proveedor está activo → Error (debe inactivarse primero)
        - Si el proveedor está inactivo → Eliminación física completa
        - Los DocumentoSoporte asociados se eliminan en cascada (CASCADE FK)
        """
        # Paso 1: Validar que no esté activo
        if proveedor.activo:
            raise ValidationError({
                "error": "active_record",
                "message": "No se puede eliminar un proveedor activo. Márquelo como 'Inactivo' primero."
            })

        # Paso 2: Hard delete (CASCADE automático de DocumentoSoporte)
        return self.crud.delete(proveedor)

    @transaction.atomic
    def registrar_proveedor_con_contactos(self, datos_proveedor, lista_contactos):
        """
        Mantiene compatibilidad con el flujo maestro-detalle de contactos.
        """
        empresa_id = datos_proveedor.get("empresa") or datos_proveedor.get("empresa_id")
        if not empresa_id:
             raise ValidationError({"empresa": ["La empresa es obligatoria."]})

        if not Empresa.objects.filter(id=empresa_id).exists():
            raise ValidationError({"empresa": ["La empresa no existe."]})
        
        # Normalizar numero_documento / nit
        nit = datos_proveedor.get("nit") or datos_proveedor.get("numero_documento")
        nit = (nit or "").strip().upper()
        if not nit:
            raise ValidationError({"numero_documento": ["La identificacion tributaria es obligatoria."]})
        
        datos_proveedor["numero_documento"] = nit
        
        # Usar update_or_create via CRUD (SSoT)
        proveedor_instancia, creado = self.crud.update_or_create(
            empresa_id=empresa_id,
            filter_data={'numero_documento': nit},
            defaults=datos_proveedor,
        )

        # Manejo de contactos (si el modelo existe)
        contacto_model = self._get_contacto_proveedor_model()
        if lista_contactos is not None and contacto_model:
            contacto_model.objects.filter(
                proveedor_id=proveedor_instancia.id,
                empresa_id=proveedor_instancia.empresa_id,
            ).delete()
            for contacto_payload in lista_contactos:
                contacto_model.objects.create(
                    proveedor=proveedor_instancia,
                    empresa_id=proveedor_instancia.empresa_id,
                    **contacto_payload,
                )

        return proveedor_instancia, creado

# ==============================================================================
# CuentasPagar Business Service (Control de Deudas y Abonos)
# ==============================================================================

class CuentasPagarBusinessService:
    """
    Logica de negocio para Cuentas por Pagar a Proveedores.
    Se encarga del registro de obligaciones y gestion de pagos.
    """

    @staticmethod
    @transaction.atomic
    def registrar_cuenta_pagar(
        proveedor,
        empresa_id: int,
        datos_cuenta_pagar: dict,
    ):
        """
        Crea o recupera un registro de CuentasPagar para una factura de compra.
        Idempotente: si ya existe para (empresa, proveedor, numero_factura), la retorna.
        """
        from apps.tenant.proveedores.models import CuentasPagar
        from apps.tenant.empresa.models import Empresa

        empresa = Empresa.objects.only("id").get(pk=empresa_id)
        numero_factura = datos_cuenta_pagar.get("numero_factura")

        # Configuracion inicial de campos
        defaults = {
            "fecha_emision": datos_cuenta_pagar.get("fecha_emision"),
            "fecha_vencimiento": datos_cuenta_pagar.get("fecha_vencimiento"),
            "valor_total": Decimal(str(datos_cuenta_pagar.get("valor_total", 0))),
            "observaciones": datos_cuenta_pagar.get("observaciones", ""),
        }

        cuenta_pagar_obj, created = CuentasPagar.objects.get_or_create(
            empresa=empresa,
            proveedor=proveedor,
            numero_factura=numero_factura,
            defaults=defaults,
        )
        
        return cuenta_pagar_obj

    @staticmethod
    @transaction.atomic
    def registrar_abono(cuenta_pagar_uuid: str, monto, observaciones: str, empresa_id: int):
        """
        Registra un abono sobre una factura en Cuentas por Pagar.
        Delega el recalculo del saldo y estado de pago al metodo save() del modelo.
        """
        from apps.tenant.proveedores.models import CuentasPagar

        cuenta_pagar_obj = (
            CuentasPagar.objects
            .select_for_update()
            .filter(uuid=cuenta_pagar_uuid, empresa_id=empresa_id)
            .first()
        )
        
        if not cuenta_pagar_obj:
            raise ValidationError(f"Registro de Cuentas por Pagar con UUID {cuenta_pagar_uuid} no encontrado.")

        monto_dec = Decimal(str(monto))
        if monto_dec <= Decimal("0"):
            raise ValidationError("El monto del abono debe ser mayor a cero.")
            
        if monto_dec > cuenta_pagar_obj.saldo:
            raise ValidationError(
                f"El abono ({monto_dec}) supera el saldo pendiente de la factura ({cuenta_pagar_obj.saldo})."
            )

        # Sumamos el nuevo abono al acumulado de pagos
        cuenta_pagar_obj.valor_pagado += monto_dec
        
        # Anexamos la observacion si se provee alguna
        if observaciones:
            separador = " | " if cuenta_pagar_obj.observaciones else ""
            cuenta_pagar_obj.observaciones += f"{separador}Abono: {observaciones}"

        # Se hace un save completo para asegurar que las validaciones y el calculo
        # dinamico de saldo y estado_pago de CuentasPagar.save() se ejecuten adecuadamente.
        cuenta_pagar_obj.save()
        
        return cuenta_pagar_obj

# ==============================================================================
# CuentaPorPagar Business Service
# ==============================================================================

class CuentaPorPagarBusinessService:
    """Business service para CuentaPorPagar — registro de deuda y abonos."""

    @staticmethod
    @transaction.atomic
    def registrar_cuenta_por_pagar(proveedor, factura_uuid: str, empresa_id: int,
                                    fecha_vencimiento, observaciones: str = ''):
        from apps.tenant.proveedores.models import CuentaPorPagar
        from apps.tenant.empresa.models import Empresa
        import uuid as uuid_mod

        empresa = Empresa.objects.only('id').get(pk=empresa_id)

        monto_total = Decimal('0.00')
        try:
            from apps.tenant.facturas.services import FacturaInterAppAPI
            factura = FacturaInterAppAPI.get_by_id(factura_uuid=str(factura_uuid))
            if factura:
                monto_total = Decimal(str(getattr(factura, 'total', 0) or 0))
        except Exception:
            pass

        cxp, _ = CuentaPorPagar.objects.get_or_create(
            empresa=empresa,
            factura_origen_uuid=uuid_mod.UUID(str(factura_uuid)),
            defaults={
                'proveedor': proveedor,
                'monto_total': monto_total,
                'saldo_pendiente': monto_total,
                'fecha_vencimiento': fecha_vencimiento,
                'estado_pago': 'NO_PAGADA',
                'observaciones': observaciones,
            },
        )
        return cxp

    @staticmethod
    @transaction.atomic
    def registrar_abono(cxp_uuid: str, monto, empresa_id: int):
        from apps.tenant.proveedores.models import CuentaPorPagar

        cxp = (
            CuentaPorPagar.objects
            .select_for_update()
            .filter(uuid=cxp_uuid, empresa_id=empresa_id)
            .first()
        )
        if not cxp:
            raise ValidationError(f'CuentaPorPagar {cxp_uuid} no encontrada.')

        monto = Decimal(str(monto))
        if monto <= 0:
            raise ValidationError('El monto del abono debe ser mayor a cero.')
        if monto > cxp.saldo_pendiente:
            raise ValidationError(
                f'El abono ({monto}) supera el saldo pendiente ({cxp.saldo_pendiente}).')

        cxp.saldo_pendiente -= monto
        if cxp.saldo_pendiente <= Decimal('0.00'):
            cxp.saldo_pendiente = Decimal('0.00')
            cxp.estado_pago = 'PAGADA'
        else:
            cxp.estado_pago = 'PAGO_PARCIAL'

        cxp.save(update_fields=['saldo_pendiente', 'estado_pago', 'updated_at'])
        return cxp
