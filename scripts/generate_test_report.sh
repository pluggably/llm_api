#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="$ROOT_DIR/reports"

mkdir -p "$REPORT_DIR"

# Python tests (pytest)
pytest "$ROOT_DIR/tests" --junitxml "$REPORT_DIR/pytest.xml"

# Flutter tests (machine-readable JSON)
(
  cd "$ROOT_DIR/frontend"
  flutter test --machine > "$REPORT_DIR/flutter_test.json"
)

echo "Test reports written to: $REPORT_DIR"
