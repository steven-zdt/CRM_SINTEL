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
            # RELEASE-CLOSE/PROVEEDORES-02: "todo Proveedor debe tener un
            # Representante" es una regla de la UI interactiva de creacion
            # (Fase 9/10 de la mision, "cuando el usuario crea un
            # proveedor..."). Este caller resuelve/crea un Proveedor de forma
            # automatica desde metadata fiscal de una Factura XML (sin
            # usuario ni representante disponibles en el documento) -- no
            # confundir con la creacion interactiva. Sin llamadores en vivo
            # hoy (verificado por grep repo-wide: solo el management command
            # backfill_proveedores_facturas_compra.py lo invoca), pero se
            # mantiene fail-open aqui para no romperlo.
            exigir_representante=False,
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

    @staticmethod
    def _construir_payload_representante(representante_data: dict, usuario, tipo_persona: str) -> dict:
        """
        Arma el payload final del Representante principal a crear junto con
        el Proveedor. Para NATURAL, precarga nombre/email/telefono/cargo
        desde el usuario real (TenantProfile + su User) cuando
        representante_data no los trae -- "no pedir datos que el sistema ya
        posee" (mandato de la mision). `numero_documento`/`tipo_documento`
        NUNCA se auto-rellenan: ni `User` ni `TenantProfile` tienen ese dato
        en el sistema hoy (verificado en apps/tenant/perfil/models.py) -- se
        exigen explicitos en el payload, ver crear_proveedor().
        """
        payload = dict(representante_data or {})
        payload.setdefault("tipo_documento", "CC")
        payload["es_principal"] = True

        if tipo_persona == "NATURAL" and usuario is not None:
            user_obj = getattr(usuario, "user", usuario)
            nombre = f"{getattr(user_obj, 'first_name', '') or ''} {getattr(user_obj, 'last_name', '') or ''}".strip()
            payload.setdefault("nombre_completo", nombre or getattr(user_obj, "email", "") or "Representante")
            payload.setdefault("email_contacto", getattr(user_obj, "email", "") or "")
            payload.setdefault("telefono_contacto", getattr(usuario, "telefono_corporativo", "") or "")
            payload.setdefault("cargo", getattr(usuario, "cargo", "") or "Representante Legal")

        return payload

    @transaction.atomic
    def crear_proveedor(self, empresa_id, data, representante_data=None, usuario=None, exigir_representante=True):
        """
        Orquesta la creación de un proveedor con validaciones.

        representante_data / usuario (parametros nuevos, opcionales):
        permiten crear el Proveedor + su primer Representante en la MISMA
        transaccion atomica -- Regla de Oro de la mision Proveedores: "todo
        Proveedor debe tener al menos un Representante".
          - tipo_persona=JURIDICA: representante_data es obligatorio (numero_
            documento + nombre_completo como minimo) -- si falta, se rechaza
            ANTES de tocar la BD, nunca queda un Proveedor huerfano sin
            representante.
          - tipo_persona=NATURAL: se autogenera el representante principal
            usando datos reales del usuario que crea el proveedor
            (`usuario`, un TenantProfile) -- salvo numero_documento/
            tipo_documento, que el sistema no posee y SI se piden.

        exigir_representante (default True): la regla de arriba aplica a la
        creacion INTERACTIVA (ProveedorViewSet.create(), la UI real). Se
        pone en False para callers automatizados sistema-a-sistema que no
        tienen ni usuario ni datos de representante disponibles, ej.
        resolver_o_crear_desde_factura_compra() (resuelve un Proveedor desde
        metadata fiscal de una Factura XML, sin intervencion humana) -- con
        False se preserva el comportamiento historico (proveedor sin
        representante) para esos casos, en vez de romperlos.
        """
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

        tipo_persona = data.get("tipo_persona", "JURIDICA")
        if not exigir_representante:
            pass
        elif tipo_persona == "JURIDICA":
            if not representante_data or not str(representante_data.get("numero_documento", "")).strip():
                raise ValidationError({
                    "representante": [
                        "Un Proveedor Persona Jurídica requiere un Representante Legal "
                        "con número de documento."
                    ]
                })
            if not str(representante_data.get("nombre_completo", "")).strip():
                raise ValidationError({
                    "representante": ["El Representante Legal requiere nombre completo."]
                })
        elif tipo_persona == "NATURAL":
            if not str((representante_data or {}).get("numero_documento", "")).strip():
                raise ValidationError({
                    "representante": [
                        "Falta el número de documento del representante principal "
                        "(no existe en el sistema para el usuario actual, indíquelo)."
                    ]
                })

        proveedor = self.crud.create(empresa_id, data)

        if representante_data or (exigir_representante and tipo_persona == "NATURAL"):
            rep_payload = ProveedorBusinessService._construir_payload_representante(
                representante_data, usuario, tipo_persona
            )
            RepresentanteCRUDService().create(empresa_id, proveedor.id, rep_payload)

        return proveedor

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
    def _materializar_desde_factura(empresa_id: int, factura_uuid: str):
        """
        Si `factura_uuid` corresponde a una Factura(COMPRA) real de esta
        empresa sin CuentasPagar vinculada aun, la materializa de forma
        idempotente (get_or_create, mismo patron que
        CuentasPagarBusinessService.registrar_cuenta_pagar()) para poder
        operar sobre ella (abono). Retorna None si el uuid no corresponde a
        ninguna Factura de compra real de esta empresa.

        [RELEASE-CLOSE / PROVEEDORES-02] Hallazgo real: antes de este metodo,
        "Abonar" sobre una fila de CxP originada en una Factura (la fuente
        PRIMARIA del listado unificado -- ver CuentasPagarSelector.
        qs_list_unificado) fallaba con 400 "no encontrado", porque
        registrar_abono() solo buscaba en CuentasPagar por uuid, y ninguna
        Factura tiene una CuentasPagar vinculada hasta su primer abono.
        """
        from apps.tenant.facturas.models import Factura
        from apps.tenant.proveedores.models import CuentasPagar, Proveedor

        factura = (
            Factura.objects
            .filter(empresa_id=empresa_id, uuid=factura_uuid, naturaleza="COMPRA")
            .only("id", "uuid", "numero", "proveedor_uuid", "total", "fecha_emision", "payment_due_date")
            .first()
        )
        if not factura or not factura.proveedor_uuid:
            return None

        proveedor = (
            Proveedor.objects
            .filter(empresa_id=empresa_id, uuid=factura.proveedor_uuid)
            .only("id")
            .first()
        )
        if not proveedor:
            return None

        fecha_emision = factura.fecha_emision.date() if factura.fecha_emision else None
        cuenta_pagar_obj, _created = CuentasPagar.objects.get_or_create(
            empresa_id=empresa_id, proveedor=proveedor, numero_factura=factura.numero,
            defaults={
                "factura_uuid": factura.uuid,
                "fecha_emision": fecha_emision or factura.payment_due_date,
                "fecha_vencimiento": factura.payment_due_date or fecha_emision,
                "valor_total": factura.total,
            },
        )
        if not cuenta_pagar_obj.factura_uuid:
            # get_or_create encontro una CxP preexistente con el mismo numero
            # (ej. creada a mano antes de que llegara la Factura electronica) --
            # se vincula ahora para que quede como fuente autoritativa unica.
            cuenta_pagar_obj.factura_uuid = factura.uuid
            cuenta_pagar_obj.save(update_fields=["factura_uuid"])
        return cuenta_pagar_obj

    @staticmethod
    def resolver_cuenta_pagar(cuenta_pagar_uuid: str, empresa_id: int):
        """
        Resuelve una CuentasPagar por uuid aceptando los 2 origenes posibles
        del listado unificado: (a) uuid de una CuentasPagar real, o (b) uuid
        de una Factura(COMPRA) sin CuentasPagar aun -- se materializa antes
        de devolverla. Usado por mutaciones (registrar_abono); el detalle de
        solo lectura usa CuentasPagarSelector.resolver_fila_por_uuid() (no
        escribe).
        """
        from apps.tenant.proveedores.models import CuentasPagar

        cuenta_pagar_obj = CuentasPagar.objects.filter(
            uuid=cuenta_pagar_uuid, empresa_id=empresa_id,
        ).first()
        if cuenta_pagar_obj:
            return cuenta_pagar_obj
        return CuentasPagarBusinessService._materializar_desde_factura(empresa_id, cuenta_pagar_uuid)

    @staticmethod
    @transaction.atomic
    def registrar_abono(cuenta_pagar_uuid: str, monto, observaciones: str, empresa_id: int):
        """
        Registra un abono sobre una factura en Cuentas por Pagar.
        Delega el recalculo del saldo y estado de pago al metodo save() del modelo.
        """
        from apps.tenant.proveedores.models import CuentasPagar

        resuelta = CuentasPagarBusinessService.resolver_cuenta_pagar(cuenta_pagar_uuid, empresa_id)
        cuenta_pagar_obj = (
            CuentasPagar.objects.select_for_update().filter(pk=resuelta.pk).first()
            if resuelta else None
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

    @staticmethod
    @transaction.atomic
    def eliminar_cuenta_pagar(cuenta_pagar_uuid: str, empresa_id: int):
        """
        Elimina una Cuenta por Pagar preservando integridad financiera.

        Regla (decision explicita, no se inventa un estado ANULADA nuevo --
        la maquina de estados de CuentasPagar se mantiene minima a
        proposito, ver PROVEEDORES_AUDIT.md):
          - Debe ser una CuentasPagar real, SIN Factura asociada
            (factura_uuid IS NULL). Una fila originada en una Factura NUNCA
            es eliminable desde aqui -- el documento fiscal sigue existiendo
            en Facturas y volveria a aparecer en el listado unificado en la
            siguiente carga; "eliminar" esa fila no elimina la obligacion
            real, solo la trazabilidad de sus abonos.
          - valor_pagado == 0 -> hard delete permitido (no hay historial de
            pagos que perder).
          - valor_pagado > 0 -> rechazado (400), preserva el historial
            financiero. No hard-delete parcial ni soft-delete disponible hoy.
        """
        from apps.tenant.proveedores.models import CuentasPagar

        cuenta_pagar_obj = (
            CuentasPagar.objects
            .select_for_update()
            .filter(uuid=cuenta_pagar_uuid, empresa_id=empresa_id)
            .first()
        )
        if not cuenta_pagar_obj:
            raise ValidationError(
                "Registro de Cuentas por Pagar no encontrado en su organizacion."
            )
        if cuenta_pagar_obj.factura_uuid:
            raise ValidationError(
                "Esta obligacion proviene de una Factura registrada -- "
                "no puede eliminarse desde Cuentas por Pagar."
            )
        if cuenta_pagar_obj.valor_pagado > Decimal("0"):
            raise ValidationError(
                "No se puede eliminar una obligacion con pagos registrados "
                f"(valor pagado: {cuenta_pagar_obj.valor_pagado})."
            )
        cuenta_pagar_obj.delete()

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

    @transaction.atomic
    def crear_representante(self, empresa_id: int, proveedor_uuid: str, data: dict):
        """
        Orquesta la creación de un representante con validaciones DSV.

        DSV (Double Semantic Verification):
        1. Valida que la empresa exista
        2. Valida que el proveedor exista y pertenece a la empresa
        3. Valida unicidad de documento por proveedor

        Regla de un solo principal (RELEASE-CLOSE / PROVEEDORES-02): si el
        nuevo representante se crea con es_principal=True (default del
        modelo) y el proveedor ya tiene otro principal, ese otro se degrada
        a es_principal=False en la MISMA transaccion -- nunca quedan dos
        representantes principales del mismo proveedor. Antes de este fix
        solo existia el guard al ELIMINAR el ultimo principal (ver
        eliminar_representante), ninguno al crear uno nuevo.
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

        if data.get("es_principal", True):
            Representante.objects.filter(
                empresa_id=empresa_id, proveedor_id=proveedor.id, es_principal=True,
            ).update(es_principal=False)

        # CRUD: Crear con empresa_id y proveedor_id (DSV)
        return self.crud.create(empresa_id, proveedor.id, data)

    @transaction.atomic
    def actualizar_representante(
        self,
        empresa_id: int,
        representante_uuid: str,
        data: dict
    ):
        """
        Orquesta la actualización de un representante con validaciones DSV.

        Regla de un solo principal: si esta actualización marca
        es_principal=True, degrada a False cualquier OTRO representante
        principal del mismo proveedor (misma regla que crear_representante).
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

        if data.get("es_principal") is True:
            Representante.objects.filter(
                empresa_id=empresa_id, proveedor_id=representante.proveedor_id, es_principal=True,
            ).exclude(uuid=representante_uuid).update(es_principal=False)

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
