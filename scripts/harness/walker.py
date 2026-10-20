"""Filesystem traversal helpers for repository scanning."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .rules import SKIP_DIR_PREFIXES, SKIP_DIRS

ROOT_BUCKET = "."
_SCANNER_OUTPUT_PREFIX = ".agent/"


@dataclass(frozen=True)
class WalkResult:
    files: list[Path]
    ignored_top_dirs: list[str]
    submodules: list[dict[str, str]]


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def should_skip_dir(path: Path) -> bool:
    return skip_dir_name(path.name)


def skip_dir_name(name: str) -> bool:
    return name in SKIP_DIRS or any(name.startswith(prefix) for prefix in SKIP_DIR_PREFIXES)


def count_files(root: Path) -> dict[str, Any]:
    """Count files without building Path objects. Returns total and per-top-dir counts.

    Root-level files are grouped under ROOT_BUCKET so git and non-git repos report the same shape.
    """
    if _is_git_repo(root):
        return _git_count_files(root)
    return _os_walk_count_files(root)


def proportional_quota(by_top: dict[str, int], limit: int) -> dict[str, int]:
    """Split `limit` across buckets in proportion to their size; the quotas sum to at most `limit`.

    Every non-empty bucket gets at least one slot while slots remain, so a large directory
    cannot starve a small one (for example `src/auth/` next to a huge `apps/`).
    """
    total = sum(by_top.values())
    if total <= 0 or limit <= 0:
        return {key: 0 for key in by_top}
    quota = {key: n * limit // total for key, n in by_top.items()}
    remaining = limit - sum(quota.values())
    for key in sorted(by_top, key=lambda k: (-(by_top[k] * limit % total), k)):
        if remaining <= 0:
            break
        quota[key] += 1
        remaining -= 1
    for key in sorted(by_top, key=lambda k: (by_top[k], k)):
        if quota[key] > 0 or by_top[key] == 0:
            continue
        donor = max(quota, key=lambda d: (quota[d], d))
        if quota[donor] <= 1:
            break
        quota[donor] -= 1
        quota[key] = 1
    return quota


class _StrideSampler:
    """Accept files so each bucket's picks are spread evenly across its listing order,
    not just the alphabetically first `quota` files."""

    def __init__(self, quota: dict[str, int], bucket_totals: dict[str, int]) -> None:
        self._quota = quota
        self._totals = bucket_totals
        self._seen: dict[str, int] = {}
        self._taken: dict[str, int] = {}

    def accept(self, bucket: str) -> bool:
        index = self._seen.get(bucket, 0)
        self._seen[bucket] = index + 1
        quota = self._quota.get(bucket, 0)
        taken = self._taken.get(bucket, 0)
        if taken >= quota:
            return False
        total = max(self._totals.get(bucket, 0), 1)
        if quota < total and (index + 1) * quota // total <= index * quota // total:
            return False
        self._taken[bucket] = taken + 1
        return True


def walk_repo(
    root: Path,
    limit: int,
    quota: dict[str, int] | None = None,
    bucket_totals: dict[str, int] | None = None,
) -> WalkResult:
    sampler = _StrideSampler(quota, bucket_totals or {}) if quota is not None else None
    if _is_git_repo(root):
        submodules = _git_submodules(root)
        return WalkResult(
            files=_git_files(root, limit, {item["path"] for item in submodules}, sampler),
            ignored_top_dirs=_git_ignored_top_dirs(root),
            submodules=submodules,
        )
    return WalkResult(files=_os_walk_files(root, limit, sampler), ignored_top_dirs=[], submodules=[])


def top_level(root: Path) -> dict[str, list[str]]:
    dirs: list[str] = []
    files: list[str] = []
    for child in sorted(root.iterdir(), key=lambda p: p.name):
        if skip_dir_name(child.name):
            continue
        if child.is_dir():
            dirs.append(child.name)
        else:
            files.append(child.name)
    return {"directories": dirs, "files": files}


def _git_bucket(raw_path: str) -> str:
    return raw_path.split("/", 1)[0] if "/" in raw_path else ROOT_BUCKET


def _os_bucket(current: str, root_str: str) -> str:
    if current == root_str:
        return ROOT_BUCKET
    return current[len(root_str) + len(os.sep):].split(os.sep, 1)[0]


def _os_walk_files(root: Path, limit: int, sampler: _StrideSampler | None = None) -> list[Path]:
    files: list[Path] = []
    root_str = str(root)
    for current, dirs, names in os.walk(root):
        current_path = Path(current)
        dirs[:] = sorted(d for d in dirs if not skip_dir_name(d))
        bucket = _os_bucket(current, root_str)
        for name in sorted(names):
            if sampler is not None and not sampler.accept(bucket):
                continue
            files.append(current_path / name)
            if len(files) >= limit:
                return files
    return files


def _git_listing(root: Path) -> list[str] | None:
    result = _run_git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--deduplicate")
    if result.returncode != 0:
        return None
    # The scanner's own output must never feed back into the facts it describes.
    return [p for p in result.stdout.split("\0") if p and not p.startswith(_SCANNER_OUTPUT_PREFIX)]


def _git_count_files(root: Path) -> dict[str, Any]:
    listing = _git_listing(root)
    if listing is None:
        return _os_walk_count_files(root)
    by_top: dict[str, int] = {}
    for raw in listing:
        bucket = _git_bucket(raw)
        by_top[bucket] = by_top.get(bucket, 0) + 1
    return {"total": len(listing), "by_top_dir": by_top}


def _os_walk_count_files(root: Path) -> dict[str, Any]:
    by_top: dict[str, int] = {}
    total = 0
    root_str = str(root)
    for current, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if not skip_dir_name(d))
        count = len(names)
        total += count
        if count:
            bucket = _os_bucket(current, root_str)
            by_top[bucket] = by_top.get(bucket, 0) + count
    return {"total": total, "by_top_dir": by_top}


def _is_git_repo(root: Path) -> bool:
    if (root / ".git").exists():
        return True
    result = _run_git(root, "rev-parse", "--show-toplevel")
    return result.returncode == 0


def _git_files(
    root: Path, limit: int, submodule_paths: set[str], sampler: _StrideSampler | None = None
) -> list[Path]:
    listing = _git_listing(root)
    if listing is None:
        return _os_walk_files(root, limit, sampler)
    paths: list[Path] = []
    for raw_path in listing:
        if raw_path in submodule_paths:
            continue
        if sampler is not None and not sampler.accept(_git_bucket(raw_path)):
            continue
        paths.append(root / raw_path)
        if len(paths) >= limit:
            return paths
    return paths


def _git_ignored_top_dirs(root: Path) -> list[str]:
    # --directory collapses fully ignored trees (node_modules, build output) into one entry.
    result = _run_git(root, "ls-files", "--others", "--ignored", "--exclude-standard", "--directory")
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
    try:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        return subprocess.CompletedProcess(["git", *args], 127, "", str(exc))
