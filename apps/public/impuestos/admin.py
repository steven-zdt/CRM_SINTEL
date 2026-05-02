from django.contrib import admin

from .models import (
    ActividadEconomica,
    CodigoTributario,
    ConceptoRetencion,
    ContribuyenteTipo,
    DocumentoFuente,
    IngestaLog,
    NormaTributaria,
    PerfilTributario,
    RegimenRenta,
    ResponsabilidadRUT,
    TarifaIVA,
    TipoImpuesto,
)


@admin.register(TipoImpuesto)
class TipoImpuestoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo", "fecha_vigencia", "fecha_fin_vigencia")
    list_filter = ("activo", "fecha_vigencia")
    search_fields = ("codigo", "nombre", "descripcion")
    ordering = ("codigo",)


@admin.register(TarifaIVA)
class TarifaIVAAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "porcentaje", "tipo_tarifa", "activo", "fecha_vigencia")
    list_filter = ("tipo_tarifa", "activo", "fecha_vigencia")
    search_fields = ("codigo", "nombre", "descripcion")
    ordering = ("codigo",)
    fieldsets = (
        ("Información Básica", {"fields": ("codigo", "nombre", "descripcion")}),
        ("Configuración", {"fields": ("porcentaje", "tipo_tarifa", "activo")}),
        ("Vigencia", {"fields": ("fecha_vigencia", "fecha_fin_vigencia")}),
    )


@admin.register(ConceptoRetencion)
class ConceptoRetencionAdmin(admin.ModelAdmin):
    list_display = (
        "codigo",
        "nombre",
        "tipo_retencion",
        "porcentaje",
        "base_minima",
        "activo",
        "fecha_vigencia",
    )
    list_filter = ("tipo_retencion", "activo", "fecha_vigencia")
    search_fields = ("codigo", "nombre", "descripcion")
    ordering = ("tipo_retencion", "codigo")
    fieldsets = (
        ("Información Básica", {"fields": ("codigo", "nombre", "tipo_retencion", "descripcion")}),
        ("Configuración", {"fields": ("porcentaje", "base_minima", "activo")}),
        ("Vigencia", {"fields": ("fecha_vigencia", "fecha_fin_vigencia")}),
    )


@admin.register(CodigoTributario)
class CodigoTributarioAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "tipo", "activo", "fecha_vigencia")
    list_filter = ("tipo", "activo", "fecha_vigencia")
    search_fields = ("codigo", "nombre", "descripcion", "tipo")
    ordering = ("tipo", "codigo")


@admin.register(ActividadEconomica)
class ActividadEconomicaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre", "descripcion")
    ordering = ("codigo",)


class IngestaLogInline(admin.TabularInline):
    """Inline para mostrar logs en el admin de DocumentoFuente."""

    model = IngestaLog
    extra = 0
    readonly_fields = ["etapa", "nivel", "mensaje", "payload", "ts"]
    can_delete = False


class NormaTributariaInline(admin.TabularInline):
    """Inline para mostrar normas en el admin de DocumentoFuente."""

    model = NormaTributaria
    extra = 0
    readonly_fields = [
        "articulo",
        "tema",
        "impuesto",
        "vigencia_desde",
        "vigencia_hasta",
        "created_at",
    ]
    fields = ["articulo", "tema", "impuesto", "vigencia_desde", "vigencia_hasta", "created_at"]
    can_delete = False


@admin.register(DocumentoFuente)
class DocumentoFuenteAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "fuente",
        "tipo",
        "estado",
        "fecha_publicacion",
        "created_at",
    ]
    list_filter = ["estado", "tipo", "fuente", "created_at"]
    search_fields = ["fuente", "url_origen", "hash_sha256"]
    readonly_fields = [
        "hash_sha256",
        "estado",
        "robots_observado",
        "crawl_delay_s",
        "created_at",
        "updated_at",
    ]
    inlines = [IngestaLogInline, NormaTributariaInline]
    fieldsets = (
        ("Documento", {"fields": ("archivo", "url_origen", "fuente", "tipo", "fecha_publicacion")}),
        ("Metadatos", {"fields": ("hash_sha256", "estado")}),
        (
            "Cumplimiento Crawling",
            {
                "fields": ("user_agent", "robots_observado", "crawl_delay_s"),
                "classes": ("collapse",),
            },
        ),
        ("Auditoría", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(IngestaLog)
class IngestaLogAdmin(admin.ModelAdmin):
    list_display = ["documento", "etapa", "nivel", "ts"]
    list_filter = ["nivel", "etapa", "ts"]
    search_fields = ["mensaje", "documento__fuente"]
    readonly_fields = ["documento", "etapa", "nivel", "mensaje", "payload", "ts"]


@admin.register(NormaTributaria)
class NormaTributariaAdmin(admin.ModelAdmin):
    list_display = [
        "articulo",
        "tema",
        "impuesto",
        "vigencia_desde",
        "vigencia_hasta",
        "documento_fuente",
    ]
    list_filter = ["impuesto", "vigencia_desde", "vigencia_hasta", "documento_fuente__fuente"]
    search_fields = ["articulo", "tema", "impuesto", "texto_plano", "documento_fuente__fuente"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        ("Información Básica", {"fields": ("documento_fuente", "articulo", "tema", "impuesto")}),
        ("Vigencia", {"fields": ("vigencia_desde", "vigencia_hasta")}),
        ("Contenido", {"fields": ("texto_plano", "texto_html", "referencias")}),
        ("Auditoría", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


# ============================================================================
# ADMIN PARA NORMATIVA DIAN - CATÁLOGOS TRIBUTARIOS (v2.30+)
# ============================================================================


@admin.register(ContribuyenteTipo)
class ContribuyenteTipoAdmin(admin.ModelAdmin):
    """Admin para ContribuyenteTipo."""

    list_display = ["nombre", "clase", "segmento_dian", "activo", "vigente_desde", "vigente_hasta"]
    list_filter = ["activo", "clase", "segmento_dian", "vigente_desde", "vigente_hasta"]
    search_fields = ["nombre", "base_legal"]
    ordering = ["clase", "segmento_dian", "nombre"]
    fieldsets = (
        ("Información Básica", {"fields": ("nombre", "clase", "segmento_dian")}),
        ("Vigencia", {"fields": ("vigente_desde", "vigente_hasta", "activo")}),
        ("Base Legal", {"fields": ("base_legal",), "classes": ("collapse",)}),
    )

    def save_model(self, request, obj, form, change):
        """Invalidar caché después de guardar."""
        super().save_model(request, obj, form, change)
        self._clear_cache()

    def delete_model(self, request, obj):
        """Invalidar caché después de eliminar."""
        super().delete_model(request, obj)
        self._clear_cache()

    def _clear_cache(self):
        """Invalidar caché del provider."""
        try:
            from apps.public.impuestos.services.provider import clear_impuestos_cache

            clear_impuestos_cache()
        except ImportError:
            pass


@admin.register(RegimenRenta)
class RegimenRentaAdmin(admin.ModelAdmin):
    """Admin para RegimenRenta."""

    list_display = [
        "codigo",
        "nombre",
        "tarifa_base_pj",
        "requiere_facturacion_electronica",
        "aplica_retenciones",
        "activo",
        "vigente_desde",
    ]
    list_filter = [
        "activo",
        "codigo",
        "requiere_facturacion_electronica",
        "aplica_retenciones",
        "vigente_desde",
        "vigente_hasta",
    ]
    search_fields = ["nombre", "descripcion", "base_legal"]
    ordering = ["codigo"]
    fieldsets = (
        ("Información Básica", {"fields": ("codigo", "nombre", "descripcion")}),
        (
            "Configuración",
            {
                "fields": (
                    "tarifa_base_pj",
                    "requiere_facturacion_electronica",
                    "aplica_retenciones",
                    "activo",
                )
            },
        ),
        ("Vigencia", {"fields": ("vigente_desde", "vigente_hasta")}),
        ("Base Legal", {"fields": ("base_legal",), "classes": ("collapse",)}),
    )


@admin.register(ResponsabilidadRUT)
class ResponsabilidadRUTAdmin(admin.ModelAdmin):
    """Admin para ResponsabilidadRUT."""

    list_display = [
        "codigo",
        "nombre",
        "es_responsable_iva",
        "es_no_responsable_iva",
        "es_simple",
        "es_facturador_electronico",
        "es_gran_contribuyente",
        "activo",
    ]
    list_filter = [
        "activo",
        "es_responsable_iva",
        "es_no_responsable_iva",
        "es_simple",
        "es_facturador_electronico",
        "es_gran_contribuyente",
        "vigente_desde",
        "vigente_hasta",
    ]
    search_fields = ["codigo", "nombre", "descripcion", "base_legal"]
    ordering = ["codigo"]
    fieldsets = (
        ("Información Básica", {"fields": ("codigo", "nombre", "descripcion")}),
        (
            "Características",
            {
                "fields": (
                    "es_responsable_iva",
                    "es_no_responsable_iva",
                    "es_simple",
                    "es_facturador_electronico",
                    "es_gran_contribuyente",
                    "activo",
                )
            },
        ),
        ("Vigencia", {"fields": ("vigente_desde", "vigente_hasta")}),
        ("Base Legal", {"fields": ("base_legal",), "classes": ("collapse",)}),
    )


@admin.register(PerfilTributario)
class PerfilTributarioAdmin(admin.ModelAdmin):
    """Admin para PerfilTributario."""

    list_display = [
        "nombre",
        "tipo_contribuyente",
        "regimen_renta",
        "activo",
        "recomendado_desde",
        "recomendado_hasta",
    ]
    list_filter = [
        "activo",
        "tipo_contribuyente",
        "regimen_renta",
        "recomendado_desde",
        "recomendado_hasta",
    ]
    search_fields = ["nombre"]
    filter_horizontal = ["responsabilidades"]
    ordering = ["nombre"]
    fieldsets = (
        (
            "Información Básica",
            {"fields": ("nombre", "tipo_contribuyente", "regimen_renta", "responsabilidades")},
        ),
        ("Vigencia", {"fields": ("recomendado_desde", "recomendado_hasta", "activo")}),
    )

    def save_model(self, request, obj, form, change):
        """Invalidar caché después de guardar."""
        super().save_model(request, obj, form, change)
        self._clear_cache()

    def delete_model(self, request, obj):
        """Invalidar caché después de eliminar."""
        super().delete_model(request, obj)
        self._clear_cache()

    def _clear_cache(self):
        """Invalidar caché del provider."""
        try:
            from apps.public.impuestos.services.provider import clear_impuestos_cache

            clear_impuestos_cache()
        except ImportError:
            pass
