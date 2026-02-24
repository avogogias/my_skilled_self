"""Code quality analysis using Python's built-in ast module and radon.

Provides static analysis without executing code:
  - AST-based: function/class discovery, complexity hints, import audit
  - Radon: cyclomatic complexity (A–F grade), maintainability index, raw metrics

Results are returned as plain dicts so the ADK agent can narrate findings
and optionally create GitHub issues with them.
"""

import ast
import os
import textwrap
from pathlib import Path
from typing import Any

# radon is optional — degrade gracefully if not installed
try:
    from radon.complexity import cc_rank, cc_visit
    from radon.metrics import h_visit, mi_visit
    from radon.raw import analyze

    _RADON_AVAILABLE = True
except ImportError:
    _RADON_AVAILABLE = False


# ── Grades ────────────────────────────────────────────────────────────────────

CC_GRADE_MEANING = {
    "A": "Low complexity (1–5) — simple, easy to test",
    "B": "Moderate complexity (6–10) — acceptable",
    "C": "High complexity (11–15) — consider refactoring",
    "D": "Very high complexity (16–20) — difficult to test",
    "E": "Extremely high complexity (21–25) — refactor urgently",
    "F": "Unmaintainable (>25) — rewrite recommended",
}

MI_GRADE_MEANING = {
    "A": "Highly maintainable (>20)",
    "B": "Moderately maintainable (10–20)",
    "C": "Difficult to maintain (<10)",
}


def _mi_grade(mi: float) -> str:
    if mi > 20:
        return "A"
    if mi > 10:
        return "B"
    return "C"


# ── AST Visitor ───────────────────────────────────────────────────────────────

class _CodeVisitor(ast.NodeVisitor):
    """Collects structural information from an AST."""

    def __init__(self):
        self.functions: list[dict] = []
        self.classes: list[str] = []
        self.imports: list[str] = []
        self.todos: list[dict] = []
        self._class_stack: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef):
        self.classes.append(node.name)
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._visit_func(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._visit_func(node)

    def _visit_func(self, node):
        has_docstring = (
            isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ) if node.body else False

        args = [a.arg for a in node.args.args]
        has_return_annotation = node.returns is not None
        missing_annotations = [
            a.arg for a in node.args.args
            if a.annotation is None and a.arg != "self"
        ]

        self.functions.append({
            "name": node.name,
            "line": node.lineno,
            "class": self._class_stack[-1] if self._class_stack else None,
            "args": args,
            "has_docstring": has_docstring,
            "has_return_annotation": has_return_annotation,
            "missing_type_annotations": missing_annotations,
            "is_async": isinstance(node, ast.AsyncFunctionDef),
        })
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ""
        for alias in node.names:
            self.imports.append(f"{module}.{alias.name}")

    def visit_Expr(self, node: ast.Expr):
        """Detect TODO/FIXME/HACK comments in string literals."""
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            val = node.value.value.upper()
            for marker in ("TODO", "FIXME", "HACK", "XXX"):
                if marker in val:
                    self.todos.append({"line": node.lineno, "marker": marker, "text": node.value.value[:120]})
        self.generic_visit(node)


# ── Public analysis functions ──────────────────────────────────────────────────

def analyze_file(file_path: str) -> dict[str, Any]:
    """Run full static analysis on a single Python file.

    Args:
        file_path: Absolute or relative path to a .py file.

    Returns:
        Dict with structure, complexity, maintainability, and issues.
    """
    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}
    if path.suffix != ".py":
        return {"error": f"Not a Python file: {file_path}"}

    source = path.read_text(encoding="utf-8", errors="replace")
    result: dict[str, Any] = {
        "file": str(path),
        "lines": source.count("\n") + 1,
        "size_bytes": path.stat().st_size,
    }

    # ── AST Analysis ─────────────────────────────────────────────────────────
    try:
        tree = ast.parse(source, filename=str(path))
        visitor = _CodeVisitor()
        visitor.visit(tree)

        result["functions"] = visitor.functions
        result["classes"] = visitor.classes
        result["imports"] = list(set(visitor.imports))
        result["todos"] = visitor.todos

        # Quality issues from AST
        issues: list[dict] = []
        for fn in visitor.functions:
            if not fn["has_docstring"]:
                issues.append({
                    "severity": "minor",
                    "line": fn["line"],
                    "message": f"Function '{fn['name']}' is missing a docstring.",
                })
            if fn["missing_type_annotations"]:
                issues.append({
                    "severity": "minor",
                    "line": fn["line"],
                    "message": (
                        f"Function '{fn['name']}' has unannotated parameters: "
                        f"{', '.join(fn['missing_type_annotations'])}."
                    ),
                })

        result["ast_issues"] = issues
        result["ast_parse_error"] = None

    except SyntaxError as exc:
        result["ast_parse_error"] = f"SyntaxError at line {exc.lineno}: {exc.msg}"
        result["functions"] = []
        result["classes"] = []
        result["imports"] = []
        result["todos"] = []
        result["ast_issues"] = []

    # ── Radon Analysis ────────────────────────────────────────────────────────
    if _RADON_AVAILABLE:
        try:
            # Cyclomatic complexity
            cc_results = cc_visit(source)
            cc_summary: list[dict] = []
            for block in cc_results:
                grade = cc_rank(block.complexity)
                cc_summary.append({
                    "name": block.name,
                    "type": block.letter,
                    "line": block.lineno,
                    "complexity": block.complexity,
                    "grade": grade,
                    "meaning": CC_GRADE_MEANING.get(grade, ""),
                })

            result["cyclomatic_complexity"] = cc_summary
            result["complexity_grade"] = (
                cc_rank(max(b["complexity"] for b in cc_summary))
                if cc_summary else "A"
            )

            # Maintainability index
            mi = mi_visit(source, multi=True)
            mi_score = round(mi, 1) if isinstance(mi, float) else 0.0
            mi_g = _mi_grade(mi_score)
            result["maintainability_index"] = mi_score
            result["maintainability_grade"] = mi_g
            result["maintainability_meaning"] = MI_GRADE_MEANING.get(mi_g, "")

            # Raw metrics
            raw = analyze(source)
            result["raw_metrics"] = {
                "loc": raw.loc,
                "sloc": raw.sloc,
                "comments": raw.comments,
                "blank": raw.blank,
                "comment_ratio": round(raw.comments / raw.sloc, 2) if raw.sloc else 0,
            }

            # Flag high-complexity functions as issues
            for cc in cc_summary:
                if cc["grade"] in ("C", "D", "E", "F"):
                    result["ast_issues"].append({
                        "severity": "major" if cc["grade"] in ("C", "D") else "critical",
                        "line": cc["line"],
                        "message": (
                            f"'{cc['name']}' has cyclomatic complexity {cc['complexity']} "
                            f"(grade {cc['grade']}): {cc['meaning']}"
                        ),
                    })

        except Exception as exc:
            result["radon_error"] = str(exc)
    else:
        result["radon_error"] = "radon not installed — pip install radon"

    # ── Summary ───────────────────────────────────────────────────────────────
    all_issues = result.get("ast_issues", [])
    result["issue_count"] = {
        "critical": sum(1 for i in all_issues if i["severity"] == "critical"),
        "major": sum(1 for i in all_issues if i["severity"] == "major"),
        "minor": sum(1 for i in all_issues if i["severity"] == "minor"),
        "total": len(all_issues),
    }

    return result


def analyze_directory(directory: str, pattern: str = "*.py") -> dict[str, Any]:
    """Analyse all Python files in a directory.

    Args:
        directory: Path to search recursively.
        pattern: Glob pattern (default *.py).

    Returns:
        Aggregated analysis across all files.
    """
    root = Path(directory)
    if not root.exists():
        return {"error": f"Directory not found: {directory}"}

    files = [p for p in root.rglob(pattern) if "__pycache__" not in str(p)]
    file_results = []
    total_issues = {"critical": 0, "major": 0, "minor": 0, "total": 0}
    total_loc = 0
    worst_files: list[dict] = []

    for f in files:
        analysis = analyze_file(str(f))
        if "error" not in analysis:
            file_results.append({
                "file": str(f.relative_to(root)),
                "lines": analysis.get("lines", 0),
                "issue_count": analysis.get("issue_count", {}),
                "complexity_grade": analysis.get("complexity_grade", "N/A"),
                "maintainability_grade": analysis.get("maintainability_grade", "N/A"),
            })
            ic = analysis.get("issue_count", {})
            for key in total_issues:
                total_issues[key] = total_issues.get(key, 0) + ic.get(key, 0)
            total_loc += analysis.get("lines", 0)
            if ic.get("critical", 0) + ic.get("major", 0) > 0:
                worst_files.append({
                    "file": str(f.relative_to(root)),
                    "critical": ic.get("critical", 0),
                    "major": ic.get("major", 0),
                    "complexity_grade": analysis.get("complexity_grade", "N/A"),
                })

    worst_files.sort(key=lambda x: (x["critical"], x["major"]), reverse=True)

    return {
        "directory": str(root),
        "files_analysed": len(file_results),
        "total_loc": total_loc,
        "total_issues": total_issues,
        "worst_files": worst_files[:10],
        "files": file_results,
        "radon_available": _RADON_AVAILABLE,
    }
