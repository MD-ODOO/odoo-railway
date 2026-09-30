#!/bin/bash
set -euo pipefail

echo "[kiiraaye] schema patch + module upgrades"
python3 /usr/local/bin/kiiraaye_schema_patch.py
