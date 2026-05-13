"""
business_service.py - Inventario v3.5

Capa de logica de negocio (Business Logic Layer) para el modulo de Inventario.
Contiene: calculos de stock, validaciones semanticas, movimientos de Kardex,
ingesta masiva de datos y Service Mixins para ViewSets.

Reglas:
- Toda mutacion de stock usa @transaction.atomic.
- Toda validacion de pertenencia al tenant pasa por selectors.py (Zero Trust).
- Los Service Mixins inyectan metodos a los ViewSets via herencia.
- PROHIBIDO queries directas en Mixins sin pasar por selectors.
"""

from decimal import Decimal
from typing import Optional, List, Dict, Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from apps.tenant.empresa.models import Empresa
from apps.tenant.inventario.models import (
    ActivoFijo,
    CategoriaItem,
    HistorialServicio,
    MovimientoInventario,
    Producto,
    Servicio,
)
from apps.tenant.inventario.services.selectors import (
    MOVIMIENTO_LIST_FIELDS,
    ActivoFijoSelector,
    CategoriaItemSelector,
    ProductoSelector,
    ServicioSelector,
)

# ==============================================================================
# 1. MOTOR DE KARDEX (Stock Calculation Engine)
# ==============================================================================

def calcular_stock(producto_id: int) -> Decimal:
    """
    Calcula el stock actual de un producto basado en sus movimientos (solo lectura).
    No actualiza el campo stock_actual. Usar recalcular_stock_producto() para actualizar.

    Returns:
        Decimal: Stock calculado (entradas - salidas + ajustes).
    """
    if not Producto.objects.filter(pk=producto_id).exists():
        return Decimal("0")

    entradas = MovimientoInventario.objects.filter(
        producto_id=producto_id,
        tipo__in=[
            MovimientoInventario.TipoMovimiento.ENTRADA_COMPRA,
            MovimientoInventario.TipoMovimiento.ENTRADA_DEVOLUCION,
        ]
    ).aggregate(total=Sum("cantidad"))["total"] or Decimal("0")

    salidas = MovimientoInventario.objects.filter(
        producto_id=producto_id,
        tipo__in=[
            MovimientoInventario.TipoMovimiento.SALIDA_VENTA,
            MovimientoInventario.TipoMovimiento.SALIDA_BAJA,
            MovimientoInventario.TipoMovimiento.SALIDA_CONSUMO,
        ]
    ).aggregate(total=Sum("cantidad"))["total"] or Decimal("0")

    ajustes_pos = MovimientoInventario.objects.filter(
        producto_id=producto_id,
        tipo=MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE,
        cantidad__gt=0
    ).aggregate(total=Sum("cantidad"))["total"] or Decimal("0")

    ajustes_neg = MovimientoInventario.objects.filter(
        producto_id=producto_id,
        tipo=MovimientoInventario.TipoMovimiento.SALIDA_BAJA,
        cantidad__lt=0
    ).aggregate(total=Sum("cantidad"))["total"] or Decimal("0")

    return entradas + ajustes_pos - (salidas + abs(ajustes_neg))


def recalcular_stock_producto(producto_id: int) -> Decimal:
    """
    Recalcula el stock fisico de un producto y actualiza el campo desnormalizado
    `stock_actual`. Usa select_for_update() para lock optimista.

    Returns:
        Decimal: El nuevo stock calculado.
    """
    with transaction.atomic():
        producto = Producto.objects.select_for_update().only('id', 'stock_actual').get(id=producto_id)

        entradas_tipos = [
            MovimientoInventario.TipoMovimiento.ENTRADA_COMPRA,
            MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE,
            MovimientoInventario.TipoMovimiento.ENTRADA_DEVOLUCION,
        ]
        salidas_tipos = [
            MovimientoInventario.TipoMovimiento.SALIDA_VENTA,
            MovimientoInventario.TipoMovimiento.SALIDA_BAJA,
            MovimientoInventario.TipoMovimiento.SALIDA_CONSUMO,
        ]

        suma_entradas = MovimientoInventario.objects.filter(
            producto_id=producto_id, tipo__in=entradas_tipos
        ).aggregate(total=Sum('cantidad'))['total'] or Decimal(0)

        suma_salidas = MovimientoInventario.objects.filter(
            producto_id=producto_id, tipo__in=salidas_tipos
        ).aggregate(total=Sum('cantidad'))['total'] or Decimal(0)

        nuevo_stock = suma_entradas - suma_salidas
        producto.stock_actual = nuevo_stock
        producto.save(update_fields=['stock_actual', 'updated_at'])

        return nuevo_stock


# ==============================================================================
# 2. OPERACIONES DE MOVIMIENTO (Transaccionales)
# ==============================================================================

@transaction.atomic
def registrar_entrada(
    producto_id: int,
    empresa_id: int,
    cantidad: Decimal,
    tipo_movimiento: Optional[str] = None,
    costo_unitario: Optional[Decimal] = None,
    origen_referencia: Optional[str] = None,
    observaciones: Optional[str] = None,
) -> MovimientoInventario:
    """
    Registra una entrada de producto (compra, devolucion, ajuste positivo) con Zero Trust.

    Raises:
        ValidationError: Si la cantidad es negativa o el producto no pertenece al tenant.
    """
    if cantidad <= 0:
        raise ValidationError("La cantidad de entrada debe ser positiva.")

    producto = Producto.objects.only('id', 'empresa_id').filter(
        pk=producto_id, empresa_id=empresa_id
    ).first()
    if not producto:
        raise ValidationError(
            f"El producto con ID {producto_id} no existe o no pertenece a este tenant."
        )

    if not tipo_movimiento:
        tipo_movimiento = MovimientoInventario.TipoMovimiento.ENTRADA_COMPRA

    tipos_entrada = [
        MovimientoInventario.TipoMovimiento.ENTRADA_COMPRA,
        MovimientoInventario.TipoMovimiento.ENTRADA_DEVOLUCION,
        MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE,
    ]
    if tipo_movimiento not in tipos_entrada:
        raise ValidationError(f"Tipo de movimiento invalido para entrada: {tipo_movimiento}")

    movimiento = MovimientoInventario.objects.create(
        producto=producto,
        empresa_id=empresa_id,
        tipo=tipo_movimiento,
        cantidad=cantidad,
        costo_unitario=costo_unitario or Decimal('0'),
        origen_referencia=origen_referencia,
        observaciones=observaciones,
    )
    recalcular_stock_producto(producto_id)
    return movimiento


@transaction.atomic
def registrar_salida(
    producto_id: int,
    empresa_id: int,
    cantidad: Decimal,
    tipo_movimiento: Optional[str] = None,
    costo_unitario: Optional[Decimal] = None,
    origen_referencia: Optional[str] = None,
    cliente_referencia: Optional[str] = None,
    observaciones: Optional[str] = None,
) -> MovimientoInventario:
    """
    Registra una salida de producto (venta, baja, consumo) con Zero Trust.

    Raises:
        ValidationError: Si stock insuficiente o el producto no pertenece al tenant.
    """
    if cantidad <= 0:
        raise ValidationError("La cantidad de salida debe ser positiva.")

    producto = Producto.objects.only('id', 'empresa_id', 'stock_actual').filter(
        pk=producto_id, empresa_id=empresa_id
    ).first()
    if not producto:
        raise ValidationError(
            f"El producto con ID {producto_id} no existe o no pertenece a este tenant."
        )

    if producto.stock_actual < cantidad:
        raise ValidationError(
            f"Stock insuficiente. Disponible: {producto.stock_actual}, Solicitado: {cantidad}"
        )

    if not tipo_movimiento:
        tipo_movimiento = MovimientoInventario.TipoMovimiento.SALIDA_VENTA

    tipos_salida = [
        MovimientoInventario.TipoMovimiento.SALIDA_VENTA,
        MovimientoInventario.TipoMovimiento.SALIDA_BAJA,
        MovimientoInventario.TipoMovimiento.SALIDA_CONSUMO,
    ]
    if tipo_movimiento not in tipos_salida:
        raise ValidationError(f"Tipo de movimiento invalido para salida: {tipo_movimiento}")

    movimiento = MovimientoInventario.objects.create(
        producto=producto,
        empresa_id=empresa_id,
        tipo=tipo_movimiento,
        cantidad=cantidad,
        costo_unitario=costo_unitario or Decimal('0'),
        origen_referencia=origen_referencia,
        cliente_referencia=cliente_referencia,
        observaciones=observaciones,
    )
    recalcular_stock_producto(producto_id)
    return movimiento


@transaction.atomic
def ajustar_stock(
    producto_id: int,
    empresa_id: int,
    cantidad_ajuste: Decimal,
    observaciones: str = None,
) -> MovimientoInventario:
    """
    Ajusta el stock de un producto (positivo o negativo). Zero Trust.

    Raises:
        ValidationError: Si el ajuste resultaria en stock negativo o producto no existe.
    """
    producto = Producto.objects.only('id', 'empresa_id', 'stock_actual', 'costo_promedio').filter(
        pk=producto_id, empresa_id=empresa_id
    ).first()
    if not producto:
        raise ValidationError(
            f"El producto con ID {producto_id} no existe o no pertenece a este tenant."
        )

    nuevo_stock = producto.stock_actual + cantidad_ajuste
    if nuevo_stock < 0:
        raise ValidationError(
            f"El ajuste resultaria en stock negativo. "
            f"Stock actual: {producto.stock_actual}, Ajuste: {cantidad_ajuste}"
        )

    if cantidad_ajuste > 0:
        tipo_movimiento = MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE
    else:
        tipo_movimiento = MovimientoInventario.TipoMovimiento.SALIDA_BAJA
        cantidad_ajuste = abs(cantidad_ajuste)

    movimiento = MovimientoInventario.objects.create(
        producto=producto,
        empresa_id=empresa_id,
        tipo=tipo_movimiento,
        cantidad=cantidad_ajuste,
        costo_unitario=producto.costo_promedio or Decimal('0'),
        observaciones=observaciones or f"Ajuste de inventario: {cantidad_ajuste:+} unidades",
    )
    recalcular_stock_producto(producto_id)
    return movimiento


def registrar_movimiento(
    producto_id: int,
    tipo: str,
    cantidad: Decimal,
    empresa: Empresa,
    costo_unitario: Decimal = 0,
    origen_referencia: str = None,
    cliente_referencia: str = None,
    observaciones: str = None,
    usuario=None,
) -> MovimientoInventario:
    """
    Funcion generica para registrar un movimiento desde APIs externas (Ventas, Compras).
    Para entradas simples, preferir registrar_entrada().
    """
    with transaction.atomic():
        movimiento = MovimientoInventario.objects.create(
            empresa=empresa,
            producto_id=producto_id,
            tipo=tipo,
            cantidad=cantidad,
            costo_unitario=costo_unitario,
            origen_referencia=origen_referencia,
            cliente_referencia=cliente_referencia,
            observaciones=observaciones,
        )
        recalcular_stock_producto(producto_id)
        return movimiento


# ==============================================================================
# 3. INGESTA MASIVA (Document Ingest Pipeline - DTO Pattern)
# ==============================================================================

def materializar_inventario_desde_dto(dto: dict) -> tuple:
    """
    Materializa inventario desde DTO canonico del pipeline de documentos.

    Args:
        dto: DTO canonico con campos: tipo, codigo, nombre, categoria,
             precio_venta, stock_actual (solo productos), etc.

    Returns:
        Tuple (payload, status_code): 201 (creado), 200 (actualizado), 422 (error).
    """
    empresa = Empresa.objects.only('id').first()
    if not empresa:
        return {
            "error": "empresa_no_configurada",
            "message": "No existe Empresa en este tenant. Configure una Empresa antes de importar.",
        }, 422

    tipo = dto.get("tipo", "producto").lower()
    codigo = dto.get("codigo")
    nombre = dto.get("nombre")
    categoria_nombre = dto.get("categoria", "General")

    if not codigo or not nombre:
        return {
            "error": "missing_required_fields",
            "message": "Faltan campos obligatorios: codigo, nombre",
        }, 422

    try:
        with transaction.atomic():
            # SINTEL v3.5: Idempotencia Garantizada - Busqueda insensitiva manual
            categoria = CategoriaItem.objects.filter(
                empresa=empresa,
                nombre__iexact=categoria_nombre
            ).first()

            if not categoria:
                categoria = CategoriaItem.objects.create(
                    empresa=empresa,
                    nombre=categoria_nombre,
                    aplicacion=(
                        CategoriaItem.Aplicacion.PRODUCTO if tipo == "producto"
                        else CategoriaItem.Aplicacion.SERVICIO if tipo == "servicio"
                        else CategoriaItem.Aplicacion.ACTIVO
                    ),
                    descripcion='Auto-generada desde DTO',
                )

            if tipo == "producto":
                producto, created = Producto.objects.update_or_create(
                    empresa=empresa, codigo=codigo,
                    defaults={
                        'nombre': nombre,
                        'categoria': categoria,
                        'descripcion': dto.get("descripcion", ""),
                        'unidad': dto.get("unidad", "UND"),
                        'precio_venta': Decimal(str(dto.get("precio_venta", "0"))),
                        'costo_promedio': Decimal(str(dto.get("costo_promedio", "0"))),
                        'activo': True,
                    }
                )
                if created and dto.get("stock_actual"):
                    stock_inicial = Decimal(str(dto.get("stock_actual", "0")))
                    if stock_inicial > 0:
                        MovimientoInventario.objects.create(
                            empresa=empresa,
                            producto=producto,
                            tipo=MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE,
                            cantidad=stock_inicial,
                            observaciones="Carga desde DTO",
                        )
                        recalcular_stock_producto(producto.id)
                return {"id": producto.id, "codigo": producto.codigo, "nombre": producto.nombre, "created": created}, 201 if created else 200

            elif tipo == "servicio":
                servicio, created = Servicio.objects.update_or_create(
                    empresa=empresa, codigo=codigo,
                    defaults={
                        'nombre': nombre,
                        'categoria': categoria,
                        'descripcion': dto.get("descripcion", ""),
                        'precio_venta': Decimal(str(dto.get("precio_venta", "0"))),
                        'activo': True,
                    }
                )
                return {"id": servicio.id, "codigo": servicio.codigo, "nombre": servicio.nombre, "created": created}, 201 if created else 200

            elif tipo == "activo":
                activo, created = ActivoFijo.objects.update_or_create(
                    empresa=empresa, codigo=codigo,
                    defaults={
                        'nombre': nombre,
                        'categoria': categoria,
                        'descripcion': dto.get("descripcion", ""),
                        'costo_adquisicion': Decimal(str(dto.get("costo_adquisicion", "0"))),
                        'estado': dto.get("estado", ActivoFijo.Estado.ACTIVO),
                        'ubicacion': dto.get("ubicacion"),
                        'responsable': dto.get("responsable"),
                    }
                )
                return {"id": activo.id, "codigo": activo.codigo, "nombre": activo.nombre, "created": created}, 201 if created else 200

            return {
                "error": "invalid_type",
                "message": f"Tipo invalido: {tipo}. Use 'producto', 'servicio' o 'activo'.",
            }, 422

    except Exception as e:
        return {"error": "materialization_error", "message": f"Error al materializar inventario: {str(e)}"}, 422


def materializar_carga_masiva_productos(empresa_id, lista_datos, usuario=None):
    """
    Recibe lista de dicts procesados por document_parser y los materializa en BD.

    Args:
        empresa_id: ID de la empresa SSoT.
        lista_datos: Lista de dicts [{'codigo': ..., 'nombre': ..., ...}].
        usuario: Usuario que realiza la carga (opcional).

    Returns:
        dict: Resumen (creados, actualizados, errores).
    """
    resumen: Dict[str, Any] = {"creados": 0, "actualizados": 0, "errores": []}

    try:
        empresa = Empresa.objects.only('id').get(id=empresa_id)
    except Empresa.DoesNotExist:
        raise ValidationError(f"La empresa con ID {empresa_id} no existe.")

    with transaction.atomic():
        for index, fila in enumerate(lista_datos):
            codigo = None
            try:
                codigo = fila.get('codigo')
                nombre = fila.get('nombre')
                categoria_nombre = fila.get('categoria', 'General')

                if not codigo or not nombre:
                    resumen["errores"].append(f"Fila {index + 1}: Falta codigo o nombre.")
                    continue

                # SINTEL v3.5: Idempotencia Garantizada - Busqueda insensitiva manual
                categoria = CategoriaItem.objects.filter(
                    empresa=empresa,
                    nombre__iexact=categoria_nombre
                ).first()

                if not categoria:
                    categoria = CategoriaItem.objects.create(
                        empresa=empresa,
                        nombre=categoria_nombre,
                        aplicacion=CategoriaItem.Aplicacion.PRODUCTO,
                        descripcion='Auto-generada por carga masiva',
                    )

                stock_inicial = Decimal(str(fila.get('stock_actual', '0')))

                producto, created = Producto.objects.update_or_create(
                    empresa=empresa,
                    codigo=codigo,
                    defaults={
                        'nombre': nombre,
                        'categoria': categoria,
                        'descripcion': fila.get('descripcion', ''),
                        'unidad': fila.get('unidad', 'UND'),
                        'precio_venta': Decimal(str(fila.get('precio_venta', '0'))),
                        'costo_promedio': Decimal(str(fila.get('costo_promedio', '0'))),
                        'activo': True,
                    }
                )

                if created:
                    resumen["creados"] += 1
                    if stock_inicial > 0:
                        MovimientoInventario.objects.create(
                            empresa=empresa,
                            producto=producto,
                            tipo=MovimientoInventario.TipoMovimiento.ENTRADA_AJUSTE,
                            cantidad=stock_inicial,
                            observaciones="Carga Masiva Inicial",
                        )
                        producto.stock_actual = stock_inicial
                        producto.save(update_fields=['stock_actual', 'updated_at'])
                else:
                    resumen["actualizados"] += 1

            except Exception as e:
                resumen["errores"].append(
                    f"Fila {index + 1} ({codigo if codigo else '?'}): {str(e)}"
                )

    return resumen


# ==============================================================================
# 4. SERVICE MIXINS (Inyeccion por Herencia - Regla 4.4 SINTEL)
# ==============================================================================

class CategoriaItemServiceMixin:
    """Mixin para inyectar logica de negocio de Categorias en ViewSets."""

    def service_categoria_destroy(self, instance):
        """Elimina la categoria desvinculando items relacionados (set NULL)."""
        with transaction.atomic():
            Producto.objects.filter(categoria=instance).update(categoria=None)
            Servicio.objects.filter(categoria=instance).update(categoria=None)
            ActivoFijo.objects.filter(categoria=instance).update(categoria=None)
            instance.delete()
        return True

    def service_categoria_get_resumen(self, instance):
        """Retorna conteo de items asociados a la categoria."""
        conteo_productos = Producto.objects.filter(categoria=instance).count()
        conteo_servicios = Servicio.objects.filter(categoria=instance).count()
        conteo_activos = ActivoFijo.objects.filter(categoria=instance).count()
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
            categoria = CategoriaItemSelector.get_detail(empresa_id=empresa.id, categoria_id=id_instancia)
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
            .filter(empresa=empresa, pk=pk)
            .only('id', 'nombre', 'stock_actual')
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
            .filter(empresa=empresa, pk=pk)
            .only('id', 'codigo', 'nombre', 'stock_actual')
            .first()
        )
        if not producto:
            from rest_framework.exceptions import NotFound
            raise NotFound('Producto no encontrado')

        movimientos = (
            MovimientoInventario.objects
            .filter(producto=producto)
            .select_related('producto')
            .only(*MOVIMIENTO_LIST_FIELDS)
            .order_by('-created_at')
        )
        return producto, movimientos

    def service_producto_get_offcanvas_context(self, empresa, id_instancia=None, tipo_formulario='producto'):
        """Centraliza la carga de datos para formularios HTMX de productos."""
        producto = None
        if id_instancia:
            producto = ProductoSelector.get_detail(empresa_id=empresa.id, producto_id=id_instancia)

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
            servicio = ServicioSelector.get_detail(empresa_id=empresa.id, servicio_id=id_instancia)

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
            activo = ActivoFijoSelector.get_detail(empresa_id=empresa.id, activo_id=id_instancia)

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
        """Guarda el movimiento y recalcula stock atomicamente."""
        with transaction.atomic():
            movimiento = serializer.save(empresa=empresa)
            recalcular_stock_producto(movimiento.producto.id)
            return movimiento

    def service_movimiento_get_offcanvas_context(self, empresa):
        """Contexto para formulario de registro de movimiento (Kardex)."""
        productos = (
            Producto.objects
            .filter(empresa_id=empresa.id)
            .only('id', 'codigo', 'nombre')
            .order_by('nombre')
        )
        return {
            'productos': productos,
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
                'id', 'fecha_registro', 'cantidad', 'valor_cobrado',
                'origen_referencia', 'cliente_referencia', 'observaciones',
                'servicio__nombre'
            )
            .order_by('-fecha_registro')
        )
