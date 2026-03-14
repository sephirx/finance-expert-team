"""
Runtime Guards — Power of Ten Enforcement at Execution Time
============================================================
R1: No recursion. R2: Bounded loops. R3: Memory bounds.
R5: I/O validation. R7: Return value checks. R9: Nesting depth.
"""

import functools
import time

# ---------------------------------------------------------------------------
# R2: Bounded Loop Guard
# ---------------------------------------------------------------------------

MAX_FALLBACK_ATTEMPTS = 4
MAX_RETRY_ATTEMPTS = 10


def bounded_retry(max_attempts: int = MAX_RETRY_ATTEMPTS):
    """Decorator: enforce max retry attempts on any loop-based retry logic."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_attempts):  # R2: bounded
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
            raise RuntimeError(
                f"R2 Violation: {func.__name__} exceeded {max_attempts} attempts. "
                f"Last error: {last_error}"
            )
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# R5: Input/Output Validation Guards
# ---------------------------------------------------------------------------

def validate_agent_input(ticker: str) -> list[str]:
    """Validate common agent inputs. Returns list of error messages."""
    errors = []
    if not ticker or not isinstance(ticker, str):
        errors.append("ticker must be a non-empty string")
    elif len(ticker) > 10:
        errors.append(f"ticker '{ticker}' exceeds max length 10")
    return errors


def validate_agent_output(result: dict, agent_name: str) -> list[str]:
    """Validate agent output conforms to expected schema."""
    if not isinstance(result, dict):
        return [f"{agent_name} returned {type(result).__name__}, expected dict"]

    errors = []
    required_keys = {"agent", "ticker", "data", "error"}
    missing = required_keys - set(result.keys())
    if missing:
        errors.append(f"{agent_name} output missing keys: {missing}")

    if "data" in result and not isinstance(result["data"], dict):
        errors.append(f"{agent_name}.data is {type(result['data']).__name__}, expected dict")

    return errors


# ---------------------------------------------------------------------------
# R7: Return Value Check Guard
# ---------------------------------------------------------------------------

def check_agent_result(result: dict, agent_name: str) -> bool:
    """Check if an agent result indicates an error. Returns True if OK."""
    if not isinstance(result, dict):
        return False
    if result.get("error"):
        return False
    if not result.get("data"):
        return False
    return True


# ---------------------------------------------------------------------------
# R9: Nesting Depth Guard (iterative — R1 compliant, no recursion)
# ---------------------------------------------------------------------------

MAX_NESTING = 2


def check_dict_depth(d: dict) -> int:
    """Return the max nesting depth of a dict. Iterative, not recursive (R1)."""
    if not isinstance(d, dict):
        return 0
    max_depth = 1
    stack = [(d, 1)]  # (dict, current_depth)
    for _ in range(10000):  # R2: bounded
        if not stack:
            break
        current, depth = stack.pop()
        if depth > max_depth:
            max_depth = depth
        for v in current.values():
            if isinstance(v, dict) and v:
                stack.append((v, depth + 1))
    return max_depth


def validate_output_depth(result: dict, agent_name: str) -> str | None:
    """Validate output nesting depth. Returns error message or None."""
    data = result.get("data", {})
    if not isinstance(data, dict):
        return None
    depth = check_dict_depth(data)
    if depth > MAX_NESTING:
        return f"R9: {agent_name} output nesting depth {depth} > max {MAX_NESTING}"
    return None


# ---------------------------------------------------------------------------
# R3: Memory Budget Guard
# ---------------------------------------------------------------------------

MAX_DATAFRAME_ROWS = 5000
MAX_LIST_SIZE = 1000


def check_data_bounds(data: dict, agent_name: str) -> list[str]:
    """Check that data structures stay within pre-allocated bounds."""
    warnings = []
    for key, val in data.items():
        if isinstance(val, list) and len(val) > MAX_LIST_SIZE:
            warnings.append(
                f"R3: {agent_name}.{key} list has {len(val)} items (max {MAX_LIST_SIZE})"
            )
        if hasattr(val, "__len__") and hasattr(val, "iloc"):
            if len(val) > MAX_DATAFRAME_ROWS:
                warnings.append(
                    f"R3: {agent_name}.{key} DataFrame has {len(val)} rows (max {MAX_DATAFRAME_ROWS})"
                )
    return warnings


# ---------------------------------------------------------------------------
# Pipeline-level enforcement
# ---------------------------------------------------------------------------

class RegulationContext:
    """Tracks regulation compliance during a single pipeline run."""

    def __init__(self):
        self.violations: list[str] = []
        self.warnings: list[str] = []
        self.agents_checked: int = 0
        self.agents_passed: int = 0
        self.start_time: float = time.time()

    def check_agent(self, result: dict, agent_name: str):
        """Run all runtime checks on an agent's output."""
        self.agents_checked += 1
        schema_errors = validate_agent_output(result, agent_name)
        self.violations.extend(schema_errors)

        if not check_agent_result(result, agent_name):
            self.warnings.append(f"R7: {agent_name} returned error or empty data")

        depth_error = validate_output_depth(result, agent_name)
        if depth_error:
            self.violations.append(depth_error)

        if isinstance(result.get("data"), dict):
            bound_warnings = check_data_bounds(result["data"], agent_name)
            self.warnings.extend(bound_warnings)

        if not schema_errors and not depth_error:
            self.agents_passed += 1

    def summary(self) -> dict:
        return {
            "agents_checked": self.agents_checked,
            "agents_passed": self.agents_passed,
            "runtime_violations": len(self.violations),
            "runtime_warnings": len(self.warnings),
            "violations": self.violations[:10],
            "warnings": self.warnings[:10],
            "elapsed_ms": round((time.time() - self.start_time) * 1000),
        }

    def is_compliant(self) -> bool:
        return len(self.violations) == 0
