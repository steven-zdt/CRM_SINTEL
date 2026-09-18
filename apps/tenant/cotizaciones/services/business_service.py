import logging
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from ..models import Cotizacion
from .crud_service import CotizacionCRUDService
from apps.tenant.clientes.models import Cliente
from apps.tenant.cotizaciones.configuracion.models import ConfiguracionCotizacion
from .pdf_export_service import CotizacionPDFExportService
from .item_service import CotizacionItemBusinessService

logger = logging.getLogger(__name__)

def _generar_pdf_sincronizado(cotizacion, empresa):
    """Genera PDF de forma sincrona despues de guardar cotizacion."""
    try:
        pdf_bytes = CotizacionPDFExportService.generar_pdf_publico(cotizacion, empresa)
        if pdf_bytes:
            logger.info(f"[PDF] Generado para cotizacion {cotizacion.uuid}")
            return pdf_bytes
        else:
            logger.warning(f"[PDF] Fallo generacion para cotizacion {cotizacion.uuid}")
    except Exception as e:
        logger.error(f"[PDF] Error generando PDF para {cotizacion.uuid}: {str(e)}", exc_info=True)


class CotizacionService:
    MONEY_Q = Decimal("0.01")
    HUNDRED = Decimal("100")

    # COTIZACIONES-02: unica fuente de verdad de transiciones validas.
    # Reemplaza el mapa de 4 estados de COTIZACIONES-01 (mismo dia) --
    # ACEPTADA->APROBADA, CANCELADA->RECHAZADA, + ARCHIVADA nuevo (cierre
    # administrativo terminal). BORRADOR->ENVIADA solo ocurre via
    # generar_pdf_y_enviar() (gated por PDF exitoso, Fase 04) -- cambiar_estado()
    # la sigue validando aqui para que exista una unica fuente de verdad de
    # transiciones, pero el endpoint publico 'enviar/' esta reemplazado por
    # 'generar-pdf/'.
    TRANSICIONES_VALIDAS = {
        Cotizacion.Estado.BORRADOR: {Cotizacion.Estado.ENVIADA},
        Cotizacion.Estado.ENVIADA: {
            Cotizacion.Estado.BORRADOR, Cotizacion.Estado.APROBADA, Cotizacion.Estado.RECHAZADA,
        },
        Cotizacion.Estado.APROBADA: {Cotizacion.Estado.ARCHIVADA},
        Cotizacion.Estado.RECHAZADA: {Cotizacion.Estado.ARCHIVADA},
        Cotizacion.Estado.ARCHIVADA: set(),
    }

    @staticmethod
    def _to_decimal(value, field_name="value", default="0.00"):
        if value is None:
            return Decimal(default)
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValueError(f"Invalid decimal for {field_name}") from exc

    @staticmethod
    def _q(value):
        return value.quantize(CotizacionService.MONEY_Q, rounding=ROUND_HALF_UP)

    @classmethod
    def _get_payload_value(cls, datos, field_name, default_value):
        value = datos.get(field_name)
        if value is None:
            return default_value
        return value

    @staticmethod
    def get_configuracion_for_empresa(configuracion_input, empresa_id):
        if isinstance(configuracion_input, ConfiguracionCotizacion):
            if configuracion_input.empresa_id != empresa_id:
                raise ValueError("configuracion does not belong to tenant empresa")
            return configuracion_input

        if not configuracion_input:
            configuracion = ConfiguracionCotizacion.objects.filter(empresa_id=empresa_id, es_activo=True).first()
            if not configuracion:
                configuracion = ConfiguracionCotizacion.objects.filter(empresa_id=empresa_id).first()
            if not configuracion:
                configuracion = ConfiguracionCotizacion.objects.create(
                    empresa_id=empresa_id,
                    nombre_configuracion="Perfil General",
                    es_activo=True,
                    dias_validez=15,
                    prefijo_secuencia="COT-",
                    sufijo_secuencia="",
                    semilla_inicial=1,
                    ultimo_numero=0
                )
            return configuracion

        configuracion_id = int(configuracion_input)
        configuracion = ConfiguracionCotizacion.objects.filter(id=configuracion_id, empresa_id=empresa_id).first()
        if not configuracion:
            raise ValueError("configuracion not found for tenant empresa")
        return configuracion

    @staticmethod
    def get_cliente_for_empresa(cliente_input, empresa_id):
        if not cliente_input:
            return None
        if isinstance(cliente_input, Cliente):
            if cliente_input.empresa_id != empresa_id:
                raise ValueError("cliente does not belong to tenant empresa")
            return cliente_input

        cliente_id = int(cliente_input)
        cliente = Cliente.objects.filter(id=cliente_id, empresa_id=empresa_id).first()
        if not cliente:
            raise ValueError("cliente not found for tenant empresa")
        return cliente

    @classmethod
    def _build_header_fields(cls, configuracion, datos):
        dias_validez = int(getattr(configuracion, "dias_validez", 15) or 15)
        fecha_emision = cls._get_payload_value(datos, "fecha_emision", timezone.now().date())
        fecha_vencimiento = fecha_emision + timedelta(days=dias_validez)

        tipo_default = getattr(configuracion, "tipo_cotizacion_default", "MIXTO")
        iva_default = getattr(configuracion, "iva_porcentaje_default", Decimal("19.00"))
        
        return {
            "tipo_cotizacion": cls._get_payload_value(datos, "tipo_cotizacion", tipo_default),
            "fecha_emision": fecha_emision,
            "fecha_vencimiento": fecha_vencimiento,
            "iva_porcentaje": cls._to_decimal(cls._get_payload_value(datos, "iva_porcentaje", iva_default)),
            "porcentaje_aiu_admin": cls._to_decimal(datos.get("porcentaje_aiu_admin", getattr(configuracion, "aiu_admin_default", 0))),
            "porcentaje_aiu_imprevistos": cls._to_decimal(datos.get("porcentaje_aiu_imprevistos", getattr(configuracion, "aiu_imprevistos_default", 0))),
            "porcentaje_aiu_utilidad": cls._to_decimal(datos.get("porcentaje_aiu_utilidad", getattr(configuracion, "aiu_utilidad_default", 0))),
            "dias_totales": int(datos.get("dias_totales") or 1),
            "dias_infraestructura": int(datos.get("dias_infraestructura") or 0),
            "dias_instalacion": int(datos.get("dias_instalacion") or 0),
            "dias_configuracion": int(datos.get("dias_configuracion") or 0),
            "dias_pruebas": int(datos.get("dias_pruebas") or 0),
        }

    @classmethod
    @transaction.atomic
    def _sync_items(cls, cotizacion, items_data):
        """
        Sincroniza los items de la cotizacion (crea, actualiza o elimina).
        Matching: preferencia por uuid (si viene en payload), fallback a id.
        """

        # 1. Mapear items existentes por uuid y por id
        existing_by_uuid = {}
        existing_by_id = {}
        for item in cotizacion.items.all():
            existing_by_uuid[str(item.uuid)] = item
            existing_by_id[item.id] = item

        matched_pks = set()

        # 2. Procesar payload
        for item_data in items_data:
            item_data.pop('empresa', None)

            item_uuid = str(item_data.get('uuid') or '')
            item_id = item_data.get('id')

            instance = None
            if item_uuid and item_uuid in existing_by_uuid:
                instance = existing_by_uuid[item_uuid]
            elif item_id and int(item_id) in existing_by_id:
                instance = existing_by_id[int(item_id)]

            if instance:
                matched_pks.add(instance.pk)
                CotizacionItemBusinessService.registrar(cotizacion.empresa_id, item_data, instance=instance, recalcular=False)
            else:
                item_data['cotizacion'] = cotizacion
                new_item = CotizacionItemBusinessService.registrar(cotizacion.empresa_id, item_data, recalcular=False)
                matched_pks.add(new_item.pk)

        # 3. Eliminar remanentes (items que no vinieron en el payload)
        for item in list(existing_by_id.values()):
            if item.pk not in matched_pks:
                CotizacionItemBusinessService.eliminar_item(item, recalcular=False)

        # N+1 real corregido (auditoria de modernizacion, 2026-08-27): antes
        # cada registrar()/eliminar_item() del loop de arriba recalculaba
        # los totales por su cuenta (2 SELECT + 1 UPDATE cada uno,
        # descartados de inmediato). recalcular=False deja el unico
        # recalculo real a cargo de crear_preforma()/actualizar_cotizacion(),
        # que ya llaman cls.calcular_totales() justo despues de _sync_items()
        # -- no se duplica aqui.

    @classmethod
    @transaction.atomic
    def crear_preforma(cls, empresa, datos):
        configuracion = cls.get_configuracion_for_empresa(datos.get("configuracion"), empresa.id)
        cliente = cls.get_cliente_for_empresa(datos.get("cliente"), empresa.id)

        codigo_unico = cls.generar_codigo_unico(configuracion.id, empresa.id)
        header_fields = cls._build_header_fields(configuracion, datos)

        items_data = datos.pop('items', [])

        cotizacion = CotizacionCRUDService.create_cotizacion(
            empresa=empresa,
            cliente=cliente,
            configuracion=configuracion,
            numero_cotizacion=str(configuracion.ultimo_numero),
            codigo_unico=codigo_unico,
            estado=Cotizacion.Estado.BORRADOR,
            **header_fields,
        )

        # Sincronizar items
        if items_data:
            cls._sync_items(cotizacion, items_data)

        # Recalcular totales finales
        cls.calcular_totales(cotizacion.id, empresa.id)
        cotizacion.refresh_from_db()

        # Generar PDF sincronizado con datos guardados
        _generar_pdf_sincronizado(cotizacion, empresa)

        return cotizacion

    @classmethod
    def generar_codigo_unico(cls, perfil_id, empresa_id):
        configuracion = ConfiguracionCotizacion.objects.select_for_update().filter(id=perfil_id, empresa_id=empresa_id).first()
        if not configuracion:
            raise ValueError("configuracion not found")

        siguiente = (configuracion.ultimo_numero or 0) + 1
        configuracion.ultimo_numero = siguiente
        configuracion.save(update_fields=["ultimo_numero"])

        prefijo = configuracion.prefijo_secuencia or ""
        sufijo = configuracion.sufijo_secuencia or ""
        return f"{prefijo}{siguiente:04d}{sufijo}"

    @staticmethod
    def calcular_totales(cotizacion_id, empresa_id):
        cotizacion = CotizacionCRUDService.get_cotizacion_for_totals(cotizacion_id, empresa_id)
        subtotal = CotizacionCRUDService.get_items_subtotal(cotizacion.id, empresa_id)

        aiu_admin = subtotal * (Decimal(str(cotizacion.porcentaje_aiu_admin or 0)) / CotizacionService.HUNDRED)
        aiu_imprevistos = subtotal * (Decimal(str(cotizacion.porcentaje_aiu_imprevistos or 0)) / CotizacionService.HUNDRED)
        aiu_utilidad = subtotal * (Decimal(str(cotizacion.porcentaje_aiu_utilidad or 0)) / CotizacionService.HUNDRED)
        aiu_total = aiu_admin + aiu_imprevistos + aiu_utilidad

        base_iva = subtotal + aiu_total
        iva = base_iva * (Decimal(str(cotizacion.iva_porcentaje or 0)) / CotizacionService.HUNDRED)
        
        total_q = CotizacionService._q(subtotal + aiu_total + iva)
        cotizacion.total_con_impuestos = total_q
        cotizacion.save(update_fields=["total_con_impuestos"])

        return {"total_con_impuestos": total_q}

    @classmethod
    @transaction.atomic
    def actualizar_cotizacion(cls, instance, datos):
        """
        Actualiza los campos de cabecera y los items de la cotizacion.
        Genera PDF sincronizado con datos guardados.
        """
        # COTIZACIONES-02 (Fase 12, proteccion de datos): solo BORRADOR es
        # editable. ENVIADA/APROBADA/RECHAZADA/ARCHIVADA no permiten cambios
        # de cabecera/items directos -- una ENVIADA que necesite correccion
        # debe volver a BORRADOR primero (POST .../volver-a-borrador/) para
        # que el cambio quede explicito, no silencioso. Evita exactamente lo
        # que el mandato prohibe: "cambios comerciales silenciosos que
        # alteren la propuesta aprobada" / "modificacion de importes en
        # ARCHIVADA".
        from rest_framework.exceptions import ValidationError

        if instance.estado != Cotizacion.Estado.BORRADOR:
            raise ValidationError({
                "estado": [
                    f"Solo se puede editar una cotizacion en BORRADOR "
                    f"(estado actual: {instance.estado})."
                ]
            })

        items_data = datos.pop('items', None)

        # COTIZACIONES-01: 'estado' NO es editable via PATCH generico -- la
        # unica via para transicionar es cambiar_estado() (accion de dominio
        # explicita, con validacion de transicion). Antes estaba en esta
        # lista y se podia hacer PATCH {"estado": "ACEPTADA"} sin ninguna
        # validacion (deuda documentada en varias auditorias previas del
        # modulo, nunca cerrada hasta ahora).
        allowed_fields = [
            'cliente', 'configuracion', 'tipo_cotizacion',
            'fecha_emision', 'iva_porcentaje',
            'porcentaje_aiu_admin', 'porcentaje_aiu_imprevistos', 'porcentaje_aiu_utilidad',
            'dias_totales', 'dias_infraestructura', 'dias_instalacion', 'dias_configuracion', 'dias_pruebas'
        ]

        update_data = {}
        for field in allowed_fields:
            if field in datos:
                val = datos[field]
                if field == 'cliente':
                    update_data[field] = cls.get_cliente_for_empresa(val, instance.empresa_id)
                elif field == 'configuracion':
                    update_data[field] = cls.get_configuracion_for_empresa(val, instance.empresa_id)
                else:
                    update_data[field] = val

        # Aplicar cambios via CRUD a la cabecera
        updated_instance = CotizacionCRUDService.update_cotizacion(instance, **update_data)

        # Sincronizar items si vienen en el payload
        if items_data is not None:
            cls._sync_items(updated_instance, items_data)

        # Recalcular totales
        cls.calcular_totales(updated_instance.id, updated_instance.empresa_id)
        updated_instance.refresh_from_db()

        # Generar PDF sincronizado con datos guardados
        empresa = updated_instance.empresa
        _generar_pdf_sincronizado(updated_instance, empresa)

        return updated_instance

    @classmethod
    def eliminar_cotizacion(cls, instance):
        """
        DELETE fisico -- bloqueado en 2 casos:

        1. (COTIZACIONES-01) Existe trazabilidad real que se romperia: una
           Factura vinculada via Factura.cotizacion_uuid (bridge de
           solo-enlace, CotizacionBridge en
           apps/tenant/facturas/services/selectors.py). Sin este chequeo,
           borrar la cotizacion dejaba el cotizacion_uuid de la Factura
           apuntando a un registro inexistente sin ningun error (hallazgo
           real, auditoria REL Cotizaciones FASE 5, 2026-08-26). Lectura
           Pull directa (mismo patron ya usado por los extractores de
           Contabilidad: import local + filtro empresa_id explicito, sin
           pasar por el Service Layer de Facturas ya que es solo lectura).

        2. (COTIZACIONES-02 Fase 12) El estado ya no es BORRADOR/ENVIADA:
           APROBADA/RECHAZADA nunca permiten hard delete ("no borrar para
           representar cancelacion" -- para eso existe RECHAZADA/ARCHIVADA
           como estados reales); ARCHIVADA es de solo lectura salvo
           acciones administrativas justificadas (no implementadas en esta
           fase por falta de evidencia de que se necesiten -- DEFERRED, ver
           docs/comercial/COTIZACIONES_02_CICLO_COMERCIAL.md).
        """
        from rest_framework.exceptions import ValidationError

        from apps.tenant.facturas.models import Factura

        if instance.estado not in (Cotizacion.Estado.BORRADOR, Cotizacion.Estado.ENVIADA):
            raise ValidationError({
                "estado": [
                    f"No se puede eliminar una cotizacion en estado {instance.estado}. "
                    f"Solo BORRADOR/ENVIADA admiten eliminacion (con trazabilidad intacta)."
                ]
            })

        tiene_factura_vinculada = Factura.objects.filter(
            empresa_id=instance.empresa_id, cotizacion_uuid=instance.uuid,
        ).exists()
        if tiene_factura_vinculada:
            raise ValidationError({
                "error": "cotizacion_vinculada",
                "message": "Esta cotizacion ya fue vinculada a una factura y no puede eliminarse.",
            })

        CotizacionCRUDService.delete_cotizacion(instance)

    # ==================================================================
    # Maquina de estados (COTIZACIONES-01, extendida en COTIZACIONES-02)
    # ==================================================================

    @classmethod
    @transaction.atomic
    def cambiar_estado(cls, instance, nuevo_estado, *, usuario=None, motivo=""):
        """
        Unica via para transicionar el estado de una Cotizacion. Nunca via
        PATCH generico -- 'estado' fue removido a proposito de
        allowed_fields en actualizar_cotizacion().

        select_for_update() serializa transiciones concurrentes sobre la
        MISMA cotizacion (2 clicks de "Aprobar" a la vez) -- mismo patron ya
        usado en generar_codigo_unico() para el consecutivo.

        Idempotente (mandato §10): repetir la transicion actual (ej.
        aprobar de nuevo algo que ya esta APROBADA) no es un error, devuelve
        la cotizacion tal cual sin tocarla NI escribir historial -- solo una
        transicion a un estado DISTINTO no permitido por
        TRANSICIONES_VALIDAS es rechazada.

        COTIZACIONES-02 (Fase 03): cada transicion real (no la idempotente)
        escribe una fila en CotizacionHistorialEstado -- append-only, usuario
        y timestamp reales.
        """
        from rest_framework.exceptions import ValidationError

        from ..models import CotizacionHistorialEstado

        if nuevo_estado not in Cotizacion.Estado.values:
            raise ValidationError({"estado": [f"Estado '{nuevo_estado}' invalido."]})

        cotizacion = Cotizacion.objects.select_for_update().filter(pk=instance.pk).first()
        if not cotizacion:
            raise ValidationError({"cotizacion": ["No encontrada."]})

        actual = cotizacion.estado
        if nuevo_estado == actual:
            return cotizacion

        permitidos = cls.TRANSICIONES_VALIDAS.get(actual, set())
        if nuevo_estado not in permitidos:
            raise ValidationError({
                "estado": [f"Transicion no permitida: {actual} -> {nuevo_estado}."]
            })

        cotizacion.estado = nuevo_estado
        cotizacion.save(update_fields=["estado", "updated_at"])

        CotizacionHistorialEstado.objects.create(
            empresa_id=cotizacion.empresa_id,
            cotizacion=cotizacion,
            estado_anterior=actual,
            estado_nuevo=nuevo_estado,
            usuario=usuario,
            motivo=motivo or "",
        )

        logger.info(
            "[CotizacionService] estado %s -> %s (uuid=%s, usuario=%s)",
            actual, nuevo_estado, cotizacion.uuid, getattr(usuario, "id", None),
        )
        return cotizacion

    # ==================================================================
    # PDF -> ENVIADA (COTIZACIONES-02, Fase 04)
    # ==================================================================

    @classmethod
    @transaction.atomic
    def generar_pdf_y_enviar(cls, instance, empresa, *, usuario=None):
        """
        BORRADOR -> generar PDF -> exito: ENVIADA / error: se queda en
        BORRADOR. La transicion ocurre SOLO despues de comprobar que la
        generacion del PDF termino correctamente -- nunca antes.

        Si la cotizacion ya esta en ENVIADA/APROBADA/RECHAZADA/ARCHIVADA,
        genera el PDF igual (para descarga) pero NO toca el estado -- mismo
        criterio que el endpoint 'exportar-pdf' ya existente, que siempre
        pudo descargar sin importar el estado.

        A diferencia de `_generar_pdf_sincronizado()` (el wrapper "fire and
        forget" usado por crear_preforma()/actualizar_cotizacion(), que
        traga la excepcion y descarta el resultado), esta funcion SI
        propaga la señal real de exito/fallo -- necesaria para decidir la
        transicion. `generar_pdf_publico()` puede devolver bytes, None
        (fallo controlado xhtml2pdf) o lanzar una excepcion (fallo no
        controlado) -- los 3 casos se tratan aqui como "fallo" salvo bytes
        reales.
        """
        from rest_framework.exceptions import ValidationError

        cotizacion = Cotizacion.objects.select_for_update().filter(pk=instance.pk).first()
        if not cotizacion:
            raise ValidationError({"cotizacion": ["No encontrada."]})

        try:
            pdf_bytes = CotizacionPDFExportService.generar_pdf_publico(cotizacion, empresa)
        except Exception as exc:  # noqa: BLE001 -- clasificado abajo, nunca silenciado
            logger.error(
                "[PDF] Error generando PDF para %s: %s", cotizacion.uuid, exc, exc_info=True,
            )
            pdf_bytes = None

        if not pdf_bytes:
            if cotizacion.estado == Cotizacion.Estado.BORRADOR:
                logger.warning(
                    "[CotizacionService] PDF fallo para %s -- permanece BORRADOR", cotizacion.uuid,
                )
            raise ValidationError({
                "pdf": ["No se pudo generar el PDF. La cotizacion permanece en su estado actual."]
            })

        if cotizacion.estado == Cotizacion.Estado.BORRADOR:
            cotizacion = cls.cambiar_estado(
                cotizacion, Cotizacion.Estado.ENVIADA, usuario=usuario, motivo="PDF generado exitosamente",
            )

        return cotizacion, pdf_bytes

    # ==================================================================
    # Cotizacion -> Venta (COTIZACIONES-01, extendido en COTIZACIONES-02 §6)
    # ==================================================================

    @classmethod
    @transaction.atomic
    def convertir_a_venta(cls, instance):
        """
        Convierte una Cotizacion APROBADA en una Venta. Venta pasa a ser
        dueña del proceso comercial desde aqui -- Cotizaciones no vuelve a
        tocar la Venta creada.

        Idempotente (mandato §14): si ya existe una Venta con este
        cotizacion_uuid, la devuelve tal cual en vez de crear una segunda.
        select_for_update() sobre la Cotizacion serializa conversiones
        concurrentes (doble click) igual que cambiar_estado().

        Los items se copian como snapshot (descripcion + cantidad + precio +
        IVA), SIN vincular producto/servicio de Inventario:
        CotizacionItem.producto/servicio apuntan al catalogo PROPIO de
        Cotizaciones (cotizaciones.Producto/Servicio), no a
        inventario.Producto/Servicio -- no existe un mapeo real entre ambos
        catalogos (ver docs/cotizaciones/COTIZACIONES_INTEGRATIONS.md).
        Inventar una correspondencia por nombre/codigo seria una regla no
        respaldada por evidencia real, con riesgo de vincular el producto
        de inventario incorrecto.
        """
        from rest_framework.exceptions import ValidationError

        from apps.tenant.ventas.models import Venta
        from apps.tenant.ventas.services.crud_service import VentaCRUDService

        cotizacion = Cotizacion.objects.select_for_update().filter(pk=instance.pk).first()
        if not cotizacion:
            raise ValidationError({"cotizacion": ["No encontrada."]})

        existente = Venta.objects.filter(
            cotizacion_uuid=cotizacion.uuid, empresa_id=cotizacion.empresa_id,
        ).first()
        if existente:
            return existente

        if cotizacion.estado != Cotizacion.Estado.APROBADA:
            raise ValidationError({
                "estado": [
                    f"Solo una cotizacion APROBADA puede convertirse en venta "
                    f"(estado actual: {cotizacion.estado})."
                ]
            })

        if not cotizacion.cliente_id:
            raise ValidationError({
                "cliente": ["La cotizacion debe tener un cliente asignado para convertirla en venta."]
            })

        items = list(cotizacion.items.select_related("producto", "servicio").all())
        if not items:
            raise ValidationError({"items": ["La cotizacion no tiene items para convertir."]})

        items_data = []
        for item in items:
            descripcion = (item.descripcion or "").strip()
            if not descripcion:
                if item.producto_id and item.producto:
                    descripcion = item.producto.nombre
                elif item.servicio_id and item.servicio:
                    descripcion = item.servicio.nombre
                else:
                    descripcion = "Item de cotizacion"
            items_data.append({
                "descripcion": descripcion,
                "cantidad": item.cantidad,
                "precio_unitario": item.precio_unitario_venta,
                "porcentaje_iva": cotizacion.iva_porcentaje,
            })

        venta = VentaCRUDService.crear_venta(
            empresa=cotizacion.empresa,
            cliente=cotizacion.cliente,
            data={
                "fecha_emision": timezone.now().date(),
                "observaciones": (
                    f"Generada desde Cotizacion "
                    f"{cotizacion.codigo_unico or cotizacion.numero_cotizacion}."
                ),
            },
            items_data=items_data,
        )
        venta.cotizacion_uuid = cotizacion.uuid
        venta.save(update_fields=["cotizacion_uuid"])

        logger.info(
            "[CotizacionService] Venta uuid=%s creada desde Cotizacion uuid=%s",
            venta.uuid, cotizacion.uuid,
        )
        return venta

    # ==================================================================
    # Venta -> Factura VENTA (COTIZACIONES-02, Fase 07)
    # ==================================================================

    @classmethod
    def facturar_venta_de_cotizacion(cls, instance, *, sede_id=None):
        """
        Venta -> VentaFacturaDTO -> Factura VENTA, reutilizando el flujo
        OFICIAL ya existente (VentaBusinessService.procesar_y_facturar_venta,
        COMERCIAL-04) -- no reimplementa calculo de impuestos ni
        construccion del DTO UBL, eso pertenece integramente al bounded
        context de Ventas/Facturas.

        Requiere que ya exista una Venta para esta Cotizacion
        (convertir_a_venta() debe haberse llamado antes -- se rechaza
        explicitamente si no).

        Idempotente (mandato §7, "no duplicar Factura por doble click"):
        se le pasa `venta_existente=venta` a procesar_y_facturar_venta(),
        que ya tiene su propia proteccion real (COMERCIAL-04): si la Venta
        ya esta FACTURADA_DIAN, la devuelve tal cual sin crear una 2a
        Factura. `naturaleza=VENTA` queda fijado por
        FacturaBusinessService.crear_factura_desde_venta() (hardcodeado ahi,
        nunca calculado) -- no se reescribe manualmente ningun total: los
        montos vienen de la Venta ya persistida (subtotal/impuestos/
        total_neto calculados por VentaCRUDService.crear_venta()).
        """
        from rest_framework.exceptions import ValidationError

        from apps.tenant.ventas.models import Venta
        from apps.tenant.ventas.services.business_service import VentaBusinessService

        cotizacion = Cotizacion.objects.filter(pk=instance.pk).first()
        if not cotizacion:
            raise ValidationError({"cotizacion": ["No encontrada."]})

        venta = (
            Venta.objects.filter(cotizacion_uuid=cotizacion.uuid, empresa_id=cotizacion.empresa_id)
            .select_related("cliente")
            .prefetch_related("items__producto", "items__servicio")
            .first()
        )
        if not venta:
            raise ValidationError({
                "venta": ["Esta cotizacion no tiene una Venta asociada. Conviertala a venta primero."]
            })

        # Misma reconstruccion de payload que VentaViewSet.procesar_facturar()
        # ya hace a partir de una Venta existente cuando el body no trae items
        # (apps/tenant/ventas/api/viewsets.py) -- no se inventa un contrato nuevo.
        payload = {
            "cliente": str(venta.cliente.uuid),
            "fecha_emision": str(venta.fecha_emision),
            "items": [
                {
                    "descripcion": item.descripcion,
                    "cantidad": str(item.cantidad),
                    "precio_unitario": str(item.precio_unitario),
                    "porcentaje_iva": str(item.porcentaje_iva),
                    "producto_id": str(item.producto.uuid) if item.producto_id else None,
                    "servicio_id": str(item.servicio.uuid) if item.servicio_id else None,
                }
                for item in venta.items.all()
            ],
        }

        ok, resultado, status_code = VentaBusinessService.procesar_y_facturar_venta(
            empresa=cotizacion.empresa,
            payload=payload,
            sede_id=sede_id,
            venta_existente=venta,
        )
        if not ok:
            detalle = resultado.get("detail", "No se pudo facturar la venta.") if isinstance(resultado, dict) else str(resultado)
            raise ValidationError({"factura": [detalle]})

        return resultado, status_code

    # ==================================================================
    # Servicios -> Proyecto (COTIZACIONES-02, Fase 11)
    # ==================================================================

    @classmethod
    @transaction.atomic
    def convertir_a_proyecto(cls, instance):
        """
        Para cotizaciones cuyo contenido incluya items tipo SERVICIO:
        APROBADA -> crear/asociar Proyecto. Reutiliza el orquestador YA
        EXISTENTE de Proyectos (`orchestrate_create_proyecto`, apps/tenant/
        proyectos/services/business_service.py) -- no se crea un segundo
        modelo Proyecto ni un service paralelo.

        Señal usada para filtrar servicios: `CotizacionItem.tipo_item ==
        'SERVICIO'` (choices reales del modelo). `Cotizacion.tipo_cotizacion`
        NO se usa como filtro -- es texto libre sin choices, y en la
        practica queda casi siempre en 'MIXTO' por un bug ya documentado
        (lee un atributo `tipo_cotizacion_default` que fue eliminado de
        ConfiguracionCotizacion en v2.60) -- no es una señal confiable.

        Idempotente sin tocar el modelo `Proyecto` de otro dominio
        (Zero-Coupling, confirmado en auditoria previa -- no tiene campo
        `cotizacion_uuid` ni ninguna FK a Cotizaciones): el `codigo` del
        Proyecto se deriva deterministicamente de la Cotizacion (mismo
        criterio que `generar_codigo_unico`), y se busca por ese codigo
        antes de crear uno nuevo -- doble click / retry devuelve el mismo
        Proyecto en vez de crear uno hermano.
        """
        from rest_framework.exceptions import ValidationError

        from apps.tenant.proyectos.models import Proyecto
        from apps.tenant.proyectos.services.business_service import orchestrate_create_proyecto

        cotizacion = Cotizacion.objects.select_related("cliente").filter(pk=instance.pk).first()
        if not cotizacion:
            raise ValidationError({"cotizacion": ["No encontrada."]})

        if cotizacion.estado != Cotizacion.Estado.APROBADA:
            raise ValidationError({
                "estado": [
                    f"Solo una cotizacion APROBADA puede asociarse a un proyecto "
                    f"(estado actual: {cotizacion.estado})."
                ]
            })

        items_servicio = list(cotizacion.items.filter(tipo_item="SERVICIO"))
        if not items_servicio:
            raise ValidationError({
                "items": ["La cotizacion no tiene items de tipo SERVICIO -- no aplica crear un proyecto."]
            })

        codigo_derivado = f"PRJ-COT-{cotizacion.codigo_unico or cotizacion.numero_cotizacion}"
        existente = Proyecto.objects.filter(empresa_id=cotizacion.empresa_id, codigo=codigo_derivado).first()
        if existente:
            return existente

        valor_servicios = sum((item.subtotal_linea or Decimal("0")) for item in items_servicio)

        data = {
            "codigo": codigo_derivado,
            "nombre": f"Proyecto - {cotizacion.codigo_unico or cotizacion.numero_cotizacion}",
            "valor_contrato_proyectado": valor_servicios,
        }
        if cotizacion.cliente_id:
            data["cliente_id"] = cotizacion.cliente_id
            data["cliente_nombre"] = cotizacion.cliente.razon_social

        proyecto = orchestrate_create_proyecto(cotizacion.empresa, data)

        logger.info(
            "[CotizacionService] Proyecto uuid=%s creado desde Cotizacion uuid=%s",
            proyecto.uuid, cotizacion.uuid,
        )
        return proyecto
