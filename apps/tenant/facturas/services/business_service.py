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


def same_nit(nit_a, nit_b) -> bool:
    """
    Compara dos NIT tratando el digito de verificacion (cuando viene
    delimitado por guion, ej. "900123456-7") como no significativo --
    unica funcion de comparacion de identidad fiscal (FACTURAS-UI-CRONO-01
    FASE 3, SSoT). Consolida sobre clean_nit() en vez de
    FacturaBusinessService.normalize_document_number(): esa segunda
    funcion CONCATENA el DV en vez de descartarlo (proposito distinto --
    limpieza generica de "numero" de factura, no comparacion fiscal), lo
    que daba falsos "no coincide" cuando el NIT del XML trae el DV con
    guion y Empresa.nit esta guardado sin el (hallazgo real, ver
    docs/facturas/FACTURAS_NATURALEZA_RULE.md). Requiere pasar los NIT
    "crudos" (antes de normalize_document_number), nunca ya concatenados.
    """
    a = clean_nit(nit_a)
    b = clean_nit(nit_b)
    return bool(a) and bool(b) and a == b


def normalize_business_name(name) -> str:
    """Normaliza razon social para comparacion secundaria/informativa
    (mayusculas, espacios repetidos, puntuacion no significativa) --
    NUNCA usar como unica condicion de clasificacion VENTA/COMPRA
    (FACTURAS-UI-CRONO-01, regla explicita)."""
    if not name:
        return ""
    normalized = str(name).strip().upper()
    normalized = re.sub(r'[^\w\s]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized.strip()


def same_business_name(name_a, name_b) -> bool:
    """Comprobacion COMPLEMENTARIA de razon social -- nunca decide
    VENTA/COMPRA por si sola. Ver same_nit(), que es la unica fuente de
    verdad de identidad fiscal."""
    a = normalize_business_name(name_a)
    b = normalize_business_name(name_b)
    return bool(a) and bool(b) and a == b


class FacturaBusinessService:
    """
    Servicio de logica de negocio para Facturas.
    """

    # FISCAL-03 (docs/fiscal/FISCAL_03_ESTADOS.md): secuencia fiscal real
    # BORRADOR -> ENVIADA -> ACEPTADA|RECHAZADA|ERROR_TRANSMISION, +ANULADA
    # como excepcion desde cualquier estado no terminal. Unica fuente de
    # verdad de que transicion es legitima -- pensada para que el pipeline
    # de transmision real (FISCAL-05, cuando exista un adaptador detras de
    # ElectronicDocumentTransportPort) la use al procesar una respuesta.
    #
    # WARNING: por decision explicita del usuario (FISCAL-03), esta matriz
    # NO esta conectada a FacturaViewSet.cambiar_estado() -- ese endpoint
    # sigue permitiendo cualquier transicion manual (hoy es el mecanismo
    # real para sincronizar a mano el estado consultado en el portal de la
    # DIAN, mientras no existe transporte real). validar_transicion_automatica()
    # esta lista para cuando FISCAL-05 la necesite, sin bloquear el uso
    # administrativo actual.
    TRANSICIONES_VALIDAS = {
        'BORRADOR':          {'ENVIADA', 'ANULADA'},
        'ENVIADA':           {'ACEPTADA', 'RECHAZADA', 'ERROR_TRANSMISION', 'ANULADA'},
        'ACEPTADA':          {'ANULADA'},
        'RECHAZADA':         {'ENVIADA', 'ANULADA'},
        'ERROR_TRANSMISION': {'ENVIADA', 'ANULADA'},
        'ANULADA':           set(),
    }

    @staticmethod
    def validar_transicion_automatica(factura: Factura, estado_destino: str) -> None:
        """
        Valida que `estado_destino` sea alcanzable desde `factura.estado`
        segun TRANSICIONES_VALIDAS. Pensado para uso futuro del pipeline de
        transmision real (FISCAL-05) al procesar un TransmissionResult --
        NO se invoca desde FacturaViewSet.cambiar_estado() hoy (ver nota en
        TRANSICIONES_VALIDAS). Lanza DRFValidationError si la transicion no
        es legitima; no hace nada si lo es.
        """
        permitidos = FacturaBusinessService.TRANSICIONES_VALIDAS.get(factura.estado, set())
        if estado_destino not in permitidos:
            raise DRFValidationError({
                'estado': f'No se puede pasar de {factura.estado} a {estado_destino}. '
                          f'Transiciones validas desde {factura.estado}: {sorted(permitidos) or "ninguna"}.'
            })

    @staticmethod
    @transaction.atomic
    def eliminar_factura(factura: Factura) -> None:
        """
        REM P0-01 (docs/remediation/REM-P0-01.md): antes de esta correccion,
        FacturaViewSet.destroy() permitia hard-delete incondicional -- incluso
        de una factura ACEPTADA con CUFE ya reconocido por la DIAN, dejando
        huerfano el AsientoContable ya extraido (el extractor de Contabilidad
        solo toma estado='ACEPTADA', ver
        apps/tenant/contabilidad/integracion/extractores/facturas.py:52,71).

        Solo BORRADOR es eliminable de forma destructiva: es el unico estado
        con evidencia real de que no hay extraccion contable posible (nunca
        fue ENVIADA, no tiene CUFE aceptado). Para cualquier otro estado, la
        via sancionada es la anulacion (transicion a ANULADA via
        cambiar_estado(), ya alcanzable desde todo estado no terminal segun
        TRANSICIONES_VALIDAS) -- nunca DELETE fisico, mismo criterio que
        Venta.anular_venta()/Gasto.anular_documento() en sus apps.

        No revierte automaticamente AsientoContable/MovimientoInventario ya
        extraidos al anular -- eso queda fuera del alcance minimo de esta
        correccion (ver docs/remediation/REM-P0-01.md "Deuda pendiente").
        """
        if factura.estado != Factura.Estado.BORRADOR:
            raise DRFValidationError({
                'estado': (
                    f"No se puede eliminar una factura en estado '{factura.estado}'. "
                    "Solo facturas en BORRADOR admiten eliminacion directa. "
                    "Use la anulacion (cambiar estado a ANULADA) para facturas ya "
                    "enviadas/aceptadas/rechazadas -- preserva la trazabilidad fiscal "
                    "y contable del documento."
                )
            })
        FacturaCRUDService.eliminar(factura)

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
            # Facturas Hub FASE 7-8: crear_factura_desde_venta() nunca pasa
            # por guardar_desde_dto() -- es el unico otro punto de creacion
            # de Factura, siempre INTERNO/SINTEL (push real desde Ventas).
            "origen": Factura.Origen.INTERNO,
            "source_system": Factura.SourceSystem.SINTEL,
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

        # COTIZACIONES-02: cierre del gap de idempotencia documentado --
        # antes, este metodo confiaba por completo en que el caller
        # (VentaBusinessService.procesar_y_facturar_venta, COMERCIAL-04)
        # revisara Venta.estado==FACTURADA_DIAN antes de invocar. Ahora la
        # propia Factura tiene un UniqueConstraint(empresa, numero)
        # (migracion facturas.0041) y esta funcion se protege a si misma:
        # si una llamada concurrente/repetida ya inserto la misma
        # Factura(empresa, numero) entre el calculo del consecutivo y este
        # insert, se recupera y devuelve la existente en vez de propagar el
        # IntegrityError. transaction.atomic() anidado crea un savepoint
        # real (nunca un savepoint "pelado" fuera de atomic() -- ver
        # incidente documentado de 2026-08-25) para que el rollback del
        # INSERT fallido no envenene la transaccion exterior.
        from django.db import IntegrityError

        try:
            with transaction.atomic():
                factura = FacturaCRUDService.crear(factura_data)
        except IntegrityError:
            factura_existente = Factura.objects.filter(
                empresa_id=empresa.id, numero=num_definitivo,
            ).only(
                'id', 'uuid', 'numero', 'naturaleza', 'cufe', 'empresa_id',
                'cliente_uuid', 'proveedor_uuid',
            ).first()
            if not factura_existente:
                raise
            logger.info(
                "[FacturaBS] Factura ya existia (idempotencia numero=%s) -- "
                "devolviendo existente id=%s en vez de duplicar.",
                num_definitivo, factura_existente.id,
            )
            return factura_existente

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
    def _resolver_cliente_existente(empresa_id: int, receptor_nit_raw: str | None):
        """
        Reestructuracion arquitectonica (Facturas = document store, no dueño
        de Cliente): busca un Cliente YA EXISTENTE por NIT -- solo lectura,
        nunca crea. Usa clean_nit() (SSoT de comparacion fiscal, descarta el
        DV) sobre el NIT crudo, no normalize_document_number() (que lo
        concatena, formato distinto al usado para persistir numero_documento
        en Cliente).
        """
        nit = clean_nit(receptor_nit_raw)
        if not nit:
            return None
        from apps.tenant.clientes.services.selectors import ClienteSelector
        return ClienteSelector.get_cliente_by_documento(
            empresa_id=empresa_id, tipo_documento="NIT", numero_documento=nit,
        )

    @staticmethod
    def _resolver_proveedor_existente(empresa_id: int, emisor_nit_raw: str | None):
        """Equivalente a _resolver_cliente_existente() para Proveedor -- solo lectura."""
        nit = clean_nit(emisor_nit_raw)
        if not nit:
            return None
        from apps.tenant.proveedores.models import Proveedor
        return Proveedor.objects.filter(
            empresa_id=empresa_id, tipo_documento="NIT", numero_documento=nit,
        ).only("id", "uuid").first()

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
    def _resolver_naturaleza(
        emisor_nit: str | None, receptor_nit: str | None, empresa_nit: str | None
    ) -> str | None:
        """
        Resuelve si la factura es VENTA, COMPRA, o ambigua (SSoT).

        Retorna None ("Revisar" en UI, FACTURAS-UI-CRONO-01) en vez de
        adivinar cuando: la Empresa no tiene NIT configurado; emisor Y
        receptor son ambos la propia empresa (autofactura, caso no
        cubierto por esta regla); o ni emisor ni receptor son
        identificables como la empresa. Antes de esta mision, cualquier
        caso que no fuera "emisor == empresa" caia por defecto a COMPRA
        sin importar si el emisor estaba vacio o si el documento era en
        realidad ambiguo -- regla explicita nueva: "no inventar
        naturaleza". Usa same_nit() (no normalize_document_number) para
        que el digito de verificacion con guion no cause falsos
        negativos -- ver same_nit().
        """
        if not empresa_nit:
            return None

        tiene_emisor = bool(clean_nit(emisor_nit))
        tiene_receptor = bool(clean_nit(receptor_nit))
        emisor_es_empresa = tiene_emisor and same_nit(emisor_nit, empresa_nit)
        receptor_es_empresa = tiene_receptor and same_nit(receptor_nit, empresa_nit)

        if emisor_es_empresa and receptor_es_empresa:
            return None
        if emisor_es_empresa:
            # A diferencia de COMPRA (ver rama de abajo), VENTA no exige
            # receptor presente: ya sabemos con certeza que el emisor
            # somos nosotros (comparacion de NIT positiva), lo cual basta
            # -- mismo comportamiento que el wrapper de compatibilidad
            # _determinar_naturaleza() siempre tuvo (nunca recibio
            # receptor_nit), confirmado por su propia suite de tests
            # (test_naturaleza_unit.py::test_venta_igual). El FASE 4 de la
            # mision solo lista "Proveedor | Sin receptor | REVISAR" como
            # fila explicita -- no su simetrico.
            return Factura.Naturaleza.VENTA
        if receptor_es_empresa:
            # "Sin emisor | Nuestra Empresa | REVISAR" (FASE 4): que el
            # receptor seamos nosotros no basta si no sabemos quien
            # emitio el documento -- nunca inventar un proveedor.
            return Factura.Naturaleza.COMPRA if tiene_emisor else None
        return None

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
        # NIT "crudos" (antes de normalize_document_number, que concatena el
        # DV) -- same_nit()/clean_nit() son la unica fuente de verdad de
        # comparacion fiscal (FACTURAS-UI-CRONO-01 FASE 3). emisor_nit/
        # receptor_nit (normalizados) se conservan solo para el snapshot
        # guardado en el modelo, nunca para decidir identidad/naturaleza.
        emisor_nit_raw = emisor.get("nit") or dto.get("emisor_nit", "")
        receptor_nit_raw = receptor.get("nit") or dto.get("receptor_nit", "")
        emisor_nit = FacturaBusinessService.normalize_document_number(emisor_nit_raw)
        receptor_nit = FacturaBusinessService.normalize_document_number(receptor_nit_raw)

        # Validacion de campos obligatorios
        if not numero or (not is_credit_note and (not emisor_nit or not receptor_nit)):
            return {"error": "missing_required_fields", "message": "Numero, NIT Emisor y NIT Receptor son obligatorios."}, 422

        # Validar pertenencia del NIT (DIAN) - Fase 1
        if not same_nit(emisor_nit_raw, empresa_instance.nit) and not same_nit(receptor_nit_raw, empresa_instance.nit):
            from django.core.exceptions import ValidationError as DjangoValidationError
            raise DjangoValidationError("El NIT de la empresa actual no coincide con el emisor ni con el receptor del documento.")

        # Determinar naturaleza usando empresa_instance.nit (None = ambiguo, "Revisar")
        naturaleza = FacturaBusinessService._resolver_naturaleza(emisor_nit_raw, receptor_nit_raw, empresa_instance.nit)

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
                # Reestructuracion arquitectonica (mision "Facturas = document
                # store"): Facturas ya NO crea Cliente/Proveedor como efecto
                # lateral de importar un documento -- solo RESUELVE (lectura)
                # un tercero que ya exista por NIT. Si no existe, la
                # referencia queda sin resolver (cliente_uuid/proveedor_uuid
                # en None); vincularlo es responsabilidad de Clientes/
                # Proveedores o de una accion manual del usuario, nunca un
                # side-effect automatico de la ingestion documental.
                if factura_existente.naturaleza == Factura.Naturaleza.VENTA and not factura_existente.cliente_uuid:
                    cliente = FacturaBusinessService._resolver_cliente_existente(empresa_instance.id, receptor_nit_raw)
                    if cliente:
                        FacturaCRUDService.actualizar(factura_existente, {"cliente_uuid": cliente.uuid})

                if factura_existente.naturaleza == Factura.Naturaleza.COMPRA and not factura_existente.proveedor_uuid:
                    proveedor = FacturaBusinessService._resolver_proveedor_existente(empresa_instance.id, emisor_nit_raw)
                    if proveedor:
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
        else:
            # F26-006: sin CUFE (documento incompleto o DTO armado a mano)
            # la rama anterior no aplica, pero Factura.cufe/NotaCredito.cude
            # siguen siendo unique -- guardar "" ahi choca contra la unique
            # constraint con un IntegrityError sin manejar en el segundo
            # intento. Fallback de idempotencia por numero (mismo criterio
            # de "ya existe" que la rama por CUFE) antes de seguir a crear.
            if is_credit_note:
                nota_existente = NotaCredito.objects.filter(
                    numero=numero, empresa=empresa_instance
                ).only("id", "uuid", "numero", "cude", "empresa_id").first()
                if nota_existente:
                    return {
                        "id": nota_existente.id,
                        "uuid": str(nota_existente.uuid),
                        "numero": nota_existente.numero,
                        "cude": nota_existente.cude,
                        "created": False,
                        "error": "duplicate",
                        "message": "Nota credito ya existe (idempotencia por numero, sin CUFE).",
                    }, 200
            else:
                factura_existente = Factura.objects.filter(
                    numero=numero, empresa=empresa_instance
                ).only('id', 'uuid', 'numero', 'naturaleza', 'cufe', 'empresa_id').first()
                if factura_existente:
                    return {
                        "id": factura_existente.id,
                        "uuid": str(factura_existente.uuid),
                        "numero": factura_existente.numero,
                        "naturaleza": factura_existente.naturaleza,
                        "cufe": factura_existente.cufe,
                        "created": False,
                        "message": "Factura ya existe (idempotencia por numero, sin CUFE).",
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

        # Reestructuracion arquitectonica (mision "Facturas = document
        # store"): solo RESUELVE (lectura) un tercero que ya exista por NIT
        # -- nunca lo crea. cliente_uuid/proveedor_uuid quedan en None
        # (valor por defecto ya asignado arriba) cuando no hay match; eso NO
        # bloquea la persistencia del documento fiscal.
        if naturaleza == Factura.Naturaleza.VENTA:
            cliente = FacturaBusinessService._resolver_cliente_existente(empresa_instance.id, receptor_nit_raw)
            cliente_uuid = cliente.uuid if cliente else None
        elif naturaleza == Factura.Naturaleza.COMPRA:
            proveedor = FacturaBusinessService._resolver_proveedor_existente(empresa_instance.id, emisor_nit_raw)
            proveedor_uuid = proveedor.uuid if proveedor else None

        # Construir factura_data con TODOS los campos del modelo
        factura_data = {
            "empresa": empresa_instance,
            "numero": numero,
            "prefijo": dto.get("prefijo", ""),
            # REM P3-08 (docs/remediation/REM-P3-08.md): `consecutivo` es
            # exclusivamente el consecutivo INTERNO asignado por
            # crear_factura_desde_venta() (Empresa.select_for_update() +
            # Max()+1); para Origen.EXTERNO el DTO importado no trae ese
            # concepto -- 0 es un sentinel de "no aplica", NUNCA un
            # consecutivo real. La identidad fiscal real de CUALQUIER
            # Factura (interna o externa) es siempre `numero`
            # (unique=True), nunca `consecutivo`. No se hizo el campo
            # nullable (evaluado y descartado: requeriria migracion +
            # tocar cada consumidor que asume int, para un campo que ya no
            # se usa como identificador en ningun lado real) -- se
            # documenta el sentinel en su lugar.
            "consecutivo": dto.get("consecutivo", 0),
            "tipo": tipo,
            "estado": estado,
            "naturaleza": naturaleza,
            # Facturas Hub FASE 7-8: guardar_desde_dto() es el unico punto
            # de persistencia alcanzable desde importacion XML/upload
            # (confirmado en docs/facturas/FACTURAS_HUB_BASELINE.md §1) --
            # siempre EXTERNO. source_system solo si el DTO lo declara
            # explicitamente (nunca inferido del contenido del XML).
            "origen": Factura.Origen.EXTERNO,
            "source_system": dto.get("source_system") or Factura.SourceSystem.DESCONOCIDO,
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
            # F26-006: None (no "") cuando falta -- unique=True + null=True
            # permite multiples NULL sin chocar; "" repetido si chocaba.
            "cufe": cufe or None,
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
                cude=cufe or None,  # F26-006: ver nota en "cufe" de Factura mas arriba
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
            try:
                result, code = ingest_document(
                    content=file_bytes, filename=filename,
                    preview=preview, async_mode=async_mode,
                )
            except Exception as e:
                logger.exception("[FacturaBS] ingest_document fallo con excepcion no controlada")
                return {"error": "parse_error", "message": str(e)}, 422

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

        # REM P0-02 (docs/remediation/REM-P0-02.md): PeriodoContable.__doc__
        # afirma "Bloquea edicion/anulacion de Facturas y Gastos en periodos
        # cerrados", pero verificar_periodo_cerrado() nunca se invocaba desde
        # aqui -- una factura podia editarse libremente con fecha dentro de
        # un periodo ya cerrado, descuadrando reportes ya emitidos.
        from apps.tenant.contabilidad.services.selectors import verificar_periodo_cerrado
        cerrado, periodo_nombre = verificar_periodo_cerrado(factura.fecha_emision, empresa_id)
        if cerrado:
            raise ValidationError({
                "detail": (
                    f"No se puede editar esta factura: su fecha de emision "
                    f"({factura.fecha_emision}) pertenece al periodo contable "
                    f"'{periodo_nombre}', que ya esta CERRADO."
                )
            })

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

        # Validaciones de Gestion Manual (integracion Facturas<->Ventas):
        # se evaluan sobre el estado FINAL resultante (lo ya persistido +
        # lo que llega en este PATCH), no solo los campos de este request
        # -- evita que un PATCH que solo manda fecha_pago se salte la
        # consistencia con un estado_pago ya guardado antes, y viceversa.
        estado_pago_final = update_data.get('estado_pago', factura.estado_pago)
        fecha_pago_final = update_data.get('fecha_pago', factura.fecha_pago)
        # 'fecha_pago' en update_data puede llegar como string "YYYY-MM-DD"
        # (aun no paso por el DateField del ORM) -- normalizar antes de
        # comparar con objetos date reales.
        if isinstance(fecha_pago_final, str):
            fecha_pago_final = parse_date(fecha_pago_final)

        if estado_pago_final == Factura.EstadoPago.PAGADA and not fecha_pago_final:
            raise ValidationError({
                'fecha_pago': 'El estado de pago "Pagada" requiere una fecha_pago.'
            })

        if fecha_pago_final:
            if factura.fecha_emision and fecha_pago_final < factura.fecha_emision.date():
                raise ValidationError({
                    'fecha_pago': 'La fecha de pago no puede ser anterior a la fecha de emision de la factura.'
                })
            if fecha_pago_final > timezone.localdate():
                raise ValidationError({
                    'fecha_pago': 'La fecha de pago no puede ser una fecha futura.'
                })

        # Nota (reestructuracion arquitectonica facturas=document store): se
        # retiro la validacion de estado_pago vs conciliacion bancaria
        # (v3.11.0, dependia 100% de Factura.total_pagado_bancos/
        # saldo_pendiente -> BancosBridge). Facturas ya no bloquea una
        # edicion de estado_pago basandose en datos de Bancos -- estado_pago
        # vuelve a ser un campo manual simple (MANUAL_EDITABLE_FIELDS), sin
        # tests que dependieran de este bloque (grep repo-wide, 0
        # resultados). El acoplamiento Bancos<->Facturas de fondo
        # (total_pagado_bancos/saldo_pendiente/BancosBridge en si) sigue
        # como deuda documentada, no se toco.
        return FacturaCRUDService.actualizar(factura, update_data)


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

    # Nota (reestructuracion arquitectonica v4.0.0 F2): se removio
    # `recalcular_estado_pago_automatico()` (disparo cross-app desde Bancos
    # tras conciliar una transaccion, v3.11.0) -- dependia de
    # `total_pagado_bancos`/`saldo_pendiente`, tambien removidos de
    # `Factura`. `estado_pago` vuelve a ser un campo manual simple; Bancos
    # ya no lo modifica. El unico call site (`bancos/services/crud_service.py
    # ::conciliar_transaccion()`) se actualizo en la misma pasada para dejar
    # de invocarlo.


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
