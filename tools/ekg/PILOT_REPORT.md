# EKG Pilot Report — 17/17 tenant apps extracted, rollout complete

**Every app under `apps/tenant/` has been extracted, spot-checked against its own `.agent/`
audit doc, and merged into one graph: 2,506 nodes, 3,597 edges, zero dangling edges, and exactly
one harmless remaining cross-app stub (`settings.AUTH_USER_MODEL`) in the whole project** —
`compras`, `ventas`, `facturas`, `proveedores`, `proyectos`, `gastos`, `clientes`, `inventario`,
`empresa`, `empleados`, `perfil`, `core`, `contabilidad`, `bancos`, `cotizaciones`, `dashboard`,
`landing`.

Seven real bugs were found and fixed along the way, not just coverage added: (1) `proveedores` -
cross-app Model ids needed to key off Django's real `app_label`, not the `apps/tenant/<folder>`
name, or a stub from one app's FK could never merge with the real node from another app's own
extraction; (2) `inventario` - `path('', include(router.urls))`, a very common DRF idiom several
earlier apps just hadn't happened to use, was misread as a spurious unlinkable endpoint;
(3) discovered auditing the accumulated graph rather than extracting a new app ("spot-check #8")
- an already-resolved cross-app node could be silently downgraded back to an unresolved stub
depending on merge order; (4) `core` - every `defined_in` property baked in an absolute,
machine-specific path instead of a portable one, present since the very first app but invisible
until a real CLI run (not an ad-hoc test script) was inspected; (5)-(6) `dashboard` - two
separate module-qualified-view-reference bugs (`views.X.as_view()` / `router.register(r'',
viewsets.X, ...)`) silently prevented endpoint linking whenever code imported a views/viewsets
*module* instead of the class directly. Three real, non-bug findings came out too: a deprecated
same-named compat shim in `clientes` (spot-check #6), the `core/api/v1/` dual-registration
mirror layer implementing ADR-002 (spot-check #12), and a recurring "sibling package/file"
structural gap confirmed in three places across `contabilidad`/`cotizaciones` (spot-checks
#13/#15) that argues for a general fix rather than one-off patches.

**Update (2026-08-05, smoke-test session):** Docker became available; the live Neo4j load is now
done too - all 17 apps loaded into a real Neo4j, 2,506 nodes / 3,597 edges, exact match to the
offline prediction (see "DONE" section below). Two more real bugs found and fixed getting there
(a `requirements.txt` tree-sitter version pin without the API this pipeline needs, and an
unrelated pre-existing Django migration app-label typo that blocked the app from starting at
all). Governance rules (Fase 20 of the original spec) are **still deliberately not written into
`AGENTS.md`/`CLAUDE.md`** — full app coverage and the verified live load remove the two biggest
reasons to wait, but the known gaps below (django-tables2 views, sibling packages,
`contabilidad/integracion/`) should be weighed first; see the roadmap.

## Rollout spot-check #1: `ventas` (2026-08-04)

Ran the unmodified pipeline against `ventas` (23 Python files, structurally similar to
`compras`: `.agent/`, `api/`, `services/`, `static/`, `templates/`, `tests/`) with zero crashes:
157 nodes, 137 edges, 0 dangling edges. The same `tabla/`-route gap documented above reproduced
exactly as predicted (django-tables2 view, no node type for it yet).

Spot-checking the output against `apps/tenant/ventas/models.py` surfaced a real bug in the
extractor, not in the source: `Venta.factura_asociada` is a `OneToOneField("facturas.Factura",
...)` — no `tenant_` prefix — while `Venta.cliente`/`Venta.proyecto` use
`"tenant_clientes.Cliente"`/`"tenant_proyectos.Proyecto"`. `extract_python.py` had hardcoded
`app_label = f"tenant_{app_name}"`, an assumption that held for `compras`/`ventas` by
coincidence (both explicitly set `AppConfig.label = "tenant_<name>"`) but is wrong in general —
checking all 17 apps' `apps.py` shows it's roughly an even split:

| Overrides `label = "tenant_<name>"` | Keeps Django's bare default |
|---|---|
| compras, ventas, gastos, clientes, proveedores, proyectos, inventario | facturas, contabilidad, bancos, core, cotizaciones, dashboard, empleados, empresa, landing, perfil |

Fixed with `extract_python.py:resolve_app_label()`, which now reads each app's real
`AppConfig.label` via the same Tree-sitter class-body walk already used elsewhere, falling back
to Django's own default only when the app doesn't override it. Pinned by
`test_app_label_resolution_matches_real_django_labels` so it can't regress. This did not change
`compras`'/`ventas`' own output (both already had explicit labels) — it matters for the next
apps in the rollout that don't (facturas, contabilidad, bancos, ...), which would otherwise have
had every genuinely-internal same-app FK misclassified as an unresolved external stub.

## Rollout spot-check #2: `facturas` (2026-08-04) — a real coverage gap, not yet fixed

Ran the pipeline against `facturas` (99 Python files — DIAN electronic invoicing, the largest
and most structurally different app checked so far): 327 nodes, 343 edges, no crash, no
dangling edges. But `facturas/api/` and `facturas/services/` are **not** flat like
`compras`/`ventas` — they have nested subpackages the extractor has no knowledge of:

- `api/mixins/` (`factura_mail_mixin.py`, `factura_ubl_mixin.py`, `factura_xml_mixin.py`)
- `api/views_mail_ingestion.py`, `api/filters.py`, `api/permissions.py`
- `services/dian/` (`attached_document.py`, `cufe.py`, `ubl21_builder.py`, `xades_signer.py`)
- `services/services_mail_ingestion.py`

`extract_services`/`extract_viewsets`/`extract_serializers` only look at the fixed filenames
`services/{selectors,crud_service,business_service,api_mixins}.py` and
`api/{serializers,viewsets}.py` — the exact FSD layout `compras`/`ventas` follow. For `facturas`
this means the core CRUD/business/selector layer and the main `FacturaViewSet` **were**
extracted correctly, but the entire DIAN XML/UBL/XAdES subsystem and the mail-ingestion
subsystem were silently skipped — the dry-run graph is real but **partial** for this app, not
representative of full coverage the way `compras`'/`ventas`' graphs are.

**Fixed in a follow-up pass** (same session): `extract_services` now walks `services_dir`
recursively — the four canonical FSD filenames (`selectors.py`, `crud_service.py`,
`business_service.py`, `api_mixins.py`) still classify as before, and everything else
(top-level or nested, e.g. `services/dian/cufe.py`, `services/services_mail_ingestion.py`)
gets the new `SERVICE_KIND_OTHER` kind rather than a guessed/wrong one. `extract_viewsets` now
walks `api_dir` recursively too, in two passes (collect every ViewSet-family node first, then
resolve `INHERITS`/`USES` edges against the full set) — a class counts as ViewSet-family if its
name or bases contain `ViewSet`/`Mixin`/`View`/a handful of DRF base-class markers
(`APIView`, `GenericAPIView`, `ListAPIView`, `CreateAPIView`), tagged with a new `kind` property
(`viewset` / `mixin` / `view`) so the three stay distinguishable on one label instead of
needing separate node types.

Result: `facturas` went from 327/343 (nodes/edges) to 337/363. The two previously-orphaned
`ingesta-correo/run/` and `ingesta-correo/runs/` endpoints are now correctly `EXPOSES`-linked to
their real `MailIngestionRunCreateAPIView`/`MailIngestionRunsListAPIView` nodes (`kind=view`),
and `FacturaViewSet` now shows explicit `INHERITS` edges to `FacturaUBLMixin`/
`FacturaMailMixin`/`FacturaXMLMixin` (`kind=mixin`), matching its real
`class FacturaViewSet(FacturaUBLMixin, FacturaMailMixin, FacturaXMLMixin, FacturaServiceMixin,
BaseTenantViewSet)` declaration. `compras`/`ventas` counts are byte-for-byte unchanged (151/130,
157/137) — confirming the generalization is additive, not a behavior change for apps that were
already flat. Pinned by `tools/ekg/tests/test_extract_python_nested_layout.py` (4 new tests,
26/26 total passing).

**Still not modeled, and correctly not claimed:** `services/services_mail_ingestion.py` itself
is module-level functions (`enqueue_mail_ingestion`, `process_mail_ingestion_sync`, ...), not
classes — this pilot only extracts classes, so those functions have no Service node. That's an
honest scope boundary (documented in `extract_python.py`'s module docstring candidates for a
future pass), not a bug the way the pre-fix silent directory-skipping was.

## Rollout spot-check #3: `proveedores` (2026-08-04) — found and fixed a cross-app id bug

Ran the pipeline against `proveedores` (39 files, referenced by `compras.OrdenCompra.proveedor`
and several other apps' FKs — a natural next pick to see whether cross-app links actually
resolve once both sides exist): clean extraction, 193 nodes, 193 edges, 0 dangling edges, 0
unexposed endpoints, `services/services.py` (a fifth, non-FSD file) correctly picked up as
`SERVICE_KIND_OTHER` by the spot-check #2 fix.

Checking whether `compras`' `Model:tenant_proveedores.Proveedor` external stub actually becomes
the same node as `proveedores`' own real `Proveedor` model once both graphs are merged (the
entire point of building a shared multi-app graph) surfaced a real, previously-invisible bug:
**it didn't.** Every non-FK-target node type (`Application`, `Service`, `ViewSet`, `Serializer`,
`Endpoint`, `Template`, `JS`) is correctly keyed by the `apps/tenant/<folder>` name, because
that's the namespace Python's own import paths use (needed for the `IMPORTS` cross-app edges).
But `Model` ids were *also* being built from that folder name
(`model_id(app_name, class_name)`), while every FK string and `Meta.model` reference resolves
through Django's **app_label** namespace instead - the exact namespace the spot-check #1
(`ventas`) bug was about. Since roughly half the apps' folder name differs from their real
app_label, roughly half of all cross-app FK stubs created so far had an id that could never
match the real node: e.g. `compras`' stub was `Model:tenant_proveedores.Proveedor` (built
correctly from the FK string) while a direct extraction of `proveedores` was producing
`Model:proveedores.Proveedor` (built from the folder name) - two permanently separate nodes for
the same real table.

Fixed by keying `Model` ids by `app_label` everywhere (`extract_models`, `resolve_model_target`,
including the same-app and self-referential-base branches) instead of `app_name` - the only node
type where this applies, since it's the only one Django itself makes address-able by a
different name than its folder. Also fixed a related staleness bug this exposed: `Graph.add_node`
merges properties by dict-union, so a node first seen as an external stub (`external: True`) and
later actually extracted for real needs its own node to *explicitly* set `external: False` (not
omit the key) or the stale `True` survives the merge forever. Verified end-to-end: building
`compras` and `proveedores` separately and merging them now collapses the stub into the real
node, `external` correctly flips `True -> False`, and `defined_in`/`bases` populate. Pinned by
`test_cross_app_fk_stub_resolves_to_real_node_once_both_apps_are_merged` in
`tools/ekg/tests/test_build_graph.py` (27/27 tests passing). `compras`'/`ventas`'/`facturas`' own
node *counts* are unchanged by this fix (same nodes, just re-keyed) - only cross-app merge
behavior changed, which no earlier spot-check could have caught because none of them had merged
two independently-extracted apps into one graph before.

## Rollout spot-check #4: `proyectos` (2026-08-04) — clean run, one documented ambiguity

Picked `proyectos` (43 files) specifically because it's referenced by FK from *two* already-
extracted apps (`compras.OrdenCompra.proyecto`, `ventas.Venta.proyecto`), to confirm spot-check
#3's fix generalizes: merging `compras` + `ventas` + `proyectos` correctly collapses both stubs
onto the one real `Model:tenant_proyectos.Proyecto` node. Clean extraction otherwise: 252 nodes,
254 edges, 0 dangling edges, 0 unexposed endpoints. `api/mixins.py` (a single file, unlike
facturas' `api/mixins/` subpackage) and two extra non-FSD service files
(`presupuesto_service.py`, `tareas_service.py`) were picked up correctly by the spot-check #2
generalization without any further change needed.

Surfaced a genuine naming collision in the real source, not an extraction bug: `proyectos` has
**two different classes both named `ProyectoServiceMixin`** —
`api/mixins.py:11 class ProyectoServiceMixin:` (API-layer) and
`services/api_mixins.py:28 class ProyectoServiceMixin(BaseServiceMixin):` (FSD service layer).
The graph keeps them as two separate nodes (`ViewSet:proyectos.ProyectoServiceMixin` vs.
`Service:proyectos.api_mixins.ProyectoServiceMixin`), which is correct - but resolving which one
`ProyectoViewSet(ProyectoServiceMixin, ...)` actually inherits is done by **name**, preferring a
sibling ViewSet-family match over a Service-layer match (see `extract_viewsets`'s pass 2), not
by actually reading `from .mixins import ProyectoServiceMixin` at the top of the file. It got
this one right (`ProyectoViewSet` does import from `.mixins`, confirmed by grep), but that's the
extractor's base-name priority order agreeing with reality by construction, not because it
traced the import - a different app with the same kind of same-name collision but the opposite
import direction would resolve wrong. Documented as a known limitation below rather than
silently trusted; a real fix would need to track which specific imported symbol each identifier
in a class's base list actually refers to, which is a meaningfully bigger scope than this
rollout pass.

## Rollout spot-check #5: `gastos` (2026-08-04) — clean, closes out compras' FK stubs

Picked `gastos` because it's `compras.OrdenCompra.documento_soporte`'s target — the last of
`compras`' three cross-app FKs still unresolved (`proveedor`/`proyecto` were closed by
spot-checks #3/#4). Flat FSD layout, clean extraction: 169 nodes, 152 edges, 0 dangling edges.
Merging `compras` + `gastos` confirms `Model:tenant_gastos.DocumentoSoporte` collapses from stub
to real node exactly like the other two — **all three of `compras`' original external stubs are
now real, verified cross-app links.**

Two things reproduced exactly as predicted rather than surprised: `gastos` is (per `MEMORY.md`
ADR-006) one of the three apps already migrated off Tabulator, and sure enough its two
django-tables2 UI routes (`tabla-documentos/`, `tabla-resoluciones/`) show up as
`unexposed_endpoints`, same known gap as `compras`'/`facturas`' `tabla/` routes (roadmap item
2, still not started). And unlike `compras`/`ventas`/`proyectos`, `gastos` has **no untested
Models** in the validation output — consistent with the earlier research finding that `gastos`
has "3 niveles" of test coverage, the most complete of any app checked so far.

## Rollout spot-check #6: `clientes` (2026-08-04) — surfaced real technical debt, not a bug

Picked `clientes` because it's `ventas.Venta.cliente`'s target. Clean extraction (195 nodes,
199 edges, 0 dangling edges, 0 unexposed endpoints), and the `ventas` -> `Cliente` stub resolves
to the real node on merge exactly like the previous three.

The interesting find here isn't an extractor bug — it's a real architecture smell the graph
surfaced for free: `apps/tenant/clientes/services/services.py` is an explicitly self-documented
"Backward-compatibility layer" (`[ARCHITECTURE v3.5]`) that **redefines `ClienteBusinessService`
under the exact same class name** as the real one in `business_service.py`
(`class ClienteBusinessService(ClienteBusinessService):` — subclassing the imported real one,
shadowed under its own name), plus a second-generation `ClienteServiceMixin`. Both classes'
docstrings say "Deprecated: Use ... directly." The graph keeps them as two distinct nodes
(`Service:clientes.business_service.ClienteBusinessService` kind=`business` vs.
`Service:clientes.services.ClienteBusinessService` kind=`other`) — correct, since they really
are two different classes — but this is exactly the sort of "que módulos tienen deuda técnica"
question from the original EKG request that a text search wouldn't surface as cleanly as a
graph query for "two Service nodes with the same `name` property in the same Application."
Not dead code either: `grep` confirms `tests/test_clientes_api_and_service.py` and
`tests/test_idempotence_v2614.py` still import `crear_cliente` from this exact module.

This also exposed a latent (not yet triggered) bug worth documenting rather than silently
carrying: `extract_services`' `receivers` dict (used to resolve `business_service` -> other
Service `CALLS` edges) is keyed by bare class name across the *whole* app, last-file-processed
wins. Since `services.py` happens to be the last file processed here, nothing calls into
`ClienteBusinessService` by name afterward, so no edge was actually mislinked in this run — but
an app where a later-processed file calls a same-named class expecting the "real" one would
silently get routed to whichever definition was seen last, not necessarily the correct one.
Left as a known limitation (see below) rather than fixed under rollout momentum, same standard
as spot-check #4's naming-collision note.

## Rollout spot-check #7: `inventario` (2026-08-04) — fixed a real, likely-widespread bug

Picked `inventario` because it's the last of `ventas`' four cross-app FK targets
(`Producto`/`Servicio`), and turned up a genuine extractor bug. `apps/tenant/inventario/api/
urls.py` mounts its router with `path('', include(router.urls))` - a very common DRF idiom.
Every earlier app happened to use `urlpatterns = router.urls` directly instead (no wrapping
`path()` call), so this was the first time `extract_urls`'s `path()` branch ever saw an
`include(...)` call as the view argument. It didn't recognize that shape, so it created a
permanent `Endpoint:inventario::api` node for the mount line itself - route `''`, "view"
`include(router.urls)` - which could never resolve to a real ViewSet and would always show up
in `validate.py`'s `unexposed_endpoints` no matter how correct the actual extraction was.

Fixed with `_is_include_call()`: `path()` calls whose second argument is an `include(...)` call
are now skipped entirely (they mount a sub-urlconf, they are not themselves an endpoint) rather
than misrepresented as a broken one. Verified: `inventario`'s `unexposed_endpoints` went from 1
to 0, node count dropped by exactly 1 (the spurious node, nothing else changed), and rebuilding
all seven previously-extracted apps confirmed byte-for-byte identical counts (none of them used
this urls.py pattern, so none were ever affected by the bug or the fix). Both `Producto` and
`Servicio` stubs from `ventas` resolve correctly on merge. Pinned by
`test_router_include_mount_is_not_a_spurious_endpoint` (28/28 tests passing) - which also
explicitly asserts the *other* empty-route endpoint in this same app
(`path('', ProductoViewSet.as_view(...))` in the app-level `urls.py`, group `ui`) is still
extracted, so the fix doesn't overcorrect into treating every empty route as suspicious.

Also noted, not investigated further: `inventario` has real centralized tests
(`tests/tenant/inventario/test_*.py`, 4 files) yet `validate.py` shows every single Model/
Service/ViewSet as untested. Consistent with the already-documented "TESTED_BY is a literal
identifier-name scan" limitation (same category as the ViewSet->Serializer static scan) - these
test files likely exercise the app through factories/fixtures or lower-level parsing/
materialization logic rather than referencing `ProductoViewSet` etc. by name directly.

## Rollout spot-check #8: order-independence bug found auditing the accumulated stub set

Before picking a 9th app, audited *which* external stubs still existed across all 8 apps merged
together — expecting only apps not yet extracted to show up. `tenant_proveedores.Proveedor` and
`facturas.Factura` showed up as external stubs despite both `proveedores` and `facturas` already
being extracted. Root cause: `gastos` (and, transitively, any other already-extracted app with
its own FK to a model another app already resolved for real) independently builds its **own**
`external=True` stub for `tenant_proveedores.Proveedor` when extracted standalone - correct in
isolation. But `Graph.add_node`'s dict-union merge (`{**existing.properties, **node.properties}`)
let whichever app happened to be merged *last* win, so merging `gastos` after `proveedores`
silently flipped the already-resolved real node back to `external=True`. This is exactly the
kind of bug that stays invisible in any single-app or two-app test and only surfaces once enough
apps accumulate that a stub-creating reference and a real definition actually collide in one
merged graph - found by auditing the accumulated graph, not by extracting a new app.

Fixed by making `external` monotonic in `schema.Graph.add_node`: once a node is known real
(`external is False`), a later merge can never flip it back to `True`, regardless of order. The
same bug exists in `load_neo4j.py`'s live Cypher write (`SET n += row.props` blindly overwrites
`external` too) - fixed there with a `CASE` that captures the node's prior `external` value
before the blind property merge and re-applies the same monotonic rule. The Neo4j-side fix could
not be exercised against a live server in this environment (same standing limitation as the rest
of `load_neo4j.py`); the Python-side fix is fully covered by
`test_external_flag_is_monotonic_across_merge_order`, which pins both merge orders explicitly.
Verified with 3 random shuffles of all 8 extracted apps' merge order - `Proveedor` and every
other cross-app FK target stayed resolved (`external=False`) in every ordering. All 8 apps'
individual dry-run counts are unchanged (this only affects merge behavior, not extraction).
29/29 tests passing.

## Rollout spot-check #9: `empresa` (2026-08-04) — highest-value remaining stub target, clean

Re-audited the accumulated stub set after the spot-check #8 fix and picked `empresa` because it
had the most real incoming FK references from already-extracted apps (`facturas.sede`,
`proyectos.sede`, `gastos.sede`, `inventario.sede` -> `Sede`; `facturas.MailInboxState
.mailbox_config` -> `MailInboxConfig`; `clientes.Cartera.empresa` -> `Empresa` itself). Clean
extraction: 233 nodes, 254 edges, 0 dangling edges. All six of those references resolve to real
nodes once `empresa` is merged in.

Three `unexposed_endpoints` (`empresa/actividades-lookup/`, `empresa/ciiu-lookup/`,
`empresa/form-metadata/`) - not a bug, an extension of an already-documented boundary: these are
plain function-based DRF views (`form_metadata`, `actividades_lookup`, `ciiu_lookup` in
`api/urls.py`, presumably `@api_view`-decorated functions), and this pilot only extracts
*classes* (same reason `services/services_mail_ingestion.py`'s functions have no Service node,
see spot-check #2). Not fixed here - noted as the same class of gap, not a new one.

## Rollout spot-check #10: `empleados` (2026-08-04) — clean, resolves last known dangling stub

Picked `empleados` (40 files, payroll/nómina) as the last app any already-extracted app's FK
pointed at (`tenant_empleados.Empleado`, referenced from elsewhere in the graph). Clean
extraction: 298 nodes, 346 edges, 0 dangling edges. `Empleado` resolves to a real node on merge.

Reproduced the known django-tables2 gap at the largest scale seen yet: **7** `unexposed_endpoints`
(`contratos/tabla/`, `liquidaciones/master+detalle/tabla/`, `nominas/master+detalle/tabla/`,
`resoluciones/tabla/`, plain `tabla/`) - same documented cause (no `views.py`/`tables.py`
extractor), not a new finding, just the widest instance of it so far. After this app,
re-audited the full accumulated stub set again (same discipline as spot-check #8): only one
remains, `Model:perfil.TenantProfile` (1 incoming reference from an already-extracted app) -
everything else FK-referenced between the 10 apps extracted so far is now a real, resolved
link. `perfil` is next up specifically to close that last one out.

## Rollout spot-check #11: `perfil` (2026-08-04) — closes the last stub, one minor quirk noted

Extracted `perfil` (25 files) specifically to resolve `TenantProfile`, the one remaining stub
with an incoming reference from any already-extracted app. Clean: 131 nodes, 110 edges, 0
dangling edges, 0 unexposed endpoints. `TenantProfile` resolves to a real node on merge.

Re-auditing the full 11-app merged graph afterward found exactly one stub left:
`Model:settings.AUTH_USER_MODEL`. Not a bug, but worth flagging as a minor quirk:
`perfil/models.py:79`'s FK target is `settings.AUTH_USER_MODEL` (Django's own indirection for
"whatever the configured user model is"), an `attribute` expression, not a string literal.
`resolve_model_target` doesn't distinguish "a dynamic non-string reference that happens to
look like `label.Model`" from a real one, so it produces a technically-harmless but
semantically-odd stub treating `settings` as if it were an app_label. Left as-is rather than
special-cased for this one Django idiom - low value at this point in the rollout (it can never
collide with a real app node since no app is named "settings," and `validate.py` already
treats external stubs as expected/shallow, not errors).

**11/17 apps now extracted; every FK edge between them is a real, resolved, order-independent
link with zero remaining cross-app stubs** (aside from the harmless `settings.AUTH_USER_MODEL`
quirk above). Remaining apps (`bancos`, `contabilidad`, `core`, `cotizaciones`, `dashboard`,
`landing`) have no incoming references from any app extracted so far, so the "highest-value
stub target" heuristic that guided spot-checks #3-#11 no longer applies - pick order for the
rest can be driven by app size/complexity instead (see roadmap).

## Rollout spot-check #12: `core` (2026-08-04) — a portability bug and a real architecture find

Picked `core` (96 files, the cross-schema bridge layer AGENTS.md §17 singles out) as the largest
and most structurally divergent remaining app: `services/` has neither `crud_service.py` nor
`business_service.py` at all (everything classifies as `SERVICE_KIND_OTHER` or the two files
that do match, `selectors.py`/`api_mixins.py`), and `api/` has `base_viewsets.py`, `handlers.py`,
`health.py`, `utils.py`, and a whole `api/v1/` subdirectory alongside the usual files. No crash:
340 nodes, 295 edges, 0 dangling edges, 0 unexposed endpoints.

Two things came out of this app, one a bug and one a genuine architecture finding:

**Bug: every `defined_in` property, in every app extracted so far, was an absolute path.**
`build_graph.py`'s `PROJECT_ROOT` is always `Path(__file__).resolve().parents[2]` - absolute by
construction - and the four `defined_in`-emitting extractors
(`extract_models`/`extract_services`/`extract_serializers`/`extract_viewsets`) were building it
from `path.as_posix()` directly instead of relative to project root. This went unnoticed through
11 apps because every ad-hoc verification script in this rollout happened to call
`build_app_graph(app, Path('.'))` with a relative root, which masked it - only running the real
CLI (`python -m tools.ekg.build_graph --app core`) and inspecting the output surfaced it. Fixed
by threading `project_root` through all four functions and a new `_defined_in()` helper; this
matters for real, not just cosmetically - a shared graph meant to be the same regardless of
whether it was extracted on a Windows host or inside the `/app`-mounted Docker container needs
portable paths, not one machine's absolute filesystem layout baked into every node. Rebuilt all
12 extracted apps afterward: identical node/edge counts everywhere (confirms the fix only
changed the string value of `defined_in`, nothing structural). Pinned by
`test_defined_in_is_relative_not_absolute` (30/30 tests passing).

**Finding: `core/api/v1/` is a whole parallel mirror of ViewSets** -
`ClienteCoreViewSet`, `CuentaContableCoreViewSet`, `CotizacionCoreViewSet`, `EmpleadoCoreViewSet`,
`EmpresaCoreViewSet`, `FacturaCoreViewSet`, `GastoCoreViewSet`, `CategoriaItemCoreViewSet`,
`ProyectoCoreViewSet`, and more - one subdirectory per business app
(`api/v1/clientes/`, `api/v1/contabilidad/`, `api/v1/cotizaciones/`, `api/v1/empleados/`,
`api/v1/empresa/`, `api/v1/facturas/`, `api/v1/gastos/`, `api/v1/inventario/`,
`api/v1/proyectos/`), each with its own `viewsets.py`. This is the concrete implementation of
ADR-002's dual-registration rule (ANY endpoint reachable from the public-schema domain must be
registered in both URL confs) - `core` is where that second registration actually lives for
nearly every business app. The generic ViewSet-family recursion from spot-check #2 picked up all
of these correctly with no further change needed, tagged `kind=viewset` alongside `core`'s own
`CoreAuthViewSet`/`CoreLinksViewSet`/`DashboardSectionsViewSet` (`kind=viewset`) and
`HealthView`/`TenantInfoView` (`kind=view`). Worth a dedicated cross-app edge type in a future
pass (`core.ClienteCoreViewSet` "mirrors" `clientes.ClienteViewSet`) rather than just sitting
there as an unlinked second ViewSet node - noted as a roadmap item, not built here.

## Rollout spot-check #13: `contabilidad` (2026-08-04) — a deliberately undiagnosed gap

Extracted `contabilidad` (72 files, the accounting engine AGENTS.md §18/ADR-001 describe as the
"Pull Model" - `Contabilizador`, extractors, resolver). No crash: 374 nodes, 473 edges, 0
dangling edges. `AGENTS.md`'s `[CONTAB] 18.` section (not one of the universal tags, app-specific
by text mention) correctly linked to `contabilidad` via `GOVERNED_BY`. Six `unexposed_endpoints`
- five more `*/tabla/` django-tables2 routes (same known gap) plus one real, if minor, find:
`path('partials/summary/', deprecated_summary_view, ...)` - a function-based view whose own name
says `deprecated_` (same class of gap as the two other function-based-view instances already
noted in `empresa`/`facturas`' mail-ingestion views, and a smaller-scale echo of `clientes`'
deprecated-shim finding from spot-check #6). No new stubs; the 12-app merged graph still has only
the one harmless `settings.AUTH_USER_MODEL` quirk.

**A gap noted deliberately, not fixed:** `apps/tenant/contabilidad/integracion/` (and its
`extractores/` subpackage) is completely unindexed by this pilot. This is not a minor omission -
it's the literal implementation of the architecture AGENTS.md §18 and `docs/ADR-001-retention
-pull-model.md` describe as load-bearing: `Contabilizador`, the `AbstractExtractor` base class
and its four concrete extractors (`ExtractorFacturas`/`ExtractorGastos`/`ExtractorInventario`/
`ExtractorNomina` - matching §18.1's file map exactly), `ResolverCuentas`, the frozen-dataclass
DTOs (`TransaccionEconomica`, `ComprobanteManualDTO`, ...), and a dedicated exception hierarchy.
`integracion/` sits as a sibling to `services/`/`api/` under the app root, not nested inside
either, so none of the three recursive-walk extractors (models/services/viewsets) ever visit it.
Unlike the `views.py`/`tables.py` gap (which just needs another instance of a pattern this pilot
already models, ViewSet/Table), this package doesn't map cleanly onto the existing Service/kind
vocabulary at all - a DTO is not a selector/crud/business/mixin/other Service, and forcing it
into that box would misrepresent it. Doing this properly means either a new node type (the
original 20-phase spec's Fase 2 list includes "DTO" - never used until now because nothing
needed it) or a deliberate decision to keep DTOs out of scope and only model
`Contabilizador`/`AbstractExtractor`/extractors/`ResolverCuentas` as `Service`s. Left as an
explicit roadmap item rather than a rushed decision made mid-rollout.

## Rollout spot-check #14: `bancos` (2026-08-04) — clean

Flat FSD layout, clean extraction: 156 nodes, 153 edges, 0 dangling edges. Two
`unexposed_endpoints` (`cuentas/tabla/`, `extractos/tabla/`) - same known django-tables2 gap, no
new finding. No new cross-app stubs; the merged graph across all 14 extracted apps still has
only the one `settings.AUTH_USER_MODEL` quirk. 30/30 tests still passing.

## Rollout spot-check #15: `cotizaciones` (2026-08-04) — the "sibling package" gap recurs, twice

No crash: 210 nodes, 201 edges, 0 dangling edges. But 8 `unexposed_endpoints`, and tracing them
confirmed the same class of gap spot-check #13 flagged in `contabilidad/integracion/` shows up
here in two more shapes, not just one:

1. **A nested sub-app**: `apps/tenant/cotizaciones/configuracion/` has its own complete FSD
   ecosystem - `models.py` (`ConfiguracionCotizacion`), `serializers.py`, `viewsets.py` (at the
   package root, not under an `api/` subfolder), and its own `services/{api_mixins,
   business_service,crud_service,selectors}.py`. `api/urls.py` imports
   `ConfiguracionCotizacionViewSet` from `..configuracion.viewsets` and registers it - a real
   `Endpoint:cotizaciones:configuracion:api` node gets created (route extraction doesn't care
   where the ViewSet class lives), but nothing ever created the `ConfiguracionCotizacionViewSet`
   node itself, so it can never be `EXPOSES`-linked. 6 of the 8 unexposed endpoints trace to this
   one nested sub-app (the router registration plus 4 `partials/configuracion/*` UI routes plus
   the ViewSet's own render-offcanvas actions).
2. **A loose top-level file**: `apps/tenant/cotizaciones/ui_views.py` (not under `api/`, not
   under `configuracion/`, just a stray file at the app root) defines
   `CotizacionEditorTemplateView`/`CotizacionEditorDraftView`, plain Django `TemplateView`
   subclasses wired via `path('editor/...', ..., .as_view())` in `api/urls.py`. Accounts for the
   remaining 2 unexposed endpoints.

Not fixed here, same discipline as spot-check #13 - but this is now **three separate instances**
across two apps (`contabilidad/integracion/`, `cotizaciones/configuracion/`,
`cotizaciones/ui_views.py`), which changes the calculus for the roadmap item: this isn't a
one-off shape to special-case, it's a recurring pattern (apps growing sibling packages/files
outside the `models.py`/`api/`/`services/` convention as they mature) that argues for a more
general fix - e.g. also scanning `app_dir` itself (not just `api/`/`services/`) for stray
View-family files, and detecting sibling packages that themselves look like a nested FSD
ecosystem (their own `models.py`+`viewsets.py`+`services/`) - rather than three narrow
special-cases. Logged as a strengthened, more specific version of roadmap item 3. No new
cross-app stubs; 30/30 tests still passing.

## Rollout spot-checks #16-17: `dashboard`, `landing` (2026-08-04) — rollout complete, 17/17

**`dashboard`** (39 files) surfaced one more real, fixable bug: `api/urls.py` does `from . import
views` / `from . import viewsets` (module imports, not `from .viewsets import X`), so its
`path()`/`router.register()` calls reference `views.DashboardDataAPIView.as_view()` /
`viewsets.DashboardViewSet` - module-qualified, not bare class names.
`view_text.split(".", 1)[0]` (the endpoint-linking logic since spot-check #1) silently grabbed
the wrong segment ("views"/"viewsets", the module name) instead of the class name, so none of
`dashboard`'s 5 endpoints could ever resolve even though the ViewSet/APIView nodes themselves
were extracted correctly. Fixed with a proper `_extract_view_class_name()` helper (strips the
call, takes the segment before a trailing `.as_view` or the last dotted segment otherwise) for
the `path()` case, and an equivalent one-line fix for `router.register()`. Verified: `dashboard`'s
`unexposed_endpoints` went 5 -> 1 -> 0 (two separate call sites, two separate fixes). Rebuilt all
15 previously-extracted apps: identical counts everywhere - none of them happened to use
module-qualified view imports, so the bug was real but had been silently dormant since the
pilot's first app. Pinned by two new tests (32/32 total passing).

**`landing`** (17 files, the smallest app - account activation / login) extracted clean: 112
nodes, 47 edges, 0 dangling edges, 0 unexposed endpoints.

**Full rollout complete: 17/17 tenant apps extracted.** Merging all of them into one graph:
**2,506 nodes, 3,597 edges, zero dangling edges, and exactly one remaining stub in the entire
project** (the harmless `settings.AUTH_USER_MODEL` quirk from spot-check #11 - every real
cross-app FK, across every app in the codebase, resolves to a real node). 32/32 tests passing,
`ruff`/`bandit` clean throughout.

## What this is

A working, tested pipeline that extracts a Neo4j-shaped knowledge graph from one tenant app
(`compras`) — models, service layer, API, frontend, tests, and the AGENTS.md/ADR/skill
documentation that governs it — and demonstrates it answering a first slice of the
"objetivos secundarios" questions from the original EKG request. It is a proof of the
extraction approach, not the full 20-phase spec (that is an 18-app, multi-week program — see
"Roadmap" below).

## Why `compras`, why Tree-sitter, why not live-tested against Neo4j

- `compras` was picked because it's the smallest tenant app (22 Python files), was touched
  most recently (`5bab0b9`, `d3255c3`), and already has its own `.agent/AUDITORIA_FLUJO_COMPRAS.md`
  audit doc to cross-check extracted facts against.
- Every code-structure fact (classes, imports, FK targets, ViewSet/Serializer wiring, router
  registrations, endpoint literals in JS) comes from a Tree-sitter parse (`tree-sitter-python`
  / `tree-sitter-javascript`), not regex — per the original request's "No usar expresiones
  regulares. Utilizar Tree-sitter o equivalente." Two narrow, explicitly-documented exceptions
  exist (see "Known limitations"): Django template tag extraction and AGENTS.md/MEMORY.md
  heading splitting, both fixed micro-grammars with no mature Tree-sitter grammar available,
  not a stand-in for code-structure analysis.
- This sandbox has no `docker` binary, so the new `neo4j` Docker service (added to
  `docker-compose.yaml`) could not be started here. Everything up to the point of writing to
  Neo4j was verified without it: `tools/ekg/load_neo4j.py` uses the same `MERGE`-based,
  idempotent write pattern either way, and `tools/ekg/build_graph.py --dry-run` produces the
  exact graph that would be loaded, which `tools/ekg/tests/` and `tools/ekg/validate.py` both
  exercise directly.

## What was verified, concretely

```
python -m pytest tools/ekg/tests/ -q      # 21 passed
python -m ruff check tools/ekg/           # all checks passed
python -m bandit -r tools/ekg/            # no findings outside expected test asserts (B101)
python -m tools.ekg.build_graph --app compras --dry-run --output tools/ekg/out/compras.json
  # -> 151 nodes, 130 edges
python -m tools.ekg.validate --app compras --graph tools/ekg/out/compras.json
  # -> 0 dangling edges; honest WARNs below
python -m tools.ekg.queries --offline tools/ekg/out/compras.json --app compras
  # -> answers all 7 demo questions below
```

Every extracted fact in the `pytest` suite was written by first reading the real
`apps/tenant/compras/*` source and cross-checking the extractor's output against it (not
against a fixture) — the ground truth came from two dedicated research passes over the app,
its service layer, its API, its templates/JS, and the project's infra/docs/rules, all done
before a line of extraction code was written.

### Demo questions answered against the compras pilot graph

1. **What ViewSet uses `OrdenCompraListSerializer`?** -> `OrdenCompraViewSet`
2. **What JS consumes an endpoint containing "plantillas"?** -> `compras.api.js` — resolved via
   `PLANTILLAS_ROOT = \`${API_ROOT}plantillas/\`` (template-string constant folding, see
   `extract_js.py:collect_const_string_bindings`), including a direct link to the real
   router-derived `Endpoint:compras:plantillas:api` node, not just the raw string literal.
3. **What endpoints expose `OrdenCompra`?** -> `OrdenCompraViewSet -> '' (api)`, `-> '' (ui)`
   (the ViewSet -> Serializer -> `Meta.model` -> Endpoint chain).
4. **What AGENTS.md/skill rules govern `compras`?** -> 12 AGENTS.md sections (`CRUD-E2E`, `FSD`,
   `SECURITY`, `BRIDGE`, `HTMX-OFFCANVAS`, `CORE-DB`, `CRITICAL`, `CSS/JS-ISOLATION`,
   `UUID-FORMS`, `ORM-SELECTORS`, `TESTING`) + `dom-ids-sync.md` and `tabulator.md`.
5. **What ADRs/docs document `compras`?** -> `MEMORY.md ADR-006` (Server-Driven Frontend — the
   ADR body names `gastos`, `facturas`, `compras` as the three already-migrated apps) and its
   own `.agent/AUDITORIA_FLUJO_COMPRAS.md`.
6. **What FK relationships does `OrdenCompra` have?** -> `plantilla -> PlantillaOrdenCompra`
   (same app, fully resolved), `proveedor/proyecto/documento_soporte -> external stubs` in
   `tenant_proveedores`/`tenant_proyectos`/`tenant_gastos` (correctly *not* fabricated as fully
   resolved, since those apps weren't parsed).
7. **What tests cover `OrdenCompraBusinessService`?** -> `tests/tenant/compras/test_compras_plantillas.py`.

### A finding the graph got right by staying conservative

`.agents/skills/frontend/tabulator.md` **is** linked to `compras` in the graph — not because
compras uses Tabulator (it migrated off it per `MEMORY.md` ADR-006), but because the skill
doc's text literally names `compras` in an unrelated ID-collision example
(`#grid-compras`/`#grid-ventas`). The extractor's linking rule is "app name is mentioned in the
document's own text," which is coarse but honest: it never asserts "compras uses Tabulator,"
and `tools/ekg/tests/test_extract_docs.py::test_tabulator_skill_extracted_but_only_linked_via_real_mention`
pins this down so it can't silently regress into a false claim later.

## Known limitations (read before trusting a query blindly)

- **6/18 apps.** `compras`, `ventas`, `facturas`, `proveedores`, `proyectos`, `gastos`,
  `clientes` have been extracted and cross-checked (most of the later ones were picked
  specifically because earlier apps' FKs point at them, to prove the stubs resolve on merge —
  they do, see spot-checks #3/#4/#5/#6). Any FK target belonging to one of the ~12
  not-yet-extracted apps still shows up as an unresolved "external stub" node
  (`properties.external = True`) — real, but shallow. `validate.py` treats stubs differently
  from orphans for exactly this reason.
- **`views.py`/`tables.py` (django-tables2) aren't parsed.** `compras`'/`facturas`'/`gastos`'
  `tabla*/` UI routes have no ViewSet/Serializer/Table node type yet —
  `tools/ekg/tests/test_build_graph.py::test_ui_table_view_endpoint_is_a_known_gap` documents
  this as a known, intentional gap rather than letting it look silently covered. All three
  known Fase-5-BIS-migrated apps have now been extracted and all three show this gap
  consistently (roadmap item 2, still not started).
- **Same-named classes in different modules resolve by name, not by import.** `extract_viewsets`
  prefers a sibling ViewSet-family match over a Service-layer match when resolving a base class
  name — correct for `proyectos`' real `ProyectoServiceMixin` collision (spot-check #4) because
  that happens to be what's actually imported there, but this is name-based priority agreeing
  with reality, not import tracing; a same-name collision with the opposite import direction in
  some other app would resolve to the wrong node.
- **`extract_services`' CALLS resolution is last-file-processed-wins on bare class name**, not
  scoped by which specific class a caller actually imported. Harmless so far (spot-check #6's
  `clientes.services.ClienteBusinessService` deprecated shim happens to be the last file
  processed in that app, so nothing after it could be mis-linked), but an app where a
  later-processed file calls a same-named class expecting a different definition than the one
  seen last would silently link to the wrong Service node.
- **ViewSet -> Serializer wiring is a static reference scan**, not control-flow-accurate
  resolution of `get_serializer_class()`/per-action dicts (see `extract_python.py` module
  docstring).
- **JS -> Endpoint linking is best-effort.** `build_graph.py` links a JS file to a real
  router/path `Endpoint` node via substring matching after constant-folding simple
  `` `${CONST}literal` `` template strings — it will miss endpoints built with more complex JS
  string logic (loops, ternaries, computed property access).
- **No DSV / Service-Layer-violation detection.** The spec asks "what code violates the Service
  Layer" — this pilot does not attempt that; it would need real call/control-flow analysis this
  extractor doesn't do, and `validate.py`'s docstring says so explicitly rather than faking a
  check.
- **No GraphRAG / embeddings / semantic search** (Fase 18 of the original spec) — out of scope
  for this pilot.
- **No continuous sync** (Fase 19) — re-running `make ekg-build` is manual; no git hook wires it
  up yet.
- **AGENTS.md/MEMORY.md section splitting and Django-template tag extraction use regex**, not
  Tree-sitter — documented exceptions (fixed heading/tag micro-grammars, not code structure;
  see the module docstrings in `extract_docs.py` and `extract_templates.py`), not a shortcut
  around the "no regex" rule for actual code relationships.

## DONE (2026-08-05 smoke-test session): live Neo4j load verified end-to-end

Docker became available in a later session. Ran `docker compose up --build -d`, loaded all 17
apps via `python -m tools.ekg.build_graph --app <name>` (no `NEO4J_PASSWORD`/`NEO4J_URI`/
`NEO4J_USER` in `.env` at first - added them, matching `.env.example`), and queried the live
database directly:

```
MATCH (n) RETURN count(n)        -> 2506
MATCH ()-[r]->() RETURN count(r) -> 3597
MATCH (m:Model {external: true}) RETURN m.id -> only Model:settings.AUTH_USER_MODEL
```

**Exact match to every number this report predicted from the offline merge**, including the one
remaining harmless stub. A canned question (`viewsets_using_serializer` for
`OrdenCompraListSerializer`) run as live Cypher returned `OrdenCompraViewSet`, matching the
offline `queries.py` answer from spot-check #1. This closes the one item every earlier version
of this report listed as "not yet done" - the pipeline is now verified correct against a real
Neo4j, not just the in-memory `Graph` model.

Two bugs surfaced getting the live load working, both fixed, neither an EKG design flaw:

1. **`requirements.txt` pinned `tree-sitter>=0.23,<0.24`, a version without `QueryCursor`** - the
   class every extractor's queries run through. This was invisible all rollout because local
   testing happened against whatever `pip install tree-sitter` resolved to outside the pin
   (0.26.0), never against the actual pinned range. Fixed to `>=0.25,<0.27` (with
   `tree-sitter-python`/`tree-sitter-javascript` bumped to match, `>=0.25,<0.26`) and confirmed
   working after a container rebuild. Lesson for the roadmap: this class of bug (tested-against
   different version than pinned) can't be caught without actually building the Docker image at
   least once - added as a checklist item.
2. **A pre-existing, unrelated migration bug blocked the `web` container from starting at all**:
   `apps/tenant/proyectos/migrations/0020_itempresupuesto_tareadiaria_uuid.py` declared its
   dependency as `('proyectos', '0019_proyecto_sede')` instead of `('tenant_proyectos', ...)` -
   every sibling migration in that same app correctly uses `tenant_proyectos` (confirmed via
   grep), and a repo-wide scan found no other instance of this exact typo. The same class of bug
   as this pilot's own spot-check #1 (`ventas`) and spot-check #3 (`proveedores`) fixes - Django's
   real `app_label` vs. the bare app folder name - just found in application code instead of the
   EKG tool. Not an EKG file; fixed directly since it blocked all further smoke testing.

Also ran the repo's actual smoke suite (`make smoke`'s three components, `make` itself isn't on
this shell's PATH so run via the underlying `docker compose exec` commands directly):
`audit-scripts` (4 non-blocking `|| true` scripts - pre-existing findings backlog, unrelated to
this session, including one false positive flagging `tools/ekg/extract_templates.py`'s
`HTMLParser` subclass as a "Parser outside apps/services/xml_*" - harmless, not fixed),
`smoke-xml-pipeline` (4/4 tests fail on pre-existing, unrelated broken imports/signature
mismatches in `apps/tenant/facturas/tests/test_xml_pipeline_canonical.py` - not touched, out of
scope, flagged for the user), `test-api` (7/7 passed), plus `manage.py check --deploy` (0 errors,
6 expected local-dev warnings).

Docker Compose stack (`db`, `redis`, `neo4j`, `web`, `celery`, `nginx`, `cloudflared`) was left
running after this session; `nginx` reports `unhealthy` (its healthcheck expects the
`*.sintel.net.co` wildcard DNS setup this sandbox doesn't have) but doesn't block anything -
`web`/`db`/`redis`/`neo4j`/`celery` are all healthy.

## DONE (2026-08-07): impact engine ("if I change this, what breaks?")

Added `tools/ekg/impact.py` — a general-purpose reverse-dependency walker on top of the existing
`schema.Graph`/live-Neo4j pair, answering the governance-spec question this pilot's `queries.py`
didn't yet: given one starting node (by exact name, or by a file-path/route substring for
Template/JS/Test/Document), what transitively depends on it, what it produces that's also
affected, what tests already cover the blast radius, and which Applications/Rules/Docs to review.

- `load_full_offline_graph()` merges all 17 real per-app dumps under `tools/ekg/out/` into one
  `Graph` (explicitly excludes the `audit_*.json` scratch files left over from the dead-code
  audit — those are query *results*, not extractor dumps, and would double-count nodes if merged
  back in as if they were graph input).
- `impact_of_offline()` does a layered BFS: reverse over `IMPORTS/INHERITS/USES/CALLS/CONSUMES/
  REFERENCES` (dependents — the edge source depends on the target, per every extractor's actual
  direction, confirmed by grep before writing a line of traversal code), then forward over
  `EXPOSES/RENDERS` starting from *every* newly-impacted node, not just the original target — a
  ViewSet only becomes impacted via the reverse walk, so the Endpoint it `EXPOSES` is only
  reachable by then walking forward *from that ViewSet*.
- `impact_of_live()` is the Cypher equivalent, run against the real, already-loaded Neo4j
  instance (2,506 nodes / 3,730 edges, confirmed live — not the "not exercised in this
  environment" caveat that applied when `load_neo4j.py` was first written).
- CLI: `python -m tools.ekg.impact --offline --name <Name>` / `--path <fragment>` / `--live
  --name <Name>`, plus `--json`. Wired into `Makefile` as `make ekg-impact NAME=...`.
- 6 new tests in `tools/ekg/tests/test_impact.py`, built the same way every other test in this
  suite is (`build_app_graph()` from real source, not a synthetic fixture) — 42/42 pass across
  the whole `tools/ekg/tests/` suite after this change, zero regressions.

**Two real bugs found and fixed by cross-checking `--live` against `--offline` on the same real
model (`compras.OrdenCompra`) rather than trusting either implementation in isolation** — this is
exactly the kind of bug the dual-implementation convention (see every `queries.py` question) is
supposed to catch, and it worked:

1. First draft of `build_live_cypher()` only walked `EXPOSES/RENDERS` forward from the original
   `target`, never from the dependents discovered by the reverse walk — silently returned zero
   Endpoints for `CuentaContable`/`OrdenCompra` even though `--offline` correctly found them via
   their ViewSet. Fixed by collecting `impactedSoFar` after the reverse pass and `UNWIND`-ing it
   before the forward pass.
2. `collect(DISTINCT {name: coalesce(x.name, x.path, x.route, x.id), ...})` collapsed two
   genuinely different Endpoint nodes into one, because both had `route=""` (a real, meaningful
   value — the API root) and `coalesce()` only skips `NULL`, not empty strings — two structurally
   identical display maps are one entry under `DISTINCT`. Fixed two ways: (a) a `CASE`-based
   display expression that also skips `''`, matching `_display_name()`'s Python `or`-chain
   semantics exactly; (b) every returned map now also carries the node's real, always-unique `id`
   (see `schema.py`), so `DISTINCT` dedups by true identity even in cases the display-string fix
   alone wouldn't cover.

Verified: `--offline` and `--live` return the identical dependent/produced sets (by name and
count) for both `compras.OrdenCompra` and `contabilidad.CuentaContable`.

**Same known limitation as everywhere else in this report applies here too**: `GOVERNED_BY`/
`DOCUMENTED_BY` are Application-level only (roadmap item 5 below), so "rules/docs to review" is
always reported per-app, never pinpointed to the one AGENTS.md paragraph or ADR section that
actually matters for the changed node — the engine says so explicitly in its own docstring and
CLI output rather than implying a precision it doesn't have.

## DONE (2026-08-07, continued): governance sweep + 4 extractor bugs found fixing it

Added `tools/ekg/governance.py` (Fase 7 of the spec) on top of the corrected impact-engine graph.
Building its first rule ("does every tenant Model inherit SintelTenantBaseModel?") immediately
surfaced that the answer was "none of them, according to the graph" - not because the codebase is
wrong, but because of a real, previously-undiscovered extractor bug. Chasing that one bug
honestly (rather than building a governance rule on top of data already known to be wrong)
surfaced three more, all fixed, all pinned with tests:

1. **Cross-app `INHERITS` was never resolved for Models or ViewSets.** `extract_models()`/
   `extract_viewsets()` only ever looked up a base class as `schema.model_id/viewset_id(<same
   app as the subclass>, base_name)` - correct for a same-app sibling, but silently zero for the
   single most common case in the entire project: every tenant model inherits
   `apps.tenant.core.models.SintelTenantBaseModel`, and every tenant ViewSet inherits
   `apps.tenant.api.base.BaseTenantViewSet` - both always live in a *different* app. Confirmed on
   a **fresh** extraction (not a stale dump) before touching any code. Fixed with
   `_build_import_map()` + `_resolve_cross_app_base_folder()`, resolving a bare base-class name to
   the app it was actually `from ... import`ed from, mirroring the already-correct pattern
   `resolve_model_target()` uses for FK strings (just via imports instead of dotted FK-string
   syntax). Cross-app ViewSet bases living in `apps/tenant/api/` (an infrastructure app never
   extracted as one of the 17 business apps, see `arquitectura_general.md` Sec 2.3) correctly
   become permanent external stubs, same convention as `settings.AUTH_USER_MODEL`.
2. **Real ViewSet nodes never explicitly set `external: False`** (unlike real Model nodes, which
   always did). `Graph.add_node`'s "external is monotonic" merge only forces `false` when the
   *existing* node already has `external is False` - omitting the key entirely (not just leaving
   it `True`) let a cross-app stub silently downgrade an already-real ViewSet node depending on
   merge order. Only surfaced because fix #1 started creating ViewSet stubs for the first time.
3. **`models.TextChoices`/`IntegerChoices`/`Choices` subclasses were extracted as Model nodes.**
   `apps/tenant/perfil/models.py`'s `RolTenant(models.TextChoices)` - a plain enum of role-name
   string constants, not a Django Model - showed up as "doesn't inherit the base", a real
   extractor false positive, not an architecture violation (confirmed by reading the source
   before excluding it). Fixed with a small `_NON_MODEL_BASE_NAMES` guard in `extract_models()`.
4. **Not yet fixed, found and documented instead**: `resolve_model_target()` (FK/`Meta.model`
   resolution) has the same "assumes same app" blind spot as bug #1 did, but for *bare* (non-
   string, imported-identifier) FK targets - e.g. `empresa = ForeignKey(Empresa, ...)` after
   `from apps.tenant.empresa.models import Empresa`. Confirmed via `Model:tenant_empleados.
   Empresa` / `Model:tenant_inventario.Empresa` / `Model:tenant_proveedores.Empresa` /
   `Model:tenant_proyectos.Empresa` - four separate apps each producing their own wrongly-
   namespaced, never-resolving placeholder for what should be one shared `Model:empresa.Empresa`
   node. `governance.py`'s rules defensively skip any Model with no `defined_in` (i.e. any
   unresolved placeholder, of either kind) rather than guess at these - see its module docstring.
   **Left for a future pass**: applying the same import-map fix from #1 to
   `resolve_model_target()` would very likely close this too, but wasn't attempted here to keep
   this session's change scoped to what was actually needed to trust the governance rule's output.

All 17 apps' dry-run dumps regenerated and the live Neo4j reloaded (idempotent `MERGE`, no data
loss) after each fix; final state 2,520 nodes / 3,893 edges (up from 2,506 / 3,730 before this
session - net of both new correct edges and one real node removed, `perfil.RolTenant`).

**Governance sweep result** (`make ekg-governance` / `python -m tools.ekg.governance --offline`),
after all four fixes:
- `models_not_inheriting_tenant_base`: **0** (was 7, all false positives from bugs #1/#3/#4 above).
- `js_outside_own_app_static_path` / `templates_outside_own_app_path`: **0 each** - a genuine,
  verified-clean result (not "the rule never fires"; both rules are exercised and pass on real
  compliant apps in `test_governance.py`).
- `viewsets_without_service_layer`: **23**, after fixing the transitive-`INHERITS` gap that made
  every ADR-002 `*CoreViewSet` public-facade a false positive (13 of the original 36). **Not all
  23 have been individually verified** - one spot-check (`EmpresaViewSet(viewsets.ModelViewSet)`,
  skipping `BaseTenantViewSet` entirely) turned up a genuinely ambiguous case: `empresa` is
  documented elsewhere as the project's "REFERENCIA GOLDEN" module, so this may be a deliberate,
  reviewed exception rather than a violation - a judgment call outside what a static graph query
  can resolve alone. **Report the list, do not treat all 23 as confirmed findings** until each is
  read against its source, the same discipline that caught the four bugs above.

## DONE (2026-08-07, continued): extended coverage to `apps/public/*` (5 apps, 22 total)

Roadmap item 8. Added an `app_name`/`folder_name`/`schema_root` split threaded through every
extractor (`extract_python.py`, `extract_js.py`, `extract_docs.py`, `build_graph.py`) so a node's
id-namespace (`app_name`, e.g. `"public_core"`) can differ from its on-disk directory
(`folder_name`, e.g. `"core"`) - required because `apps/public/core` and `apps/tenant/core` share
a bare folder name but are two unrelated apps, and naively passing the folder name into id
construction collided them into one `Application:core` node on merge (found and fixed before it
reached a report; see `_build_import_map`/text-matching functions using `[app_name]` not
`[folder]`). Templates are skipped entirely for `schema_root != "tenant"` (public apps don't follow
the `templates/tenant/<app>/` convention - not assumed, not extracted).

`build_graph.py --app <name> --schema public` extracts one public app; `impact.py`'s
`PUBLIC_APPS` tuple and `load_full_offline_graph()`'s default now merge all 22 apps (17 tenant +
5 public: accounts, tenants, impuestos, console, core) for any impact/governance query. Merging
public apps in immediately surfaced a real scoping bug in `governance.py` (19 public models and
24 public ViewSets flagged by two tenant-only rules that were never stated to apply to the public
schema per `arquitectura_general.md` Sec 3.2/4.2) - fixed with `_tenant_app_ids()`/
`_belongs_to_tenant_app()`, verified the tenant-app-only counts (0 models / 23 ViewSets) were
unchanged by adding public apps to the merge.

## DONE (2026-08-07, continued): CI wiring for continuous graph-health checks (Fase 8)

Roadmap item 6. Added a second, independent job `ekg-graph-health` to the existing
`.github/workflows/ci-quality-gate.yml` (deliberately not folded into `test-and-quality`, so an
EKG extraction problem never blocks an unrelated PR's tests/lint/security gate). Runs on every
PR/push to `main`/`develop`:
1. Dry-run extraction of all 17 tenant apps + all 5 public apps (no Neo4j - catches a parse
   failure or a broken path assumption the moment it's introduced, not at the next manual
   `make ekg-build`).
2. `tools.ekg.validate --app <x> --graph <dump>` per tenant app - hard fail (no
   `continue-on-error`) if `dangling_edges` is ever nonzero.
3. `tools.ekg.governance --offline` - `continue-on-error: true` for now, since several of the 23
   `viewsets_without_service_layer` findings are already-triaged legitimate exceptions or known
   extractor false positives (see previous section and
   `documentacion/INFORME_FINAL_EKG_GOBERNANZA_2026-08-07.md` Sec 4) that haven't been
   individually suppressed yet - failing the build on unfiltered output would block legitimate
   PRs. Remove `continue-on-error` once that triage is encoded as an explicit allowlist.

`tools/ekg/tests/*.py` needed no CI change at all: `pyproject.toml` has no `testpaths` restriction,
so the existing `test-and-quality` job's generic `pytest` step already discovers and runs them.
Verified locally before considering this done: the workflow YAML parses
(`yaml.safe_load`), and both new steps' exact CLI invocations were run against a real tenant app
(`compras`) and a real public app (`public_core`) with the same arguments the workflow uses -
`dangling_edges: 0`, exit 0, in both cases.

## DONE (2026-08-07, continued): offline HTML graph explorer (Fase 9)

Roadmap item for Fase 9 ("Visualizacion... Todo navegable"). Added
`tools/ekg/export_html.py` / `make ekg-explorer`: a single, self-contained, offline HTML file
(`tools/ekg/out/graph_explorer.html`) generated from the merged 22-app graph - no server, no CDN,
no network access, opens straight from disk or any static file host. Lets a human search any node
by name/path, filter by the 14 node labels the graph actually has data for, open one, read its
full property table, and click through every incoming/outgoing relationship one hop at a time
(browser back/forward works too, since navigation state is just `location.hash`).

Explicitly does **not** claim tabs for Celery tasks, domain events/signals, or per-endpoint
permission classes - `schema.py`'s `NODE_LABELS`/`REL_TYPES` (the graph's actual, exhaustive
vocabulary) has no such node/relationship type, and no extractor populates one; inventing a
placeholder view for data that doesn't exist would be exactly the "documentacion ficticia" the
original spec prohibits. The explorer's own sidebar states this scope boundary up front instead
of silently omitting it.

**One real bug found and fixed while verifying this in an actual browser** (not the sandboxed
preview tool - confirmed by serving the file over a plain `python -m http.server` and inspecting
`document.scripts`/DOM child counts directly): several `Rule`/`Document` node `body` properties
are AGENTS.md text quoted verbatim, including code examples containing the literal substring
`<script>`. Embedding the graph's JSON directly inside the page's own `<script>` block let the
first such `</script`-like substring close the real tag early - the browser then rendered the
remaining JSON/markdown as plain page text instead of running the UI. Fixed by escaping `"</"` to
`"<\/"` in the embedded JSON payload (byte-identical once JS parses it back, invisible to the HTML
tokenizer); pinned with a regression test in `tools/ekg/tests/test_export_html.py` that asserts
exactly one `</script>` survives in the rendered output, using a real extracted app (`core`) whose
Rule bodies are confirmed (by the test itself) to contain a `</` substring - not a synthetic
fixture that could pass without the fix.

## DONE (2026-08-07, continued): unified platform CLI - dossier + compliance summary (Fase 10)

Roadmap item for Fase 10 ("Plataforma Enterprise"). Not a new analysis engine and not a web
dashboard - `tools/ekg/platform.py` (`make ekg-summary` / `make ekg-dossier NAME=...`) is a thin
synthesis layer over `impact.py` (Fase 6) and `governance.py` (Fase 7), because most of the
spec's example questions ("quien usa este modelo", "que rompe este cambio", "que pruebas/ADR
aplican") are already answered by `impact_of_offline()`'s existing `ImpactReport` fields - the gap
was only ever "run both tools and read the answer off one node", not "compute something new".
Two genuinely new, narrow additions, both direct proxies over data the graph already has (not new
extraction):
- `compliance_summary()`: percentage of the *applicable* population passing each of
  governance.py's 4 rules (e.g. tenant Models with a real `defined_in`, excluding placeholders and
  public-schema ones - not "all Model nodes"). Explicitly labeled in its own docstring and CLI
  output as "a proxy over 4 checkable rules, not a certified compliance score" - the spec's
  broader "cumple la arquitectura" question also covers DSV/permissions/N+1/etc., which
  `governance.py` already declared out of reach for a static extractor.
- `decoupled_apps()`: Application nodes with zero cross-app `IMPORTS/INHERITS/USES/CALLS/
  CONSUMES/REFERENCES` edge in either direction. **Found and fixed a real bug before trusting the
  first result**: `apps/tenant/api/` (never extracted as one of the 22 apps - only ever appears as
  an external stub target of other apps' cross-app `INHERITS`, e.g. `BaseTenantViewSet`) was
  reported as "decoupled" purely because an external stub's members never get a `BELONGS_TO` edge
  - the opposite of the truth (`BaseTenantViewSet` has 45 real `INHERITS` edges pointing at it
  project-wide). Fixed by excluding `external: True` Application nodes from the candidate set
  entirely (an app never extracted has no real coupling data one way or the other, so "decoupled"
  would be a guess); pinned with a test that would have caught this. After the fix, the genuine
  result is the 5 `apps/public/*` apps - real, fully-extracted apps with no static
  `IMPORTS/INHERITS/USES/CALLS/CONSUMES/REFERENCES` edge connecting any of their members to a
  tenant app's, which is plausible given the Bridge pattern (AGENTS.md Sec 17) routes through a
  runtime membership service call rather than a static import - not re-verified against the
  runtime behavior, reported as a graph-level observation only.

Current summary on the full 22-app graph: `models_not_inheriting_tenant_base` 100% (69/69),
`js_outside_own_app_static_path` / `templates_outside_own_app_path` 100% each,
`viewsets_without_service_layer` 70.9% (56/79) - the same 23 findings from the governance section
above, now expressed as a percentage of the tenant-ViewSet population instead of a raw count.

## Roadmap (rollout done: 17/17 tenant + 5 public apps, live Neo4j load verified — remaining work is depth, not breadth)

1. ~~Live Neo4j load~~ **DONE** (see above) - 2,506 nodes / 3,597 edges in the real database,
   exact match to the offline prediction.
2. Design (don't rush) a general fix for the "sibling package/file" gap - confirmed three times
   across two apps (`contabilidad/integracion/`, `cotizaciones/configuracion/`,
   `cotizaciones/ui_views.py`, spot-checks #13/#15), not a one-off. Two sub-problems, likely two
   different fixes: (a) stray View-family files directly under `app_dir` (like `ui_views.py`)
   just need `extract_viewsets` to also scan `app_dir` itself, not only `api/` - low-risk,
   similar in kind to the spot-check #2 generalization. (b) nested sub-apps with their own
   `models.py`+`viewsets.py`+`services/` (like `configuracion/`) are architecturally more like a
   second app squeezed inside the first, and deserve a real decision: treat each as its own
   `Application` node, or fold it into the parent app's namespace.
3. Design `contabilidad/integracion/`'s modeling specifically (a new `DTO` node type - in the
   original spec's node list, unused until this gap - and a decision on whether extractors are
   `Service`s with a new `kind` or their own label). The single most architecturally significant
   piece of code found unindexed in the whole rollout; worth getting right over getting done
   quickly, independent of item 2's more mechanical fixes.
4. Extend `extract_python.py` with a `views.py`/`tables.py` (django-tables2) extractor - the
   `*/tabla*/` gap showed up in every Fase-5-BIS-migrated app checked (`compras`, `facturas`,
   `gastos`, `bancos`, at minimum) and will keep showing up as more apps migrate off Tabulator.
5. Write the Fase 20 governance rule into `AGENTS.md`/`CLAUDE.md` ("consult the graph before
   modifying code"). Full app coverage plus the verified live load remove the main reasons this
   was deferred - but do items 2-4 first, or the rule would bind the project to a graph with
   known, documented holes in exactly the areas (accounting integration, django-tables2 UI,
   nested sub-apps) most likely to matter for a real code change.
6. ~~Wire `make ekg-build` into a pre-commit or CI hook for the Fase 19 continuous-sync goal, so
   the graph doesn't silently drift from the code the way this rollout found it hadn't yet.~~
   **DONE** (see above) - `ekg-graph-health` CI job, dry-run + validate on every PR/push.
7. GraphRAG/embeddings (Fase 18) only after the above - it indexes what's already extracted, it
   doesn't fix an incomplete graph.
8. ~~Extend past `apps/tenant/` - `apps/public/` (accounts, tenants, impuestos, console) and
   `apps/services/` were never in scope for this pilot.~~ **DONE for `apps/public/`** (see above,
   5 apps, 22 total). **`apps/services/*` still entirely out of scope** - not attempted.
9. Fix `apps/tenant/facturas/tests/test_xml_pipeline_canonical.py` (4/4 failing - pre-existing,
   unrelated to EKG, found while smoke-testing this work; see the smoke-test session note above)
   and investigate the ~1600 `audit_templates_and_branding.py` / 15
   `audit_tenant_ui_compliance.py` findings surfaced by `make smoke`'s audit scripts - both
   predate this session and are marked non-blocking (`|| true`), but weren't re-verified as part
   of this rollout's scope.
10. **Model `ViewSet` -> `Template` rendering** (the `render-offcanvas/crear|editar|detalle/`
    actions, `TemplateHTMLRenderer`). `REL_RENDERS` already exists in `schema.py` but no
    extractor populates it - found running a real dead-code audit against the live graph
    (`documentacion/AUDITORIA_CODIGO_MUERTO_EKG_2026-08-05.md`): the "orphan Template" query
    flagged 125 of ~140 templates project-wide (essentially every offcanvas), because the only
    Template-reachability the graph currently models is `{% include %}` and `<script src>` -
    not a ViewSet's render action returning that template as its HTTP response. This makes
    "which templates are truly unused" currently unanswerable from the graph; fixing it means
    scanning ViewSet action bodies for template name references, similar in spirit to the
    ViewSet-direct-call fix from spot-check with services. Do this before ever trusting a
    template-deletion recommendation from the graph again.
11. Also found auditing the graph for dead code (extraction gaps, not app bugs, all now fixed -
    see `documentacion/AUDITORIA_CODIGO_MUERTO_EKG_2026-08-05.md` §1.1 for the four confirmed
    patterns and their test coverage): mixin class-attribute injection
    (`business_service_class = X`), module-qualified base classes (`module.ClassName`), direct
    ViewSet-to-Selector calls bypassing the mixin, and `SERVICE_KIND_OTHER` files never being
    scanned for intra-file Business->CRUD delegation. Two related gaps found but **not** fixed
    (noted for a future pass): JS-to-JS ES module `import` statements aren't tracked (only
    `<script src>`/`{% static %}` in HTML), and lazy/local imports inside function bodies aren't
    scanned for cross-app `IMPORTS` edges (only module-level imports are).
12. ~~Apply the same import-map fix to `resolve_model_target()`~~ **DONE (2026-08-07)**. Bare
    (non-string, imported-identifier) cross-app FK targets like `empresa = ForeignKey(Empresa,
    ...)` after `from apps.tenant.empresa.models import Empresa` now resolve to the one real
    `Model:empresa.Empresa` instead of 4 separate wrongly-namespaced, never-merging placeholders
    (`Model:tenant_empleados.Empresa`, `tenant_inventario`, `tenant_proveedores`,
    `tenant_proyectos`). Pinned in `test_governance.py::
    test_bare_cross_app_fk_reference_resolves_to_the_real_model_id`. The 4 stale placeholder
    nodes left behind in the live Neo4j by the old bug (idempotent `MERGE` never deletes a node
    that stops being produced) were removed manually - a real, general limitation of the
    load/merge model worth remembering: **a code fix that changes what id an extractor emits
    requires a manual cleanup pass on the live graph, `make ekg-build` alone will not remove the
    orphaned old id.**
13. ~~Manually triage the 23 `viewsets_without_service_layer` findings~~ **DONE (2026-08-07)**,
    read against source, not just names:
    - **5 confirmed real findings** (no Service Layer mixin at all, direct or transitive):
      `ResolucionDIANViewSet` in `empleados` (contrast with `gastos`' own same-named class, which
      correctly has `ResolucionServiceMixin` - these are two different classes, not one bug),
      `ConfiguracionRetencionesViewSet`, `ItemFacturaViewSet`, `NotaCreditoViewSet`,
      `DepartamentoViewSet` (+ their 2 `*CoreViewSet` facades, which correctly inherit the finding).
    - **3 further extractor false positives found via this triage** (same class of gap):
      `LibroDiarioViewSet`/`ContabilidadServiceMixin`, `PerfilViewSet`/`PerfilServiceMixin`,
      `ProyectoViewSet`/`ProyectoServiceMixin` (+ propagated `*CoreViewSet` facades) all reference
      a real, correctly-named Service-Layer mixin that `extract_services()` cannot see because it
      is defined directly under `api/mixins.py` or `api/viewsets.py`, not under `services/*.py` -
      **not fixed** (would require `extract_services()` or a new pass to also scan `api/mixins.py`
      for `BaseServiceMixin`-shaped classes; noted here rather than expanding scope further).
      Collateral finding: `proyectos` has *two* classes both named `ProyectoServiceMixin` (one in
      `api/mixins.py`, actually used by the ViewSet; one in `services/api_mixins.py`, unused by
      it) - a naming collision worth a human's attention, not touched here.
    - **2 deliberate, documented exceptions, not violations**: `EmpresaViewSet` and
      `MailInboxConfigViewSet` (`apps/tenant/empresa/api/viewsets.py`) inherit
      `viewsets.ModelViewSet` directly, skipping `BaseTenantViewSet` entirely - but `EmpresaViewSet`'s
      own docstring explicitly documents its own manual Session-Auth/CSRF and
      STAFF/ADMIN-only enforcement, i.e. a reviewed, intentional substitute, not an oversight
      (`empresa` is elsewhere documented as the project's "REFERENCIA GOLDEN" module).
    - **4 probable legitimate exceptions** (plain `ViewSet`, not `ModelViewSet` - not CRUD-shaped
      by design): `CoreAuthViewSet`, `CoreLinksViewSet`, `DashboardSectionsViewSet`, `LandingViewSet`.
    - **1 possible dead code, not a Service Layer question**: `apps/tenant/inventario/api/
      viewsets.py`'s `BaseViewSet` has zero subclasses anywhere in that file (`grep "BaseViewSet)"`
      found nothing) - looks unused, a candidate for the dead-code backlog, not this rule.
    Net: of 23 raw hits, 5 are real, 8 are extractor false positives (now understood, not fixed),
    2 are confirmed-intentional, 4 are probable-legitimate (not individually read line-by-line),
    1 is a dead-code candidate, and the rest are `*CoreViewSet` facades whose status is inherited
    from whichever of the above their real parent falls into.

## DONE (2026-08-07, continued): verified EKG capture for ADR-003's `SedeAwareModel` (compras pilot)

Fase 9 of the governance spec, applied to the new organizational-context feature
(`docs/ADR-003-contexto-organizacional-sede-area.md`): re-extracted `compras`
(`make ekg-dry-run APP=compras`) after `OrdenCompra` adopted the new `SedeAwareModel` mixin, to
check whether the graph needs any new extractor code for this - it does not.

- `INHERITS` correctly resolves cross-app to `Model:tenant_core.SedeAwareModel` (the same
  cross-app-base-class resolution mechanism fixed earlier in this file's governance section works
  correctly for a brand new abstract mixin, not just the two bases it was built against).
- `sede` (explicitly redeclared in `OrdenCompra`'s own class body, to enforce `null=False` post-
  hardening) is captured as a `Field` + `HAS_FIELD` edge, same as any other own-declared field.
- `area` (only inherited from `SedeAwareModel`, never redeclared in `OrdenCompra`) is **not**
  captured - verified this is a pre-existing, project-wide limitation of `extract_python.py`'s
  field extraction (it walks the class body being parsed, not fields inherited from an abstract
  base), **not** something this session's `SedeAwareModel` change introduced: `PlantillaOrdenCompra`
  (unrelated to ADR-003, never touched this session) has the identical gap for `empresa`/
  `created_at`/`updated_at`, all three inherited from `SintelTenantBaseModel` and never redeclared.
  No extractor change made - fixing a project-wide, pre-existing gap was out of scope for this ADR.

## DONE (2026-08-09): OSF Fase F15 - verified EKG reflects the now-stabilized organizational scope
architecture (F0-F14 of the Organizational Scope Framework, `documentacion/ORGANIZATIONAL_SCOPE_MASTER_PLAN.md`)

Same discipline as F6 of that project: verify the graph already captures reality before writing
any new extractor code, rather than assuming it needs work.

- **Confirmed (no code change needed):** `sede`/`area` fields on the 6 "candidato fuerte" apps
  (`facturas.Factura`, `tenant_cotizaciones.Cotizacion`, `tenant_gastos.DocumentoSoporte`,
  `tenant_inventario.MovimientoInventario`, `tenant_proyectos.Proyecto`,
  `tenant_empleados.Empleado`) are captured automatically as `Field`/`HAS_FIELD`/`REFERENCES`
  nodes and edges, same generic class-body-assignment mechanism as always - no extractor work was
  ever needed for these fields, confirming F6's prediction from months earlier.
- **Found stale dumps:** the committed `tools/ekg/out/core.json` predated
  `apps/tenant/core/services/organizational_scope.py`/`organizational_filters.py`'s latest state
  (both touched earlier the same day this phase ran) - anyone running `governance --offline` or
  `impact.py` against the committed dumps got an incomplete picture of `core`. Fixed by
  re-running `ekg-dry-run` for `core` plus the 6 candidato-fuerte apps (`facturas`, `cotizaciones`,
  `gastos`, `inventario`, `proyectos`, `empleados`).
- **Confirmed blind spot, not fixed (out of scope):** `organizational_filters.py` (module-level
  functions only - `filter_by_context`/`filter_by_scope`/`filter_by_scope_null_safe`) is entirely
  invisible to the graph, because `extract_services()` only extracts classes.
  `organizational_scope.py`/`organizational_context.py` ARE visible (their public API is class-based:
  `OrganizationalScope`/`OrganizationalContext`/their `*Error`/`*Mixin` companions). Extending the
  extractor to cover module-level functions is a pre-existing, much broader roadmap item (already
  noted earlier in this report) - not scoped to this one file, not built here.
- **Governance re-run** (`ekg-governance --offline`, 2912 nodes / 4587 edges after the refresh
  above) confirmed `sede_or_area_field_without_sede_aware_model` (OCF Fase 11 rule, see governance
  section above) still fails for exactly the same 6 candidato-fuerte apps. Evaluated deliberately
  and NOT fixed: those apps use intentional NULL-safe scoping (100% of real `sede` data is NULL,
  per OSF F7's own empirical audit and explicit user decision) - forcing `SedeAwareModel`
  inheritance would mean changing 6 models' field declarations (`null`/`blank`), generating
  migrations with real risk to the NULL-safe behavior validated across OSF F7-F14. A schema/model
  change, not a knowledge-graph task - left as a flagged architectural decision for a possible
  future dedicated phase, consistent with this report's own practice of not silently expanding
  scope (see the `viewsets_without_service_layer` triage above, which took the same stance).

## DONE (2026-08-09): OSF Fase F16 - "gobernanza automatica ampliada", closing phase of the
Organizational Scope Framework - new import-cycle governance rule

Mapped the original F16 wishlist ("Nueva recomendación arquitectónica.md", FASE 16) item-by-item
against what `governance.py` already implements, what OSF Fase F14's runtime test suite already
covers (query/service/bridge semantic scope checks - exactly the category this module's own
docstring already declines as "not honestly checkable from structural graph data"), and what's
genuinely new and buildable without touching an extractor. Only "Import circular" qualified.

- **Built**: `find_import_cycles_between_tenant_apps()` - 3-color DFS cycle detection over the
  App-App subgraph induced by `IMPORTS` edges (already populated by `extract_services()` for
  `apps.tenant.<other_app>` imports inside `services/` - zero extractor changes). Added to
  `governance.py`'s `run()` sweep. 2 new tests in `test_governance.py`: one synthetic (proves the
  algorithm itself, independent of current app state so the test doesn't silently go stale if the
  real finding below is ever fixed) and one against the real merged `core`+`empresa`+`perfil`
  graph (proves it fires on real data).
- **Real finding, investigated before reporting**: running the new rule against the full 17-app
  graph (2912 nodes / 4587 edges) surfaced 2 genuine cycles - `core -> empresa -> perfil -> core`
  and `empresa -> perfil -> empresa`. Inspected the actual edge properties (module/name/line, not
  just the app-level summary) before concluding anything: all 4 underlying imports are of *Model*
  classes (`Empresa`, `TenantProfile`, `Area`), never a *Service* class - one of the four
  (`perfil -> core.services.membership.check_membership_by_schema`) is in fact the *correct*
  Bridge pattern AGENTS.md §17 recommends. Model-level cross-app FK references are normal Django
  practice, not the Service-to-Service coupling the Bridge/Soft-Reference pattern exists to
  prevent between peer business-domain apps (facturas<->gastos, not the foundational
  core/empresa/perfil trio). **Not fixed** - refactoring 3 foundational apps' cross-imports is a
  real architectural change with real risk, out of scope for a governance-rule-writing phase - left
  as a documented, evaluated finding, with a note in the rule's own docstring that a future
  refinement could distinguish Model-import cycles (likely acceptable) from Service-import cycles
  (a real violation) if this ever needs sharper precision.
- Full EKG test suite (69 -> 71 tests after the 2 additions) still green; `ruff check` clean on
  both touched files.
