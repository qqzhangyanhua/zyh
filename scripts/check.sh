#!/usr/bin/env sh
set -eu

# Single verified entry point for this repo's checks.
# Keep this calling only commands proven to exist and pass here.

echo "Harness check: unittest"
python3 -m unittest tests/test_harness_scripts.py
