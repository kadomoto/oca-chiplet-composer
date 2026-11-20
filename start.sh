#!/usr/bin/env bash
# Start the OCA Chiplet Composer server. Sources the VP toolchain env if present.
cd "$(dirname "$0")"
[ -f "$HOME/opt/src/oca-deps/oca_env.sh" ] && source "$HOME/opt/src/oca-deps/oca_env.sh"
exec python3 -m uvicorn app:app --app-dir backend --host 127.0.0.1 --port "${PORT:-8765}"
