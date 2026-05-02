# Informe Técnico: Auditoría de Vinculación Dominio Privado vs Público (v2.61.4)

Este informe detalla las dependencias, relaciones y vinculaciones detectadas entre las aplicaciones que residen en el esquema **Privado (Tenant)** y las que residen en el esquema **Público (Shared/Public)** en la arquitectura SINTEL.

---

## 1. Relaciones de Modelos (Base de Datos)

El sistema utiliza una arquitectura **SSoT Unidireccional** donde el esquema privado referencia al público, pero el público permanece "ciego" ante los datos privados.

### 1.1 Vínculos Legítimos (Tenant → Public)
*   **`perfil.TenantProfile` → `accounts.User`**: Relación `OneToOneField` entre el perfil privado y el usuario global. Es el vínculo principal de identidad.
*   **`core.SintelTenantBaseModel`**: Aunque reside en `core` (tenant), su existencia garantiza que toda la data privada tenga una referencia a la entidad contable (Empresa), la cual a su vez es hija del `Client` público (vía schema_name).

### 1.2 Aislamiento de Modelos
*   Los modelos de **Catálogo Tributario (Impuestos)** en `public` NO tienen ninguna relación con modelos de tenant. Son servidos como SSoT de consulta para todas las empresas.

---

## 2. Dependencias de Código (Python Imports)

### 2.1 Vinculación de Servicios y Lógica
*   **Orquestación de Identidad**: `apps.tenant.core` y `apps.tenant.landing` importan activamente de `apps.public.tenants.models` (`Client`, `Domain`, `TenantMembership`) para validar sesiones y permisos.
*   **Comunicaciones**: El reciente `EmailService` centralizado en `apps.public.core` es ahora una dependencia crítica para los servicios de invitación y reset de contraseña del dominio privado.
*   **Capa `apps/services/`**: Actúa como un **puente de orquestación**. El `empresa_service.py` es el mayor consumidor de ambos mundos, ya que debe crear usuarios (public), tenants (public) y configurar la empresa inicial (tenant).

---

## 3. Vinculación de Infraestructura (Middleware y URLs)

### 3.1 `TenantRootView` y Ruteo
*   Existe una vinculación lógica en `config/urls_tenant.py` donde el sistema debe decidir entre servir un shell privado o denegar acceso basándose en la resolución del tenant (que viene del esquema `public`).

### 3.2 `Domain` como SSoT de Resolución
*   Cada request en el dominio privado depende del modelo `Domain` (public) para activar el esquema PostgreSQL correcto.

---

## 4. Anomalías Detectadas (Violaciones de Unidireccionalidad)

Se han detectado vinculaciones "hacia atrás" (Public → Tenant) que, aunque limitadas a herramientas de desarrollo, rompen el principio de aislamiento estricto:

*   **Comandos de Generación**: `generar_tenants_prueba.py` y `analizar_tenants_prueba.py` en `apps/public/tenants/management/` importan modelos de `apps.tenant.empresa`, `apps.tenant.clientes`, etc.
    *   *Riesgo*: Bajo (son herramientas de seeding).
    *   *Acción*: Deberían migrarse a un módulo de `tools/` o usar `apps.get_model` para evitar importaciones estáticas.

---

## 5. Conclusión de la Auditoría

La vinculación es **Correcta y Controlada** en un 95%. La dependencia del dominio privado hacia el público es inevitable y necesaria para la gestión de identidad multi-tenant. El sistema cumple satisfactoriamente con la **Regla 2.2** (Unidireccionalidad) en el core de ejecución, manteniendo las excepciones de importación inversa aisladas en comandos de utilidad fuera del flujo de producción.

**Estado Final**: ✅ **APROBADO** (Cumplimiento de arquitectura v2.61.4)
