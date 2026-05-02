# 📧 Flujo de Activación por Email - Guía de Uso

## ✅ Estado: Funcionalidad Activa

El sistema de invitación y activación por email está **completamente implementado y activo**.

## 🔄 Flujo Completo

### 1. Creación de Tenant (Onboarding)

Cuando se crea un nuevo tenant desde la consola pública (`/console/tenants/new/`):

1. **Usuario Owner se crea** con `set_unusable_password()` (sin contraseña usable)
2. **Token de invitación se genera** (firmado, TTL: 24 horas)
3. **Email de invitación se envía** automáticamente al owner
4. **URL de activación** se incluye en el email: `https://{tenant}.{base}/activate?token=...`

### 2. Recepción del Email

El owner recibe un email con:
- **Asunto**: "Activa tu cuenta en {nombre_tenant}"
- **Contenido**: Mensaje de bienvenida y botón/link de activación
- **Link**: URL absoluta al subdominio del tenant con token de activación

### 3. Activación en el Subdominio

El owner accede al link en el email:

1. **GET `/activate?token=...`**:
   - Valida el token (firma y TTL)
   - Verifica que el token corresponda al tenant actual
   - Muestra formulario de activación

2. **POST `/activate?token=...`**:
   - Valida token nuevamente
   - Verifica membresía activa en el tenant
   - Establece contraseña del usuario (`set_password()`)
   - Loguea automáticamente al usuario
   - Redirige a `/dashboard/`

## 🧪 Pruebas

### Verificar Configuración

```bash
docker compose exec web python scripts/test_email_config.py
```

Este script verifica:
- ✅ Configuración de email cargada correctamente
- ✅ Conexión SMTP funcionando
- ✅ Envío de email de prueba
- ✅ Servicio de invitaciones funcionando
- ✅ Generación y verificación de tokens

### Crear Tenant de Prueba

1. **Acceder a la consola pública**: `http://sintel.com/console/tenants/new/`
2. **Completar formulario**:
   - Nombre: "Empresa Test"
   - Schema: "empresa_test"
   - Dominio: "empresa-test.localhost" (o subdominio real)
   - Email Owner: tu email real
3. **Crear tenant**: El sistema enviará automáticamente el email de invitación
4. **Verificar email**: Revisar bandeja de entrada (o spam)
5. **Activar cuenta**: Hacer clic en el link del email

## 📋 Checklist de Verificación

- [x] Configuración de email en `settings.py`
- [x] Variables de entorno en `.env`
- [x] Servicio de invitaciones implementado
- [x] Vista de activación implementada
- [x] Templates de email creados
- [x] Ruta `/activate/` registrada
- [x] Integración en onboarding completa
- [x] Pruebas de configuración pasando

## 🔧 Configuración Requerida

### Variables en `.env`

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com
```

### Para Gmail

1. Habilitar verificación en 2 pasos
2. Generar App Password: https://myaccount.google.com/apppasswords
3. Usar App Password en `EMAIL_HOST_PASSWORD`

## 🚀 Uso en Producción

1. **Configurar SMTP real** en `.env` (no usar console backend)
2. **Verificar dominio** en el proveedor de email
3. **Configurar SPF/DKIM** para mejor deliverability
4. **Monitorear logs** de envío de emails
5. **Configurar rate limiting** si es necesario

## 📝 Logs

Los logs del sistema muestran:
- ✅ Token generado: `user_id=X, tenant_id=Y, ttl=24 horas`
- ✅ Email enviado: `user=email@example.com, tenant=schema_name`
- ✅ URL de activación: `http://tenant.domain/activate?token=...`
- ⚠️ Errores de envío (si ocurren)

## 🔒 Seguridad

- **Tokens firmados** con `SECRET_KEY` de Django
- **TTL de 24 horas** (configurable)
- **Validación de membresía** antes de activar
- **One-time use** implícito (token se valida una vez)
- **Validación de tenant** (token solo válido para el tenant correcto)

## 📚 Referencias

- **Configuración de email**: `documentacion/VARIABLES_ENTORNO_EMAIL.md`
- **Arquitectura general**: `documentacion/arquitectura_general.md` (v2.24)
- **Flujo de creación**: `documentacion/informe_flujo_creacion_tenant_y_roles.md` (v2.0)
