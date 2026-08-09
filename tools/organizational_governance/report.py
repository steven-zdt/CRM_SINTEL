"""
Formato de reporte legible (F14.21) - agrupa findings por categoria y
cuenta PASS/WARN/FAIL. "PASS" aqui significa "regla evaluada, 0 findings",
no "todo el codigo fue verificado exhaustivamente" - honesto sobre el
alcance real de las reglas implementadas (ver rules.ALL_RULES).
"""
from __future__ import annotations

from collections import Counter, defaultdict

from tools.organizational_governance.graph import Graph
from tools.organizational_governance.rules import ALL_RULES, Finding, run_all_rules

CATEGORY_ORDER = (
    "ARCHITECTURE",
    "SECURITY",
    "MULTI_TENANT",
    "ORGANIZATIONAL",
    "INTEGRATIONS",
    "SERVICE_LAYER",
    "DOCUMENTATION",
    "TEST_COVERAGE",
)

_RULE_CATEGORY = {rule.rule_id: rule.category for rule in ALL_RULES}


def _counts_for_category(findings: list[Finding], category: str, rule_ids_in_category: set[str]) -> tuple[int, int, int]:
    cat_findings = [f for f in findings if _RULE_CATEGORY.get(f.rule_id) == category]
    fail = sum(1 for f in cat_findings if f.status == "FAIL")
    warn = sum(1 for f in cat_findings if f.status == "WARN")
    rules_evaluated = len(rule_ids_in_category)
    rules_with_findings = len({f.rule_id for f in cat_findings})
    passed = max(rules_evaluated - rules_with_findings, 0)
    return passed, warn, fail


def render_report(graph: Graph, findings: list[Finding] | None = None) -> str:
    if findings is None:
        findings = run_all_rules(graph)

    lines: list[str] = []
    lines.append("SINTEL ARCHITECTURE GOVERNANCE")
    lines.append("=" * 30)
    lines.append("")
    lines.append("KNOWLEDGE GRAPH")
    lines.append(f"Entities: {len(graph.nodes)}")
    lines.append(f"Relations: {len(graph.edges)}")
    lines.append("")

    rule_ids_by_category: dict[str, set[str]] = defaultdict(set)
    for rule in ALL_RULES:
        rule_ids_by_category[rule.category].add(rule.rule_id)

    total_fail = 0
    total_warn = 0
    for category in CATEGORY_ORDER:
        rule_ids = rule_ids_by_category.get(category, set())
        passed, warn, fail = _counts_for_category(findings, category, rule_ids)
        total_fail += fail
        total_warn += warn
        lines.append(category.replace("_", " "))
        lines.append("-" * len(category.replace("_", " ")))
        lines.append(f"PASS: {passed}")
        lines.append(f"WARN: {warn}")
        lines.append(f"FAIL: {fail}")
        lines.append("")

    if total_fail:
        final_status = "FAIL"
    elif total_warn:
        final_status = "WARN"
    else:
        final_status = "PASS"

    lines.append("FINAL STATUS:")
    lines.append(final_status)
    return "\n".join(lines)


def render_findings_detail(findings: list[Finding]) -> str:
    if not findings:
        return "(sin findings)"
    lines = []
    for f in findings:
        lines.append(f"{f.rule_id} {f.severity} {f.status}")
        lines.append(f"Component: {f.component}")
        lines.append(f"File: {f.file}" + (f":{f.line}" if f.line else ""))
        lines.append(f"Evidence: {f.evidence}")
        lines.append(f"Expected: {f.expected}")
        lines.append(f"Actual: {f.actual}")
        lines.append(f"Recommendation: {f.recommendation}")
        lines.append("")
    return "\n".join(lines)
