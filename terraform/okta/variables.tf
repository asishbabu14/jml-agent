variable "okta_org_name" {
  type        = string
  description = "Okta org subdomain, for example dev-12345678. Do not commit a real value."
  default     = ""
}

variable "okta_base_url" {
  type        = string
  description = "okta.com or oktapreview.com."
  default     = "okta.com"
}

variable "okta_client_id" {
  type        = string
  description = "Client id of the Terraform service app. Pass with TF_VAR_okta_client_id."
  sensitive   = true
  default     = ""
}

variable "okta_private_key" {
  type        = string
  description = "PEM private key for the Terraform service app. Pass with TF_VAR_okta_private_key. Do not commit it."
  sensitive   = true
  default     = ""
}

variable "okta_scopes" {
  type        = set(string)
  description = "Scopes for the Terraform service app. User lifecycle scopes are intentionally absent."
  default = [
    "okta.groups.read",
    "okta.groups.manage",
    "okta.apps.read",
    "okta.apps.manage",
    "okta.policies.read",
    "okta.policies.manage",
  ]
}
