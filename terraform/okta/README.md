# Okta identity as code

This folder declares synthetic groups, department group rules, two bookmark apps, and a sign-on policy that requires MFA. It uses the `okta/okta` provider with a private-key service app.

The Terraform service app is separate from the runtime help-desk app. Its default scopes manage groups, apps, and policies. They do not include `okta.users.manage`.

`phi-access` is created here and has no group rule. Joiner automation must not grant it.

## Local plan

Pass credentials in the environment. Do not write them into a tfvars file that could be committed.

```bash
export TF_VAR_okta_org_name="dev-yourorg"
export TF_VAR_okta_base_url="okta.com"
export TF_VAR_okta_client_id="..."
export TF_VAR_okta_private_key="$(cat /path/to/terraform-app.pem)"
terraform init
terraform plan
```

Apply is a manual step for a person who holds those credentials. GitHub Actions runs `fmt`, `validate`, and `plan` only, and it skips `plan` when the secrets are absent. The workflow does not call `terraform apply`.

State files and the `.terraform` directory are gitignored.
