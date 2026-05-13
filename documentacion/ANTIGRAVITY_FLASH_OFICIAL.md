# Antigravity Flash - Validacion Oficial

Fecha de validacion: 2026-05-06

## Fuentes Oficiales Revisadas

- Google Blog: `https://blog.google/products-and-platforms/products/gemini/gemini-3/`
- Google Blog: `https://blog.google/products-and-platforms/products/gemini/gemini-3-flash/`
- Google Developers / Google Blog: `https://blog.google/innovation-and-ai/technology/developers-tools/build-with-gemini-3-flash/`

## Lectura Operativa

- Antigravity debe tratarse como una plataforma agentica: editor, terminal y browser se usan como superficies de trabajo y validacion.
- El agente debe planear, ejecutar y validar cuando la tarea sea end-to-end, dejando evidencia revisable.
- Gemini 3 Flash esta orientado a velocidad, eficiencia y ciclos iterativos de desarrollo, sin abandonar capacidades de codigo y agentes.
- En modo Flash, la respuesta debe ser corta, directa y con evidencia minima: archivos, comandos, resultados o URLs oficiales.

## Herramientas MCP Agregadas

- `sintel_app_quality_plan`: marco general de auditoria y validacion para cualquier app tenant mediante `app_name`.
- `antigravity_official_context`: contexto oficial resumido para agentes.
- `antigravity_flash_brief`: plantilla breve para respuestas Flash.
- `antigravity_flash_check`: auditor de borradores para evitar respuestas largas, vagas o sin fuentes.

## Regla De Proposito General

Toda herramienta, skill o prompt debe ser reusable para cualquier app del proyecto:

- Parametro obligatorio conceptual: `app_name`.
- Ruta canonica: `apps/tenant/<app_name>/`.
- Templates canonicos: `templates/tenant/<app_name>/`.
- Static canonico: `static/<app_name>/js/`.
- Tests enfocados: `python -m pytest apps/tenant/<app_name>/tests -q`.
- Prohibido usar una app concreta como default para checks, tablas SQL o recomendaciones.

## Regla Practica

Usar Flash para estado, validaciones puntuales, handoffs y respuestas de alto ritmo. Cambiar a plan completo cuando haya riesgo destructivo, ambiguedad, cambios multi-app o necesidad de investigacion profunda.
