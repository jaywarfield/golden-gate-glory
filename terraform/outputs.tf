# terraform/outputs.tf
# Mission Veteran AI — outputs from the Orchestrate and Governance instances

# ── watsonx Orchestrate outputs ────────────────────────────────────────────

output "instance_id" {
  description = "ID of the watsonx Orchestrate instance."
  value       = module.watsonx_orchestrate.id
}

output "instance_crn" {
  description = "CRN of the watsonx Orchestrate instance."
  value       = module.watsonx_orchestrate.crn
}

output "instance_guid" {
  description = "GUID of the watsonx Orchestrate instance."
  value       = module.watsonx_orchestrate.guid
}

output "instance_name" {
  description = "Name of the watsonx Orchestrate instance."
  value       = module.watsonx_orchestrate.name
}

output "dashboard_url" {
  description = "Dashboard URL — open this in a browser to access the Orchestrate UI."
  value       = module.watsonx_orchestrate.dashboard_url
}

output "plan_id" {
  description = "Plan ID of the provisioned Orchestrate instance."
  value       = module.watsonx_orchestrate.plan_id
}

output "account_id" {
  description = "IBM Cloud account ID owning the instance."
  value       = module.watsonx_orchestrate.account_id
}

# ── watsonx Governance outputs ─────────────────────────────────────────────

locals {
  governance_guid = (
    var.existing_governance_instance_crn != null
    ? data.ibm_resource_instance.governance_existing[0].guid
    : ibm_resource_instance.governance[0].guid
  )
  governance_crn = (
    var.existing_governance_instance_crn != null
    ? data.ibm_resource_instance.governance_existing[0].crn
    : ibm_resource_instance.governance[0].crn
  )
  governance_id = (
    var.existing_governance_instance_crn != null
    ? data.ibm_resource_instance.governance_existing[0].id
    : ibm_resource_instance.governance[0].id
  )
}

output "governance_instance_guid" {
  description = <<-EOT
    GUID of the watsonx Governance instance.
    Copy this value into your .env file as GOVERNANCE_INSTANCE_GUID,
    then run: make register-governance
  EOT
  value       = local.governance_guid
}

output "governance_instance_crn" {
  description = "CRN of the watsonx Governance instance."
  value       = local.governance_crn
}

output "governance_instance_id" {
  description = "Resource ID of the watsonx Governance instance."
  value       = local.governance_id
}
