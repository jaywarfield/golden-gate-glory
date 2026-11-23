# **Mission Veteran AI** *by G3*

#### Terraform

The terraform directory contains three files that together provision two IBM Cloud service instances as infrastructure-as-code:

| Resource | Terraform construct | What it creates |
| :---:    | :---:               | :---:           |
| watsonx Orchestrate | Module "watsonx_orchestrate" using terraform-ibm-modules/watsonx-orchestrate/ibm v1.2.1 | The agent runtime — the managed service that hosts the Coordinator Agent, all four sub-agent, and the webchat interface |
| watsonx Governance | Resource "ibm_resource_instance" with service = "aiopenscale" | The monitoring instance that runs bias/fairness monitors, model drift detection, content safety, and explainability |

# License

This application is licensed under the Apache License, Version 2.  Separate third-party code objects invoked by this application are licensed by their respective providers pursuant to their own separate licenses.  Contributions are subject to the [Developer Certificate of Origin, Version 1.1](https://developercertificate.org/) and the [Apache License, Version 2](https://www.apache.org/licenses/LICENSE-2.0.txt).

