"""
manage.py production_readiness

Ejecuta el Production Check Registry completo (Fase 55: ProductionReadinessRun)
y produce un reporte human-readable + JSON. Disenado para correr como
proceso recurrente (Fase 70) -- no es una auditoria de una sola vez.

Uso:
    python manage.py production_readiness
    python manage.py production_readiness --json out.json
"""
import json

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.public.core.production_readiness.registry import (
    compute_blockers,
    compute_scorecard,
    overall_status,
    run_all_checks,
)


class Command(BaseCommand):
    help = "Ejecuta todos los production readiness checks registrados y produce un reporte."

    def add_arguments(self, parser):
        parser.add_argument("--json", dest="json_path", default=None, help="Ruta donde guardar el reporte JSON.")

    def handle(self, *args, **options):
        results = run_all_checks()
        blockers = compute_blockers(results)
        scorecard = compute_scorecard(results)
        status = overall_status(results)

        self.stdout.write(self.style.MIGRATE_HEADING(f"\nPRODUCTION READINESS RUN — {timezone.now().isoformat()}\n"))

        by_category: dict[str, list] = {}
        for r in results:
            by_category.setdefault(r.category, []).append(r)

        for category in sorted(by_category):
            self.stdout.write(f"\n== {category} ==")
            for r in by_category[category]:
                style = self.style.SUCCESS if r.status == "PASS" else (
                    self.style.ERROR if r.status == "BLOCKER" else self.style.WARNING
                )
                self.stdout.write(style(f"  [{r.status:20s}] {r.severity} {r.id} ({r.owner})"))
                self.stdout.write(f"      {r.evidence[:300]}")

        self.stdout.write(self.style.MIGRATE_HEADING("\n== SCORECARD ==\n"))
        for cat, counts in sorted(scorecard.items()):
            self.stdout.write(f"  {cat}: {counts}")

        self.stdout.write(self.style.MIGRATE_HEADING(f"\n== BLOCKERS ({len(blockers)}) ==\n"))
        for b in blockers:
            self.stdout.write(self.style.ERROR(f"  [{b.severity}] {b.id}: {b.evidence[:200]}"))

        final_style = self.style.SUCCESS if status == "READY" else (
            self.style.ERROR if status == "NOT_READY" else self.style.WARNING
        )
        self.stdout.write(final_style(f"\nOVERALL STATUS: {status}\n"))

        if options.get("json_path"):
            payload = {
                "timestamp": timezone.now().isoformat(),
                "overall_status": status,
                "scorecard": scorecard,
                "results": [r.to_dict() for r in results],
            }
            with open(options["json_path"], "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
            self.stdout.write(f"Reporte JSON guardado en {options['json_path']}")
