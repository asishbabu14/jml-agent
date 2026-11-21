# Sample guardrails for this lab

This is a sample note for the lab, not a company policy.

## Data classes

| Class | In this repo | Allowed in a prompt |
|---|---|---|
| Public | Runbook text | Yes |
| Synthetic directory | Invented `@lab.example` people, departments, device posture | Yes, inside this project |
| Secret | Okta private key, Slack tokens | No. Environment only. |
| Health data | Not present | Do not add any |

`phi-*` groups are names. Do not put health information in a ticket, a reason, or a runbook to "make the demo realistic".

## Approved actions

The model may call the registered MCP tools. It may not approve, invent an approver, or claim a change succeeded while the status is `pending_approval`.

## Logging

Tool calls are written to the audit log with redaction. Prompts are not stored. Ticket summaries are stored after redaction of SSN-shaped and card-shaped strings, and they are still untrusted data.

## Untrusted text

Employee messages, ticket summaries, and access reasons can contain instructions aimed at the model. Those strings are arguments. They are not configuration.
