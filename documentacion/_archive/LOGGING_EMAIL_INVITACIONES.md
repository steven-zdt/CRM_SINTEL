# 📧 Logging y Diagnóstico de Emails de Invitación

## ✅ Estado: Logging Instrumentado y Funcional

El sistema de logging para emails de invitación está **completamente instrumentado** y proporciona trazas detalladas de cada paso del proceso.

## 🔍 Configuración de Logging

### Settings.py

```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "level": "INFO",
        },
    },
    "loggers": {
        # Logger del servicio de invitaciones
        "apps.public.tenants.services.invitations": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        # Logger del servicio de onboarding
        "apps.services.onboarding.empresa_service": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        # Logger de Django mail
        "django.core.mail": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
```

## 📋 Logs Generados

### 1. Generación de Token

```
INFO ✅ Token de invitación generado: user_id=X, tenant_id=Y, ttl=24 horas
```

### 2. Construcción de URL

```
INFO ✅ URL de activación construida: http://tenant.sintel.com/activate?token=...
```

### 3. Inicio del Envío

```
INFO 📧 Iniciando envío de email de invitación: user=email@example.com, tenant=schema_name, activation_url=...
```

### 4. Renderizado de Templates

```
INFO 📝 Renderizando templates de email para email@example.com
```

### 5. Envío de Email

```
INFO 📤 Enviando email: from=remitente@example.com, to=['destino@example.com'], subject='...', backend=..., host=..., port=...
```

### 6. Resultado

**Éxito:**
```
INFO ✅ Email de invitación ENVIADO EXITOSAMENTE: user=email@example.com, tenant=schema_name, activation_url=...
```

**Error (Desarrollo):**
```
WARNING ⚠️ Modo desarrollo: continuando sin email. URL de activación disponible: ...
```

**Error (Producción):**
```
ERROR ❌ ERROR enviando email de invitación: user=..., tenant=..., error=...
ERROR ❌ FALLO CRÍTICO en producción: No se pudo enviar email de invitación. Revisar configuración SMTP.
```

## 🧪 Script de Prueba

### Uso

```bash
# Probar con email específico
docker compose exec web python scripts/test_email_sending.py tu-email@example.com

# Probar con email por defecto (DEFAULT_FROM_EMAIL)
docker compose exec web python scripts/test_email_sending.py
```

### Pruebas Incluidas

1. **Configuración del Backend**: Verifica EMAIL_BACKEND, EMAIL_HOST, etc.
2. **Renderizado de Templates**: Prueba renderizado HTML y texto plano
3. **Email Simple**: Envía un email de prueba básico
4. **Email de Invitación**: Prueba el flujo completo (token + email)

### Salida Esperada

```
============================================================
🧪 PRUEBAS DE ENVÍO DE EMAIL DE INVITACIÓN
============================================================

📧 Email de destino: tu-email@example.com

============================================================
🔍 PRUEBA 1: Configuración del Backend de Email
============================================================
  ✅ Conexión exitosa

============================================================
🔍 PRUEBA 2: Renderizado de Templates
============================================================
  ✅ Template HTML renderizado (1930 caracteres)
  ✅ Template texto plano renderizado (439 caracteres)

============================================================
🔍 PRUEBA 3: Envío de Email Simple
============================================================
  ✅ Email enviado exitosamente

============================================================
🔍 PRUEBA 4: Envío de Email de Invitación (Flujo Completo)
============================================================
INFO 📧 Iniciando envío de email de invitación...
INFO 📝 Renderizando templates de email...
INFO 📤 Enviando email: from=..., to=[...], subject='...', backend=...
INFO ✅ Email de invitación ENVIADO EXITOSAMENTE: user=..., tenant=..., activation_url=...
  ✅ Email de invitación enviado exitosamente

============================================================
📋 RESUMEN DE PRUEBAS
============================================================
  ✅ PASÓ: Backend de Email
  ✅ PASÓ: Renderizado de Templates
  ✅ PASÓ: Email Simple
  ✅ PASÓ: Email de Invitación

✅ Todas las pruebas pasaron correctamente
```

## 🔍 Verificación en Onboarding

Cuando se crea un tenant desde la consola, los logs muestran:

```
INFO 📧 Iniciando proceso de invitación por email: user=email@example.com, tenant=schema_name
INFO 🔑 Generando token de invitación para user_id=X, tenant_id=Y
INFO ✅ Token de invitación generado (TTL: 24 horas)
INFO 🌐 Construyendo URL de activación para dominio: tenant.sintel.com
INFO ✅ URL de activación construida: http://tenant.sintel.com/activate?token=...
INFO 📤 Invocando send_invitation_email para user=email@example.com
INFO ✅ PROCESO DE INVITACIÓN COMPLETADO: user=..., tenant=..., activation_url=...
```

## 🐛 Diagnóstico de Problemas

### Email no se envía

1. **Verificar logs**:
   ```bash
   docker compose logs -f web | grep -i "invitación\|email\|mail"
   ```

2. **Verificar configuración**:
   ```bash
   docker compose exec web python scripts/test_email_config.py
   ```

3. **Probar envío directo**:
   ```bash
   docker compose exec web python scripts/test_email_sending.py tu-email@example.com
   ```

### Logs no aparecen

1. **Verificar nivel de logging** en `settings.py`
2. **Verificar que el logger esté configurado** correctamente
3. **Revisar que los handlers estén activos**

### Errores SMTP

Los logs muestran el error completo con stacktrace:

```
ERROR ❌ ERROR enviando email de invitación: user=..., tenant=..., error=...
Traceback (most recent call last):
  ...
```

## 📊 Niveles de Log

- **INFO**: Proceso normal (generación de token, envío exitoso)
- **WARNING**: Problemas no críticos (modo desarrollo sin SMTP)
- **ERROR**: Errores críticos (fallo de SMTP en producción)

## 🔗 Referencias

- **Configuración de email**: `documentacion/VARIABLES_ENTORNO_EMAIL.md`
- **Flujo de activación**: `documentacion/FLUJO_ACTIVACION_EMAIL.md`
- **Script de prueba**: `scripts/test_email_sending.py`
- **Script de verificación**: `scripts/test_email_config.py`
