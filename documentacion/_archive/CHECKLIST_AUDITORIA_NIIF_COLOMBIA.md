# Checklist de Auditoría Automática - Normativa NIIF Colombia

**Fecha:** 2024-12-19  
**Versión:** 1.0  
**Objetivo:** Validaciones automáticas antes de cerrar un periodo contable

---

## 📋 Resumen

Este checklist define las validaciones que el sistema ejecutará automáticamente antes de permitir el cierre de un periodo contable, asegurando el cumplimiento de la normativa colombiana (NIIF PYMES y Estatuto Tributario).

---

## ✅ Validaciones Obligatorias

### 1. Partida Doble Estricta

**Regla:** ∑ Débitos = ∑ Créditos (sin excepciones)

**Validación:**
```python
def validar_partida_doble(periodo):
    """
    Valida que todos los asientos del periodo cumplan Partida Doble Estricta.
    
    Returns:
        dict: {
            'valido': bool,
            'asientos_no_cuadrados': list,
            'total_asientos': int,
            'asientos_cuadrados': int
        }
    """
    asientos = AsientoContable.objects.filter(
        fecha__gte=periodo.fecha_inicio,
        fecha__lte=periodo.fecha_fin
    )
    
    asientos_no_cuadrados = []
    for asiento in asientos:
        diferencia = abs(asiento.total_debe - asiento.total_haber)
        if diferencia >= Decimal('0.01'):
            asientos_no_cuadrados.append({
                'asiento': asiento.numero,
                'fecha': asiento.fecha,
                'diferencia': diferencia
            })
    
    return {
        'valido': len(asientos_no_cuadrados) == 0,
        'asientos_no_cuadrados': asientos_no_cuadrados,
        'total_asientos': asientos.count(),
        'asientos_cuadrados': asientos.count() - len(asientos_no_cuadrados)
    }
```

**Checklist:**
- [ ] Todos los asientos del periodo tienen ∑ Débitos = ∑ Créditos
- [ ] Tolerancia de redondeo: diferencia < $0.01
- [ ] No hay asientos con diferencia >= $0.01

---

### 2. Niveles de Cuenta (Solo Nivel 6)

**Regla:** Solo se permiten registros en cuentas auxiliares (Nivel 6)

**Validación:**
```python
def validar_niveles_cuenta(periodo):
    """
    Valida que todos los movimientos usen cuentas de nivel 6.
    
    Returns:
        dict: {
            'valido': bool,
            'movimientos_nivel_incorrecto': list,
            'total_movimientos': int,
            'movimientos_validos': int
        }
    """
    asientos = AsientoContable.objects.filter(
        fecha__gte=periodo.fecha_inicio,
        fecha__lte=periodo.fecha_fin
    )
    
    movimientos = MovimientoContable.objects.filter(asiento__in=asientos)
    movimientos_nivel_incorrecto = []
    
    for movimiento in movimientos:
        if movimiento.cuenta.nivel != 6:
            movimientos_nivel_incorrecto.append({
                'movimiento_id': movimiento.id,
                'asiento': movimiento.asiento.numero,
                'cuenta': movimiento.cuenta.codigo,
                'nivel': movimiento.cuenta.nivel
            })
    
    return {
        'valido': len(movimientos_nivel_incorrecto) == 0,
        'movimientos_nivel_incorrecto': movimientos_nivel_incorrecto,
        'total_movimientos': movimientos.count(),
        'movimientos_validos': movimientos.count() - len(movimientos_nivel_incorrecto)
    }
```

**Checklist:**
- [ ] Todos los movimientos usan cuentas de nivel 6
- [ ] No hay movimientos con cuentas de nivel 1, 2 o 4
- [ ] Todas las cuentas tienen nivel definido

---

### 3. Terceros Obligatorios

**Regla:** Cada movimiento debe tener un tercero (NIT/CC) para medios magnéticos

**Validación:**
```python
def validar_terceros_obligatorios(periodo):
    """
    Valida que todos los movimientos tengan tercero completo.
    
    Returns:
        dict: {
            'valido': bool,
            'movimientos_sin_tercero': list,
            'total_movimientos': int,
            'movimientos_con_tercero': int
        }
    """
    asientos = AsientoContable.objects.filter(
        fecha__gte=periodo.fecha_inicio,
        fecha__lte=periodo.fecha_fin
    )
    
    movimientos = MovimientoContable.objects.filter(asiento__in=asientos)
    movimientos_sin_tercero = []
    
    for movimiento in movimientos:
        if not movimiento.tercero_nit or not movimiento.tercero_razon_social:
            movimientos_sin_tercero.append({
                'movimiento_id': movimiento.id,
                'asiento': movimiento.asiento.numero,
                'cuenta': movimiento.cuenta.codigo,
                'tipo_tercero': movimiento.tipo_tercero,
                'tercero_id': movimiento.tercero_id
            })
    
    return {
        'valido': len(movimientos_sin_tercero) == 0,
        'movimientos_sin_tercero': movimientos_sin_tercero,
        'total_movimientos': movimientos.count(),
        'movimientos_con_tercero': movimientos.count() - len(movimientos_sin_tercero)
    }
```

**Checklist:**
- [ ] Todos los movimientos tienen `tipo_tercero` definido
- [ ] Todos los movimientos tienen `tercero_id` definido
- [ ] Todos los movimientos tienen `tercero_nit` definido (no vacío)
- [ ] Todos los movimientos tienen `tercero_razon_social` definido (no vacío)

---

### 4. Integridad de Datos (DecimalField)

**Regla:** Todos los valores monetarios usan DecimalField(15,2)

**Validación:**
```python
def validar_integridad_decimales(periodo):
    """
    Valida que todos los valores monetarios tengan precisión correcta.
    
    Returns:
        dict: {
            'valido': bool,
            'errores': list
        }
    """
    asientos = AsientoContable.objects.filter(
        fecha__gte=periodo.fecha_inicio,
        fecha__lte=periodo.fecha_fin
    )
    
    movimientos = MovimientoContable.objects.filter(asiento__in=asientos)
    errores = []
    
    for movimiento in movimientos:
        # Validar que los valores no excedan max_digits=15
        if movimiento.debe >= Decimal('9999999999999.99') or \
           movimiento.haber >= Decimal('9999999999999.99'):
            errores.append({
                'movimiento_id': movimiento.id,
                'asiento': movimiento.asiento.numero,
                'error': 'Valor excede max_digits=15'
            })
        
        # Validar que los valores tengan máximo 2 decimales
        if movimiento.debe.as_tuple().exponent < -2 or \
           movimiento.haber.as_tuple().exponent < -2:
            errores.append({
                'movimiento_id': movimiento.id,
                'asiento': movimiento.asiento.numero,
                'error': 'Valor tiene más de 2 decimales'
            })
    
    return {
        'valido': len(errores) == 0,
        'errores': errores
    }
```

**Checklist:**
- [ ] Todos los valores monetarios tienen max_digits=15
- [ ] Todos los valores monetarios tienen decimal_places=2
- [ ] No hay valores que excedan el rango permitido

---

### 5. Cálculo de IVA

**Regla:** IVA generado (240805) y descontable (240810) deben calcularse correctamente

**Validación:**
```python
def validar_calculo_iva(periodo):
    """
    Valida que el IVA se calcule correctamente según normativa.
    
    Returns:
        dict: {
            'valido': bool,
            'errores': list,
            'total_iva_generado': Decimal,
            'total_iva_descontable': Decimal
        }
    """
    asientos = AsientoContable.objects.filter(
        fecha__gte=periodo.fecha_inicio,
        fecha__lte=periodo.fecha_fin
    )
    
    movimientos_iva = MovimientoContable.objects.filter(
        asiento__in=asientos,
        cuenta__codigo__in=['240805', '240810']
    )
    
    errores = []
    total_iva_generado = Decimal('0.00')
    total_iva_descontable = Decimal('0.00')
    
    for movimiento in movimientos_iva:
        if movimiento.cuenta.codigo == '240805':  # IVA Generado
            # Validar que iva_generado = base_iva * 0.19 (aproximadamente)
            iva_esperado = (movimiento.base_iva * Decimal('0.19')).quantize(Decimal('0.01'))
            diferencia = abs(movimiento.iva_generado - iva_esperado)
            if diferencia >= Decimal('0.01'):
                errores.append({
                    'movimiento_id': movimiento.id,
                    'asiento': movimiento.asiento.numero,
                    'error': f'IVA generado incorrecto. Esperado: ${iva_esperado}, Calculado: ${movimiento.iva_generado}'
                })
            total_iva_generado += movimiento.iva_generado
        elif movimiento.cuenta.codigo == '240810':  # IVA Descontable
            # Validar que iva_descontable = base_iva * 0.19 (aproximadamente)
            iva_esperado = (movimiento.base_iva * Decimal('0.19')).quantize(Decimal('0.01'))
            diferencia = abs(movimiento.iva_descontable - iva_esperado)
            if diferencia >= Decimal('0.01'):
                errores.append({
                    'movimiento_id': movimiento.id,
                    'asiento': movimiento.asiento.numero,
                    'error': f'IVA descontable incorrecto. Esperado: ${iva_esperado}, Calculado: ${movimiento.iva_descontable}'
                })
            total_iva_descontable += movimiento.iva_descontable
    
    return {
        'valido': len(errores) == 0,
        'errores': errores,
        'total_iva_generado': total_iva_generado,
        'total_iva_descontable': total_iva_descontable
    }
```

**Checklist:**
- [ ] IVA generado (240805) se calcula correctamente (base * 19%)
- [ ] IVA descontable (240810) se calcula correctamente (base * 19%)
- [ ] Base IVA está definida para movimientos de IVA
- [ ] No hay discrepancias entre IVA calculado y esperado

---

### 6. Cálculo de Retenciones

**Regla:** ReteFuente (2365) y ReteICA (2368) deben calcularse correctamente

**Validación:**
```python
def validar_calculo_retenciones(periodo):
    """
    Valida que las retenciones se calculen correctamente según normativa.
    
    Returns:
        dict: {
            'valido': bool,
            'errores': list,
            'total_retefuente': Decimal,
            'total_reteica': Decimal
        }
    """
    asientos = AsientoContable.objects.filter(
        fecha__gte=periodo.fecha_inicio,
        fecha__lte=periodo.fecha_fin
    )
    
    movimientos_retenciones = MovimientoContable.objects.filter(
        asiento__in=asientos,
        cuenta__codigo__startswith__in=['2365', '2368']
    )
    
    errores = []
    total_retefuente = Decimal('0.00')
    total_reteica = Decimal('0.00')
    
    for movimiento in movimientos_retenciones:
        if movimiento.cuenta.codigo.startswith('2365'):  # ReteFuente
            # Validar que retefuente esté calculado (el porcentaje varía según concepto)
            if movimiento.retefuente == 0 and movimiento.debe > 0:
                errores.append({
                    'movimiento_id': movimiento.id,
                    'asiento': movimiento.asiento.numero,
                    'error': 'ReteFuente no calculado para movimiento con valor'
                })
            total_retefuente += movimiento.retefuente
        elif movimiento.cuenta.codigo.startswith('2368'):  # ReteICA
            # Validar que reteica esté calculado (el porcentaje varía según actividad)
            if movimiento.reteica == 0 and movimiento.debe > 0:
                errores.append({
                    'movimiento_id': movimiento.id,
                    'asiento': movimiento.asiento.numero,
                    'error': 'ReteICA no calculado para movimiento con valor'
                })
            total_reteica += movimiento.reteica
    
    return {
        'valido': len(errores) == 0,
        'errores': errores,
        'total_retefuente': total_retefuente,
        'total_reteica': total_reteica
    }
```

**Checklist:**
- [ ] ReteFuente (2365) se calcula cuando aplica
- [ ] ReteICA (2368) se calcula cuando aplica
- [ ] No hay movimientos de retenciones con valor pero sin cálculo

---

### 7. Comprobantes (Trazabilidad)

**Regla:** Asientos deben tener tipo y número de comprobante para trazabilidad

**Validación:**
```python
def validar_comprobantes(periodo):
    """
    Valida que los asientos tengan comprobantes para trazabilidad.
    
    Returns:
        dict: {
            'valido': bool,
            'asientos_sin_comprobante': list,
            'total_asientos': int,
            'asientos_con_comprobante': int
        }
    """
    asientos = AsientoContable.objects.filter(
        fecha__gte=periodo.fecha_inicio,
        fecha__lte=periodo.fecha_fin
    )
    
    asientos_sin_comprobante = []
    for asiento in asientos:
        if not asiento.tipo_comprobante or not asiento.numero_comprobante:
            asientos_sin_comprobante.append({
                'asiento': asiento.numero,
                'fecha': asiento.fecha,
                'tipo_comprobante': asiento.tipo_comprobante,
                'numero_comprobante': asiento.numero_comprobante
            })
    
    return {
        'valido': len(asientos_sin_comprobante) == 0,
        'asientos_sin_comprobante': asientos_sin_comprobante,
        'total_asientos': asientos.count(),
        'asientos_con_comprobante': asientos.count() - len(asientos_sin_comprobante)
    }
```

**Checklist:**
- [ ] Todos los asientos tienen `tipo_comprobante` definido
- [ ] Todos los asientos tienen `numero_comprobante` definido
- [ ] Los tipos de comprobante son válidos (FVE, CE, RC, GN, ND, NC)

---

## 🔄 Función de Auditoría Completa

```python
# apps/tenant/contabilidad/services/auditoria_service.py
from decimal import Decimal
from typing import Dict, List
from apps.tenant.contabilidad.models import PeriodoContable, AsientoContable, MovimientoContable

def ejecutar_auditoria_periodo(periodo: PeriodoContable) -> Dict:
    """
    Ejecuta todas las validaciones de auditoría para un periodo contable.
    
    ⚠️ NORMATIVA COLOMBIANA: Valida cumplimiento de NIIF PYMES y Estatuto Tributario.
    
    Args:
        periodo: Instancia de PeriodoContable a auditar
    
    Returns:
        dict: {
            'periodo': str,
            'fecha_auditoria': datetime,
            'valido': bool,
            'validaciones': {
                'partida_doble': dict,
                'niveles_cuenta': dict,
                'terceros_obligatorios': dict,
                'integridad_decimales': dict,
                'calculo_iva': dict,
                'calculo_retenciones': dict,
                'comprobantes': dict
            },
            'resumen': {
                'total_asientos': int,
                'total_movimientos': int,
                'errores_totales': int
            }
        }
    """
    from datetime import datetime
    
    # Ejecutar todas las validaciones
    validaciones = {
        'partida_doble': validar_partida_doble(periodo),
        'niveles_cuenta': validar_niveles_cuenta(periodo),
        'terceros_obligatorios': validar_terceros_obligatorios(periodo),
        'integridad_decimales': validar_integridad_decimales(periodo),
        'calculo_iva': validar_calculo_iva(periodo),
        'calculo_retenciones': validar_calculo_retenciones(periodo),
        'comprobantes': validar_comprobantes(periodo)
    }
    
    # Determinar si todas las validaciones pasaron
    valido = all(v.get('valido', False) for v in validaciones.values())
    
    # Contar errores totales
    errores_totales = sum(
        len(v.get('errores', [])) + 
        len(v.get('asientos_no_cuadrados', [])) +
        len(v.get('movimientos_nivel_incorrecto', [])) +
        len(v.get('movimientos_sin_tercero', [])) +
        len(v.get('asientos_sin_comprobante', []))
        for v in validaciones.values()
    )
    
    # Obtener totales
    asientos = AsientoContable.objects.filter(
        fecha__gte=periodo.fecha_inicio,
        fecha__lte=periodo.fecha_fin
    )
    movimientos = MovimientoContable.objects.filter(asiento__in=asientos)
    
    return {
        'periodo': periodo.periodo,
        'fecha_auditoria': datetime.now(),
        'valido': valido,
        'validaciones': validaciones,
        'resumen': {
            'total_asientos': asientos.count(),
            'total_movimientos': movimientos.count(),
            'errores_totales': errores_totales
        }
    }
```

---

## ✅ Checklist de Cierre de Periodo

Antes de cerrar un periodo contable, el sistema debe validar:

- [ ] **Partida Doble**: Todos los asientos cuadran (∑ Débitos = ∑ Créditos)
- [ ] **Niveles de Cuenta**: Todos los movimientos usan cuentas de nivel 6
- [ ] **Terceros**: Todos los movimientos tienen tercero completo (NIT/CC)
- [ ] **Integridad Decimales**: Todos los valores tienen precisión correcta
- [ ] **IVA**: IVA generado y descontable calculados correctamente
- [ ] **Retenciones**: ReteFuente y ReteICA calculadas correctamente
- [ ] **Comprobantes**: Todos los asientos tienen tipo y número de comprobante

**Si alguna validación falla:**
- ❌ El periodo NO puede cerrarse
- ⚠️ Se muestra reporte detallado de errores
- ✅ El usuario debe corregir los errores antes de intentar cerrar nuevamente

---

**Última actualización:** 2024-12-19  
**Versión del documento:** 1.0
