# ✅ Alineación del Formulario de Creación de Tenants (v2.29)

**Fecha:** 2026-01-30  
**Versión:** v2.29  
**Estado:** ✅ **ALINEADO Y VERIFICADO**

---

## 🎯 Objetivo

Eliminar campos de contraseña del formulario de creación de tenants y alinear con la política v2.29: **Onboarding sin Contraseñas - Activación Exclusiva**.

---

## ✅ Cambios Implementados

### 1. Template del Formulario (`apps/public/console/templates/console/pages/tenants/new.html`)

**Cambios:**
- ✅ Eliminado campo `owner_password` (líneas 164-182)
- ✅ Agregado bloque informativo sobre activación v2.29
- ✅ Actualizado campo `dominio_fqdn` a opcional (se autogenera si no se proporciona)
- ✅ Actualizada descripción del formulario

**Campos del Formulario (v2.29):**
1. ✅ `nombre` (requerido) - Nombre de la empresa
2. ✅ `schema_name` (opcional) - Código del tenant (se autogenera si no se proporciona)
3. ✅ `dominio_fqdn` (opcional) - Dominio FQDN (se autogenera como `{schema}.{TENANT_DOMAIN_BASE}`)
4. ✅ `owner_email` (requerido) - Email del propietario
5. ❌ `owner_password` (ELIMINADO) - Ya no se solicita
6. ✅ `paid_until` (opcional) - Fecha de vencimiento
7. ✅ `on_trial` (opcional) - Período de prueba

**Bloque Informativo Agregado:**
```html
<!-- Información de Activación (v2.29) -->
<div class="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-lg">
  <h3>Activación del Propietario (v2.29)</h3>
  <p>
    El propietario recibirá un email de invitación con un enlace de activación.
    Deberá acceder a https://{dominio}/activate?token=... para establecer su contraseña.
  </p>
  <p>
    <strong>No se requiere contraseña en el onboarding.</strong>
  </p>
</div>
```

### 2. JavaScript del Formulario (`apps/public/console/static/js/tenants_manager.js`)

**Cambios:**
- ✅ Eliminada lectura de `owner_password` (línea 518)
- ✅ Eliminada validación de `owner_password` (líneas 533-536)
- ✅ Eliminado `owner_password` del payload (línea 573)
- ✅ Actualizado autogeneración de `dominio_fqdn` para usar `TENANT_DOMAIN_BASE`
- ✅ `dominio_fqdn` ahora puede ser `null` (se autogenera en backend)

**Código Actualizado:**
```javascript
// ⚠️ v2.29: owner_password ELIMINADO
const formData = {
    nombre: nombre,
    schema_name: schemaName,
    dominio_fqdn: dominioFqdn || null,  // Opcional: se autogenera si no se proporciona
    owner_email: ownerEmail,
    // ⚠️ v2.29: owner_password ELIMINADO - NO se acepta password en onboarding
    paid_until: paidUntil,
    on_trial: onTrial
};
```

### 3. Serializer (Ya Implementado en v2.29)

**Validación:**
- ✅ Rechaza campos `password`, `password1`, `password2`, `owner_password`
- ✅ Mensaje de error claro indicando que el password se establece en la activación

---

## 📋 Flujo Completo (v2.29)

### 1. Usuario Completa el Formulario
- ✅ Ingresa nombre, schema_name (opcional), dominio_fqdn (opcional), owner_email
- ❌ NO ingresa contraseña (campo eliminado)
- ✅ Ve información sobre activación vía email

### 2. JavaScript Envía Payload
- ✅ Payload sin `owner_password`
- ✅ `dominio_fqdn` puede ser `null` (se autogenera)

### 3. Serializer Valida
- ✅ Rechaza cualquier campo de password si se envía
- ✅ Valida y autogenera `dominio_fqdn` si no se proporciona

### 4. Servicio Crea Tenant
- ✅ Crea usuario con `set_unusable_password()`
- ✅ Genera token de invitación
- ✅ Envía email con link de activación

### 5. Propietario Activa
- ✅ Recibe email con link `https://{dominio}/activate?token=...`
- ✅ Accede al link y establece su contraseña
- ✅ Se loguea automáticamente y redirige a dashboard

---

## 🔒 Garantías de Seguridad

1. ✅ **Formulario sin password**: Campo físicamente eliminado del template
2. ✅ **JavaScript sin password**: No lee, valida ni envía `owner_password`
3. ✅ **Serializer rechaza password**: Validación en `to_internal_value()` rechaza campos de password
4. ✅ **Servicio sin password**: Owner siempre se crea con `set_unusable_password()`
5. ✅ **Activación única**: Solo funciona si el usuario NO tiene password usable

---

## 📚 Archivos Modificados

1. ✅ `apps/public/console/templates/console/pages/tenants/new.html` - Eliminado campo password, agregado bloque informativo
2. ✅ `apps/public/console/static/js/tenants_manager.js` - Eliminado manejo de password
3. ✅ `documentacion/ALINEACION_FORMULARIO_TENANTS_v2.29.md` - Documentación nueva

---

## 🧪 Verificación

### 1. Template
- ✅ Campo `owner_password` eliminado
- ✅ Bloque informativo sobre activación agregado
- ✅ Campo `dominio_fqdn` marcado como opcional

### 2. JavaScript
- ✅ No lee `owner_password`
- ✅ No valida `owner_password`
- ✅ No envía `owner_password` en payload

### 3. Serializer
- ✅ Rechaza `owner_password` con mensaje claro
- ✅ Autogenera `dominio_fqdn` si no se proporciona

---

## ✅ Estado Final

- ✅ **Formulario alineado**: Sin campos de password
- ✅ **JavaScript alineado**: No maneja password
- ✅ **Serializer alineado**: Rechaza password (v2.29)
- ✅ **Servicio alineado**: Crea usuario sin password usable (v2.29)
- ✅ **Documentación actualizada**: Flujo completo documentado

---

**Fecha:** 2026-01-30  
**Versión:** v2.29  
**Estado:** ✅ **ALINEADO Y VERIFICADO**
