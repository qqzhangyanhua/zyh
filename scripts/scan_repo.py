#!/usr/bin/env python3
"""Scan a repository and write conservative facts for agent harness docs."""

from __future__ import annotations

from harness.cli import scan_main


if __name__ == "__main__":
    raise SystemExit(scan_main())
