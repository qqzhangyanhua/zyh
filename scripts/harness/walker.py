"""Filesystem traversal helpers for repository scanning."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .rules import SKIP_DIR_PREFIXES, SKIP_DIRS


@dataclass(frozen=True)
class WalkResult:
    files: list[Path]
    ignored_top_dirs: list[str]
    submodules: list[dict[str, str]]


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def should_skip_dir(path: Path) -> bool:
    return _skip_dir_name(path.name)


def walk_repo(root: Path, limit: int) -> WalkResult:
    if _is_git_repo(root):
        submodules = _git_submodules(root)
        return WalkResult(
            files=_git_files(root, limit, {item["path"] for item in submodules}),
            ignored_top_dirs=_git_ignored_top_dirs(root),
            submodules=submodules,
        )
    return WalkResult(files=_os_walk_files(root, limit), ignored_top_dirs=[], submodules=[])


def top_level(root: Path) -> dict[str, list[str]]:
    dirs: list[str] = []
    files: list[str] = []
    for child in sorted(root.iterdir(), key=lambda p: p.name):
        if _skip_dir_name(child.name):
            continue
        if child.is_dir():
            dirs.append(child.name)
        else:
            files.append(child.name)
    return {"directories": dirs, "files": files}


def _skip_dir_name(name: str) -> bool:
    return name in SKIP_DIRS or any(name.startswith(prefix) for prefix in SKIP_DIR_PREFIXES)


def _os_walk_files(root: Path, limit: int) -> list[Path]:
    files: list[Path] = []
    for current, dirs, names in os.walk(root):
        current_path = Path(current)
        dirs[:] = sorted(d for d in dirs if not _skip_dir_name(d))
        for name in sorted(names):
            path = current_path / name
            files.append(path)
            if len(files) >= limit:
                return files
    return files


def _is_git_repo(root: Path) -> bool:
    if (root / ".git").exists():
        return True
    result = _run_git(root, "rev-parse", "--show-toplevel")
    return result.returncode == 0


def _git_files(root: Path, limit: int, submodule_paths: set[str]) -> list[Path]:
    result = _run_git(
        root,
        "ls-files",
        "-z",
        "--cached",
        "--others",
        "--exclude-standard",
        "--deduplicate",
    )
    if result.returncode != 0:
        return _os_walk_files(root, limit)
    paths: list[Path] = []
    for raw_path in result.stdout.split("\0"):
        if not raw_path or raw_path in submodule_paths:
            continue
        paths.append(root / raw_path)
        if len(paths) >= limit:
            return paths
    return paths


def _git_ignored_top_dirs(root: Path) -> list[str]:
    result = _run_git(root, "ls-files", "--others", "--ignored", "--exclude-standard")
    if result.returncode != 0:
        return []
    ignored: set[str] = set()
    for raw_path in result.stdout.splitlines():
        if not raw_path or "/" not in raw_path:
            continue
        ignored.add(raw_path.split("/", 1)[0])
    return sorted(ignored - {".agent"})


def _git_submodules(root: Path) -> list[dict[str, str]]:
    result = _run_git(root, "submodule", "status")
    if result.returncode != 0:
        return []
    submodules: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        parts = line.strip().split()
        if len(parts) < 2:
            continue
        submodules.append({"path": parts[1]})
    return submodules


def _run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
