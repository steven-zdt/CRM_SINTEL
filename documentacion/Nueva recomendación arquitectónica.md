1. Qué cambió respecto a mi recomendación anterior

Mi recomendación anterior era conceptualmente:

Crear Organizational Context
        ↓
Resolver Empresa
        ↓
Resolver Sede
        ↓
Resolver Área
        ↓
Migrar aplicaciones

Después de revisar arquitectura_general(7).md, esto sería duplicar arquitectura existente.

Ya tienes:

SintelTenantBaseModel
        │
        └── empresa

y además:

SedeAwareModel
        │
        ├── sede
        └── area

y:

TenantProfile
        │
        └── alcance
             ├── EMPRESA
             ├── SEDE
             └── AREA

y:

HasOrganizationalScope

con un piloto ya aplicado en:

apps/tenant/compras/

Por tanto, la arquitectura base ya existe.

El problema real ahora es:

La infraestructura organizacional está parcialmente implementada, pero no está convertida todavía en un estándar transversal obligatorio para todas las aplicaciones.

Ese es el proyecto que debemos ejecutar.

2. El verdadero estado de SINTEL

Actualmente veo esta evolución:

                 TENANT
                    │
                    ▼
                 EMPRESA
                    │
                    │
       ┌────────────┴────────────┐
       │                         │
      SEDE                      ÁREA
       │                         │
       └────────────┬────────────┘
                    │
             Organizational
                Scope
                    │
                    ▼
             TenantProfile
                    │
             ┌──────┴──────┐
             │             │
           ROL          ALCANCE
             │             │
             │       EMPRESA/SEDE/AREA
             │
             ▼
          PERMISOS

Pero las aplicaciones todavía están mayoritariamente en:

App
 │
 └── empresa_id

mientras compras ya está comenzando a operar con:

empresa_id
+
sede_id
+
area_id

Eso genera una arquitectura híbrida.

3. El principal riesgo ahora

No es Facturas.

El verdadero riesgo es permitir que cada aplicación implemente su propia interpretación de:

sede
area
alcance
permisos
empresa

Por ejemplo:

Facturas
    empresa + sede

Ventas
    empresa

Compras
    empresa + sede + área

Inventario
    empresa + sede

Gastos
    empresa + área

Proyectos
    empresa + sede

Esto terminaría creando 17 modelos diferentes de contexto organizacional.

Y eso es precisamente lo que debemos evitar.

4. Nueva recomendación arquitectónica

Yo cambiaría el objetivo del proyecto.

No:

Crear Organizational Context Framework.

Sino:

Completar y estandarizar el Organizational Scope Framework ya iniciado por ADR-003, y convertirlo en una capacidad transversal obligatoria para las aplicaciones tenant.

El objetivo será:

                SINTEL ERP
                    │
              Tenant Schema
                    │
                 Empresa
                    │
          ┌─────────┴─────────┐
          │                   │
        Sede                 Área
          │                   │
          └─────────┬─────────┘
                    │
          Organizational Scope
                    │
          ┌─────────┴──────────┐
          │                    │
       TenantProfile       Permissions
          │                    │
          └─────────┬──────────┘
                    │
              Service Layer
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
       Selectors Bridges   Business
          │         │       Services
          └─────────┼─────────┘
                    ▼
              Aplicaciones
5. Hay además una inconsistencia documental que debemos corregir

Encontré algo importante en arquitectura_general(7).md.

En §3.6 se indica:

ADR-003
Contexto Organizacional
Sede / Área

pero en §7 aparece:

ADR-003
TareaCorta.cliente FK PROTECT → SET_NULL

Eso debe resolverse antes de avanzar, porque estamos usando ADR como fuente de gobernanza.

No recomiendo simplemente renombrar arbitrariamente.

Primero hay que inspeccionar:

docs/
ADR-003-contexto-organizacional-sede-area.md

y comprobar cuál es realmente el ADR vigente.

Luego establecer una única numeración canónica.

6. Qué haría ahora realmente
FASE 0 — GOVERNANCE BASELINE

No tocar código.

Validar:

arquitectura_general(7).md
AGENTS.md
MEMORY.md
ADR existentes
compras
empresa
perfil
facturas

Especialmente:

SedeAwareModel
TenantProfile.alcance
HasOrganizationalScope
sedes_asignadas
areas_asignadas
Resultado esperado

Un documento:

ORGANIZATIONAL_SCOPE_BASELINE.md

que indique:

IMPLEMENTADO
PARCIAL
PENDIENTE
INCONSISTENTE
Estado
🟡 FASE 0

No continuar hasta resolver inconsistencias documentales.

FASE 1 — NORMALIZAR ADR-003

Aquí no desarrollamos nada.

Debemos definir formalmente:

Empresa
Sede
Área
Alcance
Rol
Permiso

Y especialmente separar:

ROL
≠
ALCANCE

La arquitectura ya establece que son conceptos ortogonales.

Ejemplo:

Usuario
   │
   ├── Rol = OPERADOR
   │
   └── Alcance = SEDE
                    │
                    └── Sede Bogotá

Otro:

Usuario
   │
   ├── Rol = OPERADOR
   │
   └── Alcance = AREA
                    │
                    ├── Sede Bogotá
                    └── Área Comercial
FASE 2 — DEFINIR EL CONTRATO ORGANIZACIONAL

Aquí debemos crear un único contrato que todas las aplicaciones deberán utilizar.

Conceptualmente:

OrganizationalScope

con información equivalente a:

empresa
sede
area
alcance
usuario
rol

Pero atención:

No crear otra jerarquía paralela a TenantProfile.

TenantProfile sigue siendo el SSoT de identidad/rol dentro del tenant.

El nuevo contrato debe consumir ese modelo, no sustituirlo.

FASE 3 — RESOLVER EL CONTEXTO DEL USUARIO

Cuando el usuario entre a:

home.sintel.com.co

debe quedar perfectamente determinado:

TENANT
   ↓
EMPRESA
   ↓
USUARIO
   ↓
TENANT PROFILE
   ↓
ROL
   ↓
ALCANCE
   ↓
SEDE/S
   ↓
ÁREA/S

Por ejemplo:

Empresa:
Sintel Technology

Usuario:
Juan

Rol:
OPERADOR

Alcance:
SEDE

Sede permitida:
Barranquilla

Entonces:

Juan
 ├── puede ver empresa Sintel
 ├── puede operar Barranquilla
 └── NO puede operar Bogotá
FASE 4 — RESOLVER EL PROBLEMA DE LA SEDE POR DEFECTO

Esta fase es crítica para tu ERP porque ya existen datos.

No podemos decir:

"Desde hoy todo requiere sede"

y romper las aplicaciones existentes.

Debemos establecer una estrategia de transición.

Para cada empresa existente:

Empresa
   │
   └── Sede Principal

y:

Sede Principal
   │
   └── Área General

Los datos históricos sin clasificación deberán quedar temporalmente asociados al contexto predeterminado correspondiente, solo después de una auditoría de datos, no mediante una migración ciega.

FASE 5 — CONVERTIR compras EN PILOTO OFICIAL

Aquí cambia otra parte importante de mi recomendación.

No migraría primero Facturas.

Compras ya es el piloto.

La arquitectura confirma que OrdenCompra es actualmente el primer uso de SedeAwareModel y HasOrganizationalScope.

Por tanto:

COMPRAS
   ↓
PILOTO ORGANIZACIONAL

Debemos auditar exhaustivamente:

Model
Selector
BusinessService
CRUDService
ViewSet
Serializer
Permission
Template
HTMX
JS
Tests

y demostrar:

EMPRESA
+
SEDE
+
ÁREA
+
ROL
+
ALCANCE

funcionando correctamente.

FASE 6 — CREAR LA MATRIZ DE ALCANCE

Este será uno de los entregables más importantes.

Por cada aplicación:

App	Empresa	Sede	Área	Alcance
Empresa	✅	✅	✅	Configurable
Perfil	✅	✅	✅	Usuario
Compras	✅	✅	✅	Piloto
Ventas	✅	⏳	⏳	Pendiente
Facturas	✅	⚠️	❌	Pendiente
Inventario	✅	⏳	⏳	Pendiente
Gastos	✅	⏳	⏳	Pendiente
Bancos	✅	⏳	⏳	Pendiente
Contabilidad	✅	⏳	⏳	Pendiente
Empleados	✅	⏳	⏳	Pendiente
Clientes	✅	⏳	⏳	Pendiente
Proveedores	✅	⏳	⏳	Pendiente
Proyectos	✅	⏳	⏳	Pendiente
Cotizaciones	✅	⏳	⏳	Pendiente
Dashboard	✅	⏳	⏳	Pendiente

Esto nos permitirá decidir qué entidad realmente necesita sede y área.

No debemos poner sede y area indiscriminadamente en todos los modelos.

FASE 7 — MIGRAR SELECTORS

Ahora sí empezamos la migración técnica.

Orden:

Selectors
      ↓
Scopes
      ↓
QuerySets

Ejemplo actual:

FacturaSelectors.qs_list(
    empresa_id=empresa_id
)

Evolución:

FacturaSelectors.qs_list(
    scope=organizational_scope
)

El selector será responsable de aplicar:

empresa
+
sede
+
area

según el alcance.

FASE 8 — MIGRAR BUSINESS SERVICES

Después:

BusinessService

debe trabajar con el contexto organizacional.

Por ejemplo:

FacturaBusinessService
VentaBusinessService
CompraBusinessService
InventarioBusinessService

No permitir:

empresa_id
sede_id
area_id
user_id

dispersos arbitrariamente por cada método si todos representan el mismo contexto.

FASE 9 — MIGRAR BRIDGES

Este punto es especialmente importante por tu arquitectura de dependencias circulares/soft references.

No debemos romper ese diseño.

Los Bridges deben continuar siendo:

ClienteBridge
ProveedorBridge
InventarioBridge
CotizacionBridge
BancosBridge

pero ahora deben conocer el alcance organizacional cuando el dominio lo necesite.

Por ejemplo:

Factura
   │
   └── InventarioBridge
           │
           └── OrganizationalScope
                  │
                  ├── empresa
                  ├── sede
                  └── area

No convertir Bridges en Foreign Keys entre aplicaciones.

Eso violaría la arquitectura existente.

FASE 10 — VENTAS → FACTURAS

Esta fase merece una fase propia.

El documento de Facturas descubrió:

Ventas
   ↓
FacturaBusinessService
   ↓
crear_factura_desde_venta()

Por lo tanto:

Venta
   ↓
DTO
   ↓
Factura

debe transportar el contexto organizacional correcto.

Pero sin crear FK directa Ventas → Facturas.

Debe seguir siendo un contrato inter-app.

FASE 11 — FACTURAS

Ahora sí.

Aquí aplicaremos la arquitectura ya estabilizada.

Actualmente Facturas tiene:

empresa
sede

pero sede todavía es esencialmente informativa/reporting.

El objetivo será:

Factura
├── empresa
├── sede
└── área

cuando el dominio lo requiera.

Y revisar:

FacturaSelectors
FacturaBusinessService
FacturaCRUDService
FacturaInterAppAPI
FacturaViewSet
FacturaTableView
FacturaSerializer
FacturaBridge
crear_factura_desde_venta()
FASE 12 — CONTABILIDAD

Aquí debemos tener especial cuidado.

La arquitectura actual tiene una regla muy buena:

Apps origen
      ↓
    PULL
      ↓
Contabilidad

No debemos destruirla.

El contexto organizacional deberá acompañar al documento económico, pero:

Facturas → NO crea asiento
Ventas   → NO crea asiento
Gastos   → NO crea asiento

Continúa:

Contabilidad
     ↓
Extractor
     ↓
Documento origen
     ↓
Contexto organizacional
     ↓
Asiento
FASE 13 — RESTO DE APLICACIONES

Después del piloto:

Compras
 ↓
Ventas
 ↓
Facturas
 ↓
Inventario
 ↓
Gastos
 ↓
Clientes
 ↓
Proveedores
 ↓
Proyectos
 ↓
Empleados
 ↓
Bancos
 ↓
Contabilidad
 ↓
Cotizaciones
 ↓
Dashboard

No migrarlas todas simultáneamente.

FASE 14 — PRUEBAS DE AISLAMIENTO ORGANIZACIONAL

Aquí cambia la definición de "multitenant isolation".

Actualmente probamos:

Empresa A
   X
Empresa B

Debemos agregar:

Empresa A
 ├── Sede Bogotá
 │    └── Área Comercial
 │
 └── Sede Barranquilla
      └── Área Técnica

Y probar:

Usuario Bogotá
      X
Factura Barranquilla

y:

Usuario Comercial
      X
Documento Área Técnica

Esto debe probarse en:

Model
Selector
Service
ViewSet
API
HTMX
Frontend
FASE 15 — KNOWLEDGE GRAPH

Aquí también modifico mi recomendación anterior.

El Knowledge Graph no debe ser la primera fase.

Debe construirse después de estabilizar el modelo organizacional.

El grafo final debe representar:

TENANT
  ↓
EMPRESA
  ↓
SEDE
  ↓
ÁREA
  ↓
USUARIO
  ↓
ROL
  ↓
ALCANCE
  ↓
APP
  ↓
MODEL
  ↓
SERVICE
  ↓
SELECTOR
  ↓
BRIDGE
  ↓
API
  ↓
EVENTO
  ↓
TEST
  ↓
DOCUMENTACIÓN

Entonces sí tendrá valor real.

FASE 16 — GOBERNANZA AUTOMÁTICA

Finalmente construiremos reglas que detecten:

❌ Modelo con empresa pero sin sede cuando debería tenerla

❌ Query sin scope

❌ ViewSet sin permiso organizacional

❌ Service ignorando sede

❌ Bridge sin aislamiento

❌ DTO inter-app sin contexto

❌ Ventas → Facturas sin contexto

❌ Usuario accediendo a sede no autorizada

❌ Área fuera de la sede permitida

❌ Import circular

❌ FK cross-app indebida

❌ Bypass del Service Layer
7. El nuevo roadmap completo

Yo lo dejaría así:

                    SINTEL ERP
                        │
                        ▼
              F0 GOVERNANCE BASELINE
                        │
                        ▼
             F1 NORMALIZAR ADR/SCOPE
                        │
                        ▼
            F2 CONTRATO ORGANIZACIONAL
                        │
                        ▼
             F3 RESOLVER CONTEXTO
                        │
                        ▼
             F4 DATOS EXISTENTES
                        │
                        ▼
             F5 COMPRAS — PILOTO
                        │
                        ▼
            F6 MATRIZ ORGANIZACIONAL
                        │
                        ▼
             F7 SELECTORS
                        │
                        ▼
             F8 BUSINESS SERVICES
                        │
                        ▼
             F9 BRIDGES
                        │
                        ▼
            F10 VENTAS → FACTURAS
                        │
                        ▼
             F11 FACTURAS
                        │
                        ▼
             F12 CONTABILIDAD
                        │
                        ▼
             F13 RESTO DE APPS
                        │
                        ▼
             F14 TESTS
                        │
                        ▼
             F15 KNOWLEDGE GRAPH
                        │
                        ▼
             F16 GOVERNANCE ENGINE
8. Control de estado obligatorio

No recomiendo que tu IA editora ejecute una fase completa de forma automática.

Debe funcionar así:

FASE 05
       │
       ▼
AUDITORÍA
       │
       ▼
IMPLEMENTACIÓN
       │
       ▼
TESTS
       │
       ▼
AUDITORÍA POST
       │
       ▼
DOCUMENTACIÓN
       │
       ▼
GRAPH UPDATE
       │
       ▼
🟢 COMPLETA
       │
       ▼
AUTORIZACIÓN
       │
       ▼
SIGUIENTE FASE

Estados:

⚪ NO INICIADA

🔵 AUDITANDO

🟡 IMPLEMENTANDO

🟣 VALIDANDO

🟢 COMPLETADA

🔴 BLOQUEADA

⚫ ROLLBACK
9. El documento maestro que recomiendo crear

No crearía:

ORGANIZATIONAL_CONTEXT_FRAMEWORK.md

como te recomendé anteriormente.

Crearía:

docs/
└── ADR-003-contexto-organizacional-sede-area.md

documentacion/
├── ORGANIZATIONAL_SCOPE_MASTER_PLAN.md
├── ORGANIZATIONAL_SCOPE_MATRIX.md
├── ORGANIZATIONAL_SCOPE_MIGRATION_STATUS.md
└── ORGANIZATIONAL_SCOPE_AUDIT.md

Y el principal sería:

ORGANIZATIONAL_SCOPE_MASTER_PLAN.md

porque no estamos inventando una arquitectura nueva; estamos terminando el modelo organizacional definido en la arquitectura general.

10. Mi recomendación final después de ambos documentos

La arquitectura de SINTEL está en una situación bastante buena.

No veo como prioridad:

"refactorizar Facturas".

Tampoco:

"crear otro framework".

La prioridad correcta ahora es:

Terminar la transición de SINTEL desde un aislamiento puramente Empresa hacia un aislamiento organizacional Empresa → Sede → Área, utilizando la infraestructura ya existente de SedeAwareModel, TenantProfile.alcance y HasOrganizationalScope, empezando por validar y cerrar el piloto de Compras.

Esto además respeta las decisiones arquitectónicas que ya tienes:

SintelTenantBaseModel como base tenant.
Service Layer obligatorio.
DSV.
Zero-Trust.
Bridges.
Soft References.
Pull Model contable.
Separación Public/Tenant.
TenantProfile como SSoT de roles.
BaseTenantViewSet como SSoT de autenticación.
Knowledge Graph como capa posterior de gobernanza.

Y el documento de Facturas encaja perfectamente como uno de los primeros candidatos a migración posterior, porque ya demuestra que sede existe físicamente pero todavía no gobierna el alcance funcional.

En otras palabras: no debemos empezar de cero; debemos completar lo que ya construiste, convertir compras en el piloto de referencia, estandarizarlo y después propagarlo controladamente al resto del ERP.