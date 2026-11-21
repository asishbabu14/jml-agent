resource "okta_group" "dept_engineering" {
  name        = "dept-engineering"
  description = "Synthetic lab department group for Engineering."
}

resource "okta_group" "dept_clinical_ops" {
  name        = "dept-clinical-ops"
  description = "Synthetic lab department label. No patient or member data."
}

resource "okta_group" "dept_it" {
  name        = "dept-it"
  description = "Synthetic lab department group for IT."
}

resource "okta_group" "dept_security" {
  name        = "dept-security"
  description = "Synthetic lab department group for Security."
}

resource "okta_group" "role_engineer" {
  name        = "role-engineer"
  description = "Synthetic lab role group for engineers."
}

resource "okta_group" "role_it_support" {
  name        = "role-it-support"
  description = "Synthetic lab role group for IT support."
}

resource "okta_group" "role_manager" {
  name        = "role-manager"
  description = "Synthetic lab role group for people managers."
}

resource "okta_group" "app_slack" {
  name        = "app-slack"
  description = "Synthetic lab group for the Slack bookmark app."
}

resource "okta_group" "app_wiki" {
  name        = "app-wiki"
  description = "Synthetic lab group for the wiki bookmark app."
}

resource "okta_group" "phi_access" {
  name        = "phi-access"
  description = "Label only. Not assigned by a group rule. Not a store of health data."
}
