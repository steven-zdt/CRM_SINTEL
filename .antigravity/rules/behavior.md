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
[EXAMINAR]  ENTENDER EL CONTEXTO primero. Leer MEMORY.md + AGENTS.md + AUDITORIA del
            app + grep/glob acotado. NO escribir nada en esta fase.
            Producto: lista de archivos en alcance + restricciones identificadas.

[PLAN]      Definir: objetivo literal, archivos a tocar, check de exito.
            Producto: LISTA DE ACCIONES numerada (3-7 pasos), una accion por linea,
            cada una con su archivo destino. Mostrarla antes de ejecutar.
            Si pasos > 7 → tarea muy grande, dividir o preguntar al usuario.

[EJECUTAR]  Hacer los pasos EN ORDEN. Despues de cada paso: SOLO py_compile (sintaxis).
            NO correr tests aqui salvo que el usuario los haya pedido (ver §6).
            Producto: diff minimo, sin codigo adyacente modificado.

[CERRAR]    Correr el check de exito (por defecto: py_compile + manage.py check, NO tests).
            PASA → reportar "RESUELTO: <evidencia>" y STOP.
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
4. **Zero-Hardcoding (§29 AGENTS.md):** Antes de cerrar cualquier tarea que toque `scripts/`, `scratch/`, `tests/` o management commands, verificar:
   ```bash
   grep -rn "'home'\|'cliente'\|'tupapi'\|'putito'\|home\.sintel\.com" \
       apps/ tests/ scripts/ scratch/ --include="*.py" \
       | grep -v "__pycache__\|migration\|assertNotIn\|\.sintel\.local\|{schema"
   # Esperado: 0 resultados
   ```
5. **ORM Traversals en Selectors (§30 AGENTS.md — Zero-Collision Pattern):**
   Al tocar `services/selectors.py` de cualquier app:
   - `LIST_FIELDS` / `DETAIL_FIELDS` — SOLO nombres de atributos directos del modelo (sin `__`)
   - Traversals ORM (`campo__subcampo`) — van en constantes privadas `_<RELACION>_TRAVERSALS`
   - `select_related("<relacion>")` — obligatorio en cada selector que use traversals
   - `source="relacion.campo"` (punto) en serializer — nunca `source="relacion__campo"`
   ```bash
   # Verificacion automatica (ver §30.10 AGENTS.md para el script completo AST):
   docker compose exec web python -c "
   import ast, pathlib, sys
   errors = []
   for f in pathlib.Path('apps/tenant').rglob('selectors.py'):
       src = f.read_text()
       try: tree = ast.parse(src)
       except: continue
       for node in ast.walk(tree):
           if isinstance(node, ast.Assign):
               for t in node.targets:
                   if isinstance(t, ast.Name) and t.id in ('LIST_FIELDS','DETAIL_FIELDS'):
                       for elt in ast.walk(node.value):
                           if isinstance(elt, ast.Constant) and isinstance(elt.value, str) and '__' in elt.value:
                               errors.append(f'{f}:{elt.lineno} {t.id}: {elt.value!r}')
   [print(e) for e in errors] if errors else print('OK')
   "
   # Para cada resultado: verificar que el serializer de esa app NO usa tuple(FIELDS) en Meta.fields
   ```

---

## 3. Prohibiciones Estrictas

- Emoji / Unicode en `.py`
- `.all()` sin `empresa_id`
- Signals para logica de negocio
- Crear `AsientoContable` directamente (usar Contabilizador)
- Tocar codigo fuera del alcance declarado en seccion 0
- **Nombres propios de tenants en codigo** (`'home'`, `'cliente'`, `'putito'`, `'tupapi'` como strings literales en logica, fixtures o scripts). Ver §29 AGENTS.md.
- **Tests CRUD sin los 3 niveles de aislamiento** — PROHIBIDO hacer merge de tests de app tenant que omitan `test_multitenant_isolation.py` con Nivel 1 (listado), Nivel 2 (IDOR UUID) y Nivel 3 (IDOR FK). Ver §24.5 AGENTS.md.
- **Traversals ORM (`campo__subcampo`) en `LIST_FIELDS` / `DETAIL_FIELDS`** — PROHIBIDO si esa constante se usa en `Meta.fields` de serializer. Mover a `_*_TRAVERSALS` + `select_related()`. Ver §30 AGENTS.md.
- **Frontend sin consultar `.agents/skills/frontend/`** — PROHIBIDO. Antes de cualquier HTML/JS/HTMX consultar htmx.md, ui-management.md, crud-fsd.md, vanilla-js.md, tabulator.md segun corresponda (AGENTS.md §31).
- **`hx-on::after-settle` en botones/forms** — PROHIBIDO. `htmx:afterSettle` dispara en el elemento TARGET, no en el iniciador. Usar `hx-on::after-request` en botones para post-swap (el swap sync ocurre antes). Usar `document.addEventListener('htmx:afterSettle', ...)` en JS para editors. Ver §26 AGENTS.md y skill htmx.md §12.

---

## 4. Ciclo Fix-Verifica-Termina

Antes de aplicar la correccion: **definir el check de exito**. Por defecto el check es la
verificacion mas barata que prueba el objetivo: `py_compile`, `manage.py check`, leer el diff,
o describir el observable. **NO una suite de tests** salvo que el usuario los haya pedido (§6).

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
python -m py_compile <archivos.py>   # SIEMPRE — sintaxis, no es un test
python manage.py check               # cuando se tocan serializer/viewset/service
docker compose config                # cuando se toca compose/infra
# python -m pytest ...               # SOLO si el usuario lo pidio (ver §6)
```

---

## 6. Tests solo bajo demanda — REGLA EXPLICITA

**No correr ni escribir tests salvo que el usuario lo pida explicitamente.**

Distincion clave:
- `py_compile` y `manage.py check` → **validacion de sintaxis/sistema, NO son tests.** Se corren siempre que aplique (hooks + cierre de tarea).
- `pytest`, `manage.py test`, crear archivos `test_*.py` → **son tests. Solo bajo peticion.**

| Situacion | Accion |
|---|---|
| Usuario pide un fix/feature sin mencionar tests | Implementar + py_compile/check. **NO** correr ni escribir tests. |
| Usuario dice "corre los tests" / "agrega tests" / "verifica con tests" | Correr/escribir los tests pedidos. |
| Codigo nuevo CRUD que por arquitectura exige `test_multitenant_isolation.py` (§24.5) | **NO** crear el test en silencio. Mencionarlo al cerrar: "Falta test de aislamiento — ¿lo agrego?" y esperar respuesta. |
| El cambio rompe (sospecha) algo testeable | Reportar el riesgo al cerrar y ofrecer correr tests. No correrlos por iniciativa propia. |

**Por que:** velocidad y foco (Karpathy). El usuario decide cuando invertir en la red de seguridad
de tests; el agente no la impone. Esto NO relaja las reglas de arquitectura (cuando se escriban
tests, deben cumplir los 3 niveles de aislamiento de §24.5 AGENTS.md).
