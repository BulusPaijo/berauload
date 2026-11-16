#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a
curl --fail --silent --show-error "http://127.0.0.1:${APP_PORT:-8092}/api/health"
echo
echo 'API sehat. Lanjutkan login dan uji import dari browser.'
