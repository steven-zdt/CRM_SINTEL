# 🛡️ Configuración de Dominios del Tenant Público

## ✅ Estado: Sistema Idempotente Implementado

El sistema garantiza que los dominios del tenant público (`sintel.com`, `localhost`, `127.0.0.1`) existan **siempre**, incluso después de reinicios de Docker o limpiezas de base de datos.

## 🔧 Configuración

### Variables de Entorno

Añadir a `.env`:

```env
# Dominios que DEBEN existir SIEMPRE para el tenant público
# Separados por coma, el primero será el primario
PUBLIC_TENANT_DOMAINS=sintel.com,localhost,127.0.0.1

# (opcional) Modo protección: si es True, no modifica dominios existentes
PUBLIC_DOMAIN_PROTECT=False
```

### Valores por Defecto

Si no se configuran las variables de entorno:
- `PUBLIC_TENANT_DOMAINS`: `sintel.com,localhost,127.0.0.1`
- `PUBLIC_DOMAIN_PROTECT`: `False`
- Dominio primario: El primero de la lista (`sintel.com`)

## 🚀 Ejecución Automática

El comando se ejecuta **automáticamente** en el `entrypoint.sh` después de:
1. Aplicar migraciones
2. Configurar el tenant público

```bash
# En entrypoint.sh (línea ~93)
python manage.py ensure_public_domains --verbosity 0
```

## 📋 Comando Manual

### Uso Básico

```bash
# Asegurar dominios (usa variables de entorno o valores por defecto)
docker compose exec web python manage.py ensure_public_domains

# Simulación (dry-run)
docker compose exec web python manage.py ensure_public_domains --dry-run

# Especificar dominios manualmente
docker compose exec web python manage.py ensure_public_domains --domains "sintel.com,localhost"

# Especificar dominio primario
docker compose exec web python manage.py ensure_public_domains --primary "sintel.com"
```

### Opciones

- `--domains`: Lista de dominios separados por coma (sobrescribe `PUBLIC_TENANT_DOMAINS`)
- `--primary`: Dominio que debe ser primario (sobrescribe el primero de la lista)
- `--dry-run`: Simular cambios sin guardar en la base de datos

## 🔍 Comportamiento

### Idempotente

- **Crea** dominios que no existen
- **Marca como primario** el dominio especificado si no lo es
- **NO elimina** dominios existentes
- **NO modifica** dominios que ya están correctamente configurados

### No Destructivo

- Si `PUBLIC_DOMAIN_PROTECT=True`, no modifica dominios existentes
- Solo añade dominios faltantes
- Respeta la configuración existente

### Validación

- Normaliza dominios (sin protocolo/www/puerto/rutas)
- Valida FQDN (excepto `localhost` y `127.0.0.1` para desarrollo)
- Omite dominios inválidos con advertencia

## 📊 Ejemplo de Salida

```
============================================================
🛡️ GARANTIZANDO DOMINIOS DEL TENANT PÚBLICO
============================================================

📋 Configuración:
   Dominios requeridos: sintel.com, localhost, 127.0.0.1
   Dominio primario: sintel.com
   Modo protección: Desactivado
   Modo: EJECUCIÓN REAL

✅ Tenant público encontrado: SINTEL Global
  ⭐ PRIMARIO sintel.com (creado)
     localhost (ya existe)
     127.0.0.1 (ya existe)

============================================================
📋 RESUMEN
============================================================
  Dominios creados: 1
  Dominios actualizados: 0
  Dominios sin cambios: 2
  Errores/omitidos: 0

✅ 1 dominio(s) procesado(s) exitosamente

📋 Dominios finales del tenant público:
  ⭐ PRIMARIO sintel.com
     localhost
     127.0.0.1
```

## 🔄 Flujo de Inicio

1. **Docker inicia** → `entrypoint.sh`
2. **Espera BD** → `wait_for_db()`
3. **Aplica migraciones** → `migrate_schemas --shared`
4. **Configura tenant público** → `setup_public_tenant`
5. **Garantiza dominios** → `ensure_public_domains` ⭐ **NUEVO**
6. **Inicia servidor** → `runserver`

## ⚠️ Notas Importantes

1. **Orden de ejecución**: El comando se ejecuta **después** de `setup_public_tenant` para asegurar que el tenant público exista.

2. **Modo protección**: Si `PUBLIC_DOMAIN_PROTECT=True`, el comando solo crea dominios faltantes, no modifica existentes.

3. **Producción**: En producción, asegúrate de que `PUBLIC_TENANT_DOMAINS` incluya solo los dominios necesarios:
   ```env
   PUBLIC_TENANT_DOMAINS=sintel.com
   PUBLIC_DOMAIN_PROTECT=True
   ```

4. **Desarrollo**: En desarrollo, incluye `localhost` y `127.0.0.1`:
   ```env
   PUBLIC_TENANT_DOMAINS=sintel.com,localhost,127.0.0.1
   ```

## 🐛 Troubleshooting

### Dominios no se crean

1. Verificar que el tenant público existe:
   ```bash
   docker compose exec web python manage.py shell -c "from apps.public.tenants.models import Client; from django_tenants.utils import schema_context; with schema_context('public'): print(Client.objects.get(schema_name='public').nombre)"
   ```

2. Verificar variables de entorno:
   ```bash
   docker compose exec web env | grep PUBLIC_TENANT
   ```

3. Ejecutar manualmente con verbosidad:
   ```bash
   docker compose exec web python manage.py ensure_public_domains --verbosity 2
   ```

### Dominio primario incorrecto

1. Verificar dominio primario actual:
   ```bash
   docker compose exec web python manage.py shell -c "from apps.public.tenants.models import Domain; from django_tenants.utils import schema_context; from apps.public.tenants.models import Client; with schema_context('public'): public = Client.objects.get(schema_name='public'); primary = Domain.objects.filter(tenant=public, is_primary=True).first(); print(f'Primario: {primary.domain if primary else \"Ninguno\"}')"
   ```

2. Forzar dominio primario:
   ```bash
   docker compose exec web python manage.py ensure_public_domains --primary "sintel.com"
   ```

## 📚 Referencias

- **Comando**: `apps/public/tenants/management/commands/ensure_public_domains.py`
- **Entrypoint**: `entrypoint.sh` (línea ~93)
- **Configuración dominio principal**: `documentacion/CONFIGURACION_DOMINIO_PRINCIPAL.md`
- **Arquitectura**: `documentacion/arquitectura_general.md` (v2.25)
