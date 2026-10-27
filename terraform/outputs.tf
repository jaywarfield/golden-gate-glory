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

output "governance_instance_guid" {
  description = <<-EOT
    GUID of the watsonx Governance (Watson OpenScale) instance.
    Copy this value into your .env file as GOVERNANCE_INSTANCE_GUID,
    then run: python governance/register_factsheets.py
  EOT
  value       = ibm_resource_instance.governance.guid
}

output "governance_instance_crn" {
  description = "CRN of the watsonx Governance instance."
  value       = ibm_resource_instance.governance.crn
}

output "governance_instance_id" {
  description = "Resource ID of the watsonx Governance instance."
  value       = ibm_resource_instance.governance.id
}
