"""
Business Service for Proveedores v3.5 - Business Logic & orchestration.
"""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from rest_framework.exceptions import ValidationError
from django.db import transaction, IntegrityError
from .crud_service import ProveedorCRUDService
from .selectors import ProveedorSelector
from ..choices.niif_proveedores_choices import PROVEEDORES_NIIF_CODIGOS_VALIDOS
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
            from django.apps import apps
            return apps.get_model("tenant_proveedores", "ContactoProveedor")
        except (LookupError, ValueError):
            return None

    def validate_niif_code(self, codigo_contable):
        """Valida que el código contable pertenezca al catálogo permitido."""
        if codigo_contable and codigo_contable not in PROVEEDORES_NIIF_CODIGOS_VALIDOS:
            raise ValidationError({
                'codigo_contable': [f"El codigo contable '{codigo_contable}' no pertenece al catalogo NIIF de pasivos."]
            })

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
        self.validate_niif_code(data.get('codigo_contable'))
        data = self._sanitize_retenciones(data)
        return self.crud.create(empresa_id, data)

    def actualizar_proveedor(self, proveedor, data):
        """Orquesta la actualización de un proveedor con validaciones."""
        self.validate_niif_code(data.get('codigo_contable'))
        data = self._sanitize_retenciones(data)
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
        
        # Normalizar numero_documento / nit
        nit = datos_proveedor.get("nit") or datos_proveedor.get("numero_documento")
        nit = (nit or "").strip().upper()
        if not nit:
            raise ValidationError({"numero_documento": ["La identificacion tributaria es obligatoria."]})
        
        datos_proveedor["numero_documento"] = nit
        
        self.validate_niif_code(datos_proveedor.get('codigo_contable'))
        
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
