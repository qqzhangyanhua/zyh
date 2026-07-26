"""Filesystem traversal helpers for repository scanning."""

from __future__ import annotations

import os
from pathlib import Path

from .rules import SKIP_DIRS


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def should_skip_dir(path: Path) -> bool:
    return path.name in SKIP_DIRS


def walk_files(root: Path, limit: int) -> list[Path]:
    files: list[Path] = []
    for current, dirs, names in os.walk(root):
        current_path = Path(current)
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(names):
            path = current_path / name
            files.append(path)
            if len(files) >= limit:
                return files
    return files


def top_level(root: Path) -> dict[str, list[str]]:
    dirs: list[str] = []
    files: list[str] = []
    for child in sorted(root.iterdir(), key=lambda p: p.name):
        if child.name in SKIP_DIRS:
            continue
        if child.is_dir():
            dirs.append(child.name)
        else:
            files.append(child.name)
    return {"directories": dirs, "files": files}
