resource "okta_app_bookmark" "slack" {
  label  = "Slack (lab bookmark)"
  url    = "https://slack.lab.example"
  status = "ACTIVE"
}

resource "okta_app_bookmark" "notion" {
  label  = "Notion (lab bookmark)"
  url    = "https://notion.lab.example"
  status = "ACTIVE"
}

resource "okta_app_group_assignment" "slack_engineering" {
  app_id   = okta_app_bookmark.slack.id
  group_id = okta_group.dept_engineering.id
}

resource "okta_app_group_assignment" "slack_clinical_ops" {
  app_id   = okta_app_bookmark.slack.id
  group_id = okta_group.dept_clinical_ops.id
}

resource "okta_app_group_assignment" "slack_it" {
  app_id   = okta_app_bookmark.slack.id
  group_id = okta_group.dept_it.id
}

resource "okta_app_group_assignment" "slack_security" {
  app_id   = okta_app_bookmark.slack.id
  group_id = okta_group.dept_security.id
}

resource "okta_app_group_assignment" "notion_engineering" {
  app_id   = okta_app_bookmark.notion.id
  group_id = okta_group.dept_engineering.id
}

resource "okta_app_group_assignment" "notion_it" {
  app_id   = okta_app_bookmark.notion.id
  group_id = okta_group.dept_it.id
}

resource "okta_app_group_assignment" "notion_security" {
  app_id   = okta_app_bookmark.notion.id
  group_id = okta_group.dept_security.id
}
