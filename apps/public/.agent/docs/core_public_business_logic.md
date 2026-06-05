# 🧠 Lógica de Negocio: Módulo Core Public (SSoT)

Este documento centraliza las reglas de infraestructura y comunicación global.

---

## 1. SSoT de Comunicación (Email Policy)

- **Centralización**: Ninguna aplicación debe instanciar `send_mail` de Django directamente. Se debe utilizar exclusivamente el `EmailService` para garantizar que todos los correos sigan los lineamientos de marca y seguridad.
- **Fallbacks**: El servicio debe manejar fallos del backend de correo sin interrumpir el flujo del usuario (fail-safe), delegando el reintento a una tarea de Celery.

---

## 2. Gestión de Templates Transaccionales

- **Jerarquía**: Los templates de correo residen en `templates/public/core/emails/`.
- **Estandarización**: Todos los correos deben heredar de `base_email.html` para incluir el header/footer corporativo y las variables de CSS de marca global.

---

## 3. Resolución de Rutas y Contexto

- **Prioridad de Acceso**: La lógica de redirección debe priorizar la seguridad. Si un usuario tiene el token expirado, debe ser enviado a la página de login global sin excepciones.
- **Detección de Staff**: El sistema debe identificar proactivamente a los usuarios administrativos para ofrecerles acceso directo a la consola de gestión centralizada.

---

## 4. Estándares de Logging y Auditoría

- **Auditoría de Tokens**: Cada verificación de token en el esquema público debe poder ser registrada para auditoría de seguridad si se detectan anomalías (ej. múltiples IPs para el mismo token).

---

## 5. Middleware de Contexto Global

- **Inyección de Constantes**: El middleware de core público se encarga de inyectar variables globales (ej. Versión del Sistema, Nombre de la Plataforma) en el contexto de todos los templates para evitar redundancia.
