#!/usr/bin/env bash
# Print a few non-secret macOS posture facts. Does not upload anything.
# Skips the hardware serial number on purpose.
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "macos_collect_diag: this host is $(uname -s), not macOS. Nothing collected."
  exit 0
fi

echo "product: $(sw_vers -productName) $(sw_vers -productVersion)"
echo "build: $(sw_vers -buildVersion)"
if command -v fdesetup >/dev/null 2>&1; then
  fdesetup status || true
else
  echo "filevault: fdesetup not available"
fi
# Model and OS only. system_profiler hardware output includes a serial, so this
# asks the software data type and then a single model line.
system_profiler SPSoftwareDataType
sysctl -n hw.model 2>/dev/null || true
echo "diag: local output only, not transmitted"
