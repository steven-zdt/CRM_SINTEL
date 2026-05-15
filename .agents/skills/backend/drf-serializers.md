# Skill: DRF Serializers — SINTEL v2.62

**Carga cuando:** Crear o modificar serializers, validaciones de campos.

---

## Patrón List Serializer (lectura optimizada)

```python
from rest_framework import serializers
from apps.tenant.<app>.models import MiModelo

class MiModeloListSerializer(serializers.ModelSerializer):
    # Solo campos necesarios para la tabla (Zero Waste)
    campo_calculado = serializers.SerializerMethodField()

    class Meta:
        model = MiModelo
        fields = (
            'id',
            'campo_a',
            'campo_b',
            'campo_calculado',
            'created_at',
        )
        read_only_fields = fields

    def get_campo_calculado(self, obj):
        # Usar prefetch si existe, evitar query adicional
        elementos = getattr(obj, 'elementos_prefetched', None)
        if elementos:
            return {'nombre': elementos[0].nombre, 'valor': elementos[0].valor}
        return None
```

## Patrón Detail Serializer (escritura con validación)

```python
class NormalizationMixin:
    """Normalizar campos de texto antes de guardar."""
    def to_internal_value(self, data):
        data = data.copy()
        for campo in getattr(self.Meta, 'normalize_fields', []):
            if campo in data and isinstance(data[campo], str):
                data[campo] = data[campo].strip().upper()
        return super().to_internal_value(data)

class MiModeloDetailSerializer(NormalizationMixin, serializers.ModelSerializer):
    class Meta:
        model = MiModelo
        fields = ('id', 'campo_a', 'campo_b', 'campo_c')
        read_only_fields = ('id',)
        normalize_fields = ('campo_a', 'campo_b')  # se normalizan en NormalizationMixin

    def validate_campo_a(self, value):
        """Validar unicidad en contexto de empresa."""
        empresa_id = self.context.get('empresa_id')
        if empresa_id:
            qs = MiModelo.objects.filter(empresa_id=empresa_id, campo_a=value)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError('Ya existe un registro con este valor.')
        return value

    def validate(self, data):
        """Validaciones cruzadas."""
        if data.get('campo_b') and not data.get('campo_c'):
            raise serializers.ValidationError({'campo_c': 'Requerido cuando campo_b está presente.'})
        return data
```

## Context en ViewSet

```python
def get_serializer_context(self):
    context = super().get_serializer_context()
    empresa = self.get_empresa()
    if empresa:
        context['empresa_id'] = empresa.id
    return context
```

## REGLA CRITICA — Nunca `request.user.perfil` en serializers

```python
# PROHIBIDO — AttributeError si user no tiene TenantProfile
empresa_id = self.context.get('request').user.perfil.empresa_id

# CORRECTO — Helper seguro en NormalizationMixin
def _get_empresa_id(self):
    empresa_id = self.context.get('empresa_id')       # inyectado por ViewSet
    if empresa_id:
        return empresa_id
    empresa = Empresa.objects.only('id').first()       # fallback singleton
    if empresa:
        return empresa.id
    raise serializers.ValidationError("No se encontro configuracion de Empresa.")
```

**Por qué falla:** `perfil` es una relación OneToOne inversa. Si el `User` autenticado no tiene un `TenantProfile`, Django lanza `RelatedObjectDoesNotExist` (subclase de `AttributeError`). Esto ocurre en GET list antes de cualquier guard de permisos.

**Inyectar desde ViewSet:**
```python
def get_serializer_context(self):
    context = super().get_serializer_context()
    empresa = self.get_empresa()
    if empresa:
        context['empresa_id'] = empresa.id
    return context
```

## Reglas
- Serializer `List` = solo read, `fields = read_only_fields = (...)`, Zero Waste
- Serializer `Detail` = create/update, con validaciones
- `empresa_id` via `_get_empresa_id()` helper — NUNCA `request.user.perfil` en serializer
- `NormalizationMixin` antes de `ModelSerializer` en MRO
- Campos FK: retornar ID en inputs, objeto anidado en outputs (SerializerMethodField)
