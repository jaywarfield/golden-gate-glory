# terraform/variables.tf
# Mission Veteran AI — variable definitions

variable "ibmcloud_api_key" {
  description = "IBM Cloud API key with Editor access on watsonx Orchestrate."
  type        = string
  sensitive   = true
}

variable "region" {
  description = "IBM Cloud region for the Orchestrate instance (e.g. us-south, eu-de, jp-tok)."
  type        = string
  default     = "jp-tok"

  validation {
    condition     = contains(["us-south", "eu-de", "eu-gb", "jp-tok", "au-syd"], var.region)
    error_message = "region must be one of: us-south, eu-de, eu-gb, jp-tok, au-syd."
  }
}

variable "resource_group_name" {
  description = "Name of the IBM Cloud resource group to place the instance in."
  type        = string
}

variable "orchestrate_instance_name" {
  description = "Display name for the watsonx Orchestrate service instance."
  type        = string
  default     = "mission-veteran-ai"
}

variable "plan" {
  description = "Service plan. Options: lite, essentials-agentic-mau, standard-agentic-mau."
  type        = string
  default     = "lite"

  validation {
    condition     = contains(["lite", "essentials-agentic-mau", "standard-agentic-mau"], var.plan)
    error_message = "plan must be one of: lite, essentials-agentic-mau, standard-agentic-mau."
  }
}

variable "resource_tags" {
  description = "Resource tags to apply to the instance (for cost tracking and access management)."
  type        = list(string)
  default     = ["project:mission-veteran-ai", "env:dev"]
}
