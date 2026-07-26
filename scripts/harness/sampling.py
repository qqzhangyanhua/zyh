"""Sampling helpers for repository scanner."""

from __future__ import annotations


def sample_with_buckets(items: list, cap: int, key_fn) -> tuple[list, int, bool]:
    """Proportionally sample up to cap items across key_fn buckets.

    Returns (sampled, total, was_truncated).
    """
    total = len(items)
    if total <= cap:
        return list(items), total, False
    groups: dict[str, list] = {}
    for item in items:
        groups.setdefault(key_fn(item), []).append(item)
    keys = sorted(groups)
    if cap < len(keys):
        return [groups[k][0] for k in keys[:cap]], total, True
    sampled: list = []
    used = 0
    for i, k in enumerate(keys):
        remaining_groups = len(keys) - i
        remaining_cap = cap - used
        alloc = round(len(groups[k]) / total * cap)
        alloc = max(1, min(alloc, len(groups[k]), remaining_cap - remaining_groups + 1))
        sampled.extend(groups[k][:alloc])
        used += alloc
    return sampled, total, True
