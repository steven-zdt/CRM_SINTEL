"""
Servicios de dominio para Cotizaciones (v2.60) - RESILIENTE
Única fuente de verdad para cálculos y lógica de negocio.
⚠️ Desacoplado: Funciona incluso si el módulo de clientes no está disponible.
"""
import logging
from decimal import Decimal
from django.db import transaction
from .models import Cotizacion, CotizacionItem
from .configuracion.models import ConfiguracionCotizacion

logger = logging.getLogger(__name__)

class CotizacionService:
    @staticmethod
    def calcular_linea(cantidad, costo, utilidad):
        """Cálculo estandarizado para Tabulator y Models."""
        cantidad = Decimal(str(cantidad or 0))
        costo = Decimal(str(costo or 0))
        utilidad = Decimal(str(utilidad or 0))
        
        factor_utilidad = Decimal('1.00') + (utilidad / Decimal('100.00'))
        precio_venta = costo * factor_utilidad
        subtotal = cantidad * precio_venta
        
        return {
            'precio_unitario': precio_venta.quantize(Decimal('0.01')),
            'subtotal': subtotal.quantize(Decimal('0.01'))
        }

    @classmethod
    @transaction.atomic
    def crear_preforma(cls, empresa, datos):
        """
        ⚠️ v2.60: Creación directa de cotización con arquitectura User-Driven.
        Crea únicamente la cabecera de la cotización. Los items se procesan en el serializer.
        
        ⚠️ v2.60: User-Driven Architecture:
        - El perfil solo provee: generación de códigos (prefijo, sufijo, semilla) y días de validez
        - Los valores financieros (IVA, AIU) vienen directamente del frontend (diccionario datos)
        - La fecha de vencimiento se calcula automáticamente desde dias_validez del perfil
        - El número de cotización se genera automáticamente usando bloqueos de fila (select_for_update)
        - ⚠️ CRÍTICO: Usa datos.get('campo', default) para priorizar valores del usuario
        
        ⚠️ IMPORTANTE: El perfil (configuracion) y cliente son obligatorios. El frontend valida esto.
        ⚠️ RESTRICCIÓN: Los items NO se procesan aquí - se manejan en el serializer usando
        CotizacionItem.objects.create() directamente (no serializer.save()) para evitar validaciones redundantes.
        
        Args:
            empresa: Instancia de Empresa (obtenida del tenant)
            datos: Diccionario con los datos de la cotización desde el frontend:
                - configuracion: ID del perfil de configuración (obligatorio)
                - cliente: ID del cliente (obligatorio)
                - tipo_cotizacion: Tipo de cotización (opcional, default: 'MIXTO')
                - iva_porcentaje: Porcentaje de IVA (opcional, default: 19.00) - User-Driven
                - porcentaje_aiu_admin: Porcentaje AIU Administración (opcional, default: 0.00) - User-Driven
                - porcentaje_aiu_imprevistos: Porcentaje AIU Imprevistos (opcional, default: 0.00) - User-Driven
                - porcentaje_aiu_utilidad: Porcentaje AIU Utilidad (opcional, default: 0.00) - User-Driven
                - fecha_emision: Fecha de emisión (opcional) - User-Driven
                - items: Lista de items de la cotización (opcional, se procesa en el serializer)
        
        Returns:
            Cotizacion: Instancia de cotización creada con estado 'BORRADOR' (sin items)
        """
        # ⚠️ FUERZA BRUTA ARQUITECTÓNICA: Aceptar objeto ConfiguracionCotizacion directamente del serializer
        plantilla_value = datos.get('configuracion')
        
        # ⚠️ v2.60: El perfil es obligatorio
        if not plantilla_value:
            logger.error("⚠️ No se proporcionó un perfil de configuración. El perfil es obligatorio.")
            raise ValueError("Debe seleccionar un perfil de configuración para crear la cotización.")
        
        # ⚠️ FUERZA BRUTA: El serializer ya convierte el ID a objeto ConfiguracionCotizacion antes de llegar aquí
        # Si viene como objeto (caso más común), validarlo. Si viene como ID, convertirlo a objeto.
        # ConfiguracionCotizacion ya está importado en la parte superior del archivo
        
        # Caso 1: Ya es un objeto ConfiguracionCotizacion (viene del serializer después de validación)
        if isinstance(plantilla_value, ConfiguracionCotizacion):
            # Validar que pertenezca a la empresa
            if plantilla_value.empresa != empresa:
                logger.error(f"⚠️ Perfil {plantilla_value.id} no pertenece a la empresa {empresa.id}")
                raise ValueError(f"El perfil de configuración seleccionado no pertenece a esta empresa.")
            plantilla = plantilla_value
            logger.info(f"✅ Perfil recibido como objeto: {plantilla.nombre_configuracion} (ID: {plantilla.id})")
        # Caso 2: Viene como ID (int o string) - convertir a objeto
        elif isinstance(plantilla_value, (int, str)):
            try:
                # Convertir a int si es string
                plantilla_id = int(plantilla_value) if isinstance(plantilla_value, str) else plantilla_value
                plantilla = ConfiguracionCotizacion.objects.get(id=plantilla_id, empresa=empresa)
                logger.info(f"✅ Perfil encontrado: {plantilla.nombre_configuracion} (ID: {plantilla_id})")
            except ConfiguracionCotizacion.DoesNotExist:
                logger.error(f"⚠️ Perfil con ID {plantilla_value} no encontrado para empresa {empresa.id}")
                # Verificar si existe pero pertenece a otra empresa
                if ConfiguracionCotizacion.objects.filter(id=plantilla_id).exists():
                    raise ValueError(f"Perfil de configuración con ID {plantilla_id} existe pero no pertenece a esta empresa.")
                else:
                    raise ValueError(f"Perfil de configuración con ID {plantilla_id} no encontrado.")
            except (ValueError, TypeError) as e:
                logger.error(f"⚠️ Error al procesar ID de perfil {plantilla_value}: {e}")
                raise ValueError(f"ID de perfil inválido: {plantilla_value}. Error: {str(e)}")
        # Caso 3: Tipo no soportado
        else:
            raise ValueError(f"Tipo de perfil no soportado: {type(plantilla_value).__name__}. Se espera ConfiguracionCotizacion, int o str.")
        
        # ⚠️ FASE 3: Cliente de BD es obligatorio - Aceptar objeto Cliente directamente del serializer
        cliente = datos.get('cliente')
        
        # ⚠️ CRÍTICO: Cliente de BD es obligatorio
        if not cliente:
            raise ValueError("Debe proporcionar un cliente de la base de datos. El campo cliente es obligatorio.")
        
        # ⚠️ FASE 3: El serializer ya convierte el ID a objeto Cliente antes de llegar aquí
        # Si viene como ID (int o string), convertirlo a objeto. Si ya es objeto, validarlo.
        from apps.tenant.clientes.models import Cliente
        
        # Caso 1: Ya es un objeto Cliente (viene del serializer después de validación)
        if isinstance(cliente, Cliente):
            # Validar que pertenezca a la empresa
            if cliente.empresa != empresa:
                logger.error(f"⚠️ Cliente {cliente.id} no pertenece a la empresa {empresa.id}")
                raise ValueError(f"El cliente seleccionado no pertenece a esta empresa.")
            logger.info(f"✅ Cliente recibido como objeto: {cliente.razon_social} (ID: {cliente.id})")
        # Caso 2: Viene como ID (int o string) - convertir a objeto
        elif isinstance(cliente, (int, str)):
            try:
                # Convertir a int si es string
                cliente_id = int(cliente) if isinstance(cliente, str) else cliente
                cliente_obj = Cliente.objects.get(id=cliente_id, empresa=empresa)
                cliente = cliente_obj
                logger.info(f"✅ Cliente encontrado: {cliente_obj.razon_social} (ID: {cliente_obj.id})")
            except Cliente.DoesNotExist:
                logger.error(f"⚠️ Cliente con ID {cliente} no encontrado para empresa {empresa.id}")
                # Verificar si existe pero pertenece a otra empresa
                if Cliente.objects.filter(id=cliente_id).exists():
                    raise ValueError(f"Cliente con ID {cliente_id} existe pero no pertenece a esta empresa.")
                else:
                    raise ValueError(f"Cliente con ID {cliente_id} no encontrado.")
            except (ValueError, TypeError) as e:
                logger.error(f"⚠️ Error al procesar ID de cliente {cliente}: {e}")
                raise ValueError(f"ID de cliente inválido: {cliente}. Error: {str(e)}")
        # Caso 3: Tipo no soportado
        else:
            raise ValueError(f"Tipo de cliente no soportado: {type(cliente).__name__}. Se espera Cliente, int o str.")
        
        # ⚠️ v2.60: User-Driven - Los valores financieros vienen del frontend, no del perfil
        # El perfil solo provee: generación de códigos y días de validez
        
        # 1. Generación de Código Seguro (Zero Trust)
        # ⚠️ AQUI OCURRE LA MAGIA: Generamos el código bloqueando la BD
        # ⚠️ CRÍTICO: Esto debe ocurrir JUSTO ANTES de crear el objeto Cotizacion
        # para garantizar que el número se asigna en el momento exacto de guardar
        # y que si la creación falla, el número se revierte (rollback)
        perfil_id = plantilla.id if hasattr(plantilla, 'id') else plantilla
        
        # ⚠️ v2.60: generar_codigo_unico() retorna (codigo_final, siguiente_numero)
        # Este método bloquea la fila del perfil usando select_for_update() para evitar race conditions
        codigo_generado, numero_secuencia = cls.generar_codigo_unico(perfil_id, empresa.id)
        
        logger.info(f"📝 Código único generado automáticamente desde perfil '{plantilla.nombre_configuracion}': {codigo_generado} (número secuencial: {numero_secuencia})")
        
        # 2. Cálculo de Fecha de Vencimiento Automática
        # ⚠️ v2.60: La fecha de vencimiento se calcula SIEMPRE desde dias_validez del perfil
        # El frontend NO debe enviar fecha_vencimiento (se ignora si viene)
        from datetime import timedelta
        from django.utils import timezone
        
        dias_validez = getattr(plantilla, 'dias_validez', 15)
        fecha_calculada = timezone.now().date() + timedelta(days=dias_validez)
        logger.info(f"📅 Fecha de vencimiento calculada automáticamente: {fecha_calculada} (días de validez: {dias_validez})")
        
        # ⚠️ FASE 3: Validación final Zero Trust - El cliente ya fue validado arriba
        # Si llegamos aquí, el cliente es válido y pertenece a la empresa
        # No necesitamos validar de nuevo porque ya lo hicimos en los casos anteriores
        
        # 3. Creación de la cotización usando los datos financieros inyectados por el usuario
        # ⚠️ v2.60: Los valores financieros (IVA, AIU) vienen directamente del diccionario datos del frontend
        # El perfil ya NO contiene datos financieros, solo provee generación de códigos y días de validez
        # ⚠️ PASO 2: Los valores se priorizan directamente en la creación del objeto (ver abajo)
        
        # ⚠️ FUERZA BRUTA ARQUITECTÓNICA: Obtener fecha_emision del usuario si fue proporcionada
        # Si no viene, usar la fecha actual (comportamiento por defecto del modelo con auto_now_add)
        fecha_emision = datos.get('fecha_emision')
        if fecha_emision:
            # Si viene como string, convertir a date
            if isinstance(fecha_emision, str):
                from datetime import datetime
                try:
                    fecha_emision = datetime.strptime(fecha_emision, '%Y-%m-%d').date()
                except ValueError:
                    logger.warning(f"⚠️ Formato de fecha_emision inválido: {fecha_emision}. Usando fecha actual.")
                    fecha_emision = None
        
        # ⚠️ PASO 3: Sincronización User-Driven - Priorizar datos del usuario sobre valores por defecto
        # ⚠️ CRÍTICO: Usar datos.get('campo', default) para permitir que los valores del usuario tengan prioridad
        # Si el usuario no proporciona un valor, usar valores por defecto estándar
        # Nota: El modelo ConfiguracionCotizacion v2.60 ya NO tiene campos *_default (modo User-Driven)
        # Los items NO se procesan aquí - se manejan en el serializer usando CotizacionItem.objects.create()
        
        # ⚠️ PASO 3: Obtener valores con prioridad: Usuario -> Default
        # ⚠️ CRÍTICO: datos.get() garantiza que si el usuario envía un valor, se usa ese valor
        # Si no viene en el payload, se usa el valor por defecto especificado
        tipo_cotizacion = datos.get('tipo_cotizacion', 'MIXTO')
        iva_porcentaje = datos.get('iva_porcentaje', Decimal('19.00'))
        porcentaje_aiu_admin = datos.get('porcentaje_aiu_admin', Decimal('0.00'))
        porcentaje_aiu_imprevistos = datos.get('porcentaje_aiu_imprevistos', Decimal('0.00'))
        porcentaje_aiu_utilidad = datos.get('porcentaje_aiu_utilidad', Decimal('0.00'))
        
        # ⚠️ PASO 3: Logging para verificar qué valores se están usando (User-Driven)
        logger.info(f"📋 Valores financieros (User-Driven) - Tipo: {tipo_cotizacion}, IVA: {iva_porcentaje}, AIU Admin: {porcentaje_aiu_admin}, AIU Imprevistos: {porcentaje_aiu_imprevistos}, AIU Utilidad: {porcentaje_aiu_utilidad}")
        
        # ⚠️ PASO 3: Crear la cotización con todos los datos del usuario (User-Driven)
        # ⚠️ CRÍTICO: Prioridad: 1. Payload del Usuario -> 2. Valores por defecto estándar
        # Los valores financieros ya fueron obtenidos usando datos.get() arriba
        # ⚠️ NOTA: Los items NO se procesan aquí - se manejan en el serializer padre
        # El serializer usa CotizacionItem.objects.create() directamente (no serializer.save())
        cotizacion = Cotizacion.objects.create(
            empresa=empresa,
            cliente=cliente,
            configuracion=plantilla,  # Referencia al perfil (obligatorio para numeración)
            numero_cotizacion=str(numero_secuencia),  # ⚠️ Guardamos el número puro (ej: "1", "2", "422")
            codigo_unico=codigo_generado,  # ⚠️ Guardamos el string completo (ej: "STS. 0001-2026")
            fecha_vencimiento=fecha_calculada,  # ⚠️ Siempre calculada desde dias_validez del perfil
            # ⚠️ PASO 3: Valores del usuario (obtenidos con datos.get() arriba)
            tipo_cotizacion=tipo_cotizacion,
            # ⚠️ PASO 3: Valores financieros del usuario (obtenidos con datos.get() arriba)
            iva_porcentaje=iva_porcentaje,
            porcentaje_aiu_admin=porcentaje_aiu_admin,
            porcentaje_aiu_imprevistos=porcentaje_aiu_imprevistos,
            porcentaje_aiu_utilidad=porcentaje_aiu_utilidad,
            estado='BORRADOR'  # ⚠️ Estado inicial por defecto
        )
        
        # ⚠️ FUERZA BRUTA: Si el usuario proporcionó fecha_emision, actualizarla después de crear
        # Esto es necesario porque auto_now_add=True no permite establecer la fecha en create()
        if fecha_emision:
            cotizacion.fecha_emision = fecha_emision
            cotizacion.save(update_fields=['fecha_emision'])
            logger.info(f"📅 Fecha de emisión establecida por el usuario: {fecha_emision}")
        
        logger.info(f"✅ Cotización creada con perfil '{plantilla.nombre_configuracion}' (Número: {numero_secuencia}, Código Único: {codigo_generado}, Fecha Vencimiento: {fecha_calculada})")
        return cotizacion
    
    @classmethod
    def generar_codigo_unico(cls, perfil_id, empresa_id):
        """
        ⚠️ v2.60: Genera el siguiente número de la secuencia bloqueando la fila en BD
        para evitar condiciones de carrera. Debe llamarse dentro de una transacción.
        
        ⚠️ CRÍTICO: Este método debe ser llamado DENTRO de una transacción (@transaction.atomic)
        para garantizar que el bloqueo de fila funcione correctamente y que si la cotización
        falla al guardarse, el número no se desperdicie (rollback).
        
        Lógica:
        1. Bloquea la fila del perfil usando select_for_update()
        2. Calcula el siguiente número (semilla_inicial si es la primera, ultimo_numero + 1 si ya existen)
        3. Actualiza ultimo_numero en la base de datos
        4. Formatea el número (mínimo 4 dígitos)
        5. Construye el código final: prefijo + numero_formateado + sufijo
        
        Args:
            perfil_id: ID del perfil de configuración
            empresa_id: ID de la empresa (para validación SSoT)
            
        Returns:
            tuple: (codigo_final: str, siguiente_numero: int)
                - codigo_final: Código único generado (ej. "STS. 0422-2026")
                - siguiente_numero: Número secuencial usado (para logging)
        """
        from django.db import transaction
        from apps.tenant.cotizaciones.configuracion.models import ConfiguracionCotizacion
        
        # ⚠️ CRÍTICO: Validar que estamos dentro de una transacción
        # Si no estamos en una transacción, select_for_update() no funcionará correctamente
        if not transaction.get_connection().in_atomic_block:
            logger.warning(f"⚠️ generar_codigo_unico llamado fuera de una transacción. Esto puede causar race conditions.")
        
        # 1. Obtenemos y bloqueamos la fila de la configuración para este tenant
        # ⚠️ CRÍTICO: select_for_update() bloquea la fila hasta que la transacción se complete
        # Esto previene que múltiples requests simultáneos generen el mismo número
        try:
            perfil = ConfiguracionCotizacion.objects.select_for_update().get(
                id=perfil_id, 
                empresa_id=empresa_id
            )
        except ConfiguracionCotizacion.DoesNotExist:
            logger.error(f"⚠️ Perfil {perfil_id} no encontrado para empresa {empresa_id}")
            raise ValueError(f"Perfil de configuración con ID {perfil_id} no encontrado para esta empresa.")
        
        # 2. Calcular el siguiente número
        if perfil.ultimo_numero == 0 or perfil.ultimo_numero is None:
            siguiente_numero = perfil.semilla_inicial
            logger.info(f"📝 Primera cotización del perfil '{perfil.nombre_configuracion}': usando semilla_inicial={siguiente_numero}")
        else:
            siguiente_numero = perfil.ultimo_numero + 1
            logger.info(f"📝 Cotización #{siguiente_numero} del perfil '{perfil.nombre_configuracion}': incrementado desde {perfil.ultimo_numero}")
        
        # 3. Formatear el número (ej: 0001, 0002) - mínimo 4 dígitos
        numero_formateado = f"{siguiente_numero:04d}"
        
        # 4. Construir el código final
        prefijo = perfil.prefijo_secuencia or ''
        sufijo = perfil.sufijo_secuencia or ''
        codigo_final = f"{prefijo}{numero_formateado}{sufijo}".strip()
        
        # 5. Actualizar el último número en la base de datos
        # ⚠️ CRÍTICO: Esta actualización ocurre dentro de la misma transacción que bloqueó la fila
        # Si la cotización falla al guardarse, esta actualización también se revertirá (rollback)
        perfil.ultimo_numero = siguiente_numero
        perfil.save(update_fields=['ultimo_numero'])
        
        logger.info(f"📝 Código único generado para perfil '{perfil.nombre_configuracion}': {codigo_final} (número: {siguiente_numero})")
        
        return codigo_final, siguiente_numero
    
    @staticmethod
    def _generar_numero_cotizacion(plantilla):
        """
        ⚠️ DEPRECATED v2.60: Usar generar_codigo_unico() en su lugar.
        Mantenido para compatibilidad temporal.
        
        ⚠️ NOTA: generar_codigo_unico() ahora retorna (codigo_final, siguiente_numero).
        Este método retorna solo el código para mantener compatibilidad.
        """
        codigo_unico, _ = CotizacionService.generar_codigo_unico(plantilla.id, plantilla.empresa_id)
        return codigo_unico

    @staticmethod
    def calcular_totales(cotizacion_id):
        """
        ⚠️ v2.60: Calcula todos los totales de una cotización (SSoT).
        
        Lógica:
        1. Suma subtotales de todos los items
        2. Aplica descuentos (si existen)
        3. Calcula IVA sobre el subtotal
        4. Calcula AIU (si está activo) según porcentajes heredados del perfil
        5. Calcula total final con impuestos
        
        ⚠️ CRÍTICO: Esta es la única fuente de verdad para cálculos financieros.
        No debe haber lógica de cálculos en serializers ni viewsets.
        
        Args:
            cotizacion_id: ID de la cotización a calcular
            
        Returns:
            dict: Diccionario con subtotal, iva, aiu_total, total_con_impuestos
        """
        # ⚠️ FASE 2: Asegurar que la consulta sume los subtotal_linea de los ítems creados
        try:
            cotizacion = Cotizacion.objects.select_related('configuracion').prefetch_related('items').get(id=cotizacion_id)
        except Cotizacion.DoesNotExist:
            logger.error(f"⚠️ Cotización {cotizacion_id} no encontrada")
            raise ValueError(f"Cotización con ID {cotizacion_id} no encontrada.")
        
        # ⚠️ FASE 2: Obtener items y asegurar que se sumen correctamente los subtotal_linea
        items = cotizacion.items.all()
        
        # ⚠️ FASE 2: Calcular subtotal sumando todos los items
        # ⚠️ CRÍTICO: Asegurar que item.subtotal_linea sea un Decimal válido
        subtotal = Decimal('0.00')
        for item in items:
            # ⚠️ FASE 2: Validar que subtotal_linea sea un número válido
            item_subtotal = item.subtotal_linea
            if item_subtotal is None:
                logger.warning(f"⚠️ Item {item.id} tiene subtotal_linea=None, usando 0.00")
                item_subtotal = Decimal('0.00')
            elif not isinstance(item_subtotal, Decimal):
                # Convertir a Decimal si viene como float o string
                try:
                    item_subtotal = Decimal(str(item_subtotal))
                except (ValueError, TypeError):
                    logger.warning(f"⚠️ Item {item.id} tiene subtotal_linea inválido: {item_subtotal}, usando 0.00")
                    item_subtotal = Decimal('0.00')
            
            subtotal += item_subtotal
            logger.debug(f"📊 Item {item.id}: subtotal_linea={item_subtotal}, acumulado={subtotal}")
        
        logger.info(f"📊 Subtotal calculado para cotización {cotizacion_id}: {subtotal} (items: {items.count()})")
        
        # 2. Aplicar descuentos (si existen en el futuro)
        # Por ahora, no hay campo de descuento en el modelo
        subtotal_descuentos = subtotal
        
        # 3. Calcular IVA sobre el subtotal
        iva_porcentaje = cotizacion.iva_porcentaje or Decimal('0.00')
        iva = subtotal_descuentos * (iva_porcentaje / Decimal('100.00'))
        
        # 4. Calcular AIU (si está activo)
        # ⚠️ v2.60: User-Driven - AIU viene del frontend, no del perfil
        # Verificar si hay valores de AIU en la cotización (vienen del frontend)
        aiu_total = Decimal('0.00')
        usa_aiu = (
            (cotizacion.porcentaje_aiu_admin or Decimal('0.00')) > 0 or
            (cotizacion.porcentaje_aiu_imprevistos or Decimal('0.00')) > 0 or
            (cotizacion.porcentaje_aiu_utilidad or Decimal('0.00')) > 0
        )
        
        if usa_aiu:
            aiu_admin = cotizacion.porcentaje_aiu_admin or Decimal('0.00')
            aiu_imprevistos = cotizacion.porcentaje_aiu_imprevistos or Decimal('0.00')
            aiu_utilidad = cotizacion.porcentaje_aiu_utilidad or Decimal('0.00')
            
            # Calcular cada componente del AIU
            aiu_admin_valor = subtotal_descuentos * (aiu_admin / Decimal('100.00'))
            aiu_imprevistos_valor = subtotal_descuentos * (aiu_imprevistos / Decimal('100.00'))
            aiu_utilidad_valor = subtotal_descuentos * (aiu_utilidad / Decimal('100.00'))
            
            aiu_total = aiu_admin_valor + aiu_imprevistos_valor + aiu_utilidad_valor
            logger.info(f"📊 AIU calculado para cotización {cotizacion_id}: Admin={aiu_admin_valor}, Imprevistos={aiu_imprevistos_valor}, Utilidad={aiu_utilidad_valor}, Total={aiu_total}")
        
        # 5. Calcular total final: subtotal + AIU + IVA
        # ⚠️ v2.60: El IVA se calcula sobre (subtotal + AIU)
        base_para_iva = subtotal_descuentos + aiu_total
        iva_correcto = base_para_iva * (iva_porcentaje / Decimal('100.00'))
        total_con_impuestos = base_para_iva + iva_correcto
        
        # Redondear todos los valores a 2 decimales
        subtotal = subtotal.quantize(Decimal('0.01'))
        iva_correcto = iva_correcto.quantize(Decimal('0.01'))
        aiu_total = aiu_total.quantize(Decimal('0.01'))
        total_con_impuestos = total_con_impuestos.quantize(Decimal('0.01'))
        
        # ⚠️ FASE 2: Aplicar lógica financiera User-Driven (IVA y AIU)
        # Actualizar la cotización con el total calculado
        cotizacion.total_con_impuestos = total_con_impuestos
        cotizacion.save(update_fields=['total_con_impuestos'])
        
        logger.info(f"📊 Totales calculados para cotización {cotizacion_id}: Subtotal={subtotal}, AIU={aiu_total}, IVA={iva_correcto}, Total={total_con_impuestos}")
        
        return {
            'subtotal': subtotal,
            'iva': iva_correcto,
            'aiu_total': aiu_total,
            'total_con_impuestos': total_con_impuestos
        }
    
    @staticmethod
    def recalcular_totales(cotizacion):
        """
        ⚠️ DEPRECATED v2.60: Usar calcular_totales(cotizacion_id) en su lugar.
        Mantenido para compatibilidad temporal.
        """
        if isinstance(cotizacion, Cotizacion):
            return CotizacionService.calcular_totales(cotizacion.id)
        else:
            return CotizacionService.calcular_totales(cotizacion)
    
    @staticmethod
    def get_editor_config(perfil_id, empresa_id):
        """
        ⚠️ v2.60: Obtiene la configuración simplificada del editor desde el Service (SSoT).
        
        ⚠️ User-Driven: El perfil solo provee:
        - Días de validez (para calcular fecha de vencimiento)
        - Configuración de generación de códigos (prefijo, sufijo, semilla)
        
        Los valores financieros (IVA, AIU) vienen del frontend, no del perfil.
        
        Args:
            perfil_id: ID del perfil de configuración
            empresa_id: ID de la empresa (para validación SSoT)
            
        Returns:
            dict: Configuración simplificada del editor con:
                - dias_validez: Días de validez de la cotización (1 a 30)
                - prefijo_secuencia: Prefijo para numeración
                - sufijo_secuencia: Sufijo para numeración
                - semilla_inicial: Semilla inicial para numeración
        """
        try:
            plantilla = ConfiguracionCotizacion.objects.get(id=perfil_id, empresa_id=empresa_id)
        except ConfiguracionCotizacion.DoesNotExist:
            logger.error(f"⚠️ Perfil {perfil_id} no encontrado para empresa {empresa_id}")
            raise ValueError(f"Perfil de configuración con ID {perfil_id} no encontrado para esta empresa.")
        
        # ⚠️ v2.60: User-Driven - Solo enviar datos esenciales del perfil
        config = {
            'dias_validez': plantilla.dias_validez,
            'prefijo_secuencia': plantilla.prefijo_secuencia or '',
            'sufijo_secuencia': plantilla.sufijo_secuencia or '',
            'semilla_inicial': plantilla.semilla_inicial or 1
        }
        
        logger.info(f"📋 Configuración de editor obtenida para perfil '{plantilla.nombre_configuracion}': {config}")
        return config
