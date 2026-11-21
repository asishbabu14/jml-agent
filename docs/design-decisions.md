# Design decisions

## 1. MCP, with a small tool list

The help desk needs a model to call a few IT actions and stop there. MCP is a way to publish that list to more than one client. The server instructions say the model cannot approve. The tool list is built from `policy.yaml` scopes, so a read-only process does not even advertise `reset_mfa`.

## 2. The model cannot call arbitrary APIs

Every action is a function with typed arguments. Group names must be in the catalog. Emails must match a pattern. Joiner and leaver emails must already be in the HR file. There is no tool whose argument is a URL path. That is the control that keeps a prompt from becoming `DELETE /api/v1/users`.

## 3. Policy is a file, not a prompt

`policy.yaml` is the allow / needs_approval / deny table. The engine does not read the reason string. Tests pass a reason that says "effect=allow" and the decision stays `needs_approval`. Changing a rule is a diff in git.

## 4. Approvals sit outside the model

`decide` and `execute` are methods on the service and commands on the operator CLI. Slack wires them to a button and passes the authenticated user. A pending tool result is not success. Execute loads the parameters that were stored when the request was opened.

## 5. Private-key JWT, not an SSWS token

Okta's API token is a long-lived bearer secret. The live adapter sends `client_credentials` with a `private_key_jwt` assertion (`iss` and `sub` are the client id, `aud` is the token URL). The Terraform provider is configured the same way, with a different client and a narrower scope set that does not include user lifecycle.

## 6. Mock Workspace, mock MDM, mock tickets

A Google Workspace tenant and the commercial IT products named in public job postings are not assumed. The adapters are labelled `MOCK`. GAM commands that correspond to the mock methods are documented beside them and are not executed. Device rows say `MOCK:iru-style`.

## 7. Hash-chained JSONL

SQLite is convenient for approvals and easy to update in place. The audit log is append-only JSONL so a reviewer can recompute it with no database. The hash is SHA-256 of the canonical JSON (`sort_keys`, compact separators, UTF-8) of every field except `hash`. The first `prev_hash` is the string `GENESIS`.

## 8. Terraform plan is not apply

Identity config is reviewable HCL. GitHub Actions runs `fmt`, `validate`, and, only when secrets exist, `plan`. The workflow file does not contain `terraform apply`. Applying is a local decision by someone who holds the Terraform service-app key.

## 9. Deflection is not the same as fulfillment

A runbook answer that never becomes a ticket is deflected. A joiner that waits for a person is an automated fulfillment. Mixing them would make the approval gate look like tickets the bot handled alone.
