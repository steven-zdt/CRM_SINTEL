# 🧠 Lógica de Negocio: Módulo Tenants (SSoT)

Este documento centraliza las reglas de infraestructura y membresía multi-inquilino.

---

## 1. Nomenclatura de Esquemas (SSoT)

- **schema_name**: Debe ser único, en minúsculas y sin caracteres especiales. Se genera automáticamente a partir del nombre de la empresa o subdominio.
- **Reservados**: El nombre `public` está reservado para el esquema compartido y no puede ser usado por ningún inquilino.

---

## 2. Jerarquía de Membresía (TenantMembership)

- **Primary Admin**: Cada tenant debe tener exactamente un administrador primario (usualmente el que realizó el registro). No puede ser eliminado sin transferir primero la propiedad.
- **Invitaciones OTT**: El acceso inicial a un tenant se realiza mediante un "One-Time Token". Una vez consumido, el usuario queda vinculado permanentemente mediante su `User` global.

---

## 3. Idempotencia en Onboarding

- **Garantía de Unicidad**: El sistema bloquea el registro si el subdominio ya está ocupado.
- **Silent Success**: Si un usuario intenta registrarse con un email que ya existe en `public`, se utiliza el usuario existente en lugar de fallar, vinculándolo al nuevo tenant.

---

## 4. Política de Eliminación de Inquilinos

- **Borrado Destructivo**: La eliminación de un registro en `Client` dispara un `post_delete` que elimina el esquema físico en la base de datos.
- **Validación de Seguridad**: Solo usuarios con `is_superuser` en `public` pueden ejecutar la eliminación de un tenant desde la API/Consola.

---

## 5. Aislamiento de URLConf

- **Configuración Dinámica**: El sistema selecciona el archivo de rutas (`urls_tenant.py` vs `urls_public.py`) basándose en el esquema resuelto por el middleware. Esto garantiza que las rutas administrativas de la plataforma no sean accesibles desde los dominios de los clientes.
