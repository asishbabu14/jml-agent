# Security

This is a personal lab. Do not point it at a production tenant, and do not load real employee or patient data into it.

## Reporting

This repository has no production deployment and no bounty. If you find a defect in the policy gate, the approval check, or the audit chain, open a GitHub issue. Please do not include real secrets or real personal data in the report.

## Secrets

- Commit `.env.example` only, with empty values.
- Okta keys stay in `OKTA_PRIVATE_KEY_PATH` or `TF_VAR_okta_private_key`.
- CI runs gitleaks. Tests also fail if a PEM private key is committed.
- The live Okta client uses private-key JWT and does not read an SSWS token.

## Defaults

- Mock adapters when Okta variables are unset.
- Refuse to start when only some Okta variables are set.
- Read-only Okta scopes when a live process does not set `OKTA_SCOPES`.
- Deny for any tool missing from `policy.yaml`.
- The model cannot approve or execute.

## Audit

Verify a log with:

```bash
python -m mcp_server.audit.verify_chain --audit path/to/audit.jsonl
```
