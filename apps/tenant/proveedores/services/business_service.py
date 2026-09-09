"""
Business Service for Proveedores v3.5 - Business Logic & orchestration.
"""
import re

from decimal import Decimal
from django.apps import apps
from django.db import transaction, IntegrityError
from rest_framework.exceptions import ValidationError
from .crud_service import ProveedorCRUDService, RepresentanteCRUDService
from .selectors import ProveedorSelector, RepresentanteSelector
from apps.tenant.empresa.models import Empresa
from ..models import Proveedor, Representante

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
    def _get_contacto_proveedor_model():
        """Return ContactoProveedor model if it exists after refactors."""
        try:
            return apps.get_model("tenant_proveedores", "ContactoProveedor")
        except (LookupError, ValueError):
            return None

    def _sanitize_retenciones(self, payload: dict) -> dict:
        """
        Zero Trust: Limpia flags y porcentajes de retención si el proveedor no es retenedor.

        PROVEEDORES-01 (H2): estos campos son `read_only` en
        `ProveedorDetailSerializer` (nunca vienen en `validated_data` desde la
        API real -- el calculo real de retenciones vive en
        `contabilidad.ConfiguracionRetenciones`, no aqui). Si ninguno de ellos
        viene en el payload, este metodo no debe inyectar valores por defecto:
        hacerlo resetearia silenciosamente datos historicos en CADA edicion
        normal del proveedor (ej. solo cambiar el email). Solo se sanea cuando
        el caller efectivamente envio alguno (ruta legacy de `services.py`).
        """
        campos_retencion = (
            "aplica_retefuente", "retefuente_porcentaje",
            "aplica_reteica", "reteica_porcentaje",
            "aplica_reteiva", "reteiva_porcentaje",
        )
        if "es_retenedor" not in payload and not any(c in payload for c in campos_retencion):
            return payload

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
    # 2. CRUD ORCHESTRATION
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
            "orden_compra_uuid": datos_cuenta_pagar.get("orden_compra_uuid"),
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
# Representante Business Service (DSV + Validaciones)
# ==============================================================================

class RepresentanteBusinessService:
    """
    Orchestration layer for Representante.
    Handles business rules, DSV validation, and complex flows.
    """

    def __init__(self):
        self.crud = RepresentanteCRUDService()

    @staticmethod
    def _existe_documento_representante(
        empresa_id: int,
        proveedor_id: int,
        numero_documento: str,
        exclude_uuid: str | None = None,
    ) -> bool:
        """
        Verifica si ya existe un Representante con el mismo documento
        para el mismo proveedor en la misma empresa.
        """
        qs = Representante.objects.filter(
            empresa_id=empresa_id,
            proveedor_id=proveedor_id,
            numero_documento=numero_documento,
        )
        if exclude_uuid:
            qs = qs.exclude(uuid=str(exclude_uuid))
        return qs.only("id").exists()

    def crear_representante(self, empresa_id: int, proveedor_uuid: str, data: dict):
        """
        Orquesta la creación de un representante con validaciones DSV.

        DSV (Double Semantic Verification):
        1. Valida que la empresa exista
        2. Valida que el proveedor exista y pertenece a la empresa
        3. Valida unicidad de documento por proveedor
        """
        # DSV 1: Empresa existe
        if not Empresa.objects.filter(id=empresa_id).exists():
            raise ValidationError({"empresa": ["La empresa no existe."]})

        # DSV 2: Proveedor existe y pertenece a la empresa
        proveedor = (
            Proveedor.objects
            .filter(empresa_id=empresa_id, uuid=proveedor_uuid)
            .only("id")
            .first()
        )
        if not proveedor:
            raise ValidationError({"proveedor": ["El proveedor no existe en su empresa."]})

        # Validación 3: Unicidad de documento por proveedor
        numero_documento = data.get("numero_documento", "").strip()
        if numero_documento and self._existe_documento_representante(
            empresa_id, proveedor.id, numero_documento
        ):
            raise ValidationError({
                "numero_documento": [
                    "Ya existe un representante con este documento para este proveedor."
                ]
            })

        # CRUD: Crear con empresa_id y proveedor_id (DSV)
        return self.crud.create(empresa_id, proveedor.id, data)

    def actualizar_representante(
        self,
        empresa_id: int,
        representante_uuid: str,
        data: dict
    ):
        """
        Orquesta la actualización de un representante con validaciones DSV.
        """
        # DSV 1: Representante existe y pertenece a la empresa
        representante = RepresentanteSelector.get_by_uuid(empresa_id, representante_uuid)
        if not representante:
            raise ValidationError({"representante": ["El representante no existe en su empresa."]})

        # Validación 2: Unicidad de documento (excluyendo el registro actual)
        numero_documento = data.get("numero_documento", representante.numero_documento).strip()
        if numero_documento and self._existe_documento_representante(
            empresa_id, representante.proveedor_id, numero_documento, exclude_uuid=representante_uuid
        ):
            raise ValidationError({
                "numero_documento": [
                    "Ya existe otro representante con este documento para este proveedor."
                ]
            })

        # CRUD: Actualizar
        return self.crud.update(representante, data)

    def eliminar_representante(self, empresa_id: int, representante_uuid: str):
        """
        Orquesta la eliminación de un representante con validaciones.
        """
        # DSV: Representante existe y pertenece a la empresa
        representante = RepresentanteSelector.get_by_uuid(empresa_id, representante_uuid)
        if not representante:
            raise ValidationError({"representante": ["El representante no existe en su empresa."]})

        # Validación: No eliminar el único representante principal
        otros_principales = Representante.objects.filter(
            empresa_id=empresa_id,
            proveedor_id=representante.proveedor_id,
            es_principal=True
        ).exclude(uuid=representante_uuid).exists()

        if representante.es_principal and not otros_principales:
            raise ValidationError({
                "error": [
                    "No se puede eliminar el único representante principal. "
                    "Asigne primero otro representante como principal."
                ]
            })

        # CRUD: Eliminar
        return self.crud.delete(representante)
