# 📧 Configuración de Email / SMTP

## Variables de Entorno Requeridas

Para habilitar el envío de emails de invitación y notificaciones, configura las siguientes variables en tu archivo `.env`:

```env
# ============================================================================
# Email / SMTP
# ============================================================================

# Backend de email
# - Desarrollo: django.core.mail.backends.console.EmailBackend (muestra emails en consola)
# - Producción: django.core.mail.backends.smtp.EmailBackend (envía emails reales)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Configuración SMTP (solo se usa si EMAIL_BACKEND es smtp)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False

# Credenciales SMTP
# ⚠️ IMPORTANTE: Para Gmail, usar App Password (no la contraseña normal)
# Generar App Password: https://myaccount.google.com/apppasswords
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=***APP_PASSWORD_O_PASSWORD***

# Email remitente por defecto
DEFAULT_FROM_EMAIL=${EMAIL_HOST_USER}

# Email de contacto (opcional)
CONTACT_EMAIL=${EMAIL_HOST_USER}

# Timeout para conexiones SMTP (segundos)
EMAIL_TIMEOUT=20
```

## Configuración por Entorno

### Desarrollo (Local)

En desarrollo, usa el backend de consola para ver los emails en la terminal:

```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

Los emails se mostrarán en la consola cuando se ejecuten comandos Django o cuando el servidor esté corriendo.

### Producción

En producción, configura SMTP real:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com
```

## Configuración para Gmail

1. **Habilitar verificación en 2 pasos** en tu cuenta de Google
2. **Generar App Password**:
   - Ir a: https://myaccount.google.com/apppasswords
   - Seleccionar "Correo" y "Otro (nombre personalizado)"
   - Ingresar "SINTEL" como nombre
   - Copiar la contraseña generada (16 caracteres)
3. **Usar la App Password** en `EMAIL_HOST_PASSWORD` (no tu contraseña normal)

## Configuración para Otros Proveedores

### Outlook / Office 365

```env
EMAIL_HOST=smtp.office365.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
```

### SendGrid

```env
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your-sendgrid-api-key
```

### Amazon SES

```env
EMAIL_HOST=email-smtp.us-east-1.amazonaws.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-ses-smtp-username
EMAIL_HOST_PASSWORD=your-ses-smtp-password
```

## Verificación

Para verificar que la configuración de email funciona:

```bash
# En el shell de Django
python manage.py shell

# Probar envío de email
from django.core.mail import send_mail
send_mail(
    'Test Email',
    'Este es un email de prueba.',
    'from@example.com',
    ['to@example.com'],
    fail_silently=False,
)
```

## Uso en el Sistema

El sistema usa esta configuración para:

1. **Invitaciones de Owners**: Envío de emails con tokens de activación cuando se crea un nuevo tenant
2. **Notificaciones**: Emails de notificación para eventos importantes (futuro)

## Seguridad

⚠️ **IMPORTANTE**:
- **NUNCA** commits el archivo `.env` al repositorio
- Usa variables de entorno en producción (Docker, Kubernetes, etc.)
- Para Gmail, usa **App Passwords** en lugar de contraseñas normales
- Considera usar servicios de email transaccionales (SendGrid, SES) en producción
