# Comportamiento y Flujo Operativo - Antigravity

**LECTURA OBLIGATORIA ANTES DE CUALQUIER ACCION**

## Enforcement Automático

1. **`apps/public/` BLOQUEADO**: Requiere autorización explícita + RFC + `needs-admin-approval`.
2. **Validación `py_compile`**: Después de editar cualquier `.py`, ejecutar `python -m py_compile <archivo>`.

## Checklist antes de proponer código

1. Aplicar Karpathy (ver `core.md`) como primer filtro.
2. Identificar app afectada → leer su `AUDITORIA_FLUJO_COMPLETO.md`.
3. Verificar cumplimiento con `AGENTS.md` (stack, restricciones).
4. DSV en mutaciones: validar que entidades pertenezcan al tenant (`empresa_id`).

## Prohibiciones Estrictas

- Emoji/Unicode en `.py`
- `.all()` sin `empresa_id` — siempre filtrar por tenant
- Signals para lógica de negocio
- Crear `AsientoContable` directamente

## Ciclo Fix-Verifica-Termina (OBLIGATORIO)

Antes de aplicar cualquier corrección, definir el **check de éxito**: el comando o prueba mínima que confirme que el problema ya no existe.

```
Define check de éxito → Aplica fix → Corre el check
  PASA  → Reportar "RESUELTO: <evidencia>" y DETENER. No continuar.
  FALLA → Diagnóstico diferente. NUNCA repetir el mismo fix.
  FALLA x2 → Escalar a plan completo y DETENER intentos.
```

Prohibido:
- Aplicar el mismo fix más de una vez.
- Iterar sin haber corrido el check de éxito.
- Reportar "listo" sin evidencia de verificación.

## Skills + MCP

Cargar máximo 3 skills desde `.agents/skills/`. Consultar `SKILL.md` para el flujo completo.

Fallback local si MCP no disponible:

```powershell
python -m py_compile <archivos.py>
python manage.py check
python -m pytest apps/tenant/<app_name>/tests -q
docker compose config
```
