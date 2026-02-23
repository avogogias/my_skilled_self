"""Base skill definition — every skill follows this contract.

Inspired by the HuggingFace skills pattern: each skill is a self-contained
Python module that exposes:
  - SKILL_METADATA  : dict with name, description, version, tags
  - get_tools()     : returns a list of plain Python callables (ADK tools)

Adding a new skill is as simple as:
  1. Create a sub-package under skills/
  2. Implement SKILL_METADATA and get_tools()
  3. Register it in skills/registry.py
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class SkillMetadata:
    name: str
    description: str
    version: str = "1.0.0"
    author: str = "my_skilled_self"
    tags: list[str] = field(default_factory=list)
    icon: str = "🧠"


class BaseSkill(ABC):
    """Abstract base class for all agent skills."""

    metadata: SkillMetadata

    @abstractmethod
    def get_tools(self) -> list[Callable[..., Any]]:
        """Return ADK-compatible tool functions for this skill."""
