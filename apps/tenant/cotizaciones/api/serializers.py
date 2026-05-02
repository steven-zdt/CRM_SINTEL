"""
Serializers Cotizaciones v2.60 - Tabulator Ready
# WARNING: v2.60: Desacoplamiento Radical y Resiliencia.
"""
import logging
from decimal import Decimal

from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.tenant.clientes.models import (
    Cliente,  # # WARNING: v2.60: Para queryset de cliente filtrado por empresa
)

from ..configuracion.models import (
    ConfiguracionCotizacion,  # # WARNING: v2.60: Para queryset en tiempo de clase
)
from ..models import Cotizacion, CotizacionItem
from ..services import CotizacionService

logger = logging.getLogger(__name__)

class CotizacionItemSerializer(serializers.ModelSerializer):
    """
    Serializer para Items de Cotización v2.60.
    
    # WARNING: Alineado con modelo CotizacionItem:
    - Campos snapshot (descripcion, marca, referencia, unidad)
    - Campos de cálculo (cantidad, costo_unitario, porcentaje_utilidad)
    - Campos calculados (precio_unitario_venta, subtotal_linea) - read_only
    - Campo orden para mantener secuencia
    - # WARNING: v2.60: porcentaje_iva a nivel de ítem (campo extra, no en modelo)
    """
    # # WARNING: v2.60: porcentaje_iva a nivel de ítem (campo extra para aceptar desde frontend)
    # write_only=True porque no existe en el modelo, solo se usa en escritura (POST/PUT)
    porcentaje_iva = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        write_only=True,  # # WARNING: v2.60: Solo para escritura, no se serializa en GET
        help_text=_("Porcentaje de IVA para este ítem específico. Si no se proporciona, se usará el valor por defecto.")
    )
    
    # # WARNING: CORRECCIÓN: Definir el queryset y permitir que sea opcional en el POST
    # El ID de la cotización se asignará automáticamente en el método create() del CotizacionSerializer
    cotizacion = serializers.PrimaryKeyRelatedField(
        queryset=Cotizacion.objects.all(),
        required=False,  # Permite que el validador no falle si el frontend no lo envía en el POST
        allow_null=True
    )
    
    # # WARNING: CORRECCIÓN: Permitir que el campo esté en blanco y sea nulo
    # Aunque no es recomendable para el Snapshot Pattern, esto da flexibilidad al backend
    descripcion = serializers.CharField(
        required=False, 
        allow_blank=True, 
        allow_null=True,
        default=""
    )
    
    class Meta:
        model = CotizacionItem
        fields = [
            'id', 'cotizacion', 'tipo_item', 
            'producto', 'servicio',  # Referencias opcionales
            'descripcion', 'marca', 'referencia', 'unidad',  # Snapshot
            'cantidad', 'costo_unitario', 'porcentaje_utilidad',  # Inputs
            'precio_unitario_venta', 'subtotal_linea',  # Calculados
            'porcentaje_iva',  # # WARNING: v2.60: IVA a nivel de ítem
            'orden'  # Secuencia
        ]
        read_only_fields = ['precio_unitario_venta', 'subtotal_linea']
        # # WARNING: v2.60: porcentaje_iva es write_only (no existe en modelo, solo para escritura)
    
    def to_representation(self, instance):
        """
        # WARNING: v2.60: Sobrescribir para asegurar que porcentaje_iva no se intente leer del modelo
        """
        representation = super().to_representation(instance)
        # porcentaje_iva es write_only, no debe aparecer en la representación
        representation.pop('porcentaje_iva', None)
        return representation


class CotizacionListSerializer(serializers.ModelSerializer):
    """
    Serializer optimizado para listado Tabulator.

    Campos planos sin nested objects. Alineado con LIST_FIELDS de selectors.py.
    Requiere select_related('cliente') en el queryset.
    """
    cliente_nombre = serializers.ReadOnlyField(source='cliente.nombre_comercial')
    cliente_razon_social = serializers.ReadOnlyField(source='cliente.razon_social')
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = Cotizacion
        fields = [
            'id', 'uuid', 'numero_cotizacion', 'estado', 'estado_display',
            'fecha_emision', 'fecha_vencimiento', 'total_con_impuestos',
            'cliente', 'cliente_nombre', 'cliente_razon_social',
            'empresa', 'created_at',
        ]
        read_only_fields = fields


class CotizacionSerializer(serializers.ModelSerializer):
    """
    Serializer de Cabecera v2.60.
    
    # WARNING: Alineado con modelo Cotizacion:
    - Campos básicos (uuid, numero_cotizacion, empresa)
    - Relaciones opcionales (cliente, configuracion) - Resiliencia
    - Campos de estado (tipo_cotizacion, estado, fechas)
    - DNA Financiero (porcentajes AIU, IVA, total_con_impuestos)
    - Items anidados (ordenados por campo 'orden')
    """
    items = CotizacionItemSerializer(many=True, required=False, read_only=False)  # # WARNING: v2.60: Aceptar items anidados en el payload
    cliente_display = serializers.SerializerMethodField(read_only=True)  # # WARNING: v2.60: Solo lectura
    cliente_nombre = serializers.ReadOnlyField(source='cliente.nombre_comercial')  # # WARNING: Sincronización: Campo legible para el frontend
    configuracion_nombre = serializers.SerializerMethodField(read_only=True)  # # WARNING: v2.60: Cambiado a SerializerMethodField para manejar None
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    subtotal = serializers.SerializerMethodField(read_only=True)  # # WARNING: Sincronización: Subtotal calculado desde items
    
    # # WARNING: v2.60: ALINEACIÓN CON FRONTEND (Editor Directo):
    # - HTML: <select id="editor-select-cliente" name="cliente">
    # - JS: payload.cliente = parseInt(selectCliente.value, 10) → Serializer espera int
    # # WARNING: v2.60: cliente debe recibir el ID como entero
    # Se define explícitamente como PrimaryKeyRelatedField para aceptar IDs
    # # WARNING: FASE 1: Limpieza del Campo Cliente - Usar queryset estándar para conversión ID → Objeto
    # El queryset se filtra por empresa en __init__() para seguridad (SSoT)
    cliente = serializers.PrimaryKeyRelatedField(
        queryset=Cliente.objects.all(),  # # WARNING: FASE 1: Queryset estándar para conversión ID → Objeto
        required=True,  # # WARNING: v2.60: Cliente es obligatorio
        allow_null=False,  # # WARNING: v2.60: Cliente no puede ser null
        help_text=_("ID del cliente de la base de datos. Campo obligatorio.")
    )
    
    # # WARNING: v2.60: ALINEACIÓN CON FRONTEND (Editor Directo):
    # - HTML: <select id="editor-select-perfil" name="configuracion">
    # - JS: payload.configuracion = parseInt(selectPerfil.value, 10) → Serializer espera int
    # # WARNING: v2.60: configuracion debe recibir el ID como entero
    # Se define explícitamente como PrimaryKeyRelatedField para aceptar IDs
    # # WARNING: FUERZA BRUTA ARQUITECTÓNICA: Usar queryset estándar para conversión ID → Objeto
    # El queryset se filtra por empresa en __init__() para seguridad (SSoT)
    configuracion = serializers.PrimaryKeyRelatedField(
        queryset=ConfiguracionCotizacion.objects.all(),  # # WARNING: Queryset estándar para conversión ID → Objeto
        required=True,
        allow_null=False,
        help_text=_("ID del perfil de configuración. El número de cotización se generará automáticamente desde este perfil.")
    )
    
    # # WARNING: v2.60: numero_cotizacion es STRICTAMENTE de solo lectura - se genera ÚNICAMENTE en el backend al guardar
    # El frontend NO debe enviar este campo. Se genera automáticamente en el momento exacto de guardar usando bloqueos de fila.
    numero_cotizacion = serializers.CharField(
        read_only=True,
        max_length=50,
        help_text=_("Número de cotización generado automáticamente desde el Perfil de Configuración. No debe ser enviado desde el frontend.")
    )
    
    # # WARNING: v2.60: codigo_unico es STRICTAMENTE de solo lectura - se genera automáticamente en el backend al guardar
    # El frontend NO debe enviar este campo. Se genera automáticamente en el momento exacto de guardar usando bloqueos de fila.
    codigo_unico = serializers.CharField(
        read_only=True,
        max_length=100,
        help_text=_("Código único generado automáticamente desde el perfil de configuración (ej: 'STS. 0422-2026'). No debe ser enviado desde el frontend.")
    )
    
    # # WARNING: v2.60: fecha_emision puede ser proporcionada por el usuario o usar auto_now_add como fallback
    # Si el usuario no la proporciona, el modelo usará auto_now_add=True
    fecha_emision = serializers.DateField(
        required=False,
        allow_null=True,
        help_text=_("Fecha de emisión de la cotización. Si no se proporciona, se usará la fecha actual.")
    )
    
    # # WARNING: v2.60: fecha_vencimiento es STRICTAMENTE de solo lectura - se calcula automáticamente desde dias_validez del perfil
    # El frontend NO debe enviar este campo. Se calcula automáticamente en el backend.
    fecha_vencimiento = serializers.DateField(
        read_only=True,
        help_text=_("Fecha de vencimiento calculada automáticamente desde los días de validez del perfil. No debe ser enviada desde el frontend.")
    )

    class Meta:
        model = Cotizacion
        fields = [
            # Identificación
            'uuid', 'numero_cotizacion', 'codigo_unico', 'empresa',
            # Cliente
            'cliente', 'cliente_display', 'cliente_nombre',
            # Configuración
            'configuracion', 'configuracion_nombre',
            # Estado y fechas
            # # WARNING: ALINEACIÓN CON FRONTEND:
            # - tipo_cotizacion: CharField (acepta: MIXTO, PRODUCTOS, SERVICIOS, MATERIALES)
            #   # WARNING: v2.60: Ya no se envía desde el frontend, se asigna automáticamente desde el perfil
            #   El campo es opcional en creación, el servicio lo asigna desde tipo_cotizacion_default del perfil
            # - fecha_vencimiento: DateField (espera string YYYY-MM-DD)
            #   HTML: <input type="date" id="fecha_vencimiento" name="fecha_vencimiento">
            #   JS: payload.fecha_vencimiento = fechaVencimientoLimpia (string YYYY-MM-DD)
            'tipo_cotizacion', 'estado', 'estado_display',
            'fecha_emision', 'fecha_vencimiento',
            # DNA Financiero (# WARNING: v2.60: Campos opcionales - Lógica financiera ahora a nivel de ítem)
            'porcentaje_aiu_admin', 'porcentaje_aiu_imprevistos', 'porcentaje_aiu_utilidad',
            'iva_porcentaje', 'subtotal', 'total_con_impuestos',
            # # WARNING: v2.60: porcentaje_aiu (write_only) - Único parámetro financiero global que conservamos
            'porcentaje_aiu',
            # Items
            'items'
        ]
        read_only_fields = ['uuid', 'empresa', 'total_con_impuestos', 'estado_display', 'cliente_display', 'cliente_nombre', 'configuracion_nombre', 'codigo_unico', 'numero_cotizacion', 'fecha_vencimiento', 'subtotal']
        # # WARNING: v2.60: fecha_emision removida de read_only_fields para permitir escritura desde el frontend
        # Si no se proporciona, el modelo usará auto_now_add=True como fallback
        # # WARNING: v2.60: numero_cotizacion es STRICTAMENTE read_only - se genera automáticamente al guardar usando bloqueos de fila
        # # WARNING: v2.60: codigo_unico es STRICTAMENTE read_only - se genera automáticamente al guardar usando bloqueos de fila
        # # WARNING: v2.60: fecha_vencimiento es STRICTAMENTE read_only - se calcula automáticamente desde dias_validez del perfil
        # # WARNING: v2.60: tipo_cotizacion es opcional en creación - se asigna automáticamente desde el perfil en el servicio
    
    # # WARNING: v2.60: User-Driven - Campos financieros enviados desde el frontend
    # # WARNING: PASO 1: Habilitar escritura - Estos campos NO están en read_only_fields y son explícitamente DecimalField
    # Permiten que el frontend envíe valores manuales y también aparecen en la respuesta
    iva_porcentaje = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=False,
        default=19.00,
        help_text=_("Porcentaje de IVA global. Enviado desde el frontend (User-Driven).")
    )
    porcentaje_aiu_admin = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=False,
        default=0.00,
        help_text=_("Porcentaje de AIU Administración. Enviado desde el frontend (User-Driven).")
    )
    porcentaje_aiu_imprevistos = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=False,
        default=0.00,
        help_text=_("Porcentaje de AIU Imprevistos. Enviado desde el frontend (User-Driven).")
    )
    porcentaje_aiu_utilidad = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=False,
        default=0.00,
        help_text=_("Porcentaje de AIU Utilidad. Enviado desde el frontend (User-Driven).")
    )
    tipo_cotizacion = serializers.CharField(
        write_only=True,
        required=False,
        default='MIXTO',
        help_text=_("Tipo de cotización (MIXTO, PRODUCTOS, SERVICIOS, MATERIALES). Enviado desde el frontend (User-Driven).")
    )
    # # WARNING: v2.60: Campo extra para aceptar porcentaje_aiu del frontend (se mapea a los tres campos del modelo)
    porcentaje_aiu = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        write_only=True,  # Solo para escritura, no se serializa en lectura
        help_text=_("Porcentaje de AIU único (frontend). Se mapea automáticamente a porcentaje_aiu_admin si se proporciona.")
    )

    def get_cliente_display(self, obj):
        """
        # WARNING: v2.60: Muestra el cliente de la base de datos.
        # WARNING: v2.60: Solo se llama durante la serialización (lectura), nunca durante validación.
        Maneja casos edge donde obj puede ser un dict (durante respuesta de creación).
        """
        # # WARNING: Seguridad: Si obj es un diccionario (edge case durante creación)
        if isinstance(obj, dict):
            cliente = obj.get('cliente')
            if cliente:
                if isinstance(cliente, dict):
                    return cliente.get('razon_social', str(cliente))
                return str(cliente)
            return _("Cliente no especificado")
        
        # Si obj es una instancia del modelo
        if hasattr(obj, 'cliente') and obj.cliente:
            if hasattr(obj.cliente, 'razon_social'):
                return obj.cliente.razon_social
            elif hasattr(obj.cliente, 'nombre_completo'):
                return obj.cliente.nombre_completo
            return str(obj.cliente)
        
        return _("Cliente no especificado")
    
    def get_subtotal(self, obj):
        """
        # WARNING: Sincronización: Calcula el subtotal sumando los subtotal_linea de todos los items.
        El subtotal es la suma de los subtotales de línea antes de aplicar IVA y AIU.
        """
        from decimal import Decimal
        
        # Si obj es una instancia del modelo con items relacionados
        if hasattr(obj, 'items'):
            # Sumar todos los subtotal_linea de los items
            subtotal = sum(
                item.subtotal_linea 
                for item in obj.items.all() 
                if hasattr(item, 'subtotal_linea') and item.subtotal_linea is not None
            )
            return Decimal(str(subtotal)) if subtotal else Decimal('0.00')
        
        # Si obj es un diccionario (edge case durante creación)
        if isinstance(obj, dict):
            items = obj.get('items', [])
            if items:
                subtotal = sum(
                    Decimal(str(item.get('subtotal_linea', 0)))
                    for item in items
                    if isinstance(item, dict) and item.get('subtotal_linea') is not None
                )
                return subtotal
        
        return Decimal('0.00')
    
    def get_configuracion_nombre(self, obj):
        """
        # WARNING: v2.60: Muestra el nombre de la configuración de forma segura.
        Maneja el caso cuando configuracion es None.
        """
        if isinstance(obj, dict):
            configuracion = obj.get('configuracion')
            if configuracion:
                if isinstance(configuracion, dict):
                    return configuracion.get('nombre_configuracion', str(configuracion))
                return str(configuracion)
            return _("Sin configuración")
        
        # Si obj es una instancia del modelo
        if hasattr(obj, 'configuracion') and obj.configuracion:
            if hasattr(obj.configuracion, 'nombre_configuracion'):
                return obj.configuracion.nombre_configuracion
            return str(obj.configuracion)
        return _("Sin configuración")

    def to_internal_value(self, data):
        """
        # WARNING: FUERZA BRUTA ARQUITECTÓNICA: Limpiar y normalizar el valor del cliente ANTES de validación.
        Esto previene errores cuando el frontend envía texto en lugar del ID numérico.
        
        Casos manejados:
        - String con solo números: "123" → 123
        - String con texto y números: "cliente SAS (10000000)" → 10000000
        - Número: 123 → 123
        - None/vacío: se valida después
        """
        # Limpiar el valor del cliente si viene como string
        if isinstance(data, dict) and 'cliente' in data:
            cliente_value = data.get('cliente')
            
            # Si es None o vacío, dejar que la validación lo maneje
            if cliente_value is None or (isinstance(cliente_value, str) and not cliente_value.strip()):
                return super().to_internal_value(data)
            
            # Si es string, intentar extraer el ID numérico
            if isinstance(cliente_value, str):
                cliente_value_limpio = cliente_value.strip()
                
                # Caso 1: String con solo dígitos
                if cliente_value_limpio.isdigit():
                    data['cliente'] = int(cliente_value_limpio)
                else:
                    # Caso 2: String con texto y números (ej: "cliente SAS (10000000)")
                    # Buscar el primer número completo en el string
                    import re
                    # Buscar números que puedan ser IDs (más de 1 dígito)
                    matches = re.findall(r'\b(\d{1,})\b', cliente_value_limpio)
                    if matches:
                        # Usar el número más largo encontrado (probablemente el ID)
                        id_candidato = max(matches, key=len)
                        data['cliente'] = int(id_candidato)
                    else:
                        # Si no hay números, intentar convertir directamente
                        try:
                            data['cliente'] = int(cliente_value_limpio)
                        except (ValueError, TypeError):
                            # Dejar que el campo valide y muestre el error apropiado
                            pass
            # Si ya es un número, asegurarse de que sea int
            elif isinstance(cliente_value, (int, float)):
                data['cliente'] = int(cliente_value)
        
        return super().to_internal_value(data)
    
    def __init__(self, *args, **kwargs):
        """
        # WARNING: v2.60: Establecer queryset dinámicamente para configuracion y cliente (SSoT).
        Los querysets se filtran por empresa del tenant para garantizar aislamiento de datos.
        """
        super().__init__(*args, **kwargs)
        # Establecer queryset para configuracion y cliente filtrando por empresa del tenant
        from apps.tenant.empresa.models import Empresa
        # ConfiguracionCotizacion ya está importado en la parte superior del archivo
        
        # # WARNING: Zero Trust: Obtener empresa del request si está disponible
        request = self.context.get('request')
        empresa = self.context.get('empresa')
        if not empresa and request:
            empresa = getattr(request, 'empresa', None)
        if not empresa and request:
            tenant = getattr(request, 'tenant', None)
            empresa = getattr(tenant, 'empresa', None)
        if not empresa:
            empresa = Empresa.objects.only('id').first()
        
        if empresa:
            # # WARNING: SSoT: Filtrar configuracion por empresa del tenant
            self.fields['configuracion'].queryset = ConfiguracionCotizacion.objects.filter(empresa=empresa)
            # # WARNING: SSoT: Filtrar cliente por empresa del tenant
            self.fields['cliente'].queryset = Cliente.objects.filter(empresa=empresa)
        else:
            self.fields['configuracion'].queryset = ConfiguracionCotizacion.objects.none()
            self.fields['cliente'].queryset = Cliente.objects.none()
    
    def validate_cliente(self, value):
        """
        # WARNING: FUERZA BRUTA ARQUITECTÓNICA: Validación resiliente del cliente con múltiples fallbacks.
        Este método se ejecuta después de que PrimaryKeyRelatedField valida que el ID existe
        y convierte el ID a objeto Cliente.
        
        # WARNING: Zero Trust: Validar que el cliente pertenezca a la empresa del usuario/tenant.
        """
        from apps.tenant.clientes.models import Cliente
        
        # PrimaryKeyRelatedField ya convirtió el ID en objeto Cliente
        if not isinstance(value, Cliente):
            # Dejar que DRF maneje el error de tipo si no es objeto
            return value
        
        # # WARNING: FUERZA BRUTA: Obtener empresa con fallback múltiple
        request = self.context.get('request')
        empresa = self.context.get('empresa') or getattr(request, 'empresa', None)
        if not empresa and request:
            tenant = getattr(request, 'tenant', None)
            empresa = getattr(tenant, 'empresa', None)
        
        # Fallback final: Obtener empresa del tenant (singleton)
        if not empresa:
            from apps.tenant.empresa.models import Empresa
            empresa = Empresa.objects.only('id').first()
        
        # Validación final: Si no existe empresa, error explícito
        if not empresa:
            raise serializers.ValidationError(
                _("No se pudo determinar la empresa del tenant actual.")
            )
        
        # # WARNING: Zero Trust: Validar SSoT - El cliente debe pertenecer al tenant actual
        if value.empresa_id != empresa.id:
            raise serializers.ValidationError(
                _("El cliente no pertenece a esta empresa (Seguridad Zero Trust).")
            )
        
        return value
    
    def validate(self, data):
        """
        Zero Trust: Valida que exista al menos una identificación del cliente.
        # WARNING: v2.60: Valida unicidad de numero_cotizacion por empresa y perfil.
        # WARNING: v2.60: Mapea porcentaje_aiu del frontend a los campos del modelo si se proporciona.
        """
        # # WARNING: v2.60: Mapear porcentaje_aiu del frontend a porcentaje_aiu_admin si se proporciona
        porcentaje_aiu = data.pop('porcentaje_aiu', None)
        if porcentaje_aiu is not None:
            # Si el frontend envía porcentaje_aiu, mapearlo a porcentaje_aiu_admin
            # Los otros campos (imprevistos, utilidad) se dejan en 0 por defecto
            if 'porcentaje_aiu_admin' not in data or data.get('porcentaje_aiu_admin') is None:
                data['porcentaje_aiu_admin'] = porcentaje_aiu
            if 'porcentaje_aiu_imprevistos' not in data:
                data['porcentaje_aiu_imprevistos'] = 0
            if 'porcentaje_aiu_utilidad' not in data:
                data['porcentaje_aiu_utilidad'] = 0
        
        # En actualización (PATCH), validamos solo si se están enviando estos campos
        if self.instance:
            # En actualización, validar unicidad solo si se cambia el número
            numero_cotizacion = data.get('numero_cotizacion')
            if numero_cotizacion and numero_cotizacion != self.instance.numero_cotizacion:
                empresa = self.instance.empresa
                configuracion = data.get('configuracion', self.instance.configuracion)
                
                if Cotizacion.objects.filter(
                    empresa=empresa,
                    configuracion=configuracion,
                    numero_cotizacion=numero_cotizacion
                ).exclude(pk=self.instance.pk).exists():
                    raise serializers.ValidationError({
                        "numero_cotizacion": _("Ya existe una cotización con este número para este perfil.")
                    })
            return data
            
        # # WARNING: FUERZA BRUTA ARQUITECTÓNICA: Confiar 100% en PrimaryKeyRelatedField para configuracion
        # El campo 'configuracion' ya está definido como PrimaryKeyRelatedField en la cabecera de la clase.
        # PrimaryKeyRelatedField se encarga automáticamente de:
        # 1. Convertir el ID (int o string) a objeto ConfiguracionCotizacion
        # 2. Validar que el perfil exista
        # 3. Validar que el perfil pertenezca al queryset (filtrado por empresa en __init__)
        # 
        # La validación adicional de empresa se hace en validate_configuracion() si existe.
        # NO intentar validar o convertir el perfil manualmente aquí.
        
        # # WARNING: FUERZA BRUTA ARQUITECTÓNICA: Confiar 100% en PrimaryKeyRelatedField
        # El campo 'cliente' ya está definido como PrimaryKeyRelatedField en la cabecera de la clase.
        # PrimaryKeyRelatedField se encarga automáticamente de:
        # 1. Convertir el ID (int o string) a objeto Cliente
        # 2. Validar que el cliente exista
        # 3. Validar que el cliente pertenezca al queryset (filtrado por empresa en __init__)
        # 
        # La validación adicional de empresa se hace en validate_cliente() que se ejecuta DESPUÉS.
        # NO intentar validar o convertir el cliente manualmente aquí.
        
        # # WARNING: v2.60: numero_cotizacion NO debe venir del frontend - se genera automáticamente al guardar
        # Si viene en el payload, eliminarlo (el backend lo generará automáticamente)
        if 'numero_cotizacion' in data:
            data.pop('numero_cotizacion')
        
        # # WARNING: v2.60: codigo_unico NO debe venir del frontend - se genera automáticamente al guardar
        # Si viene en el payload, eliminarlo (el backend lo generará automáticamente)
        if 'codigo_unico' in data:
            data.pop('codigo_unico')
        
        # # WARNING: v2.60: fecha_vencimiento NO debe venir del frontend - se calcula automáticamente desde dias_validez del perfil
        # Si viene en el payload, eliminarlo (el backend lo calculará automáticamente)
        if 'fecha_vencimiento' in data:
            data.pop('fecha_vencimiento')
        
        return data

    @transaction.atomic
    def create(self, validated_data):
        """
        # WARNING: REFACTORIZACIÓN v2.60: Creación transaccional atómica con Soberanía del Usuario.
        
        # WARNING: OBJETIVO 1: Transaccionalidad Atómica
        - Todo el proceso (cotización, items, cálculo de totales) se ejecuta en una sola transacción
        - Si cualquier paso falla, se revierte todo (incluyendo la numeración secuencial)
        - Esto previene desperdiciar folios en caso de error
        
        # WARNING: OBJETIVO 2: Soberanía del Usuario (User-Driven)
        - Los datos manuales del payload (IVA, AIU, Fecha Emisión) tienen prioridad absoluta
        - Los valores por defecto de la plantilla solo se usan si el usuario no proporciona datos
        - Garantiza que los datos digitados por el usuario NO sean ignorados ni sobreescritos
        
        # WARNING: SSoT v2.60: La empresa se extrae del tenant, nunca del payload.
        El campo 'empresa' está en read_only_fields para garantizar seguridad.
        
        # WARNING: v2.60: Los items se procesan junto con la cotización en una sola transacción.
        Los items se crean directamente usando CotizacionItem.objects.create() para mayor eficiencia.
        """
        # # WARNING: A. Obtener Empresa (SSoT) y contexto
        from apps.tenant.empresa.models import Empresa
        
        request = self.context.get('request')
        empresa = self.context.get('empresa')
        if not empresa and request:
            empresa = getattr(request, 'empresa', None)
        if not empresa and request:
            tenant = getattr(request, 'tenant', None)
            empresa = getattr(tenant, 'empresa', None)
        if not empresa:
            empresa = Empresa.objects.only('id').first()
        
        # Validación final: Si no existe empresa, error explícito
        if not empresa:
            raise serializers.ValidationError({
                'detail': _('No se encontró la empresa del tenant. Por favor, configure la empresa primero.')
            })
        
        payload = dict(validated_data)
        payload.pop('empresa', None)
        payload.pop('empresa_id', None)
        payload.pop('numero_cotizacion', None)
        payload.pop('codigo_unico', None)
        payload.pop('fecha_vencimiento', None)

        if not payload.get('configuracion'):
            raise serializers.ValidationError({
                'configuracion': _('Debe seleccionar un perfil de configuración para generar la numeración.')
            })

        return CotizacionService.crear_preforma(
            empresa=empresa,
            datos=payload,
        )

    @transaction.atomic
    def update(self, instance, validated_data):
        """
        # WARNING: FASE 3: Actualización transaccional atómica con sincronización de ítems.
        
        # WARNING: OBJETIVO 1: Transaccionalidad Atómica
        - Todo el proceso (actualización de cabecera, sincronización de items, cálculo de totales) se ejecuta en una sola transacción
        - Si cualquier paso falla, se revierte todo
        
        # WARNING: OBJETIVO 2: Sincronización de Ítems
        - Estrategia de reemplazo total: Borrar ítems antiguos y crear nuevos
        - Esto garantiza que no haya duplicados ni ítems huérfanos
        - Los ítems se recalculan usando el mismo patrón que en create()
        
        # WARNING: OBJETIVO 3: Soberanía del Usuario (User-Driven)
        - Los datos manuales del payload (IVA, AIU, Fecha Emisión) tienen prioridad absoluta
        - Los valores existentes se actualizan con los nuevos valores del payload
        """
        payload = dict(validated_data)
        payload.pop('numero_cotizacion', None)
        payload.pop('codigo_unico', None)
        payload.pop('fecha_vencimiento', None)
        payload.pop('empresa', None)
        payload.pop('empresa_id', None)

        return CotizacionService.actualizar_cotizacion(instance, payload)
