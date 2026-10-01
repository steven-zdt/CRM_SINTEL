# ADK_DEPENDENCY_MAP — Fase 0 (Baseline Forense) del plan de evolución

**Fecha:** 2026-09-22
**Fuente:** `documentacion/PLAN_MAESTRO_ADK_SINTEL_AGENTIC_ERP_LOOP_20260922.md` §30

Qué depende de qué, verificado por import real (no inferido). Un solo grafo de dependencias reales — no hay una segunda estructura paralela que mantener.

## Cadena de dependencias real (de arriba hacia abajo = quién llama a quién)

```text
apps/services/ai/adk/agent.py          (root_agent, ADK real)
  └─ apps/services/ai/adk/tools.py     (saludar, buscar_cliente -- async, sync_to_async al ORM)
       └─ apps/services/ai/adk/context.py   (build_context_from_session -- re-deriva AIContext desde BD)
            └─ apps/services/ai/context/ai_context.py   (AIContext, PermissionDeniedError)
       └─ apps/services/ai/engine/ai_engine.py   (AIEngine.run_tool -- punto unico de ejecucion)
            ├─ apps/services/ai/tools/registry.py    (AIToolRegistry -- get_tool())
            ├─ apps/services/ai/tools/base.py         (ToolKind, ToolRisk, AUTO_APPROVED_KINDS)
            └─ apps/services/ai/tools/clientes_tools.py  (BuscarClienteTool -- la tool real que ejecuta)
                 └─ apps/tenant/clientes/services/selectors.py  (ClienteSelector -- Service Layer real)
                      └─ apps/tenant/clientes/models.py  (Cliente -- ORM, unica fuente de verdad de datos)
```

Ningún salto se hace directo al ORM desde el agente ni desde las tools de ADK -- siempre pasa por `AIEngine.run_tool()` → `AIToolRegistry` → la tool de dominio → el Selector/Service Layer de esa app. Esto es lo que el plan de evolución exige en su §64 ("NO ACCEDAS DIRECTAMENTE AL ORM DESDE EL AGENTE... USA SELECTORS PARA READ").

## Dependencias de infraestructura (paquetes)

| Paquete | Usado por | Versión |
|---|---|---|
| `google-adk` | `apps/services/ai/adk/` | `==2.9.2`, mismo entorno que Django (ver `ADK_BASELINE.md` "arquitectura simplificada") |
| `cryptography` | `apps/tenant/facturas/services/dian/xades_signer.py`, `apps/tenant/core/dian/xades_signer.py`, `apps/services/security/crypto.py` (Fernet) — Y transitivamente `google-adk` (vía `authlib`) | `>=45.0.1,<51.0` (subido desde `<44.0`, ver adenda en `ADK_BASELINE.md`) |
| `anthropic` | `apps/services/ai/providers/anthropic_provider.py`, `ContabilidadBusinessService.sugerir_lineas_asiento_ia()` | `>=0.40.0,<1.0` |
| `pgvector` | `apps/tenant/ai_knowledge/models.py` | `>=0.5,<0.6` |
| `fastembed` | `apps/services/ai/providers/fastembed_provider.py` | `>=0.8,<0.9` |
| `asgiref` (`sync_to_async`) | `apps/services/ai/adk/tools.py` (bug real corregido en esta pasada -- tools async no pueden llamar ORM sincrono) | ya en el entorno vía Django (dependencia transitiva) |
| `django-tenants` | Todo lo anterior (`schema_context`) | ya en el entorno |

## Dependencias de datos (qué tabla/schema toca cada capa)

```text
AIContext.schema_name  -> determina el schema Postgres activo (django-tenants, aislamiento real)
Cliente (tenant_clientes.Cliente)  -> vive SOLO en el schema del tenant, nunca en 'public'
TenantProfile (perfil.TenantProfile)  -> vive en el schema del tenant, FK a User (schema 'public', SHARED_APPS)
AIKnowledgeChunk (ai_knowledge)  -> vive en el schema del tenant (pgvector), aislamiento por schema, no por filtro
```

## Qué NO depende de qué (verificado, para no romperlo por accidente en fases futuras)

- `apps/services/ai/engine/ai_engine.py` **no importa** `google.adk` en ningún punto -- el motor de IA existente es independiente de ADK, ADK es un consumidor más (igual que `form_assistant.py`).
- `apps/services/ai/adk/` **no importa** `apps/services/ai/orchestrator/form_assistant.py` -- son dos caminos de entrada distintos al mismo `AIEngine`, no se llaman entre sí.
- Ninguna tool de dominio (`clientes_tools.py`, etc.) importa nada de `apps/services/ai/adk/` -- la dependencia es unidireccional (ADK depende del dominio, nunca al revés).
- `tools/ekg/` (grafo estático) no importa nada de `apps/services/ai/` -- es una herramienta de análisis de código standalone, consumida (no consumidora).

## Conclusión

```
FASE 0 — DEPENDENCY MAP (plan de evolución) = PASS
```

Un solo grafo de dependencias real, sin ciclos, sin acceso directo al ORM desde el agente, sin una segunda vector DB/EKG/RBAC. Consistente con las reglas absolutas de ambos planes (original y evolución).
