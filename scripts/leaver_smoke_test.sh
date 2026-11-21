#!/usr/bin/env bash
# Run one synthetic leaver against the MOCK adapters and require a valid audit chain.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 - <<'PY'
from pathlib import Path
import tempfile

from mcp_server.audit.verify_chain import verify_chain
from mcp_server.config import Settings
from mcp_server.factory import build_service

root = Path(tempfile.mkdtemp(prefix="jml-leaver-"))
service = build_service(Settings.for_lab(root))
email = "taylor.brooks@lab.example"
request = service.run_leaver(email, actor="it-agent@lab.example")
assert request["status"] == "pending_approval", request
assert request["executed"] is False
service.decide(request["approval_id"], "morgan.lee@lab.example", "approve", "it")
done = service.execute(request["approval_id"], actor="operator@lab.example")
assert done["executed"] is True, done
user = service.lookup_user(email, actor="it-agent@lab.example")["user"]
assert user["status"] == "deprovisioned"
google = service.gws.get_user(email)
assert google["status"] == "suspended"
assert google["drive_status"] == "transferred"
status = verify_chain(service.audit.path)
assert status.ok, status.message
print(status.message)
print("leaver smoke test ok")
PY
