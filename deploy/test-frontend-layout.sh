#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if ! command -v node >/dev/null; then echo 'Node.js 22+ diperlukan untuk tes unit geometri UI'; exit 2; fi
node --experimental-strip-types --test frontend/tests/*.test.mjs
