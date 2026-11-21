"""Hash-chained audit log.

Import `AuditLog` from `mcp_server.audit.log` and `verify_chain` from
`mcp_server.audit.verify_chain`. Keeping this package init empty lets
`python -m mcp_server.audit.verify_chain` run without a double-import warning.
"""
