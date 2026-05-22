"""
Comprehensive Data Quality Engine.

Per-column validation rules modeled after DLT Expectations.
Every check produces a structured result: passed/failed, count of failures,
and optional sample of failing rows.
"""
import duckdb
from typing import Any, Optional
from dataclasses import dataclass, field

@dataclass
class QualityCheck:
    column: str
    rule: str
    params: dict[str, Any] = field(default_factory=dict)
    severity: str = "error"  # error, warning, info

@dataclass
class QualityResult:
    check: QualityCheck
    passed: bool
    failed_rows: int = 0
    sample: list[dict] = field(default_factory=list)
    error: Optional[str] = None

RULES = {}

def rule(name: str):
    def decorator(fn):
        RULES[name] = fn
        return fn
    return decorator

@rule("not_null")
def check_not_null(col: str, params: dict) -> tuple[str, str]:
    return f"{col} IS NOT NULL", f"SELECT * FROM {{table}} WHERE {col} IS NULL"

@rule("unique")
def check_unique(col: str, params: dict) -> tuple[str, str]:
    return f"{col} IS NOT NULL", f"""
        SELECT {col}, count(*) as cnt FROM {{table}}
        GROUP BY {col} HAVING count(*) > 1
    """

@rule("positive")
def check_positive(col: str, params: dict) -> tuple[str, str]:
    return f"{col} > 0", f"SELECT * FROM {{table}} WHERE {col} <= 0"

@rule("non_negative")
def check_non_negative(col: str, params: dict) -> tuple[str, str]:
    return f"{col} >= 0", f"SELECT * FROM {{table}} WHERE {col} < 0"

@rule("in_range")
def check_in_range(col: str, params: dict) -> tuple[str, str]:
    lo = params.get("min", -float("inf"))
    hi = params.get("max", float("inf"))
    return f"{col} >= {lo} AND {col} <= {hi}", f"SELECT * FROM {{table}} WHERE {col} < {lo} OR {col} > {hi}"

@rule("in_set")
def check_in_set(col: str, params: dict) -> tuple[str, str]:
    values = params.get("values", [])
    vals = ", ".join(f"'{v}'" for v in values)
    return f"{col} IN ({vals})", f"SELECT * FROM {{table}} WHERE {col} NOT IN ({vals})"

@rule("matches_regex")
def check_matches_regex(col: str, params: dict) -> tuple[str, str]:
    pattern = params.get("pattern", ".*")
    return f"regexp_matches({col}, '{pattern}')", f"SELECT * FROM {{table}} WHERE NOT regexp_matches({col}, '{pattern}')"

@rule("no_future_dates")
def check_no_future_dates(col: str, params: dict) -> tuple[str, str]:
    return f"{col} <= current_date", f"SELECT * FROM {{table}} WHERE {col} > current_date"

class DataQualityValidator:
    def __init__(self, db_path: str = ":memory:"):
        self.con = duckdb.connect(db_path)

    def check_table(self, table: str, checks: list[QualityCheck], sample_limit: int = 5) -> list[QualityResult]:
        results = []
        for check in checks:
            try:
                rule_fn = RULES.get(check.rule)
                if not rule_fn:
                    results.append(QualityResult(check=check, passed=False, error=f"Unknown rule: {check.rule}"))
                    continue
                condition, failure_query = rule_fn(check.column, check.params)
                failed = self.con.execute(f"SELECT count(*) FROM {table} WHERE NOT ({condition})").fetchone()[0]
                sample = []
                if failed > 0 and sample_limit > 0:
                    sample = self.con.execute(failure_query.replace("{table}", table) + f" LIMIT {sample_limit}").fetchdf().to_dict(orient="records")
                results.append(QualityResult(check=check, passed=failed == 0, failed_rows=failed, sample=sample))
            except Exception as e:
                results.append(QualityResult(check=check, passed=False, error=str(e)))
        return results

    def check_all(self, table: str, schema: dict[str, list[QualityCheck]]) -> dict[str, list[QualityResult]]:
        return {col: self.check_table(table, checks) for col, checks in schema.items()}

    def report(self, results: list[QualityResult]) -> str:
        lines = []
        passed = sum(1 for r in results if r.passed)
        total = len(results)
        lines.append(f"Data Quality: {passed}/{total} checks passed")
        for r in results:
            marker = "✅" if r.passed else "❌"
            detail = f" ({r.failed_rows} failures)" if not r.passed else ""
            error = f" — {r.error}" if r.error else ""
            lines.append(f"  {marker} {r.check.column}.{r.check.rule}{detail}{error}")
            if not r.passed and r.sample:
                for s in r.sample:
                    lines.append(f"      Sample: {s}")
        return "\n".join(lines)

    def close(self):
        self.con.close()
