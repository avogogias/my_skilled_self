"""Skill registry — the single place to register and discover all agent skills.

To add a new skill:
  1. Create a sub-package under skills/ with SKILL_METADATA and get_tools()
  2. Import and add it to REGISTERED_SKILLS below
  3. That's it — the agent picks it up automatically.
"""

from typing import Any, Callable

from skills.chart_generator import ChartGeneratorSkill
from skills.trading_advisor import TradingAdvisorSkill


REGISTERED_SKILLS = [
    TradingAdvisorSkill(),
    ChartGeneratorSkill(),
]


def get_all_tools() -> list[Callable[..., Any]]:
    """Return the flat list of all ADK tool functions from all registered skills."""
    tools = []
    for skill in REGISTERED_SKILLS:
        tools.extend(skill.get_tools())
    return tools


def get_skills_manifest() -> list[dict]:
    """Return metadata for all registered skills (used by the /skills API endpoint)."""
    return [
        {
            "name": skill.metadata.name,
            "description": skill.metadata.description,
            "version": skill.metadata.version,
            "tags": skill.metadata.tags,
            "icon": skill.metadata.icon,
            "tools": [fn.__name__ for fn in skill.get_tools()],
        }
        for skill in REGISTERED_SKILLS
    ]
