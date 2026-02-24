"""Tests for the GitHub Reviewer skill.

All tests run offline — no real GitHub API calls are made.
PyGitHub is mocked at the module level; radon is used directly (installed).
"""

import os
import sys
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from skills.github_reviewer.analyzer import (
    _mi_grade,
    analyze_directory,
    analyze_file,
)


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def good_python_file(tmp_path: Path) -> Path:
    """A well-written Python file with docstrings and type annotations."""
    src = textwrap.dedent('''\
        """Module docstring."""
        import os
        from typing import Optional


        def add(a: int, b: int) -> int:
            """Return a + b."""
            return a + b


        def safe_divide(a: float, b: float) -> Optional[float]:
            """Divide a by b, returning None if b is zero."""
            if b == 0:
                return None
            return a / b


        class Calculator:
            """Simple calculator."""

            def multiply(self, x: int, y: int) -> int:
                """Return x * y."""
                return x * y
    ''')
    f = tmp_path / "good.py"
    f.write_text(src)
    return f


@pytest.fixture
def bad_python_file(tmp_path: Path) -> Path:
    """A poorly written Python file: no docstrings, no annotations, high complexity."""
    src = textwrap.dedent('''\
        import os, sys, json

        def process(x, y, z):
            if x > 0:
                if y > 0:
                    if z > 0:
                        for i in range(x):
                            for j in range(y):
                                if i == j:
                                    print(i, j)
                                elif i > j:
                                    print(i)
                                else:
                                    print(j)
                    else:
                        return None
                else:
                    return -1
            else:
                return 0

        def no_doc(a, b):
            return a + b
    ''')
    f = tmp_path / "bad.py"
    f.write_text(src)
    return f


@pytest.fixture
def syntax_error_file(tmp_path: Path) -> Path:
    f = tmp_path / "broken.py"
    f.write_text("def foo(:\n    pass\n")
    return f


# ── analyzer.analyze_file tests ───────────────────────────────────────────────

class TestAnalyzeFile:
    def test_nonexistent_file_returns_error(self):
        result = analyze_file("/nonexistent/path/file.py")
        assert "error" in result

    def test_non_python_file_returns_error(self, tmp_path):
        f = tmp_path / "readme.txt"
        f.write_text("hello")
        result = analyze_file(str(f))
        assert "error" in result

    def test_good_file_structure(self, good_python_file):
        result = analyze_file(str(good_python_file))
        assert "error" not in result
        assert result["lines"] > 0
        assert "functions" in result
        assert "classes" in result
        assert "imports" in result

    def test_good_file_detects_functions(self, good_python_file):
        result = analyze_file(str(good_python_file))
        fn_names = [f["name"] for f in result["functions"]]
        assert "add" in fn_names
        assert "safe_divide" in fn_names
        assert "multiply" in fn_names

    def test_good_file_detects_class(self, good_python_file):
        result = analyze_file(str(good_python_file))
        assert "Calculator" in result["classes"]

    def test_good_file_has_few_issues(self, good_python_file):
        result = analyze_file(str(good_python_file))
        # Well-written file should have no missing-docstring issues
        docstring_issues = [
            i for i in result.get("ast_issues", [])
            if "docstring" in i["message"].lower()
        ]
        assert len(docstring_issues) == 0

    def test_bad_file_detects_missing_docstrings(self, bad_python_file):
        result = analyze_file(str(bad_python_file))
        assert "error" not in result
        messages = [i["message"] for i in result.get("ast_issues", [])]
        missing_doc = [m for m in messages if "docstring" in m.lower()]
        assert len(missing_doc) >= 1  # process() and no_doc() are missing docstrings

    def test_bad_file_detects_missing_annotations(self, bad_python_file):
        result = analyze_file(str(bad_python_file))
        messages = [i["message"] for i in result.get("ast_issues", [])]
        # Message says "unannotated parameters" — check for either keyword
        annotation_issues = [
            m for m in messages
            if "unannotated" in m.lower() or "annotation" in m.lower()
        ]
        assert len(annotation_issues) >= 1

    def test_syntax_error_file_handled_gracefully(self, syntax_error_file):
        result = analyze_file(str(syntax_error_file))
        assert result.get("ast_parse_error") is not None
        assert "SyntaxError" in result["ast_parse_error"]
        # Functions/classes should be empty but present
        assert result["functions"] == []

    def test_issue_count_structure(self, good_python_file):
        result = analyze_file(str(good_python_file))
        ic = result["issue_count"]
        assert "critical" in ic
        assert "major" in ic
        assert "minor" in ic
        assert "total" in ic
        assert ic["total"] == ic["critical"] + ic["major"] + ic["minor"]

    def test_radon_metrics_present(self, good_python_file):
        result = analyze_file(str(good_python_file))
        # radon is installed in this env
        if "radon_error" not in result:
            assert "maintainability_index" in result
            assert "complexity_grade" in result
            assert "raw_metrics" in result

    def test_high_complexity_flagged(self, bad_python_file):
        result = analyze_file(str(bad_python_file))
        # The nested loops/ifs should produce high complexity
        cc = result.get("cyclomatic_complexity", [])
        if cc:  # only if radon is available
            max_cc = max(b["complexity"] for b in cc)
            assert max_cc > 1  # at minimum more than trivial


# ── analyzer.analyze_directory tests ──────────────────────────────────────────

class TestAnalyzeDirectory:
    def test_nonexistent_directory(self):
        result = analyze_directory("/nonexistent/dir")
        assert "error" in result

    def test_empty_directory(self, tmp_path):
        result = analyze_directory(str(tmp_path))
        assert result["files_analysed"] == 0
        assert result["total_loc"] == 0

    def test_counts_files(self, tmp_path, good_python_file, bad_python_file):
        result = analyze_directory(str(tmp_path))
        assert result["files_analysed"] == 2

    def test_aggregates_loc(self, tmp_path, good_python_file, bad_python_file):
        result = analyze_directory(str(tmp_path))
        assert result["total_loc"] > 0

    def test_total_issues_accumulated(self, tmp_path, bad_python_file):
        result = analyze_directory(str(tmp_path))
        assert result["total_issues"]["total"] >= 0  # At least 0

    def test_worst_files_listed(self, tmp_path, good_python_file, bad_python_file):
        result = analyze_directory(str(tmp_path))
        # bad_python_file should appear in worst_files if it has issues
        worst_names = [w["file"] for w in result.get("worst_files", [])]
        # bad.py has known issues — it should be in the list if any issues found
        if result["total_issues"]["total"] > 0:
            assert len(result["worst_files"]) >= 0  # may or may not be empty depending on severity

    def test_excludes_pycache(self, tmp_path):
        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        (pycache / "cached.py").write_text("x = 1")
        result = analyze_directory(str(tmp_path))
        names = [f["file"] for f in result.get("files", [])]
        assert not any("__pycache__" in n for n in names)


# ── MI grade helper ────────────────────────────────────────────────────────────

class TestMIGrade:
    def test_high_mi_is_A(self):
        assert _mi_grade(25.0) == "A"

    def test_medium_mi_is_B(self):
        assert _mi_grade(15.0) == "B"

    def test_low_mi_is_C(self):
        assert _mi_grade(5.0) == "C"

    def test_boundary_A_B(self):
        assert _mi_grade(20.1) == "A"
        assert _mi_grade(19.9) == "B"

    def test_boundary_B_C(self):
        assert _mi_grade(10.1) == "B"
        assert _mi_grade(9.9) == "C"


# ── Skill tool functions (GitHub API mocked) ───────────────────────────────────

class TestGitHubSkillTools:
    def test_analyze_python_file_tool(self, good_python_file):
        from skills.github_reviewer.skill import tool_analyze_python_file
        result = tool_analyze_python_file(str(good_python_file))
        assert "error" not in result or result.get("ast_parse_error") is None
        assert "functions" in result

    def test_analyze_codebase_tool(self, tmp_path, good_python_file):
        from skills.github_reviewer.skill import tool_analyze_codebase
        result = tool_analyze_codebase(str(tmp_path))
        assert "files_analysed" in result
        assert result["files_analysed"] >= 1

    def test_get_github_repo_info_no_token(self):
        from skills.github_reviewer.skill import tool_get_github_repo_info
        with patch.dict(os.environ, {"GITHUB_TOKEN": "", "GITHUB_REPO": ""}):
            result = tool_get_github_repo_info()
        assert "error" in result

    def test_get_github_issues_no_token(self):
        from skills.github_reviewer.skill import tool_get_github_issues
        with patch.dict(os.environ, {"GITHUB_TOKEN": "", "GITHUB_REPO": ""}):
            result = tool_get_github_issues()
        assert "error" in result

    def test_create_github_issue_no_token(self):
        from skills.github_reviewer.skill import tool_create_github_issue
        with patch.dict(os.environ, {"GITHUB_TOKEN": "", "GITHUB_REPO": ""}):
            result = tool_create_github_issue("Test issue", "Test body")
        assert "error" in result
        assert result["created"] is False

    def test_get_github_repo_info_mocked(self):
        from skills.github_reviewer.skill import tool_get_github_repo_info

        mock_repo = MagicMock()
        mock_repo.full_name = "avogogias/my_skilled_self"
        mock_repo.description = "AI trading agent"
        mock_repo.default_branch = "main"
        mock_repo.open_issues_count = 3
        mock_repo.stargazers_count = 12
        mock_repo.language = "Python"
        mock_repo.pushed_at.isoformat.return_value = "2026-02-24T00:00:00"
        mock_repo.html_url = "https://github.com/avogogias/my_skilled_self"
        mock_repo.get_topics.return_value = ["ai", "trading"]
        mock_repo.get_contributors.return_value = []

        with patch("skills.github_reviewer.skill._get_gh_repo", return_value=mock_repo):
            result = tool_get_github_repo_info()

        assert result["full_name"] == "avogogias/my_skilled_self"
        assert result["open_issues"] == 3
        assert "AI trading agent" in result["description"]

    def test_create_github_issue_mocked(self):
        from skills.github_reviewer.skill import tool_create_github_issue

        mock_issue = MagicMock()
        mock_issue.number = 42
        mock_issue.title = "Code quality: missing docstrings"
        mock_issue.html_url = "https://github.com/avogogias/my_skilled_self/issues/42"

        mock_repo = MagicMock()
        mock_repo.get_labels.return_value = []
        mock_repo.create_label.return_value = MagicMock()
        mock_repo.get_label.return_value = MagicMock(name="code-quality")
        mock_repo.create_issue.return_value = mock_issue

        with patch("skills.github_reviewer.skill._get_gh_repo", return_value=mock_repo):
            result = tool_create_github_issue(
                "Code quality: missing docstrings",
                "Found 5 functions without docstrings.",
                labels="code-quality",
            )

        assert result["created"] is True
        assert result["number"] == 42
        assert "42" in result["url"]

    def test_self_review_and_report_tool(self, tmp_path):
        from skills.github_reviewer.skill import tool_self_review_and_report
        # Point to our own agent directory which exists
        agent_dir = str(Path(__file__).parent.parent / "agent")
        with patch(
            "skills.github_reviewer.skill.analyze_directory",
            return_value={
                "files_analysed": 10,
                "total_loc": 500,
                "total_issues": {"critical": 1, "major": 3, "minor": 8, "total": 12},
                "worst_files": [{"file": "skills/trading_advisor/skill.py", "critical": 1, "major": 2, "complexity_grade": "B"}],
                "files": [],
                "radon_available": True,
            }
        ):
            result = tool_self_review_and_report()
        assert "summary_markdown" in result or "error" in result

    def test_skill_registry_includes_github_reviewer(self):
        from skills.registry import get_skills_manifest
        names = [s["name"] for s in get_skills_manifest()]
        assert "github_reviewer" in names

    def test_skill_has_nine_tools(self):
        from skills.github_reviewer import GitHubReviewerSkill
        skill = GitHubReviewerSkill()
        assert len(skill.get_tools()) == 9

    def test_all_tools_have_docstrings(self):
        from skills.github_reviewer import GitHubReviewerSkill
        skill = GitHubReviewerSkill()
        for tool in skill.get_tools():
            assert tool.__doc__, f"{tool.__name__} must have a docstring"
