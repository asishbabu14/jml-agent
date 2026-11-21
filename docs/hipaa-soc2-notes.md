# Access, audit, and minimum necessary

This is a lab note about how those ideas show up in the code. It is not a HIPAA assessment, not a SOC 2 report, and not legal advice. The dataset has no patient records, no member records, and no health values. `phi-access` is a group name used to exercise a stricter approval rule.

| Idea | Where it shows up here |
|---|---|
| Minimum necessary | `lookup_user` returns a fixed field list. Secrets and free-form profile keys are dropped. |
| Access control | `policy.yaml` plus Okta scopes. Missing scopes unregister the tool. |
| Unique identity | Approver emails are an explicit roster. The requester cannot approve. |
| Two-person control | `suspend_user`, and any `phi-*` group, need two roles and two people. |
| Audit | Every decision is a hash-chained line: who asked, which tool, the effect, the approver, the result. |
| Workforce clearance | The mock does not prove a background check. The roster is the stand-in for "this person may approve". |
| Data retention | The log is local JSONL. There is no export to a SIEM. |

If this were pointed at a real tenant, the private key, the approver roster, and the scopes would be the first things to review. The mock labels would have to be replaced with real adapters, and this note would still not be an attestation.
