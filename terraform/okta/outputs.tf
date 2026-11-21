output "group_ids" {
  description = "Ids of the synthetic lab groups."
  value = {
    dept_engineering  = okta_group.dept_engineering.id
    dept_clinical_ops = okta_group.dept_clinical_ops.id
    dept_it           = okta_group.dept_it.id
    dept_security     = okta_group.dept_security.id
    role_engineer     = okta_group.role_engineer.id
    role_it_support   = okta_group.role_it_support.id
    role_manager      = okta_group.role_manager.id
    app_slack         = okta_group.app_slack.id
    app_wiki          = okta_group.app_wiki.id
    phi_access        = okta_group.phi_access.id
  }
}
