# terraform/main.tf
# Mission Veteran AI
# Provisions IBM Cloud service instances:
#   1. watsonx Orchestrate  — agent runtime
#   2. watsonx Governance   — AI Factsheets, bias/drift/safety monitors
#
# Module: terraform-ibm-modules/watsonx-orchestrate/ibm
# Registry: https://registry.terraform.io/modules/terraform-ibm-modules/watsonx-orchestrate/ibm/latest
# Source:   https://github.com/terraform-ibm-modules/terraform-ibm-watsonx-orchestrate
#
# NOTE: The IBM Terraform provider does not yet expose native resources for
# Governance use cases or monitor subscriptions. This layer provisions the
# Governance SERVICE INSTANCE only. Use case and monitor registration is
# handled post-apply by:
#   python governance/register_factsheets.py
#
# Usage:
#   terraform init
#   terraform plan
#   terraform apply
#   terraform output governance_instance_guid   ← copy into .env
#   terraform destroy   ← destroys both instances and all agents inside them

terraform {
  required_version = ">= 1.9.0"

  required_providers {
    ibm = {
      source  = "IBM-Cloud/ibm"
      version = ">= 1.79.0, < 3.0.0"
    }
  }
}

provider "ibm" {
  ibmcloud_api_key = var.ibmcloud_api_key
  region           = var.region
}

# ── Data source: resolve resource group name → ID ──────────────────────────
data "ibm_resource_group" "group" {
  name = var.resource_group_name
}

# ── watsonx Orchestrate instance ───────────────────────────────────────────
module "watsonx_orchestrate" {
  source  = "terraform-ibm-modules/watsonx-orchestrate/ibm"
  version = "1.2.1" # pin to latest stable; update deliberately

  watsonx_orchestrate_name = var.orchestrate_instance_name
  region                   = var.region
  plan                     = var.plan
  resource_group_id        = data.ibm_resource_group.group.id
  resource_tags            = var.resource_tags
}

# ── watsonx Governance (Watson OpenScale) instance ─────────────────────────
# Provisions the service instance and captures its GUID as a Terraform output.
# The IBM provider does not yet support use case / monitor subscription
# resources — those are registered post-apply via register_factsheets.py.
resource "ibm_resource_instance" "governance" {
  name              = var.governance_instance_name
  service           = "aiopenscale"
  plan              = var.governance_plan
  location          = var.region
  resource_group_id = data.ibm_resource_group.group.id
  tags              = var.resource_tags
}
