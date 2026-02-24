"""GitHub Reviewer skill — self-improvement through automated code review.

This skill enables the agent to:
  1. Analyse the codebase statically (AST + radon complexity)
  2. Interact with the GitHub repository (issues, PRs, file contents)
  3. Create detailed code-quality issues automatically
  4. Review pull request diffs and provide structured feedback

Skill pattern (HuggingFace-inspired):
  - SKILL_METADATA : describes the skill
  - get_tools()    : returns list of Python functions for the ADK agent

GitHub authentication:
  Set GITHUB_TOKEN in the environment (fine-grained PAT or classic token).
  Set GITHUB_REPO  to "owner/repo" (e.g. "avogogias/my_skilled_self").

The agent can use this skill autonomously to self-review its own code,
create issues with findings, and request human review — a self-improvement loop.
"""

import json
import os
from pathlib import Path
from typing import Optional

from skills.base import BaseSkill, SkillMetadata
from skills.github_reviewer.analyzer import analyze_directory, analyze_file

# PyGitHub — optional, degrade gracefully
try:
    from github import Github, GithubException

    _GH_AVAILABLE = True
except ImportError:
    _GH_AVAILABLE = False


# ── GitHub Client Helper ───────────────────────────────────────────────────────

def _get_gh_repo():
    """Return a PyGitHub Repository object using env credentials.

    Raises:
        RuntimeError: if token or repo env vars are missing, or PyGitHub unavailable.
    """
    if not _GH_AVAILABLE:
        raise RuntimeError("PyGitHub not installed. Run: pip install PyGithub")
    token = os.getenv("GITHUB_TOKEN", "")
    repo_name = os.getenv("GITHUB_REPO", "")
    if not token:
        raise RuntimeError("GITHUB_TOKEN environment variable is not set.")
    if not repo_name:
        raise RuntimeError("GITHUB_REPO environment variable is not set (format: owner/repo).")
    gh = Github(token)
    return gh.get_repo(repo_name)


# ── ADK Tool Functions ─────────────────────────────────────────────────────────

def tool_analyze_python_file(file_path: str) -> dict:
    """Statically analyse a single Python file for code quality issues.

    Uses Python's built-in AST module and radon (cyclomatic complexity,
    maintainability index) to detect:
      - Missing docstrings and type annotations
      - High cyclomatic complexity functions (grades C–F)
      - Low maintainability index
      - Structural summary (classes, functions, imports)

    Args:
        file_path: Absolute path to the .py file to analyse.

    Returns:
        Analysis report: issue list, complexity grades, raw metrics.
    """
    return analyze_file(file_path)


def tool_analyze_codebase(directory: str) -> dict:
    """Analyse all Python files in a directory for code quality.

    Recursively scans the directory, runs static analysis on each .py file,
    and returns an aggregated report highlighting the files with the most
    critical and major issues.

    Args:
        directory: Absolute path to the directory to scan (e.g. /app/agent).

    Returns:
        Aggregated report: total issues by severity, worst files, per-file summaries.
    """
    return analyze_directory(directory)


def tool_get_github_repo_info() -> dict:
    """Get metadata about the configured GitHub repository.

    Reads GITHUB_TOKEN and GITHUB_REPO from environment variables.

    Returns:
        Repository name, description, default branch, open issues count,
        stars, language, last push time, and top contributors.
    """
    try:
        repo = _get_gh_repo()
        contributors = []
        try:
            for c in list(repo.get_contributors())[:5]:
                contributors.append({"login": c.login, "contributions": c.contributions})
        except Exception:
            pass

        return {
            "full_name": repo.full_name,
            "description": repo.description,
            "default_branch": repo.default_branch,
            "open_issues": repo.open_issues_count,
            "stars": repo.stargazers_count,
            "language": repo.language,
            "last_push": repo.pushed_at.isoformat() if repo.pushed_at else None,
            "url": repo.html_url,
            "contributors": contributors,
            "topics": repo.get_topics(),
        }
    except Exception as exc:
        return {"error": str(exc)}


def tool_get_github_issues(state: str = "open", limit: int = 10) -> dict:
    """List GitHub issues on the configured repository.

    Args:
        state: Issue state — 'open', 'closed', or 'all' (default: 'open').
        limit: Maximum number of issues to return (1–30, default: 10).

    Returns:
        List of issues with number, title, labels, creation date, and URL.
    """
    try:
        repo = _get_gh_repo()
        limit = max(1, min(30, limit))
        issues_list = []
        for issue in repo.get_issues(state=state)[:limit]:
            if issue.pull_request:
                continue  # Skip PRs (GitHub API includes them in issues)
            issues_list.append({
                "number": issue.number,
                "title": issue.title,
                "state": issue.state,
                "labels": [l.name for l in issue.labels],
                "created_at": issue.created_at.isoformat(),
                "url": issue.html_url,
                "body_preview": (issue.body or "")[:200],
            })
        return {"issues": issues_list, "count": len(issues_list)}
    except Exception as exc:
        return {"error": str(exc)}


def tool_create_github_issue(
    title: str,
    body: str,
    labels: str = "code-quality",
) -> dict:
    """Create a GitHub issue with code review findings.

    Use this to report code quality issues, bugs, or improvement suggestions
    found during automated analysis. The agent can call this after running
    tool_analyze_codebase to file actionable issues automatically.

    Args:
        title: Issue title (concise, descriptive, max 256 chars).
        body:  Issue body in Markdown. Should include: description, affected files,
               code snippets if relevant, and suggested fix.
        labels: Comma-separated label names to apply (default: 'code-quality').
                Common values: 'bug', 'enhancement', 'code-quality', 'documentation'.

    Returns:
        Created issue number, URL, and title.
    """
    try:
        repo = _get_gh_repo()
        label_names = [l.strip() for l in labels.split(",") if l.strip()]

        # Ensure labels exist (create if missing)
        existing = {l.name for l in repo.get_labels()}
        label_colors = {
            "code-quality": "0075ca",
            "bug": "d73a4a",
            "enhancement": "a2eeef",
            "documentation": "0075ca",
            "automated-review": "e4e669",
        }
        gh_labels = []
        for name in label_names:
            if name not in existing:
                try:
                    color = label_colors.get(name, "ededed")
                    repo.create_label(name=name, color=color)
                except GithubException:
                    pass  # Label may have been created concurrently
            try:
                gh_labels.append(repo.get_label(name))
            except GithubException:
                pass  # Skip if still not found

        issue = repo.create_issue(
            title=title[:256],
            body=body,
            labels=gh_labels,
        )
        return {
            "number": issue.number,
            "title": issue.title,
            "url": issue.html_url,
            "created": True,
        }
    except Exception as exc:
        return {"error": str(exc), "created": False}


def tool_get_pull_requests(state: str = "open", limit: int = 5) -> dict:
    """List pull requests on the configured GitHub repository.

    Args:
        state: PR state — 'open', 'closed', or 'all' (default: 'open').
        limit: Maximum number of PRs to return (1–20, default: 5).

    Returns:
        List of PRs with number, title, author, branch, changed files count, and URL.
    """
    try:
        repo = _get_gh_repo()
        limit = max(1, min(20, limit))
        pr_list = []
        for pr in repo.get_pulls(state=state)[:limit]:
            pr_list.append({
                "number": pr.number,
                "title": pr.title,
                "author": pr.user.login,
                "head_branch": pr.head.ref,
                "base_branch": pr.base.ref,
                "changed_files": pr.changed_files,
                "additions": pr.additions,
                "deletions": pr.deletions,
                "created_at": pr.created_at.isoformat(),
                "url": pr.html_url,
                "draft": pr.draft,
            })
        return {"pull_requests": pr_list, "count": len(pr_list)}
    except Exception as exc:
        return {"error": str(exc)}


def tool_review_pull_request(pr_number: int) -> dict:
    """Analyse the files changed in a pull request for code quality issues.

    Fetches the PR diff, extracts changed Python files, and runs static
    analysis to identify potential issues introduced or modified in the PR.

    Args:
        pr_number: The pull request number to review.

    Returns:
        Per-file analysis of changed Python files, highlighting new issues.
    """
    try:
        repo = _get_gh_repo()
        pr = repo.get_pull(pr_number)
        file_analyses = []

        for pr_file in pr.get_files():
            if not pr_file.filename.endswith(".py"):
                continue

            # Get file content from the PR head commit
            try:
                content = repo.get_contents(
                    pr_file.filename, ref=pr.head.sha
                ).decoded_content.decode("utf-8", errors="replace")

                # Write to a temp file for analysis
                import tempfile
                with tempfile.NamedTemporaryFile(
                    suffix=".py", mode="w", delete=False, encoding="utf-8"
                ) as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name

                try:
                    analysis = analyze_file(tmp_path)
                    analysis["filename"] = pr_file.filename
                    analysis["status"] = pr_file.status  # added/modified/removed
                    analysis["additions"] = pr_file.additions
                    analysis["deletions"] = pr_file.deletions
                    file_analyses.append(analysis)
                finally:
                    os.unlink(tmp_path)

            except Exception as file_exc:
                file_analyses.append({
                    "filename": pr_file.filename,
                    "error": str(file_exc),
                })

        total_issues = sum(
            f.get("issue_count", {}).get("total", 0) for f in file_analyses
        )
        return {
            "pr_number": pr_number,
            "pr_title": pr.title,
            "pr_url": pr.html_url,
            "files_reviewed": len(file_analyses),
            "total_issues_found": total_issues,
            "file_analyses": file_analyses,
        }
    except Exception as exc:
        return {"error": str(exc), "pr_number": pr_number}


def tool_post_pr_review_comment(
    pr_number: int,
    body: str,
    event: str = "COMMENT",
) -> dict:
    """Post a review comment on a GitHub pull request.

    Use this after tool_review_pull_request to share findings with the team.

    Args:
        pr_number: Pull request number.
        body: Review body in Markdown — include findings, suggestions, severity.
        event: Review event — 'COMMENT' (default), 'APPROVE', or 'REQUEST_CHANGES'.

    Returns:
        Review ID and URL if successful.
    """
    try:
        repo = _get_gh_repo()
        pr = repo.get_pull(pr_number)
        review = pr.create_review(body=body, event=event)
        return {
            "review_id": review.id,
            "state": review.state,
            "url": review.html_url,
            "submitted": True,
        }
    except Exception as exc:
        return {"error": str(exc), "submitted": False}


def tool_self_review_and_report() -> dict:
    """Run a full self-review of the agent codebase and return a structured report.

    Analyses all Python files in the agent's skills directory, aggregates
    quality metrics, and returns a report suitable for creating GitHub issues
    or displaying to the user.

    This is the entry point for the self-improvement loop:
    1. Call this tool to get a full codebase quality report
    2. Use tool_create_github_issue to file issues for critical/major findings
    3. The agent (or human) can then address the issues

    Returns:
        Complete code quality report with files, issues, grades, and recommendations.
    """
    # Try to locate the agent directory
    candidate_dirs = [
        "/app/agent",            # Docker container path
        "/home/user/my_skilled_self/agent",  # Dev path
        os.path.join(os.path.dirname(__file__), "..", ".."),  # Relative
    ]

    agent_dir = None
    for d in candidate_dirs:
        p = Path(d)
        if p.exists() and (p / "skills").exists():
            agent_dir = str(p)
            break

    if not agent_dir:
        return {"error": "Could not locate agent directory for self-review."}

    report = analyze_directory(agent_dir)
    report["agent_directory"] = agent_dir

    # Build human-readable summary
    total = report.get("total_issues", {})
    worst = report.get("worst_files", [])

    summary_lines = [
        f"## Self-Review Report",
        f"",
        f"**Files analysed**: {report.get('files_analysed', 0)}",
        f"**Total lines of code**: {report.get('total_loc', 0):,}",
        f"**Critical issues**: {total.get('critical', 0)}",
        f"**Major issues**: {total.get('major', 0)}",
        f"**Minor issues**: {total.get('minor', 0)}",
        f"",
    ]

    if worst:
        summary_lines.append("**Files needing most attention:**")
        for w in worst[:5]:
            summary_lines.append(
                f"- `{w['file']}` — {w['critical']} critical, {w['major']} major "
                f"(complexity: {w.get('complexity_grade', 'N/A')})"
            )

    report["summary_markdown"] = "\n".join(summary_lines)
    return report


# ── Skill Class ────────────────────────────────────────────────────────────────

class GitHubReviewerSkill(BaseSkill):
    metadata = SkillMetadata(
        name="github_reviewer",
        description=(
            "Self-improvement skill: statically analyses Python code quality using "
            "AST and radon (cyclomatic complexity, maintainability index), interacts "
            "with the GitHub API to list issues and PRs, creates detailed code-quality "
            "issues automatically, and reviews pull request diffs. Enables a "
            "self-improvement loop where the agent reviews its own codebase."
        ),
        version="1.0.0",
        tags=["github", "code-review", "static-analysis", "self-improvement", "quality"],
        icon="🔍",
    )

    def get_tools(self):
        return [
            tool_analyze_python_file,
            tool_analyze_codebase,
            tool_self_review_and_report,
            tool_get_github_repo_info,
            tool_get_github_issues,
            tool_create_github_issue,
            tool_get_pull_requests,
            tool_review_pull_request,
            tool_post_pr_review_comment,
        ]
