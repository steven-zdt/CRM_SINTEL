import logging
import re
from django.db import transaction
from rest_framework.exceptions import ValidationError
from ..models import Cliente, ContactoCliente
from .crud_service import ClienteCRUDService, ContactoCRUDService, CarteraCRUDService
from .selectors import ClienteSelector, CarteraSelector

logger = logging.getLogger(__name__)

class ClienteBusinessService:
    """Orchestration and Business logic for Clientes."""

    def __init__(self):
        self.crud = ClienteCRUDService()
        self.contacto_crud = ContactoCRUDService()
        self.selector = ClienteSelector()

    @staticmethod
    def normalize_document_number(value) -> str:
        """Normalizes legal document values for matching imported XML data."""
        if value is None:
            return ""
        raw = str(value).strip()
        return re.sub(r"[\s\.\-]", "", raw).upper()

    @staticmethod
    @transaction.atomic
    def resolver_o_crear_desde_factura_venta(
        empresa_id: int,
        receptor_nit: str,
        receptor_razon_social: str,
        receptor_email: str | None = None,
        receptor_telefono: str | None = None,
        receptor_direccion: str | None = None,
    ) -> tuple[Cliente, bool]:
        """
        Resolves or creates the Cliente required by an imported sales invoice.
        """
        numero_documento = ClienteBusinessService.normalize_document_number(receptor_nit)
        razon_social = str(receptor_razon_social or "").strip()

        if not numero_documento:
            raise ValidationError({"receptor_nit": "La factura de venta requiere NIT de receptor para vincular cliente."})
        if not razon_social:
            raise ValidationError({"receptor_razon_social": "La factura de venta requiere razon social de receptor para vincular cliente."})

        existing = ClienteSelector.get_cliente_by_documento(
            empresa_id=empresa_id,
            tipo_documento="NIT",
            numero_documento=numero_documento,
        )
        if existing:
            return existing, False

        service = ClienteBusinessService()
        cliente, _ = service.registrar_cliente_completo(
            empresa_id=empresa_id,
            data={
                "tipo_persona": "JURIDICA",
                "tipo_documento": "NIT",
                "numero_documento": numero_documento,
                "razon_social": razon_social,
                "nombre_comercial": "",
                "regimen_tributario": "ORDINARIO",
                "email": str(receptor_email or "").strip(),
                "telefono": str(receptor_telefono or "").strip(),
                "direccion": str(receptor_direccion or "").strip(),
                "ciudad": "",
                "activo": True,
                "observaciones": "Creado automaticamente desde factura XML de venta.",
            },
            contactos_raw=None,
        )

        email = str(receptor_email or "").strip()
        if email:
            ContactoCliente.objects.get_or_create(
                empresa_id=empresa_id,
                cliente=cliente,
                email=email,
                defaults={
                    "nombre_completo": razon_social[:180],
                    "telefono": str(receptor_telefono or "").strip(),
                    "is_principal": True,
                    "activo": True,
                },
            )

        return cliente, True

    @transaction.atomic
    def registrar_cliente_completo(
        self, empresa_id: int, data: dict, contactos_raw: list = None,
        cliente_instance: Cliente = None, validar_representante: bool = False,
    ) -> tuple:
        """
        Orchestrates creation or update of a client and their contacts.
        If cliente_instance is provided, updates directly without upsert logic.

        `validar_representante` (default False, opt-in explicito): la
        regla de representante legal (seccion 7-10 de la mision) solo debe
        exigirse en el formulario de captura manual (ClienteViewSet, que
        pasa True). Los flujos de resolucion automatica desde documentos
        externos -- `resolver_o_crear_desde_factura_venta()` (XML de
        factura de venta) y el wrapper legacy `services.crear_cliente()`
        usado solo por tests de idempotencia -- crean un Cliente JURIDICA
        de snapshot sin datos de representante disponibles en ese momento;
        exigirla ahi habria roto ambos flujos reales sin beneficio (la
        info de representante no viene en el XML de la factura).
        """
        data = self._sanitize_retenciones(data)
        
        created = False
        if cliente_instance:
            cliente = self.crud.update_cliente(cliente_instance, data)
        else:
            # 1. Normalize and check uniqueness
            tipo_doc = data.get("tipo_documento")
            num_doc = data.get("numero_documento")
            
            # Upsert logic (Idempotency)
            existing = Cliente.objects.filter(
                empresa_id=empresa_id,
                tipo_documento=tipo_doc,
                numero_documento=num_doc
            ).first()

            if existing:
                cliente = self.crud.update_cliente(existing, data)
            else:
                cliente = self.crud.create_cliente(empresa_id, data)
                created = True

        # 2. Sync contacts if provided
        if contactos_raw is not None:
            self.sincronizar_contactos(empresa_id, cliente.id, contactos_raw)

        # 3. Representante legal -- solo si el caller opta explicitamente
        # (ver docstring), y solo al crear o cuando esta peticion toco los
        # contactos explicitamente (un PATCH que no envia 'contactos', ej.
        # solo cambia telefono, no debe romper clientes JURIDICA
        # historicos que nunca tuvieron esta regla). Se valida contra el
        # estado REAL en BD (post-sincronizacion, misma transaccion
        # atomica): si falla, transaction.atomic() revierte Cliente +
        # ContactoCliente juntos (nunca cliente incompleto).
        if validar_representante and (created or contactos_raw is not None):
            ClienteBusinessService.validar_representante_legal(cliente, empresa_id)

        return cliente, created

    @staticmethod
    def validar_representante_legal(cliente: Cliente, empresa_id: int) -> None:
        """
        Regla central (mision "Clientes + Cartera" seccion 9): NATURAL es
        valido sin representante; JURIDICA exige al menos un
        ContactoCliente activo marcado es_representante_legal=True.
        """
        if cliente.tipo_persona != 'JURIDICA':
            return
        tiene_representante = ContactoCliente.objects.filter(
            cliente_id=cliente.id, empresa_id=empresa_id,
            es_representante_legal=True, activo=True,
        ).only('id').exists()
        if not tiene_representante:
            raise ValidationError({
                'representante_legal': (
                    'Un cliente de tipo Persona Juridica debe tener al menos un '
                    'contacto marcado como Representante Legal.'
                )
            })

    def sincronizar_contactos(self, empresa_id: int, cliente_id: int, contactos_raw: list):
        """
        Sync contacts for a client (Create/Update/Delete).
        MOVED FROM VIEWSET - Fase 0 Phantom Logic Purge.
        """
        if not isinstance(contactos_raw, list):
            return

        existing_ids = set(
            ContactoCliente.objects.filter(
                cliente_id=cliente_id, empresa_id=empresa_id
            ).values_list('id', flat=True)
        )
        submitted_ids = set()

        for c_data in contactos_raw:
            if not isinstance(c_data, dict):
                continue
            
            # Basic validation
            nombre = str(c_data.get('nombre_completo', '')).strip()
            email = str(c_data.get('email', '')).strip()
            if not nombre or not email:
                continue

            c_id = c_data.get('id')
            if c_id and int(c_id) in existing_ids:
                # Update
                contacto = ContactoCliente.objects.get(id=c_id, empresa_id=empresa_id)
                payload = self._clean_payload(c_data)
                self.contacto_crud.update_contacto(contacto, payload)
                submitted_ids.add(int(c_id))
            else:
                # Create
                payload = self._clean_payload(c_data)
                payload['cliente_id'] = cliente_id
                new_c = self.contacto_crud.create_contacto(empresa_id, payload)
                submitted_ids.add(new_c.id)

        # Delete removed contacts
        to_delete = existing_ids - submitted_ids
        if to_delete:
            ContactoCliente.objects.filter(id__in=to_delete, empresa_id=empresa_id).delete()

    def _sanitize_retenciones(self, payload: dict) -> dict:
        """
        Zero Trust: Limpia flags y porcentajes de retención si el cliente no es retenedor.
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

    def _clean_payload(self, data: dict) -> dict:
        """Removes metadata fields before DB save."""
        p = dict(data)
        p.pop('id', None)
        p.pop('empresa', None)
        p.pop('empresa_id', None)
        p.pop('cliente', None)
        return p


class CarteraBusinessService:
    """Orchestration and Business logic for Cartera."""

    def __init__(self):
        self.crud = CarteraCRUDService()
        self.selector = CarteraSelector()

    @staticmethod
    @transaction.atomic
    def registrar_cartera(empresa_id: int, data: dict):
        """
        Idempotent registration of a Cartera record from invoice synchronization.
        """
        from ..models import Cartera
        
        cliente_id = data.get("cliente_id")
        cliente = Cliente.objects.filter(empresa_id=empresa_id, id=cliente_id).first()
        if not cliente:
            raise ValidationError({"cliente": ["El cliente especificado no pertenece a esta empresa."]})

        numero_factura = data.get("numero_factura")
        
        cartera, created = Cartera.objects.get_or_create(
            empresa_id=empresa_id,
            cliente=cliente,
            numero_factura=numero_factura,
            defaults={
                "factura_uuid": data.get("factura_uuid"),
                "fecha_emision": data.get("fecha_emision"),
                "fecha_vencimiento": data.get("fecha_vencimiento"),
                "valor_total": data.get("valor_total"),
                "valor_pagado": data.get("valor_pagado", 0),
                "observaciones": data.get("observaciones", ""),
            }
        )

        if not created:
            cartera.factura_uuid = data.get("factura_uuid", cartera.factura_uuid)
            cartera.fecha_emision = data.get("fecha_emision", cartera.fecha_emision)
            cartera.fecha_vencimiento = data.get("fecha_vencimiento", cartera.fecha_vencimiento)
            cartera.valor_total = data.get("valor_total", cartera.valor_total)
            if "valor_pagado" in data:
                cartera.valor_pagado = data.get("valor_pagado")
            if "observaciones" in data:
                cartera.observaciones = data.get("observaciones")
            cartera.save()

        return cartera, created

    @staticmethod
    @transaction.atomic
    def registrar_abono(empresa_id: int, cartera_uuid, monto) -> tuple:
        """
        Atomic payment/abono registration on a Cartera record with locking.
        """
        from ..models import Cartera
        from decimal import Decimal

        if monto is None or Decimal(str(monto)) <= Decimal("0"):
            raise ValidationError({"monto": ["El monto del abono debe ser mayor a cero."]})

        monto = Decimal(str(monto))

        cartera = Cartera.objects.select_for_update().filter(empresa_id=empresa_id, uuid=cartera_uuid).first()
        if not cartera:
            raise ValidationError({"detail": "La obligacion de cartera no existe o no pertenece a esta empresa."})

        if cartera.estado_pago == "PAGADA":
            raise ValidationError({"detail": "La obligacion ya esta pagada en su totalidad."})

        if monto > cartera.saldo:
            raise ValidationError({"monto": [f"El abono ({monto}) no puede ser mayor al saldo pendiente ({cartera.saldo})."]})

        cartera.valor_pagado += monto
        cartera.save()

        return cartera, monto

    @staticmethod
    def agregar_nota(empresa_id: int, cartera_uuid, texto: str, usuario=None, tipo: str = "SEGUIMIENTO"):
        """
        Registra una anotacion de seguimiento sobre una obligacion de
        Cartera (mision "Clientes + Cartera" seccion 29-30). Append-only --
        nunca actualiza/borra notas existentes, ni el campo `observaciones`
        legado de `Cartera` (siguen siendo dos cosas distintas).
        """
        from ..models import Cartera, CarteraNota

        texto = str(texto or "").strip()
        if not texto:
            raise ValidationError({"texto": ["El texto de la nota es requerido."]})

        cartera = Cartera.objects.filter(empresa_id=empresa_id, uuid=cartera_uuid).only("id").first()
        if not cartera:
            raise ValidationError({"detail": "La obligacion de cartera no existe o no pertenece a esta empresa."})

        return CarteraNota.objects.create(
            empresa_id=empresa_id, cartera=cartera, usuario=usuario, tipo=tipo, texto=texto,
        )

    @staticmethod
    @transaction.atomic
    def registrar_abono_desde_conciliacion_bancaria(empresa_id: int, factura_uuid, monto, fecha=None):
        """
        DEUDA-C03 "Clientes + Cartera" (decision del usuario, 2026-09-11):
        Bancos es la unica fuente que dispara este metodo, al conciliar una
        TransaccionBancaria contra una Factura de VENTA (ver
        apps/tenant/bancos/services/crud_service.py::conciliar_transaccion()).
        Cartera queda como la UNICA SSoT real de pagos -- nunca se vuelve a
        inferir el pago solo del enum Factura.estado_pago.

        Resuelve o crea la Cartera asociada (mismo patron get_or_create ya
        usado en CarteraViewSet.render_offcanvas_abono_factura()) y aplica
        el abono via registrar_abono() -- reutiliza sus guards existentes
        (select_for_update, no-sobrepago, no-doble-pago), nunca los duplica.

        Disenado para NUNCA propagar una excepcion al caller (Bancos): una
        discrepancia de Cartera no debe bloquear ni revertir una
        conciliacion bancaria ya validada por su propio dominio. Por eso el
        monto se acota al saldo disponible en vez de fallar por sobrepago
        -- una diferencia de centavos entre el monto bancario real y el
        saldo de Cartera (por redondeos u otros movimientos) no debe
        impedir la sincronizacion del grueso del pago.

        Retorna None si la factura no es de naturaleza VENTA (Cartera es
        CxC, no CxP -- las compras se gestionan en `proveedores`), no tiene
        cliente vinculado, o el monto es <= 0. Nunca lanza ValidationError
        hacia el caller.
        """
        from decimal import Decimal
        from django.utils import timezone as tz
        from ..models import Cartera
        from apps.tenant.facturas.models import Factura

        try:
            monto = Decimal(str(monto or '0'))
        except Exception:
            return None
        if monto <= Decimal('0'):
            return None

        factura = Factura.objects.filter(
            uuid=factura_uuid, empresa_id=empresa_id, naturaleza='VENTA',
        ).only(
            'id', 'uuid', 'numero', 'total', 'payment_due_date', 'fecha_emision', 'cliente_uuid',
        ).first()
        if not factura or not factura.cliente_uuid:
            return None

        cartera = Cartera.objects.filter(empresa_id=empresa_id, factura_uuid=factura.uuid).first()
        if not cartera:
            cliente = Cliente.objects.filter(uuid=factura.cliente_uuid, empresa_id=empresa_id).only('id').first()
            if not cliente:
                return None
            hoy = fecha or tz.now().date()
            fecha_emision = factura.fecha_emision
            if hasattr(fecha_emision, 'date'):
                fecha_emision = fecha_emision.date()
            cartera = Cartera.objects.create(
                empresa_id=empresa_id, cliente=cliente, numero_factura=factura.numero[:50],
                factura_uuid=factura.uuid,
                fecha_emision=fecha_emision or hoy,
                fecha_vencimiento=factura.payment_due_date or hoy,
                valor_total=factura.total or Decimal('0'),
            )

        if cartera.estado_pago == 'PAGADA':
            return cartera

        monto_aplicable = min(monto, cartera.saldo)
        if monto_aplicable <= Decimal('0'):
            return cartera

        cartera, _ = CarteraBusinessService.registrar_abono(
            empresa_id=empresa_id, cartera_uuid=cartera.uuid, monto=monto_aplicable,
        )
        return cartera
