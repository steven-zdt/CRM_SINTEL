---
name: sintel-antigravity-mcp
description: Use when working in SINTEL with Antigravity, MCP tools, repo skills, agent rules, or when auditing/fixing tenant apps with the SINTEL architecture contract.
---

# SINTEL Antigravity MCP

Use this skill before code changes that touch SINTEL tenant apps, MCP tooling, agent rules, or repo skills.

## Startup

1. Read `MEMORY.md`.
2. Read root `AGENTS.md`.
3. Identify the target app and read its flow/audit document.
4. Load at most three focused skills from `.agents/skills`:
   - backend work: `backend/service-layer`, `backend/drf-viewset`, `backend/drf-serializers`, `backend/django-tenant`
   - frontend work: `frontend/crud-fsd`, `frontend/htmx`, `frontend/tabulator`, `frontend/vanilla-js`
   - security work: `security/zero-trust` or `anti-idor-security`

## MCP Workflow

Prefer MCP/tools for repeatable checks before manual review:

- `list_available_skills`: confirm the relevant skills are discoverable.
- `sintel_app_quality_plan`: build the reusable checklist for any `apps/tenant/<app_name>` module before app-specific work.
- `antigravity_official_context`: load the official Google Antigravity/Gemini Flash context when the task mentions Antigravity, Flash mode, official docs, MCP, or agent behavior.
- `antigravity_flash_brief`: create a compact answer scaffold before replying in Flash mode.
- `antigravity_flash_check`: audit the final draft before answering when the user asked for validation, official docs, or a concise status.
- `audit_bridge_isolation`: before finishing tenant app changes.
- app audits: run the most specific audit tool available for models, viewsets, service layer, assets, or tenant isolation.
- local fallback: `python -m py_compile <changed .py files>`, `python manage.py check`, and focused pytest.

## General-Purpose App Rule

All frameworks, tools, prompts, and skills must be parameterized by `app_name`.

- Do not hardcode module names such as a single business app.
- Prefer reusable paths: `apps/tenant/<app_name>/`, `templates/tenant/<app_name>/`, `static/<app_name>/js/`.
- Prefer reusable commands: `python -m pytest apps/tenant/<app_name>/tests -q`.
- If a tool needs a database table, require the caller to provide it instead of choosing an app-specific default.
- App-specific fixes can be implemented only inside the selected app after the general framework has identified the target.

## Flash Mode

Use Flash mode for quick, high-frequency work where the user needs the answer more than the story.

### Lifecycle (Karpathy) — OBLIGATORIO

Every Flash task MUST traverse these 4 gates in order. Do not skip.

```
[EXAMINE]  Read MEMORY.md + AGENTS.md + target app audit + targeted grep/glob.
           Output: list of in-scope files + constraints. NO writes here.

[PLAN]     Declare in <=5 lines:
             OBJECTIVE  : <verbatim user goal>
             IN-SCOPE   : <closed file list, max 10>
             OUT-OF-SCOPE: <anything else — DO NOT TOUCH>
             SUCCESS    : <observable check>
           If steps > 7 → task is too big, split and ask user.

[EXECUTE]  Apply minimal diff. After each .py edit → py_compile.
           Never touch out-of-scope files. Never refactor adjacent code.
           If you find unrelated bugs → note them, DO NOT fix.

[CLOSE]    Run SUCCESS check.
             PASS → "RESUELTO: <evidence>" + STOP.
             FAIL → different diagnosis, never same fix. 2 fails → escalate + STOP.
```

### Tangent Guard (Karpathy) — STRICT

Before every Edit/Write tool call, the action must answer YES to:

> *"Does this change appear LITERALLY in the user's stated objective?"*

If unsure → do not do it. Examples of forbidden tangents:

- "Aproveche para arreglar los tests" (unless tests are the objective)
- "Refactorice mientras estaba ahi"
- "Tambien actualice X que estaba mal"
- "Anadi una validacion extra por seguridad"

These belong in a CLOSE-time report to the user, not in the diff.

### Response contract

0. Define the success check FIRST — the exact command/observable.
1. Start with the result or next concrete action.
2. Keep only key evidence: file paths, commands, statuses, official URLs.
3. Use 2-6 bullets only when bullets aid scanning.
4. Escalate to a fuller plan when risky, destructive, ambiguous, or cross-app.
5. For official/latest claims, cite Google sources or state verification was not possible.

## Guardrails

- Do not edit `apps/public/` without explicit approval.
- Do not add Python files outside the approved service-layer structure.
- Do not add signals for business logic.
- Do not use `.all()` for tenant queries; filter by `empresa_id` and use `.only()` or `.defer()`.
- Do not put emojis or non-ASCII text in `.py` files.
- Preserve user changes in the worktree.

## Finish (CLOSE gate)

1. Run the success check defined in PLAN. PASS → `RESUELTO: <evidencia>` + **STOP**.
2. FAIL → different approach, never the same fix. 2 failures → escalate + STOP.
3. Summarize changed behavior (NOT every edited line).
4. Report exact validation commands and outcomes.
5. List any **out-of-scope findings** discovered but NOT fixed (so user can prioritize).
6. Update `MEMORY.md` after structural fixes or significant bugs.
