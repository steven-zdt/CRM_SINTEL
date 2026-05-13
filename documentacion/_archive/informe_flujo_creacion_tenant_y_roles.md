# 📋 Informe Detallado: Flujo de Creación de Tenant y Manejo de Roles de Usuarios

**Fecha:** 2026-01-30  
**Versión:** 2.0 (Actualizado v2.25)  
**Estado:** ✅ Documentación completa del flujo end-to-end con sistema de invitación/activación + Autogeneración de dominios FQDN

---

## 📑 Tabla de Contenidos

1. [Visión General del Flujo](#visión-general-del-flujo)
2. [Paso 1: Inicio desde la Consola Pública](#paso-1-inicio-desde-la-consola-pública)
3. [Paso 2: Creación del Usuario Global (Owner)](#paso-2-creación-del-usuario-global-owner)
4. [Paso 3: Creación del Tenant (Client)](#paso-3-creación-del-tenant-client)
5. [Paso 4: Creación del Dominio](#paso-4-creación-del-dominio)
6. [Paso 5: Creación de TenantMembership](#paso-5-creación-de-tenantmembership)
7. [Paso 6: Creación de TenantProfile (Opcional)](#paso-6-creación-de-tenantprofile-opcional)
8. [Paso 7: Generación de Token de Invitación y Envío de Email](#paso-7-generación-de-token-de-invitación-y-envío-de-email) ⭐ v2.24
9. [Paso 8: Activación del Owner en el Subdominio](#paso-8-activación-del-owner-en-el-subdominio) ⭐ v2.24
10. [Paso 9: Acceso y Login](#paso-9-acceso-y-login)
11. [Modelos y Relaciones](#modelos-y-relaciones)
12. [Diagrama de Flujo](#diagrama-de-flujo)

---

## 🎯 Visión General del Flujo

El proceso de creación de un tenant privado en SINTEL sigue un flujo atómico y transaccional que garantiza la integridad de los datos. El flujo completo abarca desde la interfaz de consola hasta el acceso del usuario propietario al tenant.

### Flujo Completo (End-to-End)

```
1. Consola Pública (/console/tenants/new/)
   ↓
2. JavaScript (tenants_manager.js) → POST /api/public/v1/tenants/onboard/
   ↓
3. DRF ViewSet (ClientViewSet.onboard) → Validación con Serializer
   ↓
4. Servicio de Onboarding (crear_tenant_con_owner) → @transaction.atomic
   ├─ 4.1. Crear/obtener User (apps/public/accounts) → set_unusable_password() ⭐ v2.24
   ├─ 4.2. Crear Client (apps/public/tenants) → auto_create_schema=True
   ├─ 4.3. Crear Domain (apps/public/tenants) → is_primary=True
   ├─ 4.4. Crear TenantMembership (apps/public/tenants) → rol=ADMIN, is_primary_admin=True
   ├─ 4.5. Crear TenantProfile (apps/tenant/perfil) → Opcional, dentro de schema_context
   └─ 4.6. Generar token de invitación y enviar email ⭐ v2.24
   ↓
5. Respuesta 201 → {client_id, domain, membership_id, login_url, activation_url} ⭐ v2.24
   ↓
6. JavaScript muestra activation_url al usuario (o login_url si no hay invitación)
   ↓
7. Owner recibe email con link → https://cliente.sintel.com/activate?token=... ⭐ v2.24
   ↓
8. Owner accede a /activate?token=... en el subdominio del tenant ⭐ v2.24
   ↓
9. ActivateOwnerView valida token y muestra formulario de activación ⭐ v2.24
   ↓
10. Owner establece password → user.set_password() + login() automático ⭐ v2.24
   ↓
11. Redirección a /dashboard/ → Acceso completo al tenant
```

---

## 📍 Paso 1: Inicio desde la Consola Pública

### Ubicación
- **Template:** `apps/public/console/templates/console/pages/tenants/new.html`
- **URL:** `/console/tenants/new/`
- **Acceso:** Solo usuarios con `is_staff=True` (requiere autenticación en dominio público)

### Formulario HTML

El formulario captura los siguientes datos:

```html
<form id="tenant-form" 
      data-api-onboard-url="/api/public/v1/tenants/onboard/"
      onsubmit="return false;">
  
  <!-- Campos del formulario -->
  - nombre: Nombre de la empresa (requerido)
  - schema_name: Código del tenant (opcional, se genera automáticamente)
  - dominio_fqdn: Dominio FQDN sin puerto/www (requerido)
  - owner_email: Email del propietario (requerido)
  - owner_password: Contraseña del propietario (requerido, mínimo 8 caracteres)
  - paid_until: Fecha de vencimiento (opcional)
  - on_trial: Marcar como período de prueba (checkbox, default: true)
</form>
```

### Validación JavaScript

El archivo `apps/public/console/static/js/tenants_manager.js` incluye:

1. **Validación en tiempo real de `schema_name`:**
   - Solo letras minúsculas, números y guiones bajos
   - Máximo 63 caracteres
   - No puede ser "public" (reservado)
   - No puede empezar ni terminar con guión bajo

2. **Auto-generación de campos:**
   - Si `schema_name` está vacío, se genera desde `nombre` (slugify)
   - Si `dominio_fqdn` está vacío, se genera como `{schema_name}.localhost`

### Envío del Formulario

```javascript
// Función initTenantForm() en tenants_manager.js
function initTenantForm() {
    const form = document.getElementById('tenant-form');
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Recopilar datos del formulario
        const formData = {
            nombre: document.getElementById('nombre').value,
            schema_name: document.getElementById('schema_name').value || null,
            dominio_fqdn: document.getElementById('dominio_fqdn').value || null,
            owner_email: document.getElementById('owner_email').value,
            owner_password: document.getElementById('owner_password').value,
            paid_until: document.getElementById('paid_until').value || null,
            on_trial: document.getElementById('on_trial').checked
        };
        
        // POST a /api/public/v1/tenants/onboard/
        const response = await fetch('/api/public/v1/tenants/onboard/', {
            method: 'POST',
            headers: getHeaders(), // Incluye CSRF y JWT
            body: JSON.stringify(formData),
            credentials: 'include' // Cookies de sesión
        });
        
        // Manejo de respuesta
        if (response.ok) {
            const data = await response.json();
            // Mostrar login_url al usuario
            showNotification(`Tenant creado exitosamente. Login URL: ${data.login_url}`, 'success');
        } else {
            // Mostrar errores de validación
            handleAPIError(response);
        }
    });
}
```

---

## 📍 Paso 2: Creación del Usuario Global (Owner)

### Ubicación
- **Modelo:** `apps/public/accounts/models.py` → `User(AbstractUser)`
- **Service Layer:** `apps/public/accounts/api/services/user_service.py` → `create_user_service()`
- **Manager:** `apps/public/accounts/managers.py` → `UserManager`

### Esquema de Base de Datos
- **Esquema:** `public` (SHARED_APPS)
- **Tabla:** `accounts_user`
- **Características:**
  - Email único y obligatorio
  - Username generado automáticamente desde email (si el modelo lo tiene)
  - Password hasheado con `set_password()` (nunca texto plano)

### Flujo de Creación

#### 2.1. Verificación de Usuario Existente

```python
# apps/services/onboarding/empresa_service.py (línea 202)
user = User.objects.filter(email=email).first()

if user:
    # Usuario existente: verificar que tenga password válido
    if not user.has_usable_password():
        user.set_password(owner_password)
        user.save(update_fields=["password"])
    logger.info("✅ Usuario existente en public: %s", email)
```

#### 2.2. Creación de Usuario Nuevo

```python
# apps/services/onboarding/empresa_service.py (línea 216)
user = create_user_service(
    email=email,
    password=owner_password,
    is_staff=owner_is_staff,  # Default: True
    is_active=owner_is_active,  # Default: True
)
```

#### 2.3. Service Layer: `create_user_service()`

```python
# apps/public/accounts/api/services/user_service.py

@transaction.atomic
def create_user_service(
    *,
    email: str,
    password: str,
    first_name: str = "",
    last_name: str = "",
    is_staff: bool = False,
    is_active: bool = True,
    telefono: str = None,
) -> User:
    """
    Crea un nuevo usuario global (esquema public).
    
    ⚠️ SEGURIDAD:
    - Normaliza email a minúsculas
    - Usa set_password() para hashing seguro (nunca texto plano)
    - Genera username único si el modelo lo tiene (compatibilidad con AbstractUser)
    """
    # Normalizar email
    email = (email or "").strip().lower()
    if not email or not password:
        raise ValueError("Email y password son obligatorios.")
    
    # Preparar kwargs para crear usuario
    user_kwargs = {
        "email": email,
        "first_name": first_name or "",
        "last_name": last_name or "",
        "is_staff": is_staff,
        "is_active": is_active,
    }
    
    # Si existe el campo username, generarlo de forma única
    if _user_has_field("username"):
        user_kwargs["username"] = _generate_unique_username(email)
    
    # Crear usuario
    user = User(**user_kwargs)
    user.set_password(password)  # ⚠️ CRÍTICO: Hashing seguro
    
    try:
        user.save()
    except IntegrityError as e:
        raise IntegrityError("No se pudo crear el usuario: email o username ya existente.") from e
    
    return user
```

#### 2.4. Generación de Username Único

```python
# apps/public/accounts/api/services/user_service.py

def _generate_unique_username(email: str) -> str:
    """
    Genera un username único a partir del local-part del email.
    Evita colisiones añadiendo sufijos -1, -2, ...
    """
    base = (email.split("@")[0] if email else "user").strip().replace(" ", "").lower() or "user"
    candidate = base[:150]  # tamaño seguro (max_length de username en AbstractUser)
    
    if not User.objects.filter(username=candidate).exists():
        return candidate
    
    i = 1
    while True:
        cand = f"{base}-{i}"[:150]
        if not User.objects.filter(username=cand).exists():
            return cand
        i += 1
```

#### 2.5. UserManager: Validación Adicional

```python
# apps/public/accounts/managers.py

def _create_user(self, email, password, **extra_fields):
    if not email:
        raise ValueError("El email es obligatorio")
    
    email = self.normalize_email(email)
    username = extra_fields.pop("username", None)
    
    if not username:
        # Generar username desde el local-part del email
        local_part = email.split("@")[0] if "@" in email else email
        base = slugify(local_part.lower()) if local_part else "user"
        if not base or base.strip() == "":
            base = "user"
        username = base
        
        # Evitar colisiones
        Model = self.model
        i = 1
        while Model.objects.filter(username=username).exists():
            i += 1
            username = f"{base}{i}"
    
    # Asegurar que username no esté vacío
    if not username or username.strip() == "":
        username = "user"
        Model = self.model
        i = 1
        while Model.objects.filter(username=username).exists():
            i += 1
            username = f"user{i}"
    
    # Delegar en la implementación de Django
    return super()._create_user(
        username=username,
        email=email,
        password=password,
        **extra_fields,
    )
```

### Resultado del Paso 2

- ✅ Usuario creado en esquema `public` (tabla `accounts_user`)
- ✅ Email único y normalizado (minúsculas)
- ✅ Username único generado automáticamente
- ⚠️ **v2.24**: Password unusable (`set_unusable_password()`) - se establecerá en activación
- ✅ `is_staff=True` (permite acceso a admin)
- ✅ `is_active=True` (usuario activo)

**⚠️ CAMBIO v2.24:**
- El owner se crea **sin password usable** para mejorar la higiene de credenciales
- El password se establece durante la activación en el subdominio del tenant
- Si el usuario ya existe con password usable, se mantiene (compatibilidad hacia atrás)

---

## 📍 Paso 3: Creación del Tenant (Client)

### Ubicación
- **Modelo:** `apps/public/tenants/models.py` → `Client(TenantMixin)`
- **Esquema:** `public` (SHARED_APPS)
- **Tabla:** `tenants_client`

### Modelo Client

```python
# apps/public/tenants/models.py

class Client(TenantMixin):
    """
    Modelo de Tenant conforme a la instalación oficial de django-tenants.
    Configuración crítica: auto_create_schema = True.
    """
    nombre = models.CharField(max_length=100)
    paid_until = models.DateField(null=True, blank=True)
    on_trial = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    # ⚠️ CRÍTICO: django-tenants crea el esquema PostgreSQL automáticamente
    auto_create_schema = True
    auto_drop_schema = True
```

### Flujo de Creación

```python
# apps/services/onboarding/empresa_service.py (línea 240)

# 1. Validar schema_name
raw_schema = schema_name.strip().lower()
validate_schema_name(raw_schema)

# 2. Crear Client
client = Client(
    schema_name=raw_schema,
    nombre=nombre.strip(),
    paid_until=paid_until,
    on_trial=on_trial,
    is_active=True,
)

# 3. Guardar → django-tenants ejecuta migrate_schemas automáticamente
client.save()  # ⚠️ CRÍTICO: Crea esquema PostgreSQL + migra TENANT_APPS
```

### Proceso Automático de django-tenants

Cuando se llama `client.save()` con `auto_create_schema=True`:

1. **Crea el esquema PostgreSQL:**
   ```sql
   CREATE SCHEMA IF NOT EXISTS "acme";
   ```

2. **Ejecuta migraciones de TENANT_APPS:**
   ```python
   # django-tenants internamente ejecuta:
   call_command('migrate_schemas', schema_name=client.schema_name, interactive=False)
   ```

3. **Crea todas las tablas de TENANT_APPS en el nuevo esquema:**
   - `perfil_tenantprofile`
   - `empresa_empresa`
   - `facturas_*`
   - `contabilidad_*`
   - etc.

### Resultado del Paso 3

- ✅ Client creado en esquema `public` (tabla `tenants_client`)
- ✅ Esquema PostgreSQL creado automáticamente (ej: `acme`)
- ✅ Todas las tablas de TENANT_APPS migradas al nuevo esquema
- ✅ `is_active=True` (tenant activo y accesible)

---

## 📍 Paso 4: Creación del Dominio ⭐ v2.25

### Ubicación
- **Modelo:** `apps/public/tenants/models.py` → `Domain(DomainMixin)`
- **Esquema:** `public` (SHARED_APPS)
- **Tabla:** `tenants_domain`

### ⚠️ CAMBIO v2.25: Autogeneración de Dominio FQDN
- Si `dominio_fqdn` no se proporciona o es inválido, se autogenera como `<schema>.<TENANT_DOMAIN_BASE>`
- Ejemplo: schema `cliente` → dominio autogenerado `cliente.sintel.com`
- El dominio siempre debe ser un FQDN válido con TLD (ej: `.com`, `.local`, etc.)
- Si el dominio proporcionado no tiene TLD o no termina con `.<TENANT_DOMAIN_BASE>`, se autogenera

### Modelo Domain

```python
# apps/public/tenants/models.py

class Domain(DomainMixin):
    """Dominio asociado al tenant."""
    tenant = models.ForeignKey(
        Client,
        related_name="domains",
        on_delete=models.CASCADE
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant"],
                condition=models.Q(is_primary=True),
                name="unique_primary_domain_per_tenant",
            )
        ]
```

### Flujo de Creación (v2.25)

```python
# apps/services/onboarding/empresa_service.py

# 1. Construir dominio primario FQDN (autogeneración si no viene o es inválido)
# ⚠️ v2.25: _build_primary_domain() autogenera <schema>.<TENANT_DOMAIN_BASE> si:
#   - dominio_fqdn es None o vacío
#   - dominio_fqdn no es un FQDN válido
#   - dominio_fqdn no termina con .<TENANT_DOMAIN_BASE>
primary_fqdn = _build_primary_domain(client.schema_name, dominio_fqdn)
# Ejemplo: schema "cliente" → "cliente.sintel.com" (siempre con TLD)

# 2. Crear Domain (idempotente)
try:
    domain, created = Domain.objects.get_or_create(
        domain=primary_fqdn,
        defaults={"tenant": client, "is_primary": True},
    )
    if not created and domain.tenant_id != client.id:
        raise ValidationError(f"El dominio '{primary_fqdn}' ya está asociado a otro tenant.")
except IntegrityError:
    # Read-back para condiciones de carrera
    domain = Domain.objects.get(domain=primary_fqdn)
    if domain.tenant_id != client.id:
        raise ValidationError(f"El dominio '{primary_fqdn}' ya está asociado a otro tenant.")
```

### Normalización de Dominio

```python
# apps/public/tenants/utils.py

def normalize_domain(domain: str) -> str:
    """
    Normaliza un dominio FQDN eliminando protocolo, www, puerto y rutas.
    
    Ejemplos:
    - "https://acme.localhost:8000/admin/" → "acme.localhost"
    - "www.acme.com" → "acme.com"
    - "acme.localhost" → "acme.localhost"
    """
    # Eliminar protocolo
    domain = re.sub(r'^https?://', '', domain)
    
    # Eliminar www
    domain = re.sub(r'^www\.', '', domain)
    
    # Eliminar puerto
    domain = domain.split(':')[0]
    
    # Eliminar rutas
    domain = domain.split('/')[0]
    
    # Eliminar espacios y convertir a minúsculas
    domain = domain.strip().lower()
    
    return domain
```

### Resultado del Paso 4

- ✅ Domain creado en esquema `public` (tabla `tenants_domain`)
- ✅ Dominio normalizado (sin puerto, sin www, sin protocolo)
- ✅ **v2.25**: Dominio siempre es FQDN válido con TLD (ej: `cliente.sintel.com`)
- ✅ **v2.25**: Autogeneración automática si no se proporciona o es inválido
- ✅ `is_primary=True` (dominio principal del tenant)
- ✅ Relación ForeignKey con Client (CASCADE)
- ✅ Constraint único: solo un dominio primario por tenant

---

## 📍 Paso 5: Creación de TenantMembership

### Ubicación
- **Modelo:** `apps/public/tenants/models.py` → `TenantMembership`
- **Esquema:** `public` (SHARED_APPS)
- **Tabla:** `tenants_tenantmembership`

### Modelo TenantMembership

```python
# apps/public/tenants/models.py

class TenantMembership(models.Model):
    """
    Modelo de membresía de usuarios a tenants.
    
    Relaciona usuarios globales con tenants específicos,
    permitiendo que un usuario sea miembro de múltiples tenants
    con diferentes roles.
    """
    ROLE_CHOICES = (
        ("ADMIN", "Admin"),
        ("STAFF", "Staff"),
        ("USER", "User"),
    )
    
    client = models.ForeignKey(
        "tenants.Client",
        on_delete=models.CASCADE,
        related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # User (esquema public)
        on_delete=models.CASCADE,
        related_name="tenant_memberships"
    )
    rol = models.CharField(max_length=10, choices=ROLE_CHOICES, default="ADMIN")
    is_primary_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = (("client", "user"),)  # Un usuario solo puede tener una membresía por tenant
        indexes = [
            models.Index(fields=["client", "user"]),
        ]
    
    def clean(self):
        """
        Garantiza que solo exista un primary admin por tenant.
        """
        if self.is_primary_admin and self.client_id:
            qs = TenantMembership.objects.filter(
                client_id=self.client_id,
                is_primary_admin=True,
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            
            if qs.exists():
                raise ValidationError(
                    "Ya existe un administrador principal para este tenant. "
                    "Solo puede haber un 'is_primary_admin=True' por tenant."
                )
```

### Flujo de Creación

```python
# apps/services/onboarding/empresa_service.py (línea 273)

# Crear TenantMembership (idempotente)
membership, created = TenantMembership.objects.get_or_create(
    client=client,
    user=user,
    defaults={
        "rol": "ADMIN",
        "is_primary_admin": True,  # ⚠️ CRÍTICO: Owner es primary admin
        "is_active": True,
    },
)
```

### Características de TenantMembership

1. **Relación Many-to-Many implícita:**
   - Un `User` puede tener múltiples `TenantMembership` (uno por tenant)
   - Un `Client` puede tener múltiples `TenantMembership` (uno por usuario)

2. **Roles:**
   - `ADMIN`: Administrador completo del tenant
   - `STAFF`: Personal con permisos limitados
   - `USER`: Usuario estándar

3. **is_primary_admin:**
   - Solo puede haber UN `is_primary_admin=True` por tenant
   - Validado en `clean()` método del modelo
   - El owner creado en onboarding siempre tiene `is_primary_admin=True`

4. **is_active:**
   - Controla si el usuario tiene acceso activo al tenant
   - Si `is_active=False`, el middleware `require_tenant_membership` bloquea el acceso

### Resultado del Paso 5

- ✅ TenantMembership creado en esquema `public` (tabla `tenants_tenantmembership`)
- ✅ Relación User ↔ Client establecida
- ✅ `rol="ADMIN"` (administrador completo)
- ✅ `is_primary_admin=True` (administrador principal)
- ✅ `is_active=True` (acceso activo)
- ✅ Constraint único: un usuario solo puede tener una membresía por tenant

---

## 📍 Paso 6: Creación de TenantProfile (Opcional)

### Ubicación
- **Modelo:** `apps/tenant/perfil/models.py` → `TenantProfile`
- **Esquema:** Esquema del tenant (TENANT_APPS)
- **Tabla:** `perfil_tenantprofile` (en el esquema del tenant, ej: `acme.perfil_tenantprofile`)

### Modelo TenantProfile

```python
# apps/tenant/perfil/models.py

class TenantProfile(models.Model):
    """
    Perfil privado del colaborador dentro de un tenant específico.
    
    ⚠️ ARQUITECTURA MULTI-TENANT:
    - Este modelo vive en el esquema del tenant (TENANT_APPS)
    - Tiene una relación OneToOneField con User (que está en SHARED_APPS/public)
    - Django permite relaciones FK/OneToOne desde tenant hacia public (pero no al revés)
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,  # User (esquema public)
        on_delete=models.CASCADE,
        related_name='tenant_profile',
    )
    cargo = models.CharField(max_length=100)
    departamento = models.CharField(max_length=100, blank=True, null=True)
    telefono_corporativo = models.CharField(max_length=20, blank=True, null=True)
    avatar = models.ImageField(upload_to='perfiles/avatars/', blank=True, null=True)
    configuracion = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### Flujo de Creación (Opcional y Resiliente)

```python
# apps/services/onboarding/empresa_service.py (línea 287)

try:
    # 1. Verificar que la tabla existe
    required_tables = ["perfil_tenantprofile"]
    
    # 2. Forzar migraciones si faltan tablas
    _ensure_schema_ready(client, required_tables)
    
    # 3. Verificar que la tabla existe después de forzar migraciones
    if _table_exists(client.schema_name, "perfil_tenantprofile"):
        # 4. Ejecutar dentro del esquema del tenant
        with schema_context(client.schema_name):
            from apps.tenant.perfil.models import TenantProfile
            TenantProfile.objects.get_or_create(
                user=user,
                defaults={
                    "cargo": "Administrador Principal",
                    "departamento": "Gerencia",
                    "configuracion": {"theme": "light", "notifications": True},
                },
            )
        logger.info(f"✅ Perfil creado para usuario {user.email} en tenant {raw_schema}")
    else:
        # Tabla no existe: log de advertencia pero onboarding continúa
        logger.warning(
            "⚠️ Tabla 'perfil_tenantprofile' no existe en schema '%s'. "
            "Seed de perfil omitido. Onboarding continúa normalmente.",
            raw_schema
        )
except Exception as ex:
    # Error al crear perfil: log pero NO abortar onboarding
    logger.error(
        f"Error creando/actualizando TenantProfile para tenant '{raw_schema}': {ex}",
        exc_info=True,
    )
    # ⚠️ CRÍTICO: El onboarding SIEMPRE retorna login_url aunque el seed falle
```

### Funciones Auxiliares

```python
# apps/services/onboarding/empresa_service.py

def _table_exists(schema: str, table: str) -> bool:
    """
    Verifica si una tabla existe en el schema del tenant.
    """
    with connection.cursor() as cur:
        cur.execute("""
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = %s AND table_name = %s
            LIMIT 1
        """, [schema, table])
        return cur.fetchone() is not None

def _ensure_schema_ready(client: Client, required_tables: list[str] = None):
    """
    Verifica que el schema del tenant tenga las tablas requeridas.
    Si faltan, intenta forzar migración del schema del tenant.
    """
    if not required_tables:
        return
    
    missing = [t for t in required_tables if not _table_exists(client.schema_name, t)]
    if missing:
        logger.info(
            f"⚠️ Tablas faltantes en schema '{client.schema_name}': {missing}. "
            f"Forzando migraciones..."
        )
        call_command(
            "migrate_schemas",
            schema_name=client.schema_name,
            interactive=False,
            verbosity=0,
        )
```

### Características de TenantProfile

1. **Relación OneToOne con User:**
   - Un `User` puede tener UN `TenantProfile` por tenant
   - El `TenantProfile` vive en el esquema del tenant
   - El `User` vive en el esquema `public`

2. **Datos Específicos del Tenant:**
   - `cargo`: Cargo del colaborador en este tenant
   - `departamento`: Departamento al que pertenece
   - `telefono_corporativo`: Teléfono corporativo (diferente al personal)
   - `configuracion`: Preferencias de UI (JSON)

3. **Resiliencia:**
   - El seed de `TenantProfile` es OPCIONAL
   - Si la tabla no existe o hay errores, el onboarding continúa
   - El onboarding SIEMPRE retorna `login_url` aunque el seed falle

### Resultado del Paso 6

- ✅ TenantProfile creado en esquema del tenant (tabla `perfil_tenantprofile`)
- ✅ Relación OneToOne con User establecida
- ✅ Datos iniciales: cargo="Administrador Principal", departamento="Gerencia"
- ⚠️ OPCIONAL: Si falla, el onboarding continúa normalmente

---

## 📍 Paso 7: Generación de Token de Invitación y Envío de Email ⭐ v2.24

### Ubicación
- **Servicio:** `apps/public/tenants/services/invitations.py`
- **Esquema:** `public` (SHARED_APPS)

### Generación de Token

```python
# apps/public/tenants/services/invitations.py

def generate_invitation_token(user_id: int, tenant_id: int, ttl_hours: int = 24) -> str:
    """
    Genera un token de invitación firmado con TTL.
    
    ⚠️ SEGURIDAD:
    - Token firmado con SECRET_KEY de Django
    - Incluye user_id y tenant_id para validación
    - TTL configurable (default: 24 horas)
    - One-time use (se invalida tras uso)
    """
    payload = {
        'user_id': user_id,
        'tenant_id': tenant_id,
        'expires_at': (datetime.now() + timedelta(hours=ttl_hours)).isoformat(),
    }
    
    # Firmar con SECRET_KEY
    token = signing.dumps(payload, salt='tenant-owner-invitation')
    return token
```

### Construcción de URL de Activación

```python
# apps/public/tenants/services/invitations.py

def build_activation_url(domain: str, token: str) -> str:
    """
    Construye URL absoluta de activación en el subdominio del tenant.
    
    ⚠️ IMPORTANTE:
    - URL debe apuntar al subdominio del tenant (no al dominio público)
    - Protocolo HTTP en desarrollo, HTTPS en producción
    - Sin puerto explícito
    """
    protocol = "https" if not settings.DEBUG and getattr(settings, "SECURE_SSL_REDIRECT", False) else "http"
    return f"{protocol}://{domain}/activate?token={token}"
```

### Envío de Email

```python
# apps/public/tenants/services/invitations.py

def send_invitation_email(user: User, tenant, activation_url: str) -> bool:
    """
    Envía email de invitación al owner.
    
    ⚠️ IMPORTANTE:
    - Si no hay SMTP configurado, solo loguea (no falla)
    - Email incluye link absoluto al subdominio del tenant
    - Template HTML/texto plano
    """
    context = {
        'user': user,
        'tenant': tenant,
        'activation_url': activation_url,
        'tenant_name': getattr(tenant, 'nombre', 'Tenant'),
    }
    
    html_message = render_to_string('emails/owner_invitation.html', context)
    text_message = render_to_string('emails/owner_invitation.txt', context)
    
    send_mail(
        subject=f'Activa tu cuenta en {context["tenant_name"]}',
        message=text_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )
```

### Integración en Onboarding

```python
# apps/services/onboarding/empresa_service.py (línea 337)

# 7) Generar token de invitación y enviar email (solo si owner_email fue proporcionado)
activation_url = None
if owner_email and not admin_user_id:
    try:
        from apps.public.tenants.services.invitations import (
            generate_invitation_token,
            send_invitation_email,
            build_activation_url,
        )
        
        # Generar token (TTL: 24 horas)
        token = generate_invitation_token(user_id=user.id, tenant_id=client.id, ttl_hours=24)
        
        # Construir URL de activación
        activation_url = build_activation_url(domain.domain, token)
        
        # Enviar email
        send_invitation_email(user, client, activation_url)
    except Exception as e:
        # No abortar onboarding si falla el envío de email
        logger.error("⚠️ Error generando/enviando invitación: %s", e)
```

### Respuesta del Servicio

```python
# apps/services/onboarding/empresa_service.py (línea 377)

result = {
    "client_id": client.id,
    "domain": domain.domain,
    "membership_id": membership.id,
    "login_url": login_url,  # Para compatibilidad
    "activation_url": activation_url,  # ⭐ v2.24: URL de activación
}
```

### Resultado del Paso 7

- ✅ Token de invitación generado (firmado, TTL: 24 horas)
- ✅ URL de activación construida en el subdominio del tenant
- ✅ Email de invitación enviado (o logueado en desarrollo)
- ✅ `activation_url` incluido en respuesta del onboarding
- ⚠️ Resiliente: Si falla el envío, el onboarding continúa normalmente

---

## 📍 Paso 8: Activación del Owner en el Subdominio ⭐ v2.24

### Ubicación
- **Vista:** `apps/tenant/landing/views.py` → `ActivateOwnerView`
- **URL:** `/activate/` (en `TENANT_URLCONF`)
- **Template:** `apps/tenant/landing/templates/tenant/landing/activate.html`

### Flujo de Activación

#### 8.1. GET /activate?token=...

```python
# apps/tenant/landing/views.py

class ActivateOwnerView(FormView):
    """
    Vista de activación de owner en el subdominio del tenant (v2.24).
    
    ⚠️ FLUJO DE ACTIVACIÓN:
    - GET: Muestra formulario de activación si el token es válido
    - POST: Verifica token, valida membresía, establece password y loguea al usuario
    """
    template_name = 'tenant/landing/activate.html'
    form_class = ActivationForm
    
    def dispatch(self, request, *args, **kwargs):
        """
        Valida el token antes de procesar la request.
        """
        token = request.GET.get('token')
        if not token:
            messages.error(request, 'Token de activación no proporcionado.')
            return redirect('tenant_landing:login')
        
        # Verificar token
        from apps.public.tenants.services.invitations import verify_invitation_token
        payload = verify_invitation_token(token)
        
        if not payload:
            messages.error(request, 'Token de activación inválido o expirado.')
            return redirect('tenant_landing:login')
        
        # Almacenar payload en request
        request._activation_payload = payload
        request._activation_token = token
        
        return super().dispatch(request, *args, **kwargs)
```

#### 8.2. POST /activate?token=...

```python
# apps/tenant/landing/views.py

def form_valid(self, form):
    """
    Procesa el formulario de activación.
    
    ⚠️ FLUJO:
    1. Verificar token (ya validado en dispatch)
    2. Obtener usuario y tenant
    3. Validar membresía activa
    4. Establecer password
    5. Loguear usuario
    6. Redirigir a dashboard
    """
    from django.contrib.auth import get_user_model
    from apps.public.tenants.models import TenantMembership
    
    User = get_user_model()
    payload = getattr(self.request, '_activation_payload', None)
    
    # 1. Obtener usuario
    user = User.objects.get(pk=payload['user_id'], is_active=True)
    
    # 2. Obtener tenant (debe coincidir con el tenant activo)
    tenant = getattr(self.request, 'tenant', None)
    if not tenant or tenant.id != payload['tenant_id']:
        messages.error(self.request, 'El token no corresponde al tenant actual.')
        return redirect('tenant_landing:login')
    
    # 3. Validar membresía activa
    membership = TenantMembership.objects.filter(
        client=tenant,
        user=user,
        is_active=True,
    ).first()
    
    if not membership:
        messages.error(self.request, 'No tienes acceso a este tenant.')
        return redirect('tenant_landing:login')
    
    # 4. Establecer password
    password = form.cleaned_data['password']
    user.set_password(password)
    user.save(update_fields=['password'])
    
    # 5. Loguear usuario
    login(self.request, user)
    
    # 6. Redirigir a dashboard
    return redirect('/dashboard/')
```

### Formulario de Activación

```python
# apps/tenant/landing/views.py

class ActivationForm(Form):
    """
    Formulario para activación de owner (establecer contraseña).
    """
    password = CharField(min_length=8, required=True)
    password_confirm = CharField(min_length=8, required=True)
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise ValidationError('Las contraseñas no coinciden.')
        
        return cleaned_data
```

### Resultado del Paso 8

- ✅ Token validado (firma y TTL)
- ✅ Membresía verificada (usuario tiene acceso al tenant)
- ✅ Password establecido con `set_password()` (hash seguro)
- ✅ Usuario logueado automáticamente
- ✅ Redirección a `/dashboard/`
- ✅ Acceso completo al tenant

---

## 📍 Paso 9: Acceso y Login

### Acceso al Login URL

**⚠️ v2.24:** El owner debe activar su cuenta primero usando el token de invitación antes de poder hacer login.

**Flujo Normal (Usuario con password usable):**
El usuario accede a `http://acme.localhost/login/` (o `https://acme.sintel.com/login/` en producción).

### Resolución del Tenant por Hostname

1. **TenantMainMiddleware:**
   ```python
   # django-tenants resuelve el tenant por hostname
   # Busca en tenants_domain: domain='acme.localhost'
   # Encuentra: Domain(domain='acme.localhost', tenant=Client(schema_name='acme'))
   # Activa el esquema: connection.set_schema_to('acme')
   # Selecciona URLConf: request.urlconf = 'config.urls_tenant'
   ```

2. **URLConf del Tenant:**
   ```python
   # config/urls_tenant.py
   urlpatterns = [
       path("", include("apps.tenant.landing.urls")),  # "/", "/login/", "/dashboard/"
       # ...
   ]
   ```

3. **Rutas del Landing:**
   ```python
   # apps/tenant/landing/urls.py
   urlpatterns = [
       path("", views.TenantLandingView.as_view(), name="index"),
       path("login/", views.TenantLoginView.as_view(), name="login"),
       path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
   ]
   ```

### Vista de Login

```python
# apps/tenant/landing/views.py

class TenantLoginView(LoginView):
    """
    Vista de login HTML para tenants privados.
    
    ⚠️ INTEGRACIÓN CON DJANGO-TENANTS:
    - Usa LoginView de Django para procesar autenticación
    - TenantAwareBackend valida membresía del tenant automáticamente
    - Redirige a /dashboard/ después de login exitoso
    """
    template_name = 'tenant/landing/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        """Redirige al dashboard del tenant después de login exitoso."""
        return '/dashboard/'
```

### Template de Login

```html
<!-- apps/tenant/landing/templates/tenant/landing/login.html -->

<form method="post" action="{% url 'tenant_landing:login' %}">
    {% csrf_token %}
    
    <!-- Campo Username -->
    <input type="text" name="username" id="id_username" 
           placeholder="Ingresa tu usuario o email" required>
    
    <!-- Campo Password -->
    <input type="password" name="password" id="id_password" 
           placeholder="Ingresa tu contraseña" required>
    
    <!-- Botón Submit -->
    <button type="submit">Ingresar</button>
</form>
```

### Proceso de Autenticación

1. **POST /login/ → TenantLoginView:**
   ```python
   # Django procesa el formulario
   # username: "owner@acme.com" o "owner" (username generado)
   # password: "Secr3tPass!"
   ```

2. **TenantAwareBackend:**
   ```python
   # config/settings.py
   AUTHENTICATION_BACKENDS = [
       'apps.public.tenants.backends.TenantAwareBackend',  # Primero
       'django.contrib.auth.backends.ModelBackend',
   ]
   ```

3. **Validación de Usuario:**
   ```python
   # apps/public/tenants/backends.py
   
   class TenantAwareBackend(ModelBackend):
       def authenticate(self, request, username=None, password=None, **kwargs):
           # 1. Autenticar usuario (busca en esquema public)
           user = super().authenticate(request, username, password, **kwargs)
           
           if not user:
               return None
           
           # 2. Obtener tenant activo (resuelto por TenantMainMiddleware)
           tenant = getattr(request, 'tenant', None)
           if not tenant:
               return None
           
           # 3. Verificar membresía activa
           membership = TenantMembership.objects.filter(
               client=tenant,
               user=user,
               is_active=True
           ).first()
           
           if not membership:
               return None  # Usuario no tiene acceso a este tenant
           
           return user
   ```

4. **Validación de Membresía (Middleware):**
   ```python
   # apps/public/tenants/authz.py
   
   def require_tenant_membership(get_response):
       def middleware(request):
           tenant = getattr(request, "tenant", None)
           user = getattr(request, "user", None)
           
           # Solo validar en rutas privadas
           is_private = any(request.path.startswith(pfx) for pfx in PRIVATE_PREFIXES)
           
           if tenant and user and user.is_authenticated and is_private:
               has_access = TenantMembership.objects.filter(
                   client=tenant,
                   user=user,
                   is_active=True
               ).exists()
               
               if not has_access:
                   return HttpResponseForbidden("No tienes acceso a este tenant.")
           
           return get_response(request)
       return middleware
   ```

### Redirección al Dashboard

```python
# Después de autenticación exitosa:
# 1. Django establece sesión
# 2. TenantLoginView.get_success_url() retorna '/dashboard/'
# 3. Redirección 302 → http://acme.localhost/dashboard/
# 4. require_tenant_membership valida membresía → ✅ OK
# 5. DashboardView renderiza el dashboard del tenant
```

### Resultado del Paso 9

- ✅ Usuario autenticado en el tenant
- ✅ Sesión establecida
- ✅ Membresía validada
- ✅ Redirección a `/dashboard/`
- ✅ Acceso completo al tenant

**⚠️ v2.24:** Si el usuario fue creado por onboarding v2.24, debe activar su cuenta primero usando `/activate?token=...` antes de poder hacer login normal.

---

## 🔗 Modelos y Relaciones

### Diagrama de Relaciones

```
┌─────────────────────────────────────────────────────────────┐
│                    ESQUEMA: public                           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐         ┌──────────────────────┐    │
│  │   User            │         │   Client              │    │
│  │ (AbstractUser)    │         │ (TenantMixin)         │    │
│  ├──────────────────┤         ├──────────────────────┤    │
│  │ id                │         │ id                    │    │
│  │ email (unique)    │         │ schema_name (unique)  │    │
│  │ username          │         │ nombre                │    │
│  │ password (hash)   │         │ is_active             │    │
│  │ is_staff          │         │ auto_create_schema    │    │
│  │ is_active         │         │ auto_drop_schema       │    │
│  └──────────────────┘         └──────────────────────┘    │
│         │                              │                     │
│         │                              │                     │
│         │                              │                     │
│         │         ┌────────────────────┴──────────┐          │
│         │         │                               │          │
│         │    ┌────▼────┐                    ┌────▼────┐     │
│         │    │ Domain   │                    │TenantMem│     │
│         │    │          │                    │bership  │     │
│         │    ├──────────┤                    ├─────────┤     │
│         │    │ domain   │                    │ client  │─────┘
│         │    │ tenant   │────┐               │ user    │─────┐
│         │    │is_primary│    │               │ rol     │     │
│         │    └──────────┘    │               │is_primary│    │
│         │                     │               │is_active │    │
│         │                     │               └─────────┘     │
│         │                     │                               │
└─────────┼─────────────────────┼───────────────────────────────┘
          │                     │
          │                     │
          │                     │
          │                     │
┌─────────▼─────────────────────▼───────────────────────────────┐
│                    ESQUEMA: acme (tenant)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐                                          │
│  │ TenantProfile    │                                          │
│  ├──────────────────┤                                          │
│  │ user (OneToOne)  │──────┐                                   │
│  │ cargo            │      │                                   │
│  │ departamento     │      │                                   │
│  │ telefono_corp    │      │                                   │
│  │ configuracion    │      │                                   │
│  └──────────────────┘      │                                   │
│                             │                                   │
│                             │ (FK hacia public.accounts_user)   │
│                             │                                   │
└─────────────────────────────┼───────────────────────────────────┘
                              │
                              │
                    ┌─────────▼─────────┐
                    │   User (public)    │
                    │   (AbstractUser)   │
                    └────────────────────┘
```

### Relaciones Clave

1. **User ↔ TenantMembership (Many-to-Many implícita):**
   - Un `User` puede tener múltiples `TenantMembership` (uno por tenant)
   - Un `Client` puede tener múltiples `TenantMembership` (uno por usuario)
   - Relación en esquema `public`

2. **User ↔ TenantProfile (One-to-One por tenant):**
   - Un `User` puede tener UN `TenantProfile` por tenant
   - El `TenantProfile` vive en el esquema del tenant
   - El `User` vive en el esquema `public`
   - Relación FK desde tenant hacia public (permitida por django-tenants)

3. **Client ↔ Domain (One-to-Many):**
   - Un `Client` puede tener múltiples `Domain`
   - Solo UN `Domain` puede tener `is_primary=True` por tenant
   - Relación en esquema `public`

---

## 📊 Diagrama de Flujo

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. CONSOLA PÚBLICA                                              │
│    /console/tenants/new/                                        │
│    └─ Formulario HTML (nombre, schema_name, dominio_fqdn,       │
│       owner_email, owner_password)                              │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ POST /api/public/v1/tenants/onboard/
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. DRF VIEWSET                                                  │
│    ClientViewSet.onboard()                                       │
│    └─ Validación con OnboardTenantWithOwnerSerializer          │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ crear_tenant_con_owner()
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. SERVICIO DE ONBOARDING (@transaction.atomic)                 │
│    apps/services/onboarding/empresa_service.py                   │
│                                                                  │
│    ┌────────────────────────────────────────────────────────┐  │
│    │ 3.1. CREAR/OBTENER USER (public)                        │  │
│    │     └─ create_user_service()                            │  │
│    │        ├─ Genera username único desde email             │  │
│    │        ├─ set_password() para hash seguro                │  │
│    │        └─ Guarda en accounts_user (public)               │  │
│    └────────────────────────────────────────────────────────┘  │
│                            │                                     │
│    ┌────────────────────────────────────────────────────────┐  │
│    │ 3.2. CREAR CLIENT (public)                              │  │
│    │     └─ Client(schema_name='acme', nombre='Acme SAS')    │  │
│    │        └─ client.save()                                 │  │
│    │           ├─ Crea esquema PostgreSQL: CREATE SCHEMA acme│  │
│    │           └─ Ejecuta migrate_schemas (TENANT_APPS)      │  │
│    └────────────────────────────────────────────────────────┘  │
│                            │                                     │
│    ┌────────────────────────────────────────────────────────┐  │
│    │ 3.3. CREAR DOMAIN (public)                              │  │
│    │     └─ Domain(domain='acme.localhost', is_primary=True) │  │
│    │        └─ Guarda en tenants_domain (public)             │  │
│    └────────────────────────────────────────────────────────┘  │
│                            │                                     │
│    ┌────────────────────────────────────────────────────────┐  │
│    │ 3.4. CREAR TENANTMEMBERSHIP (public)                    │  │
│    │     └─ TenantMembership(                                │  │
│    │          client=client,                                 │  │
│    │          user=user,                                     │  │
│    │          rol='ADMIN',                                   │  │
│    │          is_primary_admin=True,                          │  │
│    │          is_active=True                                 │  │
│    │        )                                                │  │
│    │        └─ Guarda en tenants_tenantmembership (public)   │  │
│    └────────────────────────────────────────────────────────┘  │
│                            │                                     │
│    ┌────────────────────────────────────────────────────────┐  │
│    │ 3.5. CREAR TENANTPROFILE (opcional, esquema tenant)     │  │
│    │     └─ schema_context('acme'):                          │  │
│    │        └─ TenantProfile(                                │  │
│    │             user=user,                                  │  │
│    │             cargo='Administrador Principal',           │  │
│    │             departamento='Gerencia'                     │  │
│    │           )                                            │  │
│    │           └─ Guarda en perfil_tenantprofile (acme)     │  │
│    └────────────────────────────────────────────────────────┘  │
│                            │                                     │
│    ┌────────────────────────────────────────────────────────┐  │
│    │ 3.6. CONSTRUIR login_url                                │  │
│    │     └─ _build_login_url('acme.localhost')              │  │
│    │        └─ Retorna: "http://acme.localhost/login/"       │  │
│    └────────────────────────────────────────────────────────┘  │
│                            │                                     │
│                            │ Retorna: {client_id, domain,        │
│                            │          membership_id, login_url}   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ Response 201 Created
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. JAVASCRIPT (tenants_manager.js)                              │
│    └─ Muestra notificación con activation_url (v2.24)          │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ Owner recibe email con link ⭐ v2.24
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. TENANTMAINMIDDLEWARE                                          │
│    └─ Resuelve tenant por hostname:                             │
│       domain='acme.localhost' → Client(schema_name='acme')      │
│       └─ Activa esquema: connection.set_schema_to('acme')       │
│       └─ Selecciona URLConf: request.urlconf = 'urls_tenant'    │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ GET /activate?token=... ⭐ v2.24
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. ACTIVATEOWNERVIEW ⭐ v2.24                                     │
│    apps/tenant/landing/views.py                                  │
│    └─ Valida token y muestra formulario de activación          │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ POST /activate?token=... (password, password_confirm)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. ACTIVATEOWNERVIEW.form_valid() ⭐ v2.24                        │
│    └─ 1. Verifica token (ya validado)                           │
│       └─ 2. Valida membresía activa                              │
│          └─ 3. Establece password (set_password)                │
│             └─ 4. Loguea usuario (login)                        │
│                └─ 5. Redirige a /dashboard/                     │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ Usuario autenticado y activado
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 8. REQUIRE_TENANT_MEMBERSHIP MIDDLEWARE                          │
│    apps/public/tenants/authz.py                                  │
│    └─ Valida membresía activa en rutas privadas                  │
│       └─ Si no tiene acceso → 403 Forbidden                      │
│       └─ Si tiene acceso → Continúa                              │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ Redirección a /dashboard/
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 9. DASHBOARD DEL TENANT                                          │
│    /dashboard/                                                   │
│    └─ Usuario tiene acceso completo al tenant                    │
└─────────────────────────────────────────────────────────────────┘

**Flujo Alternativo (Login Normal - Usuario con password usable):**
┌─────────────────────────────────────────────────────────────────┐
│ GET /login/                                                      │
│    └─ TenantLoginView renderiza login.html                      │
│ POST /login/ (username, password)                                │
│    └─ TenantAwareBackend valida credenciales y membresía       │
│       └─ Redirige a /dashboard/                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔐 Seguridad y Validaciones

### Capas de Seguridad

1. **Nivel de Modelo:**
   - `User.email` único
   - `User.username` único (si existe)
   - `Domain.domain` único
   - `TenantMembership` único por (client, user)
   - Solo UN `is_primary_admin=True` por tenant

2. **Nivel de Servicio:**
   - `@transaction.atomic` garantiza atomicidad
   - Validación de `schema_name` (no puede ser "public")
   - Normalización de dominio (sin puerto, sin www)
   - Password hasheado con `set_password()`

3. **Nivel de API:**
   - `IsAdminUser` (solo staff puede crear tenants)
   - `SessionAuthentication` (cookies de sesión)
   - Validación con Serializer

4. **Nivel de Middleware:**
   - `TenantMainMiddleware` resuelve tenant por hostname
   - `require_tenant_membership` valida membresía activa
   - `block_public_routes_on_tenants` bloquea rutas públicas en tenants

5. **Nivel de Backend:**
   - `TenantAwareBackend` valida membresía durante autenticación

---

## 📝 Resumen Ejecutivo

### Flujo Completo en 8 Pasos

1. **Consola Pública:** Usuario staff accede a `/console/tenants/new/` y completa el formulario
2. **Usuario Global:** Se crea/obtiene `User` en esquema `public` con username único y password hasheado
3. **Tenant (Client):** Se crea `Client` en esquema `public`, lo que automáticamente crea el esquema PostgreSQL y migra TENANT_APPS
4. **Dominio:** Se crea `Domain` en esquema `public` con dominio normalizado (sin puerto, sin www)
5. **Membresía:** Se crea `TenantMembership` en esquema `public` vinculando User y Client con rol ADMIN y `is_primary_admin=True`
6. **Perfil (Opcional):** Se crea `TenantProfile` en el esquema del tenant si la tabla existe
7. **Activación:** Se construye `login_url` y se retorna al usuario
8. **Acceso:** Usuario accede a `login_url`, se autentica con `TenantAwareBackend`, se valida membresía y se redirige al dashboard

### Características Clave

- ✅ **Transaccional:** Todo el proceso está envuelto en `@transaction.atomic`
- ✅ **Idempotente:** Usa `get_or_create` para evitar duplicados
- ✅ **Resiliente:** El seed de perfil es opcional y no rompe el onboarding
- ✅ **Seguro:** Password unusable en onboarding (v2.24), establecido en activación, validación de membresía, permisos de admin
- ✅ **Conforme a django-tenants:** Sigue las mejores prácticas oficiales
- ✅ **Sistema de invitación (v2.24):** Tokens firmados con TTL, activación en subdominio del tenant, mejora higiene de credenciales

---

**Última Actualización:** 2026-01-30  
**Mantenido por:** Equipo de Desarrollo SINTEL  
**Versión del Documento:** 1.0
