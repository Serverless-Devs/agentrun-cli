#!/usr/bin/env bash
# Measure agentrun binary cold-start + warm-start times.
#
# Usage: bash scripts/bench-startup.sh [binary-path]
# Default binary: ./dist/agentrun
#
# Prints per-run `real` time and the median of runs 2..10 (warm runs).

set -euo pipefail

BINARY="${1:-./dist/agentrun}"
if [ ! -x "$BINARY" ]; then
  echo "Binary not found or not executable: $BINARY" >&2
  exit 2
fi

echo "=== Benchmark: $BINARY --help ==="
echo "(run 1 = cold; runs 2..10 = warm)"
echo ""

# Portable high-resolution timer. macOS BSD `date` lacks %N, so use python3
# (required anyway as a build dep). Returns seconds as a float.
now() { python3 -c 'import time; print(time.perf_counter())'; }

TIMES=()
for i in $(seq 1 10); do
  START=$(now)
  "$BINARY" --help >/dev/null
  END=$(now)
  ELAPSED=$(awk "BEGIN{print $END - $START}")
  TIMES+=("$ELAPSED")
  printf "Run %2d: %.3f s\n" "$i" "$ELAPSED"
done

# Stats over runs 2..10 (warm). Report min as well as median: on dev
# machines with on-access AV scanners attached to unsigned binaries the
# scanner adds ~10s to some runs, polluting the median. `min` reflects
# Nuitka's true warm-start cost when the scan is cached; `median` is the
# authoritative figure on clean environments (Linux CI, signed releases).
WARM=("${TIMES[@]:1}")
SORTED=$(printf '%s\n' "${WARM[@]}" | sort -n)
N=$(echo "$SORTED" | wc -l | tr -d ' ')
MID=$(( (N + 1) / 2 ))
MIN=$(echo "$SORTED" | sed -n '1p')
MEDIAN=$(echo "$SORTED" | sed -n "${MID}p")

echo ""
printf "Warm min    (runs 2..10): %.3f s\n" "$MIN"
printf "Warm median (runs 2..10): %.3f s\n" "$MEDIAN"
