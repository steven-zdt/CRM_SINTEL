# apps/tenant/inventario/services/ingesta_service.py
# v3.10.4: Servicio de materializacion masiva e idempotente de catalogo (DT-INV-05)

from decimal import Decimal
from typing import Dict, Any, List
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.tenant.empresa.models import Empresa
from apps.tenant.inventario.models import (
    ActivoFijo,
    CategoriaItem,
    MovimientoInventario,
    Producto,
    Servicio,
)
from .business_service import KardexService


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
            ).only('id', 'empresa_id', 'nombre', 'aplicacion').first()

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
                        KardexService.recalcular_stock_producto(producto.id, empresa.id)
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
                ).only('id', 'empresa_id', 'nombre', 'aplicacion').first()

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
                        KardexService.recalcular_stock_producto(producto.id, empresa.id)
                else:
                    resumen["actualizados"] += 1

            except Exception as e:
                resumen["errores"].append(
                    f"Fila {index + 1} ({codigo if codigo else '?'}): {str(e)}"
                )

    return resumen


class IngestaService:
    """Servicio de materializacion masiva e idempotente de catalogo."""

    @staticmethod
    def materializar_inventario_desde_dto(dto: dict) -> tuple:
        """Materializa un DTO canonico de inventario."""
        return materializar_inventario_desde_dto(dto)

    @staticmethod
    def materializar_carga_masiva_productos(empresa_id, lista_datos, usuario=None):
        """Materializa una lista de productos con DSV por empresa_id."""
        return materializar_carga_masiva_productos(empresa_id, lista_datos, usuario=usuario)
