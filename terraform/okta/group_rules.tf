resource "okta_group_rule" "dept_engineering" {
  name              = "dept-engineering"
  status            = "ACTIVE"
  group_assignments = [okta_group.dept_engineering.id]
  expression_value  = "user.department == \"Engineering\""
}

resource "okta_group_rule" "dept_clinical_ops" {
  name              = "dept-clinical-ops"
  status            = "ACTIVE"
  group_assignments = [okta_group.dept_clinical_ops.id]
  expression_value  = "user.department == \"Clinical Operations\""
}

resource "okta_group_rule" "dept_it" {
  name              = "dept-it"
  status            = "ACTIVE"
  group_assignments = [okta_group.dept_it.id]
  expression_value  = "user.department == \"IT\""
}

resource "okta_group_rule" "dept_security" {
  name              = "dept-security"
  status            = "ACTIVE"
  group_assignments = [okta_group.dept_security.id]
  expression_value  = "user.department == \"Security\""
}
