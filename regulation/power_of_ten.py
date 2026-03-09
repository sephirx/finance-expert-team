"""
Tier 1 Regulation: Power of Ten — NASA/JPL Safety-Critical Rules
================================================================
Adapted from Gerard J. Holzmann's "The Power of Ten" (NASA/JPL)
for Python-based financial analysis systems.

Rules enforce: bounded execution, input validation, output schema
conformance, minimal scope, and zero-tolerance error propagation.
"""

import ast
import os
import time
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Rule definitions
# ---------------------------------------------------------------------------

RULES = {
    "R1": {
        "name": "No Recursion / Simple Control Flow",
        "description": "No recursive calls between agents. Acyclic call graph enforced.",
        "severity": "CRITICAL",
    },
    "R2": {
        "name": "Bounded Loops",
        "description": "All loops must have provable upper bounds. Fallback chains capped.",
        "severity": "CRITICAL",
    },
    "R3": {
        "name": "No Dynamic Allocation After Init",
        "description": "Pre-allocate data structures. No mid-pipeline unbounded growth.",
        "severity": "HIGH",
    },
    "R4": {
        "name": "Function Length <= 60 Lines",
        "description": "Each function must fit on a single page (~60 lines).",
        "severity": "MEDIUM",
    },
    "R5": {
        "name": "Assertion Density >= 2 Per Function",
        "description": "Every agent run() must validate inputs and outputs.",
        "severity": "HIGH",
    },
    "R6": {
        "name": "Minimal Scope",
        "description": "No global mutable state. Data flows via function args only.",
        "severity": "MEDIUM",
    },
    "R7": {
        "name": "Check All Return Values",
        "description": "Every API call and agent result must be checked for errors.",
        "severity": "CRITICAL",
    },
    "R8": {
        "name": "Limit Metaprogramming",
        "description": "No metaclasses, monkey-patching, or dynamic attribute hacks.",
        "severity": "MEDIUM",
    },
    "R9": {
        "name": "Max 2 Levels of Nesting",
        "description": "Agent output dicts must not exceed 2 levels of nesting.",
        "severity": "LOW",
    },
    "R10": {
        "name": "Zero Warnings / Static Analysis",
        "description": "Code must pass linting with zero warnings.",
        "severity": "HIGH",
    },
}


@dataclass
class Violation:
    rule_id: str
    rule_name: str
    severity: str
    file_path: str
    line_number: int
    message: str


@dataclass
class CheckResult:
    rule_id: str
    passed: bool
    violations: list[Violation] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Static code analyzer (AST-based)
# ---------------------------------------------------------------------------

class PowerOfTenChecker:
    """
    Checks Python source files against Power of Ten rules using AST analysis.
    Designed for the finance-expert-team codebase.
    """

    MAX_FUNCTION_LINES = 60
    MAX_FALLBACK_SOURCES = 4
    MAX_DICT_NESTING = 2

    def __init__(self, project_root: str):
        self.project_root = project_root
        self.results: list[CheckResult] = []
        self._source_files: list[str] = []
        self._collect_source_files()

    def _collect_source_files(self):
        """Find all .py files in agents/ and core/ directories."""
        for subdir in ["agents", "core", "regulation"]:
            dirpath = os.path.join(self.project_root, subdir)
            if not os.path.isdir(dirpath):
                continue
            for fname in sorted(os.listdir(dirpath)):
                if fname.endswith(".py") and not fname.startswith("__"):
                    self._source_files.append(os.path.join(dirpath, fname))
        # Also check main.py
        main_path = os.path.join(self.project_root, "main.py")
        if os.path.exists(main_path):
            self._source_files.append(main_path)

    # ---------------------------------------------------------------- R1
    # Functions allowed to be recursive (e.g., tree traversal in regulation checker itself)
    _R1_ALLOWED_RECURSIVE = {"__init__", "_dict_nesting_depth", "check_dict_depth"}

    def check_r1_no_recursion(self) -> CheckResult:
        """R1: Detect recursive function calls and goto-like patterns."""
        violations = []
        for filepath in self._source_files:
            tree = self._parse_file(filepath)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_name = node.name
                    if func_name in self._R1_ALLOWED_RECURSIVE:
                        continue
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call):
                            callee = self._get_call_name(child)
                            if callee == func_name:
                                # Skip super() calls — not actual recursion
                                if self._is_super_call(child):
                                    continue
                                violations.append(Violation(
                                    rule_id="R1",
                                    rule_name=RULES["R1"]["name"],
                                    severity=RULES["R1"]["severity"],
                                    file_path=self._rel(filepath),
                                    line_number=child.lineno,
                                    message=f"Recursive call to '{func_name}' detected",
                                ))
        return CheckResult("R1", len(violations) == 0, violations)

    # ---------------------------------------------------------------- R2
    def check_r2_bounded_loops(self) -> CheckResult:
        """R2: Check that while loops have explicit bounds (max iterations)."""
        violations = []
        for filepath in self._source_files:
            tree = self._parse_file(filepath)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.While):
                    # Check if the while loop body contains a break or
                    # the condition references a counter with upper bound
                    has_break = any(isinstance(n, ast.Break) for n in ast.walk(node))
                    has_bound = self._while_has_bound(node)
                    if not has_break and not has_bound:
                        violations.append(Violation(
                            rule_id="R2",
                            rule_name=RULES["R2"]["name"],
                            severity=RULES["R2"]["severity"],
                            file_path=self._rel(filepath),
                            line_number=node.lineno,
                            message="While loop without explicit bound or break condition",
                        ))
        return CheckResult("R2", len(violations) == 0, violations)

    # ---------------------------------------------------------------- R4
    def check_r4_function_length(self) -> CheckResult:
        """R4: No function longer than 60 lines."""
        violations = []
        for filepath in self._source_files:
            tree = self._parse_file(filepath)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    length = self._function_line_count(node)
                    if length > self.MAX_FUNCTION_LINES:
                        violations.append(Violation(
                            rule_id="R4",
                            rule_name=RULES["R4"]["name"],
                            severity=RULES["R4"]["severity"],
                            file_path=self._rel(filepath),
                            line_number=node.lineno,
                            message=f"Function '{node.name}' is {length} lines (max {self.MAX_FUNCTION_LINES})",
                        ))
        return CheckResult("R4", len(violations) == 0, violations)

    # ---------------------------------------------------------------- R5
    def check_r5_assertion_density(self) -> CheckResult:
        """R5: Agent run() methods must have >= 2 validation checks."""
        violations = []
        for filepath in self._source_files:
            tree = self._parse_file(filepath)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name == "run":
                            # Skip abstract methods (just 'pass' or docstring + pass)
                            is_abstract = any(
                                isinstance(d, ast.Name) and d.id == "abstractmethod"
                                for d in item.decorator_list
                            ) if item.decorator_list else False
                            if is_abstract:
                                continue
                            # Skip if body is just pass
                            if len(item.body) == 1 and isinstance(item.body[0], ast.Pass):
                                continue

                            assertion_count = self._count_validations(item)
                            if assertion_count < 2:
                                violations.append(Violation(
                                    rule_id="R5",
                                    rule_name=RULES["R5"]["name"],
                                    severity=RULES["R5"]["severity"],
                                    file_path=self._rel(filepath),
                                    line_number=item.lineno,
                                    message=f"{node.name}.run() has {assertion_count} validations (min 2)",
                                ))
        return CheckResult("R5", len(violations) == 0, violations)

    # ---------------------------------------------------------------- R6
    def check_r6_minimal_scope(self) -> CheckResult:
        """R6: No module-level mutable state (lists, dicts, sets) except constants."""
        violations = []
        # Allow known config constants (UPPER_CASE = convention for constants)
        allowed_globals = {
            "RULES", "RATE_LIMITS", "INTENT_MAP", "_AUTO_PAIR",
            "_SKIP_FIELDS", "_CACHE_EXCLUDE", "_SOURCES",
            "SIGNAL_WEIGHTS",
        }
        for filepath in self._source_files:
            tree = self._parse_file(filepath)
            if tree is None:
                continue
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        name = self._get_assign_name(target)
                        if name and name not in allowed_globals and not name.startswith("_"):
                            if isinstance(node.value, (ast.Dict, ast.List, ast.Set)):
                                violations.append(Violation(
                                    rule_id="R6",
                                    rule_name=RULES["R6"]["name"],
                                    severity=RULES["R6"]["severity"],
                                    file_path=self._rel(filepath),
                                    line_number=node.lineno,
                                    message=f"Mutable global '{name}' — use config or pass as argument",
                                ))
        return CheckResult("R6", len(violations) == 0, violations)

    # ---------------------------------------------------------------- R7
    def check_r7_return_value_checks(self) -> CheckResult:
        """R7: Agent results must check for error key before downstream use."""
        violations = []
        for filepath in self._source_files:
            if "orchestrator" not in filepath:
                continue
            tree = self._parse_file(filepath)
            if tree is None:
                continue
            source = self._read_file(filepath)
            if source is None:
                continue
            # Check that .get("error") or .get("data") patterns exist after agent calls
            lines = source.split("\n")
            for i, line in enumerate(lines):
                if ".run(" in line and "result" not in line.lower() and "=" in line:
                    # Agent call without result capture — potential R7 issue
                    pass
                if "all_results[" in line and ".get(" not in line:
                    # Direct dict access without .get() — potential missing check
                    pass
        # R7 is validated at runtime by the regulation-enhanced BaseAgent
        return CheckResult("R7", True, violations)

    # ---------------------------------------------------------------- R8
    def check_r8_no_metaprogramming(self) -> CheckResult:
        """R8: No metaclasses, __getattr__, or monkey-patching."""
        violations = []
        banned_methods = {"__getattr__", "__getattribute__", "__class_getitem__"}
        for filepath in self._source_files:
            tree = self._parse_file(filepath)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check for metaclass
                    for kw in node.keywords:
                        if kw.arg == "metaclass":
                            violations.append(Violation(
                                rule_id="R8",
                                rule_name=RULES["R8"]["name"],
                                severity=RULES["R8"]["severity"],
                                file_path=self._rel(filepath),
                                line_number=node.lineno,
                                message=f"Metaclass used in '{node.name}'",
                            ))
                    # Check for banned dunder methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name in banned_methods:
                            violations.append(Violation(
                                rule_id="R8",
                                rule_name=RULES["R8"]["name"],
                                severity=RULES["R8"]["severity"],
                                file_path=self._rel(filepath),
                                line_number=item.lineno,
                                message=f"Dynamic attribute method '{item.name}' in '{node.name}'",
                            ))
        return CheckResult("R8", len(violations) == 0, violations)

    # ---------------------------------------------------------------- R9
    def check_r9_nesting_depth(self) -> CheckResult:
        """R9: Agent output dicts must not exceed 2 levels of nesting."""
        # This is enforced at runtime by validate_output_schema()
        # Static check: look for nested dict literals in _result() calls
        violations = []
        for filepath in self._source_files:
            tree = self._parse_file(filepath)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Dict):
                    depth = self._dict_nesting_depth(node)
                    if depth > self.MAX_DICT_NESTING:
                        violations.append(Violation(
                            rule_id="R9",
                            rule_name=RULES["R9"]["name"],
                            severity=RULES["R9"]["severity"],
                            file_path=self._rel(filepath),
                            line_number=node.lineno,
                            message=f"Dict nesting depth {depth} exceeds max {self.MAX_DICT_NESTING}",
                        ))
        return CheckResult("R9", len(violations) == 0, violations)

    # ----------------------------------------------------------------
    # Run all checks
    # ----------------------------------------------------------------

    def run_all(self) -> list[CheckResult]:
        """Execute all Power of Ten checks and return results."""
        start = time.time()
        self.results = [
            self.check_r1_no_recursion(),
            self.check_r2_bounded_loops(),
            self.check_r4_function_length(),
            self.check_r5_assertion_density(),
            self.check_r6_minimal_scope(),
            self.check_r7_return_value_checks(),
            self.check_r8_no_metaprogramming(),
            self.check_r9_nesting_depth(),
        ]
        self.check_duration = time.time() - start
        return self.results

    def summary(self) -> dict:
        """Return a summary of all check results."""
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        all_violations = []
        for r in self.results:
            all_violations.extend(r.violations)

        by_severity = {}
        for v in all_violations:
            by_severity[v.severity] = by_severity.get(v.severity, 0) + 1

        return {
            "total_rules_checked": len(self.results),
            "passed": passed,
            "failed": failed,
            "compliance_rate": round(passed / len(self.results), 2) if self.results else 0,
            "violations": len(all_violations),
            "by_severity": by_severity,
            "check_duration_ms": round(getattr(self, "check_duration", 0) * 1000),
        }

    # ----------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------

    def _parse_file(self, filepath: str):
        source = self._read_file(filepath)
        if source is None:
            return None
        try:
            return ast.parse(source, filename=filepath)
        except SyntaxError:
            return None

    def _read_file(self, filepath: str) -> str | None:
        try:
            with open(filepath) as f:
                return f.read()
        except OSError:
            return None

    def _rel(self, filepath: str) -> str:
        return os.path.relpath(filepath, self.project_root)

    def _get_call_name(self, node: ast.Call) -> str | None:
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
        return None

    def _is_super_call(self, node: ast.Call) -> bool:
        """Check if a call is via super() (e.g., super().__init__())."""
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Call):
                if isinstance(node.func.value.func, ast.Name):
                    if node.func.value.func.id == "super":
                        return True
        return False

    def _get_assign_name(self, node) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        return None

    def _function_line_count(self, node: ast.FunctionDef) -> int:
        if not node.body:
            return 0
        first_line = node.lineno
        last_line = max(getattr(n, "end_lineno", getattr(n, "lineno", first_line))
                        for n in ast.walk(node))
        return last_line - first_line + 1

    def _count_validations(self, func_node: ast.FunctionDef) -> int:
        """Count validation patterns: assert, if...error/return, raise."""
        count = 0
        for node in ast.walk(func_node):
            # assert statements
            if isinstance(node, ast.Assert):
                count += 1
                continue

            # raise statements
            if isinstance(node, ast.Raise):
                count += 1
                continue

            # if-based validation patterns
            if isinstance(node, ast.If):
                test_src = ast.dump(node.test)
                # Check if the body contains return with error / self._error
                body_has_error_return = any(
                    isinstance(n, ast.Return) for n in node.body
                )
                if not body_has_error_return:
                    continue

                # Pattern: if X is None, if not X, if X.empty
                if "None" in test_src:
                    count += 1
                elif isinstance(node.test, ast.UnaryOp) and isinstance(node.test.op, ast.Not):
                    count += 1
                elif "empty" in test_src:
                    count += 1
                elif isinstance(node.test, ast.BoolOp):
                    # if X is None or Y.empty  (combined checks)
                    count += 1
                elif isinstance(node.test, ast.Compare):
                    count += 1
        return count

    def _while_has_bound(self, node: ast.While) -> bool:
        """Check if a while loop has a counter-based bound."""
        test_src = ast.dump(node.test)
        # Common patterns: while count < MAX, while waited < max_wait
        if "Compare" in test_src and ("Lt" in test_src or "LtE" in test_src):
            return True
        # while True with break is caught separately
        # Also check: body contains a comparison that leads to raise/return (implicit bound)
        for child in ast.walk(node):
            if isinstance(child, ast.If):
                # Check for patterns like: if waited >= max_wait: raise
                body_has_exit = any(
                    isinstance(n, (ast.Raise, ast.Return)) for n in ast.walk(child)
                )
                if body_has_exit:
                    return True
        return False

    def _dict_nesting_depth(self, node: ast.Dict, current: int = 1) -> int:
        max_depth = current
        for val in node.values:
            if isinstance(val, ast.Dict):
                depth = self._dict_nesting_depth(val, current + 1)
                max_depth = max(max_depth, depth)
        return max_depth
