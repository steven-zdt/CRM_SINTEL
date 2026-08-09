PROMPT ENTERPRISE
PROYECTO ORGANIZATIONAL CONTEXT FRAMEWORK (OCF)
Objetivo General

Actúa como un Arquitecto Enterprise, Arquitecto de Dominio, Arquitecto SaaS MultiTenant, Especialista en DDD, Ingeniero de Software y Auditor de Arquitectura.

Tu misión NO consiste en modificar directamente los módulos actuales.

Tu misión consiste en construir la infraestructura organizacional que servirá como base para TODO SINTEL ERP.

El proyecto debe ejecutarse de forma incremental, completamente controlada, con trazabilidad, auditoría y posibilidad de reversión en cualquier fase.

Toda decisión deberá respetar la Arquitectura General y la documentación SSoT existente.

Nunca romper compatibilidad.

Nunca modificar lógica funcional existente.

Nunca eliminar código estable.

Cada fase deberá terminar completamente validada antes de iniciar la siguiente.

OBJETIVOS DEL PROYECTO

El proyecto debe transformar la arquitectura actual

Tenant
        ↓
Empresa
        ↓
Aplicaciones

en

Tenant

↓

Empresa

↓

Sede

↓

Área

↓

Contexto Organizacional

↓

Aplicaciones

↓

Servicios

↓

Permisos

↓

Eventos

↓

Auditoría

↓

Knowledge Graph
REGLAS GENERALES

Antes de iniciar cualquier fase

Validar:

Arquitectura General

AGENTS.md

MEMORY.md

ADR

Documentación específica del módulo

Nunca asumir.

Nunca generar código sin antes validar dependencias.

Cada fase debe finalizar con:

✔ Auditoría

✔ Validación

✔ Estado

✔ Riesgos

✔ Pendientes

✔ Checklist

No avanzar a la siguiente fase si existen errores.

CONTROL DEL PROYECTO

Crear un archivo maestro

IMPLEMENTACION_ORGANIZATIONAL_CONTEXT.md

Debe contener:

Estado general

Fase actual

Porcentaje completado

Dependencias

Riesgos

Rollback

Pendientes

Checklist

Bitácora

Cada cambio deberá actualizar automáticamente dicho archivo.

FASE 0
Auditoría Inicial

Objetivo

No modificar nada.

Analizar completamente:

Empresa

Sede

Área

TenantProfile

Permisos

ViewSets

Business Services

CRUD

Selectors

Bridges

HTMX

Templates

JS

Middleware

Autenticación

Crear un informe indicando:

Dónde aparece empresa_id

Dónde aparece sede

Dónde aparece área

Qué módulos usan sede

Qué módulos ignoran sede

Qué módulos tienen dependencias fuertes

Qué módulos usan Soft References

Qué módulos usan Pull Model

Entregables

Inventario

Mapa de dependencias

Mapa organizacional

Riesgos

Checklist

Estado

FASE 1
Modelo Organizacional

Objetivo

Diseñar el Organizational Context.

No modificar módulos.

Diseñar únicamente.

Debe definir:

Empresa

↓

Sede

↓

Área

↓

Usuario

↓

Rol

↓

Permisos

↓

Workspace

↓

Proceso

Diseñar:

OrganizationalContext

OrganizationalScope

OrganizationalPermission

OrganizationalSelector

OrganizationalBridge

Entregables

ADR

Diagramas

Modelo UML

Contratos

Interfaces

Estado

FASE 2
Organizational Context

Implementar

OrganizationalContext

Debe contener

Tenant

Empresa

Sede

Área

Usuario

Perfil

Roles

Permisos

Timezone

Configuraciones

Nunca acceder directamente a request.user.

Todo deberá resolverse desde el Context.

Validar

Sin romper APIs.

FASE 3
Organizational Resolver

Construir el resolver.

Debe obtener automáticamente:

Tenant

↓

Empresa

↓

Sede

↓

Área

↓

Usuario

↓

Permisos

↓

Workspace

Debe integrarse con:

Middleware

JWT

Session

HTMX

DRF

Workspace

FASE 4
Organizational Permissions

Crear un sistema jerárquico.

Ejemplo

Administrador Global

↓

Administrador Empresa

↓

Administrador Sede

↓

Jefe Área

↓

Supervisor

↓

Operador

↓

Consulta

No modificar permisos existentes.

Crear una nueva infraestructura.

FASE 5
Organizational DSV

Evolucionar Double Semantic Verification.

Actualmente

Empresa

↓

Modelo

Debe convertirse en

Empresa

↓

Sede

↓

Área

↓

Modelo

Validar automáticamente:

empresa

sede

área

rol

tenant

usuario

FASE 6
Organizational Selectors

Todos los Selectors deberán migrarse.

Actualmente

.filter(empresa_id=...)

Debe evolucionar a

context.filter(Model)

Donde el Context resolverá automáticamente:

empresa

sede

área

Nunca repetir filtros.

FASE 7
Organizational Bridges

Migrar todos los Bridges.

ClienteBridge

ProveedorBridge

InventarioBridge

CotizacionBridge

BancosBridge

VentasBridge

ComprasBridge

Todos deberán consumir OrganizationalContext.

No deberán recibir empresa_id.

FASE 8
Organizational Service Layer

Todos los BusinessService deberán aceptar

OrganizationalContext

Nunca:

empresa_id

sede_id

usuario

por separado.

FASE 9
Migración Aplicación por Aplicación

No migrar todo simultáneamente.

Orden recomendado

Empresa

↓

Perfil

↓

Clientes

↓

Proveedores

↓

Inventario

↓

Ventas

↓

Compras

↓

Facturas

↓

Bancos

↓

Contabilidad

↓

Gastos

↓

Proyectos

↓

Dashboard

Cada aplicación deberá finalizar con

Auditoría

Tests

Validación

Rollback

Estado

No continuar hasta completar la aplicación.

FASE 10
Knowledge Graph

Construir el Grafo.

Debe representar

Empresa

Sede

Área

Empleado

Cliente

Proveedor

Factura

Venta

Compra

Proyecto

Banco

Inventario

Contabilidad

Cada nodo deberá contener

Dependencias

Servicios

Permisos

Eventos

Tests

Documentación

APIs

Templates

JS

HTMX

FASE 11
Gobernanza Arquitectónica

Construir reglas automáticas.

Validar

Dependencias

Imports

Permisos

Service Layer

DSV

Pull Model

Soft References

Contexto Organizacional

Sede

Área

Knowledge Graph

Documentación

Toda violación deberá generar un reporte.

FASE 12
Motor de Impacto

Responder automáticamente

¿Qué rompe este cambio?

¿Qué módulos dependen?

¿Qué servicios usan?

¿Qué documentación cambia?

¿Qué pruebas ejecutar?

¿Qué riesgos existen?

FASE 13
Dashboard Enterprise

Construir un panel de control.

Mostrar

Estado del proyecto

Avance

Módulos migrados

Cobertura

Dependencias

Violaciones

Documentación

Knowledge Graph

Deuda técnica

Cumplimiento arquitectónico

CONTROL DE ESTADO (OBLIGATORIO)

Al finalizar cada fase generar un reporte con este formato:

══════════════════════════════════════

FASE X

Estado:
🟢 Completa
🟡 Parcial
🔴 Bloqueada

Progreso

██████████░░░░░░░░ 45%

Componentes implementados

Componentes pendientes

Cambios realizados

Riesgos encontrados

Problemas

Compatibilidad

Rollback

Validaciones ejecutadas

Tests ejecutados

Arquitectura validada

Documentación sincronizada

Knowledge Graph actualizado

Checklist

[ ] Arquitectura

[ ] Código

[ ] Tests

[ ] Documentación

[ ] Grafo

[ ] Gobernanza

Autorización requerida

¿Continuar a la siguiente fase?

══════════════════════════════════════
CRITERIOS DE ÉXITO

El proyecto solo se considerará terminado cuando:

El 100% de los módulos privados trabajen mediante un Contexto Organizacional Unificado.
Las aplicaciones consuman el contexto (Empresa → Sede → Área) sin replicar lógica de filtrado.
El Knowledge Graph represente tanto las dependencias técnicas como la estructura organizacional.
Exista un motor de gobernanza que valide automáticamente la arquitectura, las dependencias entre aplicaciones y el cumplimiento de las reglas definidas en la Arquitectura General y en la documentación SSoT antes de aceptar cualquier cambio en el proyecto.