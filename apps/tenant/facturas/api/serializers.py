"""
Serializers para la app facturas.

# WARNING: v2.30: API-First (DRF JSON-only) - Contratos canónicos para consumo desde workspace.
# WARNING: v2.40: Alineado con XML reales en apps/tenant/facturas/xml/ - Solo campos extraídos del XML
"""
from rest_framework import serializers

from apps.tenant.facturas.models import Factura, ItemFactura, MailIngestionRun, NotaCredito
from apps.tenant.facturas.services import DETAIL_FIELDS


class ItemFacturaSerializer(serializers.ModelSerializer):
    """Serializer para ItemFactura (nested read-only en FacturaDetailSerializer)."""
    class Meta:
        model = ItemFactura
        fields = (
            "id", "linea_id", "codigo", "descripcion", "cantidad", "unidad_medida",
            "valor_unitario", "porcentaje_iva", "valor_iva", "subtotal", "total",
            "es_servicio", "orden"
        )
        read_only_fields = ("id", "valor_iva", "subtotal", "total", "es_servicio")


class FacturaListDTSerializer(serializers.ModelSerializer):
    """
    Serializer mínimo para Tabulator v2.40 de Facturas.
    
    # WARNING: OPTIMIZACIÓN: Solo campos necesarios para la tabla Tabulator.
    [OK] Alineado con columnas definidas en facturas.page.js (Tabulator v2.40)
    [OK] Sin campos pesados (XML, anexos)
    """
    emisor = serializers.CharField(source="emisor_razon_social", read_only=True)
    receptor = serializers.CharField(source="receptor_razon_social", read_only=True)
    
    class Meta:
        model = Factura
        fields = ("id", "numero", "fecha_emision", "naturaleza", "emisor", "receptor", "total", "cufe")
        read_only_fields = ("id", "cufe")


class FacturaListSerializer(serializers.ModelSerializer):
    """
    Serializer optimizado para listado de facturas (Tabulator v2.60).
    
    # WARNING: CAPA DE API: Serialización (Serializers)
    # WARNING: v2.60: Campos aplanados para Tabulator Factory
    - cliente_nombre: Campo aplanado desde receptor_razon_social (snapshot)
    - total_formateado: Campo calculado formateado para visualización
    - Solo campos necesarios para la tabla (optimización)
    
    # WARNING: CAMPO NATURALEZA: Disponible para el frontend en el listado optimizado
    - El campo `naturaleza` está incluido en los campos serializados (VENTA/COMPRA)
    - Es un campo calculado automáticamente en el Service Layer antes de persistir
    - Está marcado como `read_only` porque se determina automáticamente
    
    # WARNING: OPTIMIZACIÓN ZERO WASTE:
    - El servicio qs_list() ya incluye el campo naturaleza dentro de LIST_FIELDS
    - Esto evita consultas innecesarias a la base de datos
    - Solo se cargan los campos definidos en LIST_FIELDS usando only()
    """
    # # WARNING: CRÍTICO: Formatear fecha para mejor visualización
    fecha_emision = serializers.DateTimeField(format="%Y-%m-%d %H:%M", read_only=True)
    
    # # WARNING: v2.60: Campos aplanados para Tabulator
    cliente_nombre = serializers.CharField(source="receptor_razon_social", read_only=True)
    total_formateado = serializers.SerializerMethodField()
    
    # Campo adicional para detectar Nota de Crédito asociada
    has_nc = serializers.SerializerMethodField()
    nota_credito_id = serializers.SerializerMethodField()
    nota_credito_numero = serializers.SerializerMethodField()
    
    class Meta:
        model = Factura
        # # WARNING: v2.60: Campos optimizados para Tabulator con campos aplanados
        fields = (
            "id",
            "numero",
            "naturaleza",
            "fecha_emision",
            "fecha_vencimiento",
            # NUEVAS COLUMNAS INDEPENDIENTES (Fase 1):
            "emisor_nit",
            "emisor_razon_social",
            "receptor_nit",
            "receptor_razon_social",
            "cliente_nombre",  # MANTENER por compatibilidad backward
            "moneda",
            "subtotal",
            "impuestos",
            "total",
            "total_formateado",
            "estado",
            "estado_pago",
            "dian_validation_desc",
            "retefuente",
            "reteica",
            "reteiva",
            "forma_pago",
            "medio_pago_codigo",
            "payment_due_date",
            "cuenta_contable_uuid",
            "has_nc",
            "nota_credito_id",
            "nota_credito_numero",
        )
        read_only_fields = (
            "id", "numero", "fecha_emision", "naturaleza", "cliente_nombre",
            "emisor_nit", "emisor_razon_social", "receptor_nit", "receptor_razon_social",
            "nota_credito_id", "nota_credito_numero", "has_nc", "subtotal",
            "impuestos", "total", "total_formateado", "cufe"
        )
    
    def get_has_nc(self, obj):
        """Retorna True si la factura tiene una Nota de Crédito asociada."""
        try:
            return hasattr(obj, 'nota_credito') and obj.nota_credito is not None
        except Exception:
            return False
    
    def get_total_formateado(self, obj):
        """Formatea el total como moneda colombiana."""
        if obj.total is None:
            return "$ 0,00"
        return f"${obj.total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    def get_nota_credito_id(self, obj):
        """Retorna el ID de la Nota de Crédito asociada si existe."""
        try:
            nota_credito = obj.nota_credito
            return nota_credito.id if nota_credito else None
        except NotaCredito.DoesNotExist:
            return None
    
    def get_nota_credito_numero(self, obj):
        """Retorna el número de la Nota de Crédito asociada si existe."""
        try:
            nota_credito = obj.nota_credito
            return nota_credito.numero if nota_credito else None
        except NotaCredito.DoesNotExist:
            return None


class FacturaDetailSerializer(serializers.ModelSerializer):
    """
    Serializer de detalle para factura (uno a uno).
    
    # WARNING: v2.37: Alineado con DETAIL_FIELDS del service.
    [OK] Solo cuando el usuario abre detalle
    [OK] Acceso controlado y singular
    [OK] Incluye metadatos de anexos (no el contenido XML)
    [OK] NO incluye items (usar endpoint /items/ si es necesario)
    """
    has_ubl_xml = serializers.SerializerMethodField()
    has_application_response_xml = serializers.SerializerMethodField()
    has_pdf_file = serializers.SerializerMethodField()
    anexos_meta = serializers.SerializerMethodField()
    
    class Meta:
        model = Factura
        fields = tuple(DETAIL_FIELDS) + (
            "has_ubl_xml",
            "has_application_response_xml",
            "has_pdf_file",
            "anexos_meta",
            "cuenta_contable_uuid",
            "cuenta_contable_label",
        )
        read_only_fields = ("id", "created_at", "updated_at", "cufe", "qr_url", "has_ubl_xml", "has_application_response_xml", "has_pdf_file", "anexos_meta", "cuenta_contable_label")
    
    cuenta_contable_label = serializers.SerializerMethodField()

    def get_cuenta_contable_label(self, obj):
        """
        §18: cuenta_contable_uuid se resuelve en frontend via JS (GET /api/v1/contabilidad/cuentas-contables/?uuid=).
        NO importar desde apps.tenant.contabilidad aqui (viola §18 Pull Model / Bounded Context).
        Retorna None - el nombre se pre-carga en JS via getCuentaByUuid().
        """
        return None
    
    def get_has_ubl_xml(self, obj):
        """Indica si existe UBL XML en anexos."""
        anexos = getattr(obj, "anexos", None)
        if not anexos:
            return False
        return bool(getattr(anexos, "ubl_xml", None))
    
    def get_has_application_response_xml(self, obj):
        """Indica si existe ApplicationResponse XML en anexos."""
        anexos = getattr(obj, "anexos", None)
        if not anexos:
            return False
        return bool(getattr(anexos, "application_response_xml", None))
    
    def get_has_pdf_file(self, obj):
        """Indica si existe archivo PDF en anexos."""
        anexos = getattr(obj, "anexos", None)
        if not anexos:
            return False
        return bool(getattr(anexos, "pdf_file", None))
    
    def get_anexos_meta(self, obj):
        """Retorna metadatos de anexos (tamaños, timestamps) sin el contenido."""
        anexos = getattr(obj, "anexos", None)
        if not anexos:
            return {}
        
        ubl_xml = getattr(anexos, "ubl_xml", None)
        app_response_xml = getattr(anexos, "application_response_xml", None)
        pdf_file = getattr(anexos, "pdf_file", None)
        
        # Construir URL del PDF si existe
        pdf_url = None
        pdf_size = 0
        if pdf_file:
            request = self.context.get('request')
            if request:
                pdf_url = request.build_absolute_uri(pdf_file.url)
            pdf_size = pdf_file.size if hasattr(pdf_file, 'size') else 0
        
        return {
            "ubl_size": len(ubl_xml.encode("utf-8")) if ubl_xml else 0,
            "app_response_size": len(app_response_xml.encode("utf-8")) if app_response_xml else 0,
            "pdf_size": pdf_size,
            "pdf_url": pdf_url,
            "updated_at": getattr(anexos, "updated_at", None),
        }


class FacturaWriteSerializer(serializers.ModelSerializer):
    """
    Serializer de escritura: Permite ingresar datos manuales que no vinieron en XML.

    # WARNING: IMPORTANTE: Los campos emisor_* se poblan automáticamente desde Empresa (SSoT)
    mediante el servicio crear_factura() / actualizar_factura().
    # RETENCIONES Y FORMAS DE PAGO: Opcionales (si vienen del XML, se usan; si no, usuario ingresa manualmente).
    # ESTADO DE PAGO: Campo editable por usuario para rastrear pagos (NO_PAGADA, PAGO_PARCIAL, PAGADA).
    """
    class Meta:
        model = Factura
        fields = (
            "numero", "prefijo", "consecutivo", "tipo", "estado", "estado_pago", "fecha_emision", "fecha_vencimiento",
            "receptor_nit", "receptor_razon_social", "receptor_direccion", "receptor_email", "receptor_telefono",
            "moneda", "subtotal", "impuestos", "total",
            "retefuente", "reteica", "reteiva",
            "forma_pago", "medio_pago_codigo", "payment_due_date",
            "cuenta_contable_uuid",
        )
        # No incluir campos read-only ni campos que se calculan automáticamente


class FacturaReadDTOSerializer(serializers.Serializer):
    """
    Serializer para DTO de preview (sin persistir).
    
    # WARNING: MINIMAL: Solo campos esenciales para mostrar en preview.
    """
    numero = serializers.CharField(allow_blank=True, required=False)
    prefijo = serializers.CharField(allow_blank=True, required=False)
    consecutivo = serializers.IntegerField(required=False, allow_null=True)
    fecha_emision = serializers.DateTimeField(required=False, allow_null=True)
    moneda = serializers.CharField(allow_blank=True, required=False)
    subtotal = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    impuestos = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    total = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)
    emisor_nit = serializers.CharField(allow_blank=True, required=False)
    emisor_razon_social = serializers.CharField(allow_blank=True, required=False)
    receptor_nit = serializers.CharField(allow_blank=True, required=False)
    receptor_razon_social = serializers.CharField(allow_blank=True, required=False)
    cufe = serializers.CharField(allow_blank=True, required=False)
    qr_url = serializers.URLField(allow_blank=True, required=False)
    naturaleza = serializers.CharField(allow_blank=True, required=False)


class ImportUBLSerializer(serializers.Serializer):
    """Serializer para importar factura desde UBL XML."""
    xml = serializers.CharField(allow_blank=False, help_text="Contenido XML UBL 2.1 de la factura")


class UploadUBLFileSerializer(serializers.Serializer):
    """Serializer para subir archivo XML UBL 2.1."""
    file = serializers.FileField(allow_empty_file=False, help_text="Archivo XML UBL 2.1")


# --- Serializers para ingesta por correo (Fase 4/5) ---
# # WARNING: SSoT: Las configuraciones se gestionan en /api/v1/empresa/mailbox/configs/
class MailIngestionRunCreateSerializer(serializers.Serializer):
    """
    Serializer para crear una ejecución de ingesta por correo.
    
    # WARNING: SSoT: config_id hace referencia a MailInboxConfig de empresa.
    # WARNING: NATURALEZA: No se especifica; se determina automáticamente desde el XML UBL.
    """
    config_id = serializers.IntegerField(
        required=True,
        help_text="ID de MailInboxConfig de empresa (debe estar activa)"
    )
    limit_messages = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=500,
        default=50,
        help_text="Número máximo de mensajes a procesar"
    )


class MailIngestionRunListSerializer(serializers.ModelSerializer):
    """
    Serializer para listado de ejecuciones de ingesta.
    
    # WARNING: MINIMAL: Solo campos esenciales para tabla de ejecuciones.
    """
    class Meta:
        model = MailIngestionRun
        fields = (
            "id",
            "started_at",
            "finished_at",
            "status",
            "task_id",
            "naturaleza",
            "counts",
        )
        read_only_fields = fields


# --- Serializers para Nota Crédito (Fase 7) ---
class NotaCreditoListSerializer(serializers.ModelSerializer):
    """
    Serializer mínimo para listado de notas crédito.
    
    # WARNING: OPTIMIZACIÓN: Sin xml_content (artefacto pesado).
    [OK] Solo campos esenciales para tabla.
    """
    factura_numero = serializers.CharField(source="factura.numero", read_only=True)
    factura_cufe = serializers.CharField(source="factura.cufe", read_only=True)
    
    class Meta:
        model = NotaCredito
        fields = (
            "id",
            "numero",
            "cude",
            "fecha_emision",
            "moneda",
            "subtotal",
            "impuestos",
            "total",
            "motivo",
            "ref_factura_numero",
            "ref_factura_cufe",
            "factura_numero",
            "factura_cufe",
            "created_at",
        )
        read_only_fields = fields


class NotaCreditoDetailSerializer(serializers.ModelSerializer):
    """
    Serializer de detalle para nota crédito.
    
    # WARNING: OPTIMIZACIÓN: NO incluye xml_content (artefacto pesado).
    [OK] El XML se expone en endpoint dedicado /xml/
    """
    factura_numero = serializers.CharField(source="factura.numero", read_only=True)
    factura_cufe = serializers.CharField(source="factura.cufe", read_only=True)
    factura_id = serializers.IntegerField(source="factura.id", read_only=True)
    
    class Meta:
        model = NotaCredito
        fields = (
            "id",
            "numero",
            "cude",
            "fecha_emision",
            "moneda",
            "subtotal",
            "impuestos",
            "total",
            "motivo",
            "ref_factura_numero",
            "ref_factura_cufe",
            "factura_id",
            "factura_numero",
            "factura_cufe",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
