# terraform/main.tf
# Mission Veteran AI
# Provisions the watsonx Orchestrate service instance on IBM Cloud.
#
# Module: terraform-ibm-modules/watsonx-orchestrate/ibm
# Registry: https://registry.terraform.io/modules/terraform-ibm-modules/watsonx-orchestrate/ibm/latest
# Source:   https://github.com/terraform-ibm-modules/terraform-ibm-watsonx-orchestrate
#
# This layer owns the SERVICE INSTANCE only.
# Agent/toolkit/connection deployment is handled by deploy.sh (via Makefile).
#
# Usage:
#   terraform init
#   terraform plan
#   terraform apply
#   terraform destroy   ← destroys instance + all agents inside it

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
