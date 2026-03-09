"""
Compliance Report Generator
============================
Generates human-readable compliance reports for Power of Ten regulation checks.
Integrates with the pipeline to produce regulation status in the final output.
"""

from regulation.power_of_ten import PowerOfTenChecker, CheckResult, RULES


class ComplianceReporter:
    """Generates compliance reports from PowerOfTenChecker results."""

    def __init__(self, checker: PowerOfTenChecker):
        self.checker = checker

    def generate_text_report(self) -> str:
        """Generate a plain-text compliance report."""
        results = self.checker.results
        if not results:
            results = self.checker.run_all()

        summary = self.checker.summary()
        lines = []

        lines.append("")
        lines.append("```")
        lines.append(f"{'='*60}")
        lines.append(f"  TIER 1 REGULATION — Power of Ten Compliance Report")
        lines.append(f"{'='*60}")
        lines.append(f"")
        lines.append(f"  Rules Checked: {summary['total_rules_checked']}")
        lines.append(f"  Passed:        {summary['passed']}")
        lines.append(f"  Failed:        {summary['failed']}")
        lines.append(f"  Compliance:    {summary['compliance_rate']:.0%}")
        lines.append(f"  Check Time:    {summary['check_duration_ms']}ms")
        lines.append(f"")
        lines.append(f"  {'Rule':<6} {'Status':<8} {'Severity':<10} Description")
        lines.append(f"  {'-'*5:<6} {'-'*6:<8} {'-'*8:<10} {'-'*30}")

        for result in results:
            rule = RULES.get(result.rule_id, {})
            status = "PASS" if result.passed else "FAIL"
            severity = rule.get("severity", "?")
            name = rule.get("name", result.rule_id)
            lines.append(f"  {result.rule_id:<6} {status:<8} {severity:<10} {name}")

        # Show violations if any
        all_violations = []
        for result in results:
            all_violations.extend(result.violations)

        if all_violations:
            lines.append(f"")
            lines.append(f"  Violations ({len(all_violations)}):")
            for v in all_violations[:20]:  # Cap at 20 for readability
                lines.append(f"    [{v.rule_id}] {v.file_path}:{v.line_number}")
                lines.append(f"           {v.message}")

        lines.append(f"")
        lines.append(f"{'='*60}")
        lines.append("```")
        lines.append("")

        return "\n".join(lines)

    def generate_summary_dict(self) -> dict:
        """Generate a dict summary for embedding in pipeline results."""
        summary = self.checker.summary()
        results = self.checker.results

        rule_status = {}
        for result in results:
            rule = RULES.get(result.rule_id, {})
            rule_status[result.rule_id] = {
                "name": rule.get("name", ""),
                "passed": result.passed,
                "severity": rule.get("severity", ""),
                "violations": len(result.violations),
            }

        return {
            "compliance_rate": summary["compliance_rate"],
            "passed": summary["passed"],
            "failed": summary["failed"],
            "total_violations": summary["violations"],
            "by_severity": summary["by_severity"],
            "rules": rule_status,
            "check_duration_ms": summary["check_duration_ms"],
        }

    def get_compliance_grade(self) -> str:
        """Return a letter grade based on compliance rate."""
        summary = self.checker.summary()
        rate = summary["compliance_rate"]
        critical_violations = summary.get("by_severity", {}).get("CRITICAL", 0)

        # Any CRITICAL violation caps grade at C
        if critical_violations > 0:
            if rate >= 0.75:
                return "C+"
            return "C"

        if rate >= 1.0:
            return "A+"
        if rate >= 0.875:
            return "A"
        if rate >= 0.75:
            return "B+"
        if rate >= 0.625:
            return "B"
        if rate >= 0.50:
            return "C"
        return "D"
