# Anti-IDOR Security (Double Semantic Verification)

Patrón de diseño y seguridad para prevenir vulnerabilidades de Insecure Direct Object Reference (IDOR) en aplicaciones Django Multi-Tenant.

## Principios Core

1. **Zero Trust**: Nunca confíes en un ID proporcionado por el cliente, incluso si el usuario está autenticado.
2. **Double Semantic Verification (DSV)**: Cada clave foránea (FK) recibida en un payload debe ser validada contra el `empresa_id` (o tenant_id) del usuario actual antes de cualquier operación.
3. **Capa de Servicio SSoT**: La validación de seguridad no reside en el ViewSet ni en el Serializer, sino en el **Business Service**, garantizando que cualquier punto de entrada (API, Celery, Scripts) sea seguro por defecto.
4. **Inmutabilidad Post-Emisión**: Los registros con relevancia legal o contable deben bloquear la edición de campos críticos mediante `clean()` en el modelo.

## Implementación Paso a Paso

### 1. Validación DSV en Business Service

Cada vez que recibas un ID de una entidad relacionada (ej. `resolucion_id`, `proveedor_id`), valida su pertenencia al tenant:

```python
@staticmethod
def validar_pertenencia(modelo, pk, empresa_id, error_msg="Recurso no encontrado o no autorizado."):
    """Verifica que el objeto pertenezca al tenant actual."""
    if not modelo.objects.filter(pk=pk, empresa_id=empresa_id).exists():
        raise ValidationError(error_msg)
```

**Ejemplo de uso en `procesar_recurso`:**

```python
def procesar_gasto(self, data, empresa_id):
    # DSV: Validar que la resolución enviada sea del tenant actual
    resolucion_id = data.get('resolucion_id')
    self.validar_pertenencia(ResolucionDIAN, resolucion_id, empresa_id)
    
    # ... resto de la lógica ...
```

### 2. Inmutabilidad en Modelos

Protege los datos sensibles de modificaciones accidentales o malintencionadas:

```python
def clean(self):
    if self.pk: # Si el registro ya existe (es una actualización)
        original = type(self).objects.get(pk=self.pk)
        campos_inmutables = ['empresa_id', 'total', 'nit_receptor']
        
        for campo in campos_inmutables:
            if getattr(self, campo) != getattr(original, campo):
                raise ValidationError({campo: "Este campo es inmutable una vez creado."})
```

### 3. Tests de Aislamiento (Anti-IDOR)

Crea siempre un test que intente usar un ID de otro tenant:

```python
def test_idor_prevention(client, tenant1_user, tenant2_resource):
    client.force_login(tenant1_user)
    payload = {"resource_id": tenant2_resource.id, ...}
    
    # Debe fallar con 400 (ValidationError) o 404
    response = client.post("/api/v1/resource/", payload)
    assert response.status_code in (400, 403, 404)
```

## Checklist de Aplicación

- [ ] ¿El ViewSet hereda de un Mixin que inyecta `empresa_id`?
- [ ] ¿El Business Service valida todas las FKs del payload contra ese `empresa_id`?
- [ ] ¿Los campos críticos del modelo están protegidos en el método `clean()`?
- [ ] ¿Existe un test de aislamiento que use datos de dos tenants diferentes?
