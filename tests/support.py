"""Shared test helpers."""

from pathlib import Path


def find_course_root(project_root: Path) -> Path:
    """Locate the course workspace containing the PPTX, even from a git worktree."""
    for candidate in project_root.parents:
        if (candidate / "Week 13-15.pptx").exists():
            return candidate
    return project_root.parent
