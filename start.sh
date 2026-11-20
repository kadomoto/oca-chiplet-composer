#!/usr/bin/env bash
# Start the OCA Chiplet Composer server on http://127.0.0.1:${PORT:-8765}.
# Sources the Harness VP toolchain from $OCA_ENV, ./oca-env.sh, or
# ~/opt/src/oca-deps/oca_env.sh, whichever exists first.
cd "$(dirname "$0")"
for f in "${OCA_ENV:-}" ./oca-env.sh "$HOME/opt/src/oca-deps/oca_env.sh"; do
  if [ -n "$f" ] && [ -f "$f" ]; then source "$f"; echo "toolchain env: $f"; break; fi
done
exec python3 -m uvicorn app:app --app-dir backend --host 127.0.0.1 --port "${PORT:-8765}"
