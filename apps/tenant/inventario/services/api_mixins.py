"""
API Mixins para Inventario - Inyeccion de servicios en ViewSets.

[ARQ-C2] Extraido de business_service.py: los Service Mixins deben vivir en su
propio archivo (services/api_mixins.py), igual que en el resto de apps tenant
(ver p.ej. apps/tenant/gastos/services/api_mixins.py). business_service.py
conserva unicamente logica de negocio (KardexService y las funciones de
calculo/registro de stock); este archivo solo inyecta esos servicios en los
ViewSets via herencia.

Reglas (heredadas de business_service.py, sin cambios de comportamiento):
- PROHIBIDO queries directas en Mixins sin pasar por selectors.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.tenant.inventario.models import (
    ActivoFijo,
    CategoriaItem,
    HistorialServicio,
    MovimientoInventario,
    Producto,
    Servicio,
)
from apps.tenant.inventario.services.selectors import (
    ActivoFijoSelector,
    CategoriaItemSelector,
    MovimientoInventarioSelector,
    ProductoSelector,
    ServicioSelector,
)
from apps.tenant.inventario.services.business_service import (
    KardexService,
    ajustar_stock,
)


class CategoriaItemServiceMixin:
    """Mixin para inyectar logica de negocio de Categorias en ViewSets."""

    def service_categoria_destroy(self, instance):
        """Elimina la categoria desvinculando items relacionados (set NULL)."""
        with transaction.atomic():
            Producto.objects.filter(empresa_id=instance.empresa_id, categoria=instance).update(categoria=None)
            Servicio.objects.filter(empresa_id=instance.empresa_id, categoria=instance).update(categoria=None)
            ActivoFijo.objects.filter(empresa_id=instance.empresa_id, categoria=instance).update(categoria=None)
            instance.delete()
        return True

    def service_categoria_get_resumen(self, instance):
        """Retorna conteo de items asociados a la categoria."""
        conteo_productos = Producto.objects.filter(
            empresa_id=instance.empresa_id, categoria=instance
        ).only('id').count()
        conteo_servicios = Servicio.objects.filter(
            empresa_id=instance.empresa_id, categoria=instance
        ).only('id').count()
        conteo_activos = ActivoFijo.objects.filter(
            empresa_id=instance.empresa_id, categoria=instance
        ).only('id').count()
        return {
            "id": instance.id,
            "nombre": instance.nombre,
            "activo": instance.activo,
            "conteo_productos": conteo_productos,
            "conteo_servicios": conteo_servicios,
            "conteo_activos": conteo_activos,
            "total_items": conteo_productos + conteo_servicios + conteo_activos,
        }

    def service_categoria_get_offcanvas_context(self, empresa, id_instancia=None):
        """Contexto para formulario de categoria (HTMX Offcanvas)."""
        categoria = None
        if id_instancia:
            categoria = CategoriaItemSelector.get_detail(empresa_id=empresa.id, categoria_uuid=id_instancia)
        return {
            'categoria': categoria,
            'empresa': empresa,
            'aplicaciones': CategoriaItem.Aplicacion.choices,
        }


class ProductoServiceMixin:
    """Mixin para inyectar logica de negocio de Productos en ViewSets."""

    def service_producto_destroy(self, instance):
        """Validacion de seguridad: no se eliminan productos activos."""
        if instance.activo:
            raise ValidationError(
                "No se puede eliminar un item activo. Cambielo a 'Inactivo' antes de borrar."
            )
        with transaction.atomic():
            instance.delete()
        return True

    def service_producto_ajustar_stock(self, producto_id, empresa_id, cantidad, observaciones):
        """Wrapper para ajustar stock desde el ViewSet."""
        return ajustar_stock(producto_id, empresa_id, cantidad, observaciones)

    def service_producto_get_stock(self, empresa, pk):
        """Retorna solo campos de stock (id, nombre, stock_actual)."""
        producto = (
            Producto.objects
            .filter(empresa=empresa, uuid=pk)
            .only('id', 'uuid', 'nombre', 'stock_actual')
            .first()
        )
        if not producto:
            from rest_framework.exceptions import NotFound
            raise NotFound('Producto no encontrado')
        return producto

    def service_producto_get_kardex(self, empresa, pk):
        """Obtiene producto y sus movimientos de Kardex optimizados."""
        producto = (
            Producto.objects
            .filter(empresa=empresa, uuid=pk)
            .only('id', 'uuid', 'codigo', 'nombre', 'stock_actual')
            .first()
        )
        if not producto:
            from rest_framework.exceptions import NotFound
            raise NotFound('Producto no encontrado')

        movimientos = MovimientoInventarioSelector.get_kardex_for_producto(empresa.id, producto.id)
        return producto, movimientos

    def service_producto_get_offcanvas_context(self, empresa, id_instancia=None, tipo_formulario='producto'):
        """Centraliza la carga de datos para formularios HTMX de productos."""
        producto = None
        if id_instancia:
            producto = ProductoSelector.get_detail(empresa_id=empresa.id, producto_uuid=id_instancia)

        categorias = (
            CategoriaItem.objects
            .filter(empresa_id=empresa.id, activo=True)
            .only('id', 'nombre', 'aplicacion')
            .order_by('nombre')[:100]
        )

        tipos_movimiento = []
        if tipo_formulario == 'ajuste':
            tipos_movimiento = MovimientoInventario.TipoMovimiento.choices

        return {
            'producto': producto,
            'categorias': categorias,
            'tipo_formulario': tipo_formulario,
            'empresa': empresa,
            'tipos_movimiento': tipos_movimiento,
        }


class ServicioServiceMixin:
    """Mixin para inyectar logica de negocio de Servicios en ViewSets."""

    def service_servicio_destroy(self, instance):
        """Validacion de seguridad: no se eliminan servicios activos."""
        if instance.activo:
            raise ValidationError(
                "No se puede eliminar un servicio activo. Cambielo a 'Inactivo' antes de borrar."
            )
        with transaction.atomic():
            instance.delete()
        return True

    def service_servicio_get_offcanvas_context(self, empresa, id_instancia=None):
        """Centraliza la carga de datos para formularios HTMX de servicios."""
        servicio = None
        if id_instancia:
            servicio = ServicioSelector.get_detail(empresa_id=empresa.id, servicio_uuid=id_instancia)

        categorias = (
            CategoriaItem.objects
            .filter(
                empresa_id=empresa.id,
                activo=True,
                aplicacion__in=[CategoriaItem.Aplicacion.SERVICIO, CategoriaItem.Aplicacion.TODO]
            )
            .only('id', 'nombre', 'aplicacion')
            .order_by('nombre')[:100]
        )
        return {
            'servicio': servicio,
            'categorias': categorias,
            'empresa': empresa,
        }

    def service_servicio_get_historial_context(self, empresa):
        """Contexto para el formulario de historial de servicio."""
        return {'empresa': empresa}


class ActivoFijoServiceMixin:
    """Mixin para inyectar logica de negocio de Activos Fijos en ViewSets."""

    def service_activo_destroy(self, instance):
        """Elimina el activo fijo."""
        instance.delete()
        return True

    def service_activo_list_all(self, empresa):
        """QuerySet optimizado para DataTables ajax directo."""
        return ActivoFijoSelector.get_list(empresa_id=empresa.id).order_by('nombre')

    def service_activo_get_offcanvas_context(self, empresa, id_instancia=None):
        """Contexto para formulario de activo fijo (HTMX Offcanvas)."""
        activo = None
        if id_instancia:
            activo = ActivoFijoSelector.get_detail(empresa_id=empresa.id, activo_uuid=id_instancia)

        categorias = (
            CategoriaItem.objects
            .filter(
                empresa_id=empresa.id,
                activo=True,
                aplicacion__in=[CategoriaItem.Aplicacion.ACTIVO, CategoriaItem.Aplicacion.TODO]
            )
            .only('id', 'nombre', 'aplicacion')
            .order_by('nombre')[:100]
        )
        return {
            'activo': activo,
            'categorias': categorias,
            'empresa': empresa,
        }


class MovimientoServiceMixin:
    """Mixin para logica de Movimientos de Inventario (Kardex)."""

    def service_movimiento_perform_create(self, serializer, empresa):
        """Guarda el movimiento y recalcula stock atomicamente (v3.8.1: soporta Activo Fijo)."""
        data = serializer.validated_data
        producto = data.get('producto')
        activo_fijo = data.get('activo_fijo')

        if producto:
            movimiento = KardexService.registrar_movimiento(
                empresa_id=empresa.id,
                producto_id=producto.id,
                tipo=data['tipo'],
                cantidad=data['cantidad'],
                costo_unitario=data.get('costo_unitario') or Decimal('0'),
                origen_referencia=data.get('origen_referencia'),
                cliente_referencia=data.get('cliente_referencia'),
                observaciones=data.get('observaciones'),
            )
        elif activo_fijo:
            movimiento = KardexService.registrar_movimiento_activo(
                empresa_id=empresa.id,
                activo_fijo_id=activo_fijo.id,
                tipo=data['tipo'],
                costo_unitario=data.get('costo_unitario') or Decimal('0'),
                origen_referencia=data.get('origen_referencia'),
                cliente_referencia=data.get('cliente_referencia'),
                observaciones=data.get('observaciones'),
            )
        else:
            raise ValidationError("Debe especificar un Producto o un Activo Fijo.")

        serializer.instance = movimiento
        return movimiento

    def service_movimiento_perform_update(self, instance, validated_data, empresa):
        """Actualiza movimiento delegando recalculo atomico a KardexService."""
        return KardexService.actualizar_movimiento(
            movimiento=instance,
            empresa_id=empresa.id,
            nueva_cantidad=validated_data.get('cantidad'),
            nuevo_tipo=validated_data.get('tipo'),
            nuevo_costo=validated_data.get('costo_unitario'),
            nuevo_origen=validated_data.get('origen_referencia'),
            nuevas_observaciones=validated_data.get('observaciones'),
        )

    def service_movimiento_perform_destroy(self, instance, empresa):
        """Elimina movimiento delegando recalculo atomico a KardexService."""
        KardexService.eliminar_movimiento(movimiento=instance, empresa_id=empresa.id)

    def service_movimiento_get_offcanvas_context(self, empresa, id_instancia=None):
        """Contexto para formulario de registro/edicion de movimiento (Kardex)."""
        movimiento = None
        if id_instancia:
            from apps.tenant.inventario.services.selectors import MovimientoInventarioSelector
            try:
                movimiento = MovimientoInventarioSelector.get_detail(
                    empresa_id=empresa.id,
                    movimiento_uuid=id_instancia
                )
            except MovimientoInventario.DoesNotExist:
                movimiento = None
        return {
            'movimiento': movimiento,
            'tipos': MovimientoInventario.TipoMovimiento.choices,
            'empresa': empresa,
        }


class HistorialServiceMixin:
    """Mixin para logica de Historial de Servicios."""

    def service_historial_get_queryset(self, empresa):
        """QuerySet optimizado con select_related y campos explicitos."""
        return (
            HistorialServicio.objects
            .select_related('servicio')
            .filter(empresa=empresa)
            .only(
                'id', 'uuid', 'fecha_registro', 'cantidad', 'valor_cobrado',
                'origen_referencia', 'cliente_referencia', 'observaciones',
                'servicio', 'servicio__uuid', 'servicio__codigo', 'servicio__nombre',
            )
            .order_by('-fecha_registro')
        )
