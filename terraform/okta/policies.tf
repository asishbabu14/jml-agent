resource "okta_policy_signon" "lab" {
  name        = "jml-lab-signon"
  status      = "ACTIVE"
  description = "Lab sign-on policy for the synthetic tenant. Requires MFA."
}

resource "okta_policy_rule_signon" "require_mfa" {
  policy_id          = okta_policy_signon.lab.id
  name               = "require-mfa"
  status             = "ACTIVE"
  access             = "ALLOW"
  mfa_required       = true
  mfa_prompt         = "SESSION"
  mfa_lifetime       = 15
  session_idle       = 120
  session_lifetime   = 480
  session_persistent = false
}
