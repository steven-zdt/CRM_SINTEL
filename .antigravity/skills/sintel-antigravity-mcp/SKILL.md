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

Response contract:

0. **Define the success check first** — the exact command or observable that confirms the fix worked. Do not act without one.
1. Start with the result or next concrete action.
2. Keep only the key evidence: file paths, commands, statuses, or official URLs.
3. Use 2 to 6 bullets only when bullets make the answer easier to scan.
4. Escalate to a fuller plan when the action is risky, destructive, ambiguous, or cross-app.
5. For official/latest claims, cite official Google sources or state that verification was not possible.

## Guardrails

- Do not edit `apps/public/` without explicit approval.
- Do not add Python files outside the approved service-layer structure.
- Do not add signals for business logic.
- Do not use `.all()` for tenant queries; filter by `empresa_id` and use `.only()` or `.defer()`.
- Do not put emojis or non-ASCII text in `.py` files.
- Preserve user changes in the worktree.

## Finish

1. Run the success check defined at step 0. If it passes → report `RESUELTO: <evidencia>` and **STOP**.
2. If check fails → different approach, never the same fix again. After 2 failures → escalate and STOP.
3. Summarize changed behavior, not every edited line.
4. Report exact validation commands and outcomes.
5. Update `MEMORY.md` after structural fixes or significant bugs.
