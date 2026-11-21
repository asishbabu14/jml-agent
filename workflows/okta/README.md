# Lab stand-ins for Okta Workflows

These JSON files are not exports from an Okta org. This repository ships with no tenant, so there is no `.flopack` and no screenshot of a live flow.

`mcp_server` follows the same step order when it runs a joiner, mover, or leaver. The HR trigger is `hris_mock/employees.csv`, printed by:

```bash
python -m hris_mock.emit_event
```

An Okta Integrator Free Plan includes Workflows and allows a handful of active flows. A person with that org can rebuild these three flows there and keep the approval and the audit log in this service. The flows in this folder do not call Okta.
