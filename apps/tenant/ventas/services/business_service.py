"""
Business Service para Ventas - Logica de negocio y orquestacion DIAN.

Responsabilidades:
- Double Semantic Verification (DSV): cliente, items y resolucion pertenecen a empresa.
- Asignacion atomica de consecutivos (select_for_update).
- Crear Venta e ItemVenta (BORRADOR).
- Construir DTO canonico DIAN y delegar la creacion de Factura a FacturaBusinessService.
- Mantener desacoplamiento: ventas nunca importa modelos de facturas directamente.

Restricciones:
- Todos los imports de apps externas dentro de metodos (evitar circularidad).
- Cero emojis. Cero campos cuenta_contable_uuid.

VENTAS-COMPRAS-FACTURAS-01 (2026-09-09): el pipeline DIAN completo de este
modulo (construccion de DTO UBL 2.1, CUFE, XML, firma XAdES-EPES) sigue
presente sin modificar -- NO se elimino codigo. Lo que cambio es que
`procesar_y_facturar_venta()` ahora nunca llega a ejecutarlo: rechaza toda
peticion con `EMISION_FISCAL_VENTA_AUTORIZADA = False`. Ver el docstring de
ese metodo para el detalle completo.
"""
import logging
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone

from apps.tenant.ventas.models import Venta
from apps.tenant.ventas.services.crud_service import VentaCRUDService

logger = logging.getLogger(__name__)

# VENTAS-COMPRAS-FACTURAS-01 (2026-09-09): SINTEL todavia NO esta autorizada
# por la DIAN para crear/emitir/transmitir Facturas electronicas -- `facturas`
# es el dueño fiscal exclusivo (recibe XML ya generado/firmado por un
# proveedor tecnologico externo, via FacturaBusinessService.guardar_desde_dto()).
# Deliberadamente una CONSTANTE de codigo, no un settings/env var: reactivar
# este camino es una decision legal/fiscal que exige un cambio de codigo
# explicito y revisado (PR), nunca un toggle de entorno que alguien active
# sin supervision. Ver docs/comercial/VENTAS_COMPRAS_FACTURAS_RELEASE_GATE.md.
EMISION_FISCAL_VENTA_AUTORIZADA = False


class VentaBusinessService:
    """
    Orquestador de Ventas.

    Flujo principal: procesar_y_facturar_venta()
    1. DSV cliente + items + resolucion (si se provee).
    2. Asignar consecutivo con select_for_update() (concurrencia).
    3. Crear Venta + ItemVenta con numero_factura asignado.
    4. Construir DTO canonico basado en la estructura XML UBL DIAN.
    5. Invocar FacturaBusinessService.crear_factura_desde_venta().
    6. Vincular factura y cambiar estado a FACTURADA_DIAN.
    """

    # ------------------------------------------------------------------
    # DSV helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _dsv_cliente(cliente_uuid: str, empresa_id: int):
        """Verifica que el Cliente exista y pertenezca a la empresa. Retorna instancia."""
        from apps.tenant.clientes.models import Cliente
        cliente = Cliente.objects.filter(uuid=cliente_uuid, empresa_id=empresa_id).first()
        if not cliente:
            raise ValueError(
                f"Cliente con UUID {cliente_uuid} no encontrado o no pertenece a la empresa."
            )
        return cliente

    @staticmethod
    def _dsv_items(items_data: list, empresa_id: int) -> list:
        """
        Valida cada item: descripcion requerida, precio > 0.
        Si viene producto_id o servicio_id, verifica pertenencia.
        Retorna items_data enriquecidos con IDs internos (no UUIDs).
        """
        from apps.tenant.inventario.models import Producto, Servicio

        errores = []
        for idx, item in enumerate(items_data):
            if not item.get("descripcion"):
                errores.append(f"Item {idx + 1}: descripcion es obligatoria.")
            precio = Decimal(str(item.get("precio_unitario", "0")))
            if precio <= Decimal("0"):
                errores.append(f"Item {idx + 1}: precio_unitario debe ser mayor a cero.")
            prod_id = item.get("producto_id")
            if prod_id:
                prod = Producto.objects.filter(uuid=prod_id, empresa_id=empresa_id).only("id").first()
                if not prod:
                    errores.append(f"Item {idx + 1}: Producto {prod_id} no valido para la empresa.")
                else:
                    item["producto_id"] = prod.id
            serv_id = item.get("servicio_id")
            if serv_id:
                serv = Servicio.objects.filter(uuid=serv_id, empresa_id=empresa_id).only("id").first()
                if not serv:
                    errores.append(f"Item {idx + 1}: Servicio {serv_id} no valido para la empresa.")
                else:
                    item["servicio_id"] = serv.id

        if errores:
            raise ValueError(" | ".join(errores))

        return items_data

    @staticmethod
    def _dsv_y_asignar_resolucion(empresa_id: int, resolucion_uuid: str):
        """
        DSV + asignacion atomica del consecutivo de la ResolucionFacturacion.
        Usa select_for_update() para prevenir race conditions en entornos concurrentes.

        Debe invocarse dentro de un bloque @transaction.atomic.

        Retorna: (resolucion_instance, numero_factura_str)
        """
        from apps.tenant.ventas.models import ResolucionFacturacion

        resolucion = (
            ResolucionFacturacion.objects
            .select_for_update()
            .filter(uuid=resolucion_uuid, empresa_id=empresa_id)
            .first()
        )
        if not resolucion:
            raise ValueError(
                f"ResolucionFacturacion {resolucion_uuid} no encontrada o no pertenece a la empresa."
            )
        if not resolucion.vigente:
            raise ValueError(
                f"La resolucion {resolucion.numero_resolucion} no esta marcada como vigente."
            )
        if not resolucion.esta_vigente_en_fecha():
            raise ValueError(
                f"La resolucion {resolucion.numero_resolucion} esta fuera del rango de fechas."
            )
        if not resolucion.esta_en_rango():
            raise ValueError(
                f"La resolucion {resolucion.numero_resolucion} ha agotado su rango de consecutivos "
                f"({resolucion.rango_desde}-{resolucion.rango_hasta})."
            )

        numero_factura = resolucion.formar_numero()
        resolucion.consecutivo_actual += 1
        resolucion.save(update_fields=["consecutivo_actual"])

        logger.info(
            "[VentaBS] Consecutivo asignado: %s (resolucion id=%s, siguiente=%s)",
            numero_factura,
            resolucion.id,
            resolucion.consecutivo_actual,
        )
        return resolucion, numero_factura

    # ------------------------------------------------------------------
    # Configuracion DIAN (software provider, ambiente)
    # ------------------------------------------------------------------

    @staticmethod
    def _leer_config_dian() -> dict:
        """
        Lee la configuracion DIAN del software proveedor desde Django settings.
        Permite sobreescribir por variable de entorno o settings.py.

        Claves esperadas en settings:
          DIAN_PROVIDER_ID        - NIT del proveedor tecnologico habilitado (ej: Sintel)
          DIAN_SOFTWARE_ID        - UUID del software registrado en la DIAN
          DIAN_SOFTWARE_PIN       - PIN del software para calcular SoftwareSecurityCode
          DIAN_CL_TECN            - Clave tecnica de la autorizacion (64 hex chars)
          DIAN_TIP_AMB            - "2" habilitacion/pruebas, "1" produccion
          DIAN_AUTHORIZATION_ID   - NIT de la entidad autorizadora (DIAN: 800197268)
        """
        from django.conf import settings

        return {
            "provider_id": getattr(settings, "DIAN_PROVIDER_ID", "800197268"),
            "software_id": getattr(settings, "DIAN_SOFTWARE_ID", "00000000-0000-0000-0000-000000000000"),
            "software_pin": getattr(settings, "DIAN_SOFTWARE_PIN", ""),
            "cl_tecn": getattr(settings, "DIAN_CL_TECN", ""),
            "tip_amb": getattr(settings, "DIAN_TIP_AMB", "2"),
            "authorization_id": getattr(settings, "DIAN_AUTHORIZATION_ID", "800197268"),
            "customization_id": getattr(settings, "DIAN_CUSTOMIZATION_ID", "10"),
            "profile_id": getattr(settings, "DIAN_PROFILE_ID", "DIAN 2.1"),
        }

    @staticmethod
    def _tax_level_code_emisor(regimen_tributario: str) -> tuple:
        """
        Resuelve (TaxLevelCode, listName, TaxScheme_ID, TaxScheme_Name)
        para el emisor segun su regimen tributario.

        regimen_tributario -> TaxLevelCode DIAN:
          COMUN / IVA_RESPONSABLE  -> "O-13" (Responsable de IVA) | listName "48"
          SIMPLIFICADO / PN        -> "R-99-PN" (No responsable)  | listName "49"
          Gran Contribuyente       -> "O-13"
          default                  -> "R-99-PN"

        Retorna: (tax_level_code, list_name, tax_scheme_id, tax_scheme_name)
        """
        regimen = (regimen_tributario or "").upper().strip()
        if any(k in regimen for k in ["COMUN", "COMUN", "IVA", "GRAN"]):
            return ("O-13", "48", "01", "IVA")
        return ("R-99-PN", "49", "ZZ", "No aplica")

    @staticmethod
    def _tax_level_code_receptor(tipo_documento: str, tipo_persona: str = "") -> tuple:
        """
        Resuelve TaxLevelCode para el receptor (cliente).
        Por convencion DIAN: "R-99-PN" para personas naturales, "O-13" para empresas con NIT.
        Retorna: (tax_level_code, list_name, tax_scheme_id, tax_scheme_name, additional_account_id)
        """
        td = str(tipo_documento or "").strip()
        if td == "31":
            return ("O-13", "48", "01", "IVA", "1")
        return ("R-99-PN", "49", "ZZ", "No aplica", "2")

    @staticmethod
    def _software_security_code(software_id: str, software_pin: str, num_fac: str) -> str:
        """
        Calcula el SoftwareSecurityCode DIAN: SHA384(SoftwareID + PIN + NumFac).
        Ref: Anexo Tecnico FE DIAN v1.9 seccion 5.2.1.
        """
        import hashlib
        cadena = software_id + software_pin + num_fac
        return hashlib.sha384(cadena.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Construccion del DTO canonico DIAN UBL 2.1
    # ------------------------------------------------------------------

    @staticmethod
    def _construir_dto_factura(
        empresa,
        cliente,
        venta: Venta,
        items_data: list,
        numero_factura: str = None,
        resolucion=None,
        sede_id: int | None = None,
    ) -> dict:
        """
        Construye el DTO UBL 2.1 completo que el motor de generacion XML necesita.

        Cubre todos los nodos del estandar DIAN:
          - sts:DianExtensions (software, autorizacion, QR)
          - cac:AccountingSupplierParty (emisor con TaxLevelCode)
          - cac:AccountingCustomerParty (receptor con TaxLevelCode)
          - cac:PaymentMeans (medio de pago)
          - cac:TaxTotal (impuestos por tasa)
          - cac:LegalMonetaryTotal (totales desglosados)
          - cac:InvoiceLine[] (lineas con identificadores de producto)

        [OSF Fase F10] `sede_id` (opcional) viaja en el DTO como dato plano
        (`dto["sede_id"]`), igual que `cliente_uuid`/`venta_uuid` - nunca
        una FK directa Ventas->Facturas.
        """
        from django.utils import timezone as tz

        subtotal = venta.subtotal
        impuestos_total = venta.impuestos
        total = venta.total_neto

        num_fac = numero_factura or str(venta.uuid)
        ahora = tz.now()
        fec_fac = ahora.strftime("%Y-%m-%d")
        hor_fac = ahora.strftime("%H:%M:%S") + "-05:00"

        # -- Config DIAN --
        cfg_dian = VentaBusinessService._leer_config_dian()
        soft_security_code = VentaBusinessService._software_security_code(
            cfg_dian["software_id"],
            cfg_dian["software_pin"],
            num_fac,
        )

        # -- Emisor (empresa) --
        regimen = getattr(empresa, "regimen_tributario", "") or ""
        em_tlc, em_list_name, em_ts_id, em_ts_name = VentaBusinessService._tax_level_code_emisor(regimen)
        nit_empresa = str(getattr(empresa, "nit", "") or "")
        dv_empresa = str(getattr(empresa, "dv", "") or "")

        emisor = {
            "nit": nit_empresa,
            "dv": dv_empresa,
            "razon_social": getattr(empresa, "razon_social", "") or "",
            "direccion": getattr(empresa, "direccion", "") or "",
            "ciudad": getattr(empresa, "ciudad", "") or "",
            "departamento": getattr(empresa, "departamento", "") or "",
            "email": getattr(empresa, "email", "") or "",
            "telefono": getattr(empresa, "telefono", "") or "",
            "tipo_documento": "31",
            "additional_account_id": "1",
            "tax_level_code": em_tlc,
            "tax_level_list_name": em_list_name,
            "tax_scheme_id": em_ts_id,
            "tax_scheme_name": em_ts_name,
        }

        # -- Receptor (cliente) --
        tipo_doc_cliente = str(getattr(cliente, "tipo_documento", "31") or "31")
        rc_tlc, rc_list_name, rc_ts_id, rc_ts_name, rc_add_acc = VentaBusinessService._tax_level_code_receptor(
            tipo_doc_cliente
        )
        receptor = {
            "nit": getattr(cliente, "numero_documento", "") or "",
            "razon_social": getattr(cliente, "razon_social", "") or "",
            "email": getattr(cliente, "email", "") or "",
            "telefono": getattr(cliente, "telefono", "") or "",
            "direccion": getattr(cliente, "direccion", "") or "",
            "ciudad": "",
            "tipo_documento": tipo_doc_cliente,
            "additional_account_id": rc_add_acc,
            "tax_level_code": rc_tlc,
            "tax_level_list_name": rc_list_name,
            "tax_scheme_id": rc_ts_id,
            "tax_scheme_name": rc_ts_name,
        }

        # -- Resolucion / autorizacion DIAN --
        resol_data: dict = {}
        if resolucion:
            resol_data = {
                "numero_autorizacion": str(getattr(resolucion, "numero_resolucion", "") or ""),
                "prefijo": str(getattr(resolucion, "prefijo", "") or ""),
                "desde": str(getattr(resolucion, "rango_desde", 1)),
                "hasta": str(getattr(resolucion, "rango_hasta", 1)),
                "fecha_inicio": str(getattr(resolucion, "fecha_desde", "")),
                "fecha_fin": str(getattr(resolucion, "fecha_hasta", "")),
            }

        # -- Medio de pago --
        fecha_vcto = str(venta.fecha_vencimiento) if venta.fecha_vencimiento else fec_fac
        medio_pago = {
            "codigo": "47",
            "fecha_vencimiento": fecha_vcto,
            "instruccion": "Transferencia",
        }

        # -- Lineas e impuestos discriminados por tasa --
        impuestos_por_tasa: dict = {}
        lineas = []
        for idx, item in enumerate(items_data):
            cant = Decimal(str(item.get("cantidad", "1")))
            pu = Decimal(str(item.get("precio_unitario", "0")))
            pct_iva = Decimal(str(item.get("porcentaje_iva", "0")))
            sub_linea = cant * pu
            iva_linea = sub_linea * (pct_iva / Decimal("100"))
            tasa_key = str(pct_iva)
            impuestos_por_tasa[tasa_key] = impuestos_por_tasa.get(tasa_key, Decimal("0")) + iva_linea

            ts_id_linea = "01" if pct_iva > Decimal("0") else "ZZ"
            ts_name_linea = "IVA" if pct_iva > Decimal("0") else "No aplica"

            lineas.append({
                "id": str(idx + 1),
                "descripcion": item.get("descripcion", ""),
                "cantidad": str(cant),
                "valor_unitario": str(pu),
                "porcentaje_iva": str(pct_iva),
                "subtotal": str(sub_linea),
                "iva": str(iva_linea),
                "total": str(sub_linea + iva_linea),
                "unidad": "NAL",
                "tax_scheme_id": ts_id_linea,
                "tax_scheme_name": ts_name_linea,
                "seller_item_id": item.get("descripcion", "")[:20].upper().replace(" ", "-"),
                "std_item_id": str(item.get("producto_id") or item.get("servicio_id") or (idx + 1)),
            })

        # -- Totales desglosados (LegalMonetaryTotal) --
        line_extension_amount = subtotal
        tax_exclusive_amount = subtotal
        tax_inclusive_amount = subtotal + impuestos_total
        allowance_total = Decimal("0.00")
        charge_total = Decimal("0.00")
        payable_amount = tax_inclusive_amount

        totales = {
            "subtotal": str(subtotal),
            "impuestos": str(impuestos_total),
            "total": str(total),
            "line_extension_amount": str(line_extension_amount),
            "tax_exclusive_amount": str(tax_exclusive_amount),
            "tax_inclusive_amount": str(tax_inclusive_amount),
            "allowance_total": str(allowance_total),
            "charge_total": str(charge_total),
            "payable_amount": str(payable_amount),
        }

        # -- Impuestos discriminados para cac:TaxTotal --
        impuestos_discriminados = []
        for pct_str, val_imp in impuestos_por_tasa.items():
            pct_d = Decimal(pct_str)
            ts_id = "01" if pct_d > Decimal("0") else "ZZ"
            ts_name = "IVA" if pct_d > Decimal("0") else "No aplica"
            impuestos_discriminados.append({
                "porcentaje": pct_str,
                "valor": str(val_imp),
                "base": str(subtotal),
                "tax_scheme_id": ts_id,
                "tax_scheme_name": ts_name,
            })

        dto = {
            # Metadatos del documento
            "document_type": "FE",
            "tipo": "FE",
            "naturaleza": "VENTA",
            "customization_id": cfg_dian["customization_id"],
            "profile_id": cfg_dian["profile_id"],
            "tip_amb": cfg_dian["tip_amb"],
            "invoice_type_code": "01",
            "num_fac": num_fac,
            "fec_fac": fec_fac,
            "hor_fac": hor_fac,
            "moneda": "COP",
            "observaciones": venta.observaciones or "",
            # Partes del documento
            "emisor": emisor,
            "receptor": receptor,
            # Configuracion DIAN software
            "dian_software": {
                "provider_id": cfg_dian["provider_id"],
                "software_id": cfg_dian["software_id"],
                "software_security_code": soft_security_code,
                "authorization_id": cfg_dian["authorization_id"],
            },
            # Autorizacion de la resolucion
            "resolucion": resol_data,
            # Medio de pago
            "medio_pago": medio_pago,
            # Totales
            "totales": totales,
            # Impuestos por tasa
            "impuestos_discriminados": impuestos_discriminados,
            # Lineas de factura
            "lineas": lineas,
            # Referencias internas
            "fecha_emision": fec_fac,
            "fecha_vencimiento": str(venta.fecha_vencimiento) if venta.fecha_vencimiento else None,
            "cliente_uuid": str(cliente.uuid),
            "venta_uuid": str(venta.uuid),
            "sede_id": sede_id,
        }

        if numero_factura:
            dto["numero_externo"] = numero_factura

        return dto

    # ------------------------------------------------------------------
    # Metodo principal: crear BORRADOR
    # ------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def crear_venta_borrador(empresa, payload: dict) -> tuple:
        """
        Crea una Venta en estado BORRADOR sin generar factura.
        Util para UI que permite revisar antes de facturar.
        """
        try:
            items_data = payload.get("items", [])
            if not items_data:
                return False, {"detail": "Debe incluir al menos un item."}, 400

            # Hallazgo Batch 5 (mision UI/UX): payload["fecha_emision"] (acceso
            # directo, sin .get()) lanzaba KeyError si el campo faltaba, y
            # KeyError no es ValueError -- caia al except Exception generico de
            # abajo, devolviendo 500 en vez de 400 ante un dato faltante real.
            if not payload.get("fecha_emision"):
                return False, {"detail": "El campo 'fecha_emision' es obligatorio."}, 400

            cliente_uuid = str(payload.get("cliente", ""))
            cliente = VentaBusinessService._dsv_cliente(cliente_uuid, empresa.id)
            items_validos = VentaBusinessService._dsv_items(items_data, empresa.id)

            # DSV proyecto (opcional)
            proyecto = None
            proyecto_uuid = payload.get("proyecto")
            if proyecto_uuid:
                from apps.tenant.proyectos.models import Proyecto
                proyecto = Proyecto.objects.filter(uuid=proyecto_uuid, empresa_id=empresa.id).first()
                if not proyecto:
                    return False, {"detail": f"Proyecto {proyecto_uuid} no valido."}, 400

            venta = VentaCRUDService.crear_venta(
                empresa=empresa,
                cliente=cliente,
                data={
                    "fecha_emision": payload["fecha_emision"],
                    "fecha_vencimiento": payload.get("fecha_vencimiento"),
                    "observaciones": payload.get("observaciones", ""),
                    "proyecto": proyecto,
                },
                items_data=items_validos,
            )
            return True, venta, 201

        except ValueError as exc:
            transaction.set_rollback(True)
            return False, {"detail": str(exc)}, 400
        except Exception as exc:
            transaction.set_rollback(True)
            logger.error("[VentaBS] crear_venta_borrador error: %s", exc, exc_info=True)
            return False, {"detail": "Error interno al crear la venta."}, 500

    @staticmethod
    @transaction.atomic
    def actualizar_venta_borrador(venta_uuid: str, empresa_id: int, payload: dict) -> tuple:
        """
        Actualiza cabecera (fecha_emision, fecha_vencimiento, observaciones,
        proyecto) y, si vienen en el payload, reemplaza los items de una
        Venta en estado BORRADOR.

        REGRESION corregida (2026-09-12, hallazgo V-2): VentaDetailSerializer
        marcaba todos los campos read-only, asi que PATCH/PUT respondian 200
        sin persistir ningun cambio -- VentaCRUDService.actualizar_venta()
        ya existia (con la guarda de estado BORRADOR) pero nadie lo invocaba.
        cliente y resolucion no son editables aqui a proposito: no forman
        parte de campos_cabecera en VentaCRUDService.actualizar_venta() --
        si se necesita cambiar el cliente, se anula y se crea una Venta
        nueva (mismo criterio que Ordenes de Compra/Cotizaciones).
        """
        try:
            venta = Venta.objects.filter(uuid=venta_uuid, empresa_id=empresa_id).first()
            if not venta:
                return False, {"detail": "Venta no encontrada."}, 404

            data = {}
            for campo in ("fecha_emision", "fecha_vencimiento", "observaciones"):
                if campo in payload:
                    data[campo] = payload[campo]

            if "proyecto" in payload:
                proyecto_uuid = payload.get("proyecto")
                if proyecto_uuid:
                    from apps.tenant.proyectos.models import Proyecto
                    proyecto = Proyecto.objects.filter(uuid=proyecto_uuid, empresa_id=empresa_id).first()
                    if not proyecto:
                        return False, {"detail": f"Proyecto {proyecto_uuid} no valido."}, 400
                    data["proyecto"] = proyecto
                else:
                    data["proyecto"] = None

            items_data = None
            if "items" in payload:
                items_data = payload.get("items") or []
                if not items_data:
                    return False, {"detail": "Debe incluir al menos un item."}, 400
                items_data = VentaBusinessService._dsv_items(items_data, empresa_id)

            venta = VentaCRUDService.actualizar_venta(venta, data, items_data)
            return True, venta, 200

        except ValueError as exc:
            transaction.set_rollback(True)
            return False, {"detail": str(exc)}, 400
        except Exception as exc:
            transaction.set_rollback(True)
            logger.error("[VentaBS] actualizar_venta_borrador error: %s", exc, exc_info=True)
            return False, {"detail": "Error interno al actualizar la venta."}, 500

    # ------------------------------------------------------------------
    # Metodo principal: procesar Y facturar en un solo paso
    # ------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def procesar_y_facturar_venta(
        empresa, payload: dict, sede_id: int | None = None, venta_existente: "Venta" = None,
    ) -> tuple:
        """
        Flujo completo: crea Venta + genera Factura DIAN en una sola transaccion atomica.

        Pasos:
        1. DSV cliente e items.
        2. DSV resolucion + asignacion atomica del consecutivo (select_for_update).
        3. Crear Venta + ItemVenta (estado BORRADOR) con numero_factura asignado --
           o, si `venta_existente` fue pasada, PROMOVER esa misma fila en vez de
           crear una nueva (COMERCIAL-04, ver mas abajo).
        4. Construir DTO canonico basado en la estructura XML UBL DIAN.
        5. Invocar FacturaBusinessService.crear_factura_desde_venta(empresa, dto).
        6. Vincular factura y cambiar estado a FACTURADA_DIAN.
        7. Retornar (True, venta, 201).

        [OSF Fase F10] `sede_id` (opcional, la sede ACTIVA de quien hace la
        peticion, via OrganizationalContext) se propaga al DTO canonico
        (`dto["sede_id"]`) y de ahi a `FacturaBusinessService.
        crear_factura_desde_venta()` - nunca como FK directa Ventas->Facturas,
        siempre como dato plano dentro del contrato DTO ya existente (mismo
        patron que `cliente_uuid`/`venta_uuid`). `Venta` no tiene campo
        `sede` propio (F6: candidato plausible sin campo aun) - lo que se
        transporta es el contexto de QUIEN factura, no un campo de la Venta.

        [COMERCIAL-04] `venta_existente` (opcional): cuando se pasa una
        `Venta` ya persistida (llamada desde `VentaViewSet.procesar_facturar()`,
        que opera sobre un `{uuid}` existente), esta operacion PROMUEVE esa
        misma fila a FACTURADA_DIAN en vez de crear una `Venta` hermana nueva
        -- corrige un bug de diseno real donde `POST /ventas/{uuid}/
        procesar-facturar/` creaba siempre una Venta+Factura independientes y
        dejaba la Venta del URL huerfana en BORRADOR para siempre (ver
        docs/comercial/COMERCIAL_01_AUDITORIA.md §6 y
        docs/comercial/COMERCIAL_04_IDEMPOTENCIA.md). Ademas resuelve la
        idempotencia real: si `venta_existente` ya esta `FACTURADA_DIAN`
        (reintento de red / doble-click), se retorna esa misma Venta sin
        volver a ejecutar nada (200, no 201) -- el ancla de idempotencia es
        `Venta.uuid`, ya presente en el URL, sin requerir un
        `Idempotency-Key` nuevo del cliente. Una Venta `ANULADA` se rechaza.

        [VENTAS-COMPRAS-FACTURAS-01] Barrera de emision fiscal (Fase 8):
        rechaza SIEMPRE que `EMISION_FISCAL_VENTA_AUTORIZADA` sea False,
        antes de cualquier escritura (DSV, consecutivo, Venta, DTO, CUFE,
        XML, firma) -- garantiza cero datos parciales. La UNICA excepcion es
        el retorno idempotente de una `venta_existente` que YA esta
        `FACTURADA_DIAN` (historico previo a esta mision, o facturada
        legitimamente en un entorno donde el flag este en True): eso es una
        lectura pura, no emite nada nuevo, y por eso se evalua antes de la
        barrera.
        """
        try:
            if venta_existente is not None:
                if venta_existente.estado == Venta.Estado.FACTURADA_DIAN:
                    return True, venta_existente, 200
                if venta_existente.estado == Venta.Estado.ANULADA:
                    return False, {"detail": "Una venta anulada no puede facturarse."}, 400

            if not EMISION_FISCAL_VENTA_AUTORIZADA:
                logger.warning(
                    "[VentaBS] Intento de emision fiscal bloqueado -- SINTEL no "
                    "esta autorizada por la DIAN para emitir facturas. empresa=%s",
                    empresa.id,
                )
                return False, {
                    "detail": (
                        "La emision de facturas electronicas no esta habilitada en "
                        "SINTEL. Cargue el XML generado por su proveedor tecnologico "
                        "externo en el modulo de Facturas."
                    ),
                }, 403

            # -- Validaciones previas --
            items_data = payload.get("items", [])
            if not items_data:
                return False, {"detail": "Debe incluir al menos un item."}, 400

            cliente_uuid = str(payload.get("cliente", ""))
            if not cliente_uuid:
                return False, {"detail": "El campo 'cliente' es obligatorio."}, 400

            fecha_emision = payload.get("fecha_emision")
            if not fecha_emision:
                return False, {"detail": "El campo 'fecha_emision' es obligatorio."}, 400

            # -- Paso 1: DSV --
            cliente = VentaBusinessService._dsv_cliente(cliente_uuid, empresa.id)
            items_validos = VentaBusinessService._dsv_items(items_data, empresa.id)

            proyecto = None
            proyecto_uuid = payload.get("proyecto")
            if proyecto_uuid:
                from apps.tenant.proyectos.models import Proyecto
                proyecto = Proyecto.objects.filter(uuid=proyecto_uuid, empresa_id=empresa.id).first()
                if not proyecto:
                    return False, {"detail": f"Proyecto {proyecto_uuid} no valido."}, 400

            # -- Paso 2: DSV resolucion + asignacion de consecutivo (select_for_update) --
            resolucion = None
            numero_factura = None
            resolucion_uuid = payload.get("resolucion")
            if resolucion_uuid:
                resolucion, numero_factura = VentaBusinessService._dsv_y_asignar_resolucion(
                    empresa_id=empresa.id,
                    resolucion_uuid=str(resolucion_uuid),
                )

            # -- Paso 3: crear registro Venta (BORRADOR) con resolucion y numero
            # asignados -- o, si venta_existente fue pasada, PROMOVER esa misma
            # fila en vez de crear una hermana nueva (COMERCIAL-04, ver docstring).
            if venta_existente is not None:
                venta_existente.resolucion = resolucion
                venta_existente.numero_factura = numero_factura
                venta_existente.save(update_fields=["resolucion", "numero_factura"])
                venta = venta_existente
            else:
                venta = VentaCRUDService.crear_venta(
                    empresa=empresa,
                    cliente=cliente,
                    data={
                        "fecha_emision": fecha_emision,
                        "fecha_vencimiento": payload.get("fecha_vencimiento"),
                        "observaciones": payload.get("observaciones", ""),
                        "proyecto": proyecto,
                        "resolucion": resolucion,
                        "numero_factura": numero_factura,
                    },
                    items_data=items_validos,
                )

            # -- Paso 4: construir DTO canonico DIAN (UBL 2.1 enriquecido) --
            dto_factura = VentaBusinessService._construir_dto_factura(
                empresa=empresa,
                cliente=cliente,
                venta=venta,
                items_data=items_validos,
                numero_factura=numero_factura,
                resolucion=resolucion,
                sede_id=sede_id,
            )

            # -- Paso 5a: calcular CUFE y QR --
            from apps.tenant.facturas.services.dian.cufe import CufeService
            cufe = CufeService.calcular_desde_dto(dto_factura)
            qr_string = CufeService.generar_qr_string(cufe, dto_factura)
            dto_factura["cufe"] = cufe
            dto_factura["qr_string"] = qr_string

            # -- Paso 5b: generar XML UBL 2.1 --
            from apps.tenant.facturas.services.dian.ubl21_builder import UBL21BuilderService
            xml_bytes = UBL21BuilderService.build(dto_factura, cufe, qr_string)

            # -- Paso 5c: firmar XAdES-EPES (no-op si no hay certificado configurado) --
            # NOMINA-03: XadesSignerService/AttachedDocumentService viven en
            # apps.tenant.core.dian (genericos, compartidos con empleados/nomina).
            from apps.tenant.core.dian import XadesSignerService
            xml_signed = XadesSignerService.sign(xml_bytes)

            # -- Paso 5d: envolver en AttachedDocument + ApplicationResponse --
            from apps.tenant.core.dian import AttachedDocumentService
            attached_doc_bytes = AttachedDocumentService.build(xml_signed, dto_factura, cufe)
            app_response_bytes = AttachedDocumentService.build_application_response(
                dto_factura, cufe, validation_code="02"
            )

            # Enriquecer DTO con el XML y los documentos de respuesta para FacturaBS
            dto_factura["xml_content"] = xml_signed.decode("utf-8")
            dto_factura["dian_response_xml"] = app_response_bytes.decode("utf-8")

            # -- Paso 5e: delegar creacion de Factura a FacturaBusinessService --
            from apps.tenant.facturas.services.business_service import FacturaBusinessService
            factura = FacturaBusinessService.crear_factura_desde_venta(
                empresa=empresa,
                dto=dto_factura,
            )

            # -- Paso 6: vincular y cambiar estado BORRADOR -> FACTURADA_DIAN --
            venta = VentaCRUDService.vincular_factura(venta, factura)

            # -- Paso 7 (F23): salida de inventario real por la venta facturada --
            # Dentro de la misma transaccion atomica: si un item falla (stock
            # insuficiente, producto inactivo), toda la operacion se revierte.
            # Ver documentacion/F23_SALE_INVENTORY_CONTRACT.md.
            VentaBusinessService._generar_salida_inventario(
                venta=venta, empresa_id=empresa.id, sede_id=sede_id,
            )

            logger.info(
                "[VentaBS] Venta id=%s facturada DIAN. Factura id=%s cufe=%s...",
                venta.id,
                factura.id,
                cufe[:16],
            )
            return True, venta, 201

        except ValueError as exc:
            transaction.set_rollback(True)
            return False, {"detail": str(exc)}, 400
        except DjangoValidationError as exc:
            transaction.set_rollback(True)
            detalle = "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
            return False, {"detail": detalle}, 422
        except Exception as exc:
            transaction.set_rollback(True)
            logger.error("[VentaBS] procesar_y_facturar_venta error: %s", exc, exc_info=True)
            return False, {"detail": f"Error al procesar la venta: {exc}"}, 500

    # ------------------------------------------------------------------
    # FACTURAS-UI-CRONO-01: vinculacion MANUAL de una Factura ya
    # existente (nunca emitida desde Ventas -- la barrera fiscal de
    # arriba sigue intacta). El usuario elige una Factura de naturaleza
    # VENTA ya persistida en el modulo Facturas y la asocia a esta
    # Venta -- reutiliza factura_asociada/VentaCRUDService.vincular_factura()
    # ya existentes (VCF-005), sin crear un segundo mecanismo.
    # ------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def vincular_factura_existente(venta: Venta, factura_uuid: str, empresa_id: int) -> tuple:
        """
        Vincula manualmente una Factura YA PERSISTIDA (naturaleza VENTA) a
        esta Venta. NO crea ni emite ninguna Factura -- la barrera fiscal
        (EMISION_FISCAL_VENTA_AUTORIZADA) es ortogonal a esto y no se toca.

        DSV: la Factura debe pertenecer a la misma empresa que la Venta
        (anti-IDOR, resuelta via FacturaSelectors.qs_detail(empresa_id=...),
        nunca Factura.objects.get() directo). `ventas` no importa el
        modelo Factura a nivel de modulo (regla del Bridge, AGENTS.md
        SS17) -- import local dentro del metodo.

        Retorna (ok, resultado, status_code).
        """
        if not factura_uuid:
            return False, {"error": "missing_factura_uuid", "message": "factura_uuid es requerido."}, 400

        if venta.factura_asociada_id:
            return False, {
                "error": "venta_ya_vinculada",
                "message": "Esta Venta ya tiene una Factura vinculada.",
            }, 409

        from apps.tenant.facturas.models import Factura
        from apps.tenant.facturas.services.selectors import FacturaSelectors

        factura = FacturaSelectors.qs_detail(empresa_id=empresa_id).filter(uuid=factura_uuid).first()
        if not factura:
            return False, {
                "error": "factura_not_found",
                "message": "La Factura no existe o no pertenece a esta empresa.",
            }, 404

        if factura.naturaleza != Factura.Naturaleza.VENTA:
            return False, {
                "error": "naturaleza_incorrecta",
                "message": "Solo se puede vincular una Factura de naturaleza VENTA a una Venta.",
            }, 422

        # `venta_origen` es el accessor reverso de un OneToOneField -- Django
        # lo hace compatible con hasattr() (levanta una excepcion que
        # tambien es AttributeError cuando no existe fila vinculada, sin
        # necesidad de un try/except propio ni de un "_id" que no existe
        # en el lado reverso de una OneToOne).
        if hasattr(factura, "venta_origen") and factura.venta_origen.id != venta.id:
            return False, {
                "error": "factura_ya_vinculada",
                "message": "Esta Factura ya esta vinculada a otra Venta.",
            }, 409

        venta = VentaCRUDService.vincular_factura(venta, factura)
        logger.info(
            "[VentaBS] Venta id=%s vinculada manualmente a Factura id=%s (naturaleza=%s).",
            venta.id, factura.id, factura.naturaleza,
        )
        return True, venta, 200

    @staticmethod
    @transaction.atomic
    def crear_venta_desde_factura(factura, empresa) -> "Venta":
        """
        Reconciliacion masiva Facturas->Ventas (FST-375 secc. 16-18/35-39):
        crea una Venta comercial BORRADOR a partir de una Factura fiscal
        (naturaleza VENTA) que no tiene ninguna Venta existente que reclamar
        -- ver management command
        `facturas.management.commands.migrar_facturas_a_ventas`.

        NO reimplementa logica de creacion/vinculo: compone
        VentaCRUDService.crear_venta() (ya usado por crear_venta_borrador)
        + VentaCRUDService.vincular_factura() (ya usado por
        vincular_factura_existente), en la misma transaccion.

        DSV cliente: resuelve `factura.cliente_uuid` si ya esta backfileado;
        si no, reutiliza ClienteBusinessService.resolver_o_crear_desde_factura_venta()
        (mismo servicio que ya usa
        facturas.management.commands.backfill_clientes_facturas_venta) --
        nunca crea un catalogo paralelo de clientes.

        Raises:
            ValueError: la Factura no tiene items (no se puede crear una
            Venta sin al menos un item, misma regla que crear_venta_borrador).
        """
        from apps.tenant.clientes.models import Cliente
        from apps.tenant.clientes.services.business_service import ClienteBusinessService

        items = list(factura.items.all())
        if not items:
            raise ValueError(
                "La Factura no tiene items -- no se puede crear una Venta sin al menos un item."
            )

        cliente = None
        if factura.cliente_uuid:
            cliente = Cliente.objects.filter(
                uuid=factura.cliente_uuid, empresa_id=factura.empresa_id
            ).first()
        if cliente is None:
            cliente, _created = ClienteBusinessService.resolver_o_crear_desde_factura_venta(
                empresa_id=factura.empresa_id,
                receptor_nit=factura.receptor_nit,
                receptor_razon_social=factura.receptor_razon_social,
                receptor_email=factura.receptor_email,
                receptor_telefono=factura.receptor_telefono,
                receptor_direccion=factura.receptor_direccion,
            )

        items_data = [
            {
                "descripcion": item.descripcion,
                "cantidad": item.cantidad,
                "precio_unitario": item.valor_unitario,
                "porcentaje_iva": item.porcentaje_iva,
            }
            for item in items
        ]

        fecha_emision = factura.fecha_emision
        fecha_emision = fecha_emision.date() if hasattr(fecha_emision, "date") else fecha_emision

        venta = VentaCRUDService.crear_venta(
            empresa=empresa,
            cliente=cliente,
            data={
                "fecha_emision": fecha_emision,
                "fecha_vencimiento": factura.fecha_vencimiento,
                "observaciones": f"Migrada automaticamente desde Factura {factura.numero} "
                                  f"(uuid={factura.uuid}).",
                "numero_factura": factura.numero,
            },
            items_data=items_data,
        )
        venta = VentaCRUDService.vincular_factura(venta, factura)
        logger.info(
            "[VentaBS] Venta id=%s creada y vinculada por migracion desde Factura id=%s.",
            venta.id, factura.id,
        )
        return venta

    # ------------------------------------------------------------------
    # Integracion Facturas<->Ventas: Gestion Manual de Pago. `Factura` sigue
    # siendo el unico SSoT de estos 5 campos (ya vivian ahi antes de esta
    # mision, junto a fecha_pago -- nuevo, mismo dueno) -- este metodo es un
    # pass-through fino que reutiliza FacturaBusinessService.
    # actualizar_factura_limitado() (mismo servicio que ya usa el editor
    # propio de Facturas), restringido a los campos de gestion manual.
    # Nunca se tocan campos fiscales desde aqui (el propio servicio de
    # Facturas ya rechaza XML_IMMUTABLE_FIELDS de todos modos).
    # ------------------------------------------------------------------

    GESTION_PAGO_FIELDS = (
        "estado_pago", "forma_pago", "medio_pago_codigo", "payment_due_date", "fecha_pago",
    )

    @staticmethod
    @transaction.atomic
    def actualizar_gestion_pago(venta: Venta, data: dict, empresa_id: int) -> tuple:
        """
        Actualiza los campos de Gestion Manual de Pago de la Factura
        vinculada a esta Venta. Requiere que la Venta ya tenga una Factura
        asociada (via vincular_factura_existente()) -- no crea ninguna.

        DSV: la Factura se re-resuelve por empresa_id (nunca se confia en
        el objeto ya cacheado en venta.factura_asociada) antes de escribir.

        Retorna (ok, resultado, status_code).
        """
        if not venta.factura_asociada_id:
            return False, {
                "error": "sin_factura_vinculada",
                "message": "Esta Venta no tiene ninguna Factura vinculada todavia.",
            }, 404

        from rest_framework.exceptions import ValidationError
        from apps.tenant.facturas.services.selectors import FacturaSelectors
        from apps.tenant.facturas.services.business_service import FacturaBusinessService

        factura = FacturaSelectors.qs_detail(empresa_id=empresa_id).filter(
            pk=venta.factura_asociada_id
        ).first()
        if not factura:
            return False, {
                "error": "factura_not_found",
                "message": "La Factura vinculada no existe o no pertenece a esta empresa.",
            }, 404

        payload_filtrado = {
            field: data[field] for field in VentaBusinessService.GESTION_PAGO_FIELDS if field in data
        }
        if not payload_filtrado:
            return False, {
                "error": "sin_campos",
                "message": "No se envio ningun campo de gestion manual valido.",
            }, 400

        try:
            FacturaBusinessService.actualizar_factura_limitado(factura, payload_filtrado, empresa_id)
        except ValidationError as exc:
            detail = exc.detail if hasattr(exc, "detail") else {"detail": str(exc)}
            return False, detail, 400

        logger.info(
            "[VentaBS] Gestion de pago actualizada para Venta id=%s (Factura id=%s): campos=%s",
            venta.id, factura.id, list(payload_filtrado.keys()),
        )
        return True, venta, 200

    # ------------------------------------------------------------------
    # F23: salida de inventario real por venta facturada (Pull hacia
    # Contabilidad se resuelve solo -- ExtractorInventario, sin cambios)
    # ------------------------------------------------------------------

    @staticmethod
    def _generar_salida_inventario(venta: Venta, empresa_id: int, sede_id: int | None) -> None:
        """
        Genera MovimientoInventario(SALIDA_VENTA) por cada ItemVenta con
        producto real (excluye servicios e items de texto libre). Reutiliza
        KardexService.registrar_movimiento() -- no se crea un servicio de
        inventario nuevo. Idempotente por (empresa, 'ventas', 'ItemVenta',
        item.id, SALIDA_VENTA) via el mismo UniqueConstraint que F21 ya
        establecio en MovimientoInventario. Ver
        documentacion/F23_SALE_INVENTORY_CONTRACT.md.
        """
        from apps.tenant.inventario.models import MovimientoInventario
        from apps.tenant.inventario.services.business_service import KardexService

        items_inventariables = (
            venta.items
            .filter(producto__isnull=False)
            .select_related("producto")
            .only("id", "producto_id", "cantidad", "producto__costo_promedio")
        )
        for item in items_inventariables:
            KardexService.registrar_movimiento(
                empresa_id=empresa_id,
                producto_id=item.producto_id,
                tipo=MovimientoInventario.TipoMovimiento.SALIDA_VENTA,
                cantidad=item.cantidad.quantize(Decimal("0.001")),
                costo_unitario=item.producto.costo_promedio,
                origen_referencia=f"Venta {venta.uuid}",
                sede_id=sede_id,
                documento_origen_app="ventas",
                documento_origen_modelo="ItemVenta",
                documento_origen_id=item.id,
            )

    # ------------------------------------------------------------------
    # Anular
    # ------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def anular_venta(venta_uuid: str, empresa_id: int) -> tuple:
        """Anula una Venta en estado BORRADOR."""
        try:
            venta = Venta.objects.filter(uuid=venta_uuid, empresa_id=empresa_id).first()
            if not venta:
                return False, {"detail": "Venta no encontrada."}, 404
            venta = VentaCRUDService.anular_venta(venta)
            return True, venta, 200
        except ValueError as exc:
            return False, {"detail": str(exc)}, 400
        except Exception as exc:
            logger.error("[VentaBS] anular_venta error: %s", exc, exc_info=True)
            return False, {"detail": "Error al anular la venta."}, 500


class ResolucionFacturacionBusinessService:
    """Logica de negocio para ResolucionFacturacion."""

    @staticmethod
    @transaction.atomic
    def crear_resolucion(empresa, payload: dict) -> tuple:
        """Crea una nueva resolucion DIAN para la empresa."""
        from apps.tenant.ventas.services.crud_service import ResolucionFacturacionCRUDService
        try:
            resolucion = ResolucionFacturacionCRUDService.crear_resolucion(empresa, payload)
            return True, resolucion, 201
        except Exception as exc:
            logger.error("[ResolucionBS] crear_resolucion error: %s", exc, exc_info=True)
            return False, {"detail": str(exc)}, 400

    @staticmethod
    @transaction.atomic
    def actualizar_resolucion(resolucion_uuid: str, empresa_id: int, payload: dict) -> tuple:
        """Actualiza una resolucion DIAN existente."""
        from apps.tenant.ventas.models import ResolucionFacturacion
        from apps.tenant.ventas.services.crud_service import ResolucionFacturacionCRUDService
        try:
            resolucion = ResolucionFacturacion.objects.filter(
                uuid=resolucion_uuid, empresa_id=empresa_id
            ).first()
            if not resolucion:
                return False, {"detail": "ResolucionFacturacion no encontrada."}, 404
            resolucion = ResolucionFacturacionCRUDService.actualizar_resolucion(resolucion, payload)
            return True, resolucion, 200
        except ValueError as exc:
            return False, {"detail": str(exc)}, 400
        except Exception as exc:
            logger.error("[ResolucionBS] actualizar_resolucion error: %s", exc, exc_info=True)
            return False, {"detail": str(exc)}, 400

    @staticmethod
    @transaction.atomic
    def eliminar_resolucion(resolucion_uuid: str, empresa_id: int) -> tuple:
        """Elimina una resolucion DIAN sin ventas asociadas."""
        from apps.tenant.ventas.models import ResolucionFacturacion
        from apps.tenant.ventas.services.crud_service import ResolucionFacturacionCRUDService
        try:
            resolucion = ResolucionFacturacion.objects.filter(
                uuid=resolucion_uuid, empresa_id=empresa_id
            ).first()
            if not resolucion:
                return False, {"detail": "ResolucionFacturacion no encontrada."}, 404
            ResolucionFacturacionCRUDService.eliminar_resolucion(resolucion)
            return True, None, 204
        except ValueError as exc:
            return False, {"detail": str(exc)}, 400
        except Exception as exc:
            logger.error("[ResolucionBS] eliminar_resolucion error: %s", exc, exc_info=True)
            return False, {"detail": str(exc)}, 500
