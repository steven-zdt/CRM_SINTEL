# Comportamiento y Flujo Operativo - Antigravity

**LECTURA OBLIGATORIA ANTES DE CUALQUIER ACCION**

---

## 0. Contrato de Alcance (Karpathy) — REGLA #1

**Antes de tocar UN solo archivo, contesta por escrito (mentalmente o en plan):**

```
OBJETIVO LITERAL DEL USUARIO: <copia textual de lo que pidio>
ARCHIVOS EN ALCANCE: <lista cerrada, maximo 10>
ARCHIVOS FUERA DE ALCANCE: <todo lo demas — PROHIBIDO TOCAR>
DEFINICION DE "HECHO": <el observable concreto>
```

**Si descubres durante el trabajo:**
- Un test roto en otro archivo → ANOTAR en un comentario "TODO fuera de alcance", NO arreglar.
- Un bug adyacente → ANOTAR al usuario al cerrar, NO arreglar.
- Codigo "feo" cerca → NO REFACTORIZAR. Solo lo necesario.
- Un import faltante en otro modulo → Si no bloquea el objetivo, NO TOCAR.

**Prohibido absoluto:**
- "Aproveche para mejorar X" → NO. Reportar y seguir.
- "Tambien arregle los tests" → NO, salvo que el objetivo sea tests.
- "Refactorice mientras tanto" → NO. Cambio quirurgico.
- Encadenar 2 o mas objetivos sin permiso del usuario.

**Regla mental:** Cada Edit/Write tool debe poder responder "si" a: *"¿este cambio aparece literalmente en el OBJETIVO del usuario?"* Si dudas, no lo hagas.

---

## 1. Ciclo Operativo Obligatorio: EXAMINAR → PLAN → EJECUTAR → CERRAR

```
[EXAMINAR]  Leer MEMORY.md + AGENTS.md + AUDITORIA del app + grep/glob acotado.
            Producto: lista de archivos en alcance + restricciones identificadas.

[PLAN]      Definir: objetivo literal, archivos a tocar, check de exito.
            Producto: 3-7 pasos numerados. Si pasos > 7 → tarea muy grande, dividir.

[EJECUTAR]  Hacer los pasos EN ORDEN. Despues de cada paso: py_compile / test corto.
            Producto: diff minimo, sin codigo adyacente modificado.

[CERRAR]    Correr el check de exito. PASA → reportar "RESUELTO: <evidencia>" y STOP.
            FALLA → diagnostico distinto, no el mismo fix. 2 fallas → escalar y STOP.
```

**Prohibido:**
- Saltar de EXAMINAR a EJECUTAR sin PLAN.
- Modificar archivos durante EXAMINAR (solo lectura).
- Ejecutar mas pasos de los planeados sin re-PLAN.
- Cerrar sin correr el check de exito.

---

## 2. Enforcement Automatico

1. `apps/public/` BLOQUEADO sin autorizacion explicita + RFC.
2. Tras editar `.py` → `python -m py_compile <archivo>` (PostToolUse hook).
3. Tras editar serializer/viewset/service → `python manage.py check`.

---

## 3. Prohibiciones Estrictas

- Emoji / Unicode en `.py`
- `.all()` sin `empresa_id`
- Signals para logica de negocio
- Crear `AsientoContable` directamente (usar Contabilizador)
- Tocar codigo fuera del alcance declarado en seccion 0

---

## 4. Ciclo Fix-Verifica-Termina

Antes de aplicar la correccion: **definir el check de exito** (comando o prueba minima).

```
Define check → Aplica fix → Corre check
  PASA  → "RESUELTO: <evidencia>" + STOP
  FALLA → Diagnostico diferente (NO repetir mismo fix)
  FALLA x2 → Escalar a plan completo + STOP
```

Prohibido: aplicar el mismo fix mas de una vez. Reportar "listo" sin evidencia.

---

## 5. Skills + MCP

Maximo 3 skills cargadas desde `.agents/skills/`. Flujo completo en `SKILL.md`.

Fallback local si MCP no disponible:

```powershell
python -m py_compile <archivos.py>
python manage.py check
python -m pytest apps/tenant/<app_name>/tests -q
docker compose config
```
