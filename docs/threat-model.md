# Threat model

Lab notes for this repository. This is not a penetration test and not a compliance report.

## Assets

- The mock directory and the optional live Okta tenant the operator points at.
- Approver decisions.
- The audit log.
- The private key for the Okta service app, which is never stored in git.

## Actors

- An employee message, treated as untrusted.
- The model, which can call only registered tools and is not an approver.
- An approver on the roster in `policy.yaml`.
- An operator who can run the admin CLI.

## Threats

| STRIDE | Scenario | Mitigation in this repo |
|---|---|---|
| Spoofing | Model says it is Morgan and approves. | `decide` is not an MCP tool. The email must be on the roster for the role it claims. Slack reads the clicker's profile email. |
| Tampering | Someone edits an audit line or deletes one. | SHA-256 over the canonical JSON, `prev_hash` links to the previous line, `seq` must increase by one. `verify_chain` reports the bad line. |
| Repudiation | A change happens with no actor. | Request, decision, and execute are separate lines with actor, approver, tool, and result. |
| Information disclosure | Tool output includes a secret or a health fact. | Allow-listed user and device fields. Redaction of SSN-shaped strings, long card numbers, and bearer tokens. No health fields exist in the fixtures. |
| Denial of service | Not a goal of this lab. | The server is a local stdio process. There is no public listener in mock mode. |
| Elevation | Ticket text says "effect=allow" or names `suspend_user`. | Policy is loaded from YAML. Free text is stored or searched, not evaluated. `phi-*` and `suspend_user` keep their approval rules. |
| Confused deputy | Model calls a destructive tool and treats the reply as success. | The reply says the change has not been made. Execute checks the approval again and re-reads policy, so a later deny still stops the action. |
| Token theft | An SSWS token in a file or a prompt. | The live client builds a short-lived private-key JWT. Errors omit response bodies. Redirects are disabled on the HTTP client. |

## Residual risk

- Okta's `okta.users.manage` scope is broader than "reset MFA". The policy file narrows what this process will call. A stolen key with that scope can still be used outside this process.
- The SQLite approval row is not hash-chained. The JSONL log is the tamper-evident record. An attacker who can write the database and the log can forge both if they also rewrite every later hash. The chain detects a partial edit.
- The Slack adapter trusts Slack's `users_info` email. That is only as strong as the workspace.
- The mock Google "Drive transfer" records a row. It does not prove a real transfer.
