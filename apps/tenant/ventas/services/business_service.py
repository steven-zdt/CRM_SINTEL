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
"""
import logging
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.tenant.ventas.models import Venta
from apps.tenant.ventas.services.crud_service import VentaCRUDService

logger = logging.getLogger(__name__)


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
            return False, {"detail": str(exc)}, 400
        except Exception as exc:
            logger.error("[VentaBS] crear_venta_borrador error: %s", exc, exc_info=True)
            return False, {"detail": "Error interno al crear la venta."}, 500

    # ------------------------------------------------------------------
    # Metodo principal: procesar Y facturar en un solo paso
    # ------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def procesar_y_facturar_venta(empresa, payload: dict, sede_id: int | None = None) -> tuple:
        """
        Flujo completo: crea Venta + genera Factura DIAN en una sola transaccion atomica.

        Pasos:
        1. DSV cliente e items.
        2. DSV resolucion + asignacion atomica del consecutivo (select_for_update).
        3. Crear Venta + ItemVenta (estado BORRADOR) con numero_factura asignado.
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
        """
        try:
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

            # -- Paso 3: crear registro Venta (BORRADOR) con resolucion y numero asignados --
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
            from apps.tenant.facturas.services.dian.xades_signer import XadesSignerService
            xml_signed = XadesSignerService.sign(xml_bytes)

            # -- Paso 5d: envolver en AttachedDocument + ApplicationResponse --
            from apps.tenant.facturas.services.dian.attached_document import AttachedDocumentService
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

            logger.info(
                "[VentaBS] Venta id=%s facturada DIAN. Factura id=%s cufe=%s...",
                venta.id,
                factura.id,
                cufe[:16],
            )
            return True, venta, 201

        except ValueError as exc:
            return False, {"detail": str(exc)}, 400
        except Exception as exc:
            logger.error("[VentaBS] procesar_y_facturar_venta error: %s", exc, exc_info=True)
            return False, {"detail": f"Error al procesar la venta: {exc}"}, 500

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
