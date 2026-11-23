# **Mission Veteran AI** *by G3*

#### Terraform

The terraform directory contains three files that together provision two IBM Cloud service instances as infrastructure-as-code:

| Resource | Terraform construct | What it creates |
| :---:    | :---:               | :---:           |
| watsonx Orchestrate | Module "watsonx_orchestrate" using terraform-ibm-modules/watsonx-orchestrate/ibm v1.2.1 | The agent runtime — the managed service that hosts the Coordinator Agent, all four sub-agent, and the webchat interface |
| watsonx Governance | Resource "ibm_resource_instance" with service = "aiopenscale" | The monitoring instance that runs bias/fairness monitors, model drift detection, content safety, and explainability |

Both resources are placed in a named IBM Cloud resource group, tagged (project:mission-veteran-ai, env:dev), and scoped to a validated region (us-south, eu-de, jp-tok, etc.).

##### Existing-instance escape hatch

A deliberate design choice for hackathon/shared-environment use: both resources support a existing_*_crn variable. If you already have an Orchestrate or Governance instance (e.g., a trial or shared hackathon account), you set the CRN and Terraform skips creation entirely — it just looks up the existing instance and surfaces its GUID as an output. This means terraform apply is non-destructive in those cases.

```
variable "existing_watsonx_orchestrate_instance_crn" {
  default = null   # null = create new; set CRN = attach to existing
}
```

##### Outputs that feed the application

After terraform apply, outputs.tf surfaces the values the application actually needs:
- dashboard_url — the Orchestrate UI URL for importing agents
- governance_instance_guid — copied into .env as GOVERNANCE_INSTANCE_GUID, then consumed by governance/register_factsheets.py to register AI use cases and monitors

This creates a clean handoff: Terraform owns the infrastructure lifecycle; the Python scripts own the logical configuration on top of it.

# License

This application is licensed under the Apache License, Version 2.  Separate third-party code objects invoked by this application are licensed by their respective providers pursuant to their own separate licenses.  Contributions are subject to the [Developer Certificate of Origin, Version 1.1](https://developercertificate.org/) and the [Apache License, Version 2](https://www.apache.org/licenses/LICENSE-2.0.txt).

