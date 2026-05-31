"""Local runner package that exposes the src package without installation."""

from pathlib import Path

__path__.append(str(Path(__file__).resolve().parents[1] / "src" / "byoa_agent"))

