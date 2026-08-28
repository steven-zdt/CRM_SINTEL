# REM-P3-07 — Controles por rol en UI (backend-only)

**Estado:** DEFERRED (requiere trabajo cross-cutting de frontend, no una
corrección puntual)
**Prioridad:** P3
**Apps involucradas:** transversal — `contabilidad`, `bancos`, `empleados`
y potencialmente el resto (confirmado en las 3 apps auditadas)
**Fecha:** 2026-08-28

## Hallazgo

Un usuario `VISOR` ve exactamente el mismo HTML/botones que un `ADMIN` en
`contabilidad`, `bancos` y `empleados` — el bloqueo de mutaciones es
100% backend (correcto y suficiente como control de seguridad), pero la
UI no oculta ni deshabilita visualmente los controles que fallarán al
hacer clic (ej. "Cerrar periodo", "Editar"). Confirmado por el agente de
UX de la auditoría empresarial: grep exhaustivo de condicionales de rol en
templates de esas 3 apps → cero resultados reales (solo falsos positivos
del atributo HTML `role="..."` de accesibilidad).

## Por qué se difiere

El plan pide explícitamente: *"Integrar con User Access Context. No crear
permisos nuevos."* — el mecanismo backend (`TenantProfile.rol`,
`HasTenantRole`, `OrganizationalPermission`) ya existe y es correcto; lo
que falta es **wiring de frontend en cada template/vista de cada app**,
verificando primero cómo cada template accede al rol del usuario
actual (¿contexto de Django template? ¿llamada JS a un endpoint de
perfil?) antes de decidir el patrón de ocultamiento — un trabajo de
auditoría + implementación transversal a potencialmente todas las apps
con mutaciones restringidas por rol, no limitado a las 3 ya confirmadas.

## Decisión

**No se implementa en esta sesión.** Es un patrón cross-cutting real que
merece su propia misión dedicada (mismo criterio que se aplicó a las
misiones de modernización de `cotizaciones`/`inventario` en esta sesión:
un cambio transversal de esta naturaleza necesita su propio ciclo de
diseño + implementación + verificación, no un parche apresurado dentro de
un plan de remediación de hallazgos puntuales).

## Alcance para una sesión dedicada futura

1. Confirmar el mecanismo real por el cual el frontend puede conocer el
   rol del usuario actual sin una llamada adicional (¿ya viene en el
   contexto de render del template? ¿en `window.jwtAuth`?).
2. Diseñar un patrón reutilizable (ej. clase CSS `.solo-admin` + JS que
   oculta/deshabilita según el rol resuelto) — uno solo, aplicado
   consistentemente, no una solución ad-hoc por app.
3. Aplicar el patrón a los controles ya confirmados en `contabilidad`
   ("Cerrar periodo"), `bancos` (conciliar), `empleados` (aprobar/pagar/
   cerrar/anular nómina) — y auditar el resto de apps con mutaciones
   restringidas por rol antes de dar por cerrado el hallazgo
   transversalmente.

## Governance

N/A — sin cambio de código en esta sesión.
