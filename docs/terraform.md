# **Mission Veteran AI** *by G3*

#### Terraform

##### What Terraform provisions

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

##### What Terraform does not cover

The IBM provider doesn't yet expose resources for Governance use cases or monitor subscriptions. That gap is documented explicitly in main.tf:

```
    "Use case and monitor registration is handled post-apply by
     python governance/register_factsheets.py"
```

This is an honest, forward-looking design — the Terraform layer handles what the provider supports today, and the Python layer handles the rest, with no pretense that Terraform does everything.

##### Why including Terraform is a strong signal for a submission like this

1. Infrastructure reproducibility — anyone with an IBM Cloud account and an API key can run terraform apply and get an identical environment in minutes. Without it, the submission requires manual UI clicks that are fragile, undocumented, and hard to verify.

2. Separation of concerns — infrastructure lifecycle (create, update, destroy) is decoupled from application logic. terraform destroy cleanly tears down both IBM Cloud instances without touching any application code.

3. Hackathon-safe destroy semantics — the terraform destroy comment in main.tf explicitly notes it "destroys both instances and all agents inside them", which is the correct behavior for cost cleanup after a demo.

4. Demonstrates production-readiness thinking — a solution that provisions its own cloud infrastructure via code is architecturally closer to a real enterprise deployment than one that hardcodes service URLs or requires manual setup. It signals that the team thought beyond the demo.

5. Version-pinned module — version = "1.2.1" on the Orchestrate module means the infrastructure is deterministic. Running terraform apply a month later will not silently pick up a breaking module update.

6. Input validation — variables.tf uses validation blocks on region and plan, so invalid inputs fail fast with a descriptive error rather than propagating into a broken IBM Cloud API call.

---

# License

This application is licensed under the Apache License, Version 2.  Separate third-party code objects invoked by this application are licensed by their respective providers pursuant to their own separate licenses.  Contributions are subject to the [Developer Certificate of Origin, Version 1.1](https://developercertificate.org/) and the [Apache License, Version 2](https://www.apache.org/licenses/LICENSE-2.0.txt).
