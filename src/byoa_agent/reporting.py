from __future__ import annotations

from pathlib import Path


def save_report_draft(project_root: Path, content: str) -> Path:
    """Save an agent-produced Markdown report draft in the reports directory."""
    reports_dir = project_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / "experiment2-draft.md"
    body = content.strip()
    text = "# Experiment 2 BYOA Report Draft\n\n"
    text += body if body else "_The agent did not return report content._"
    text += "\n"
    path.write_text(text, encoding="utf-8")
    return path

