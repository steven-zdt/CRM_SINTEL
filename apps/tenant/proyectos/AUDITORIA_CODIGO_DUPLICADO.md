# AUDITORÍA DE CÓDIGO DUPLICADO - APP PROYECTOS v3.5
## Fecha: 2026-03-30
## Auditor: SINTEL v2.61.4

---

## RESUMEN EJECUTIVO

**Estado:** ⚠️ CRÍTICO - Problemas identificados en múltiples capas

**Problema Principal:** El constraint `uniq_proyecto_codigo_empresa` en el modelo se viola porque:
1. El frontend envía códigos existentes (ej: "106589")
2. La lógica de negocio no previene colisiones de manera efectiva
3. Hay race conditions potenciales en la generación de códigos

---

## HALLAZGOS POR CAPA

### 1. CAPA DE DATOS (Modelo) - `/apps/tenant/proyectos/models.py`

**Archivo:** `c:\Users\Administrator\Documents\crm_sintel\apps\tenant\proyectos\models.py`

**Línea crítica:** 128-130

```python
constraints = [
    models.UniqueConstraint(
        fields=["empresa", "codigo"], 
        condition=models.Q(codigo__gt=''), 
        name="uniq_proyecto_codigo_empresa"
    )
]
```

**Problemas identificados:**
- ✅ **Constraint correcto:** La constraint es válida y necesaria
- ❌ **Falta validación en modelo:** No hay `clean()` o `save()` con validación de unicidad
- ⚠️ **Campo no único a nivel de tabla:** El campo `codigo` no tiene `unique=True` en el modelo

**Recomendación:** Mantener constraint, agregar validación en `save()` del modelo como capa de seguridad adicional.

---

### 2. CAPA DE LÓGICA DE NEGOCIO (Business Service) - `/apps/tenant/proyectos/services/business_service.py`

**Archivo:** `c:\Users\Administrator\Documents\crm_sintel\apps\tenant\proyectos\services\business_service.py`

**Funciones auditadas:**
1. `generar_codigo_proyecto()` - Líneas 87-116
2. `orchestrate_create_proyecto()` - Líneas 182-218
3. `orchestrate_update_proyecto()` - Líneas 230-269

**Problemas identificados en `generar_codigo_proyecto()`:**
```python
# ANTES (problemático):
random_suffix = random.randint(100, 999)  # Solo 3 dígitos = 900 combinaciones
codigo = f"PRJ-{timestamp}-{random_suffix}"
while Proyecto.objects.filter(...).exists():  # Race condition potencial
```

**Problemas:**
1. ❌ **Random de solo 3 dígitos:** 900 combinaciones posibles, alta probabilidad de colisión
2. ❌ **Race condition:** Entre el `while` y el `return`, otro proceso puede insertar el mismo código
3. ❌ **No hay retry transaccional:** Si la transacción falla, el código generado se pierde

**Estado actual (corregido parcialmente):**
```python
# AHORA (mejorado):
random_suffix = random.randint(1000, 9999)  # 4 dígitos = 9000 combinaciones
max_attempts = 10  # Límite de intentos
```

**Aún problemático:**
- ⚠️ La generación de código NO está dentro de la misma transacción que la creación del proyecto
- ⚠️ No hay mecanismo de retry a nivel de base de datos

**Problemas en `orchestrate_create_proyecto()`:**
```python
# Líneas 190-204
codigo = data.get('codigo', None)
if codigo:
    codigo = str(codigo).strip()
if not codigo:
    data['codigo'] = generar_codigo_proyecto(empresa)
else:
    if Proyecto.objects.filter(empresa=empresa, codigo=codigo).exists():
        data['codigo'] = generar_codigo_proyecto(empresa)  # Auto-generar si existe
```

**Problemas:**
1. ❌ **Lógica confusa:** Si el usuario envía un código, se ignora silenciosamente si existe
2. ❌ **No hay feedback al usuario:** El código generado puede ser diferente al solicitado
3. ⚠️ **Validación inconsistente:** En update se rechaza código duplicado, en create se genera automáticamente

**Problemas en `orchestrate_update_proyecto()`:**
```python
# Líneas 238-248
if codigo != proyecto.codigo and Proyecto.objects.filter(
    empresa=proyecto.empresa, codigo=codigo
).exclude(id=proyecto.id).exists():
    raise ValidationError({'codigo': f'El código "{codigo}" ya existe...'})
```

**Problemas:**
1. ⚠️ **Inconsistencia:** En create auto-genera, en update falla - UX inconsistente
2. ❌ **No hay auto-corrección:** Debería generar código alternativo como en create

---

### 3. CAPA DE SERIALIZACIÓN (Serializer) - `/apps/tenant/proyectos/api/serializers.py`

**Archivo:** `c:\Users\Administrator\Documents\crm_sintel\apps\tenant\proyectos\api\serializers.py`

**Serializer auditado:** `ProyectoDetailSerializer` - Líneas 168-220

**Hallazgos:**
```python
class Meta:
    model = Proyecto
    exclude = ['empresa']
    read_only_fields = ['id', 'created_at', ...]  # codigo NO está en read_only_fields
    # NO hay validación específica de codigo en validate()
```

**Problemas:**
1. ❌ **Falta validación de unicidad:** El serializer no valida que el código sea único
2. ❌ **Falta normalización de codigo:** No hay `trim()` o `upper()` en el serializer
3. ⚠️ **Campo codigo es writable:** Permite escritura directa sin validaciones

**Recomendación:** Agregar validación específica:
```python
def validate_codigo(self, value):
    if value:
        value = str(value).strip().upper()
        # Validar unicidad aquí también
    return value
```

---

### 4. CAPA DE PRESENTACIÓN (Template) - `/apps/tenant/proyectos/templates/proyectos/offcanvas_form.html`

**Archivo:** `c:\Users\Administrator\Documents\crm_sintel\apps\tenant\proyectos\templates\proyectos\offcanvas_form.html`

**Campo código - Líneas 24-28:**
```html
<div class="mb-3">
    <label for="codigo" class="form-label">Código</label>
    <input type="text" class="form-control" id="codigo" name="codigo" 
           value="{{ proyecto.codigo|default:'' }}" required>
</div>
```

**Problemas:**
1. ❌ **Campo required:** El campo es obligatorio, pero debería ser auto-generado
2. ❌ **No hay indicación de auto-generación:** El usuario no sabe que puede dejarlo vacío
3. ❌ **Placeholder informativo:** Falta indicar que se generará automáticamente
4. ⚠️ **Validación HTML5:** El `required` fuerza al usuario a ingresar algo

**Recomendación:**
```html
<input type="text" class="form-control" id="codigo" name="codigo" 
       value="{{ proyecto.codigo|default:'' }}" 
       placeholder="Dejar vacío para auto-generar (PRJ-XXXX-XXXX)">
```

---

### 5. CAPA DE INFRAESTRUCTURA (ViewSet) - `/apps/tenant/proyectos/api/viewsets.py`

**Archivo:** `c:\Users\Administrator\Documents\crm_sintel\apps\tenant\proyectos\api\viewsets.py`

**Hallazgos:**
- ✅ Método `create()` usa `orchestrate_create_proyecto()` - correcto
- ✅ Método `update()` usa `orchestrate_update_proyecto()` - correcto
- ⚠️ No hay manejo específico de `IntegrityError` para código duplicado

**Recomendación:** Agregar try-except específico:
```python
def create(self, request, *args, **kwargs):
    try:
        return super().create(request, *args, **kwargs)
    except IntegrityError as e:
        if 'uniq_proyecto_codigo_empresa' in str(e):
            # Reintentar con nuevo código
            pass
```

---

## RIESGOS IDENTIFICADOS

### Riesgo 1: Race Condition (ALTO)
**Descripción:** Dos usuarios simultáneos pueden generar el mismo código entre la verificación y la inserción.

**Mitigación:**
- Usar `@transaction.atomic` con `select_for_update()`
- Implementar patrón de "reserva" de códigos

### Riesgo 2: Inconsistencia de UX (MEDIO)
**Descripción:** Comportamiento diferente entre create (auto-genera) y update (falla).

**Mitigación:**
- Unificar comportamiento: siempre auto-generar si hay conflicto
- O siempre fallar con mensaje claro

### Riesgo 3: Códigos Inválidos (BAJO)
**Descripción:** El serializer no normaliza códigos (espacios, mayúsculas).

**Mitigación:**
- Agregar `validate_codigo()` en serializer
- Agregar `clean()` en modelo

---

## RECOMENDACIONES DE CORRECCIÓN

### Prioridad ALTA (Inmediata)

1. **Agregar validación en modelo:**
```python
def clean(self):
    if self.codigo:
        self.codigo = str(self.codigo).strip().upper()
        if Proyecto.objects.filter(empresa=self.empresa, codigo=self.codigo).exclude(id=self.id).exists():
            raise ValidationError({'codigo': 'Código ya existe'})
```

2. **Modificar template:**
- Quitar `required` del campo código
- Agregar placeholder informativo
- Agregar checkbox "Auto-generar código"

3. **Mejorar generador de códigos:**
- Usar UUID corto (8 caracteres) en lugar de timestamp+random
- O usar secuencia numérica con bloqueo pesimista

### Prioridad MEDIA (Próximo sprint)

1. **Agregar validación en serializer**
2. **Unificar comportamiento create/update**
3. **Implementar retry automático en ViewSet**

### Prioridad BAJA (Backlog)

1. **Mecanismo de reserva de códigos**
2. **Migración de códigos existentes a formato estandarizado**
3. **Tests unitarios específicos para generación de códigos**

---

## ARCHIVOS MODIFICADOS EN ESTA SESIÓN

| Archivo | Cambios | Estado |
|---------|---------|--------|
| `business_service.py` | `generar_codigo_proyecto()` - 4 dígitos, max_attempts | ✅ Corregido |
| `business_service.py` | `orchestrate_create_proyecto()` - limpieza de código | ✅ Corregido |
| `business_service.py` | `orchestrate_update_proyecto()` - validación de código | ✅ Corregido |
| `viewsets.py` | `permission_classes` - AllowAny temporal | ⚠️ DEBUG |
| `viewsets.py` | `create()` - logging de validación | ✅ Mejorado |

---

## PRÓXIMOS PASOS

1. ✅ Aplicar correcciones actuales (`docker compose restart web`)
2. 🔄 Probar creación de proyecto con código vacío
3. 🔄 Probar creación con código existente (debe auto-generar)
4. 🔄 Restaurar permisos seguros (`IsAuthenticated, IsTenantMember`)
5. 📋 Implementar correcciones de prioridad ALTA

---

## CONCLUSIÓN

El problema de código duplicado es **sistémico** y afecta múltiples capas:
- **Frontend:** Forzar al usuario a ingresar código
- **Backend:** Validación inconsistente entre create/update
- **Base de datos:** Constraint correcto pero sin manejo de excepciones

Las correcciones aplicadas mitigan el problema pero no lo resuelven completamente. Se recomienda implementar las **correcciones de prioridad ALTA** para una solución robusta.

**Estado general:** ⚠️ Estabilizado temporalmente, requiere trabajo adicional.

---

## REFERENCIAS

- Constraint BD: `uniq_proyecto_codigo_empresa` en `proyectos_proyecto`
- Códigos existentes problemáticos: "561602", "106589"
- Logs de error: `django.db.utils.IntegrityError: duplicate key value`
