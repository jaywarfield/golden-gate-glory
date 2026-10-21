# terraform/outputs.tf
# Mission Veteran AI — outputs from the Orchestrate instance

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
  description = "Plan ID of the provisioned instance."
  value       = module.watsonx_orchestrate.plan_id
}

output "account_id" {
  description = "IBM Cloud account ID owning the instance."
  value       = module.watsonx_orchestrate.account_id
}
