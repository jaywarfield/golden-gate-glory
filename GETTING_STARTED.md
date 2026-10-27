# **Mission Veteran AI – Help veterans transition into civilian careers.**

### Obtain API Key (refer to lab guide)
- Go to watsonx.ai home page (https://dataplatform.cloud.ibm.com/wx/home?context=wx).
- Scroll down to "Developer access" section.
- Select "Project or deployment space" and select the sandbox.
- Leave "Project ID" and watsonx.ai URL as is (ensure region is Dallas at top right of watsonx).ai home page.
- Select "Create API key" button, enter name and optional description, choose "Disable leaked key" option, and click the Create button.
- Copy and save the API key or download to save the key in a file.

### Setup virtual environment
- python3 -m venv venv
- source venv/bin/activate

### Setup Orchestrate
- pip install pymupdf
- pip install ibm-watsonx-orchestrate
- TBD
- TBD
- Please enter WXO API key:  (cut-and-paste your API Key here)
- Note: Token will need to be reactivated when it expires.

### Setup Mission Veteran AI
- Browse to https://github.com/jaywarfield/golden-gate-glory
- Select Code and Open with GitHub Desktop.
- Execute locally: import-all.sh
- Test in UI

---

### Setup watsonx Governance (Phase 5)

watsonx Governance adds bias monitoring, model drift detection, content safety
(ML-based PII), explainability, and an immutable inference audit trail to all
four agent toolkits.

**Step 1 – Install the Governance client**
```
pip install -r requirements.txt
```
`ibm-aigov-facts-client>=2.0.0` and `pyyaml>=6.0.0` are now included.

**Step 2 – Provision the Governance service instance with Terraform**

The Governance instance is provisioned alongside watsonx Orchestrate.
If you have not run Terraform yet, add the two new variables to your
`terraform/terraform.tfvars` (see `terraform.tfvars.example`) and run:
```
cd terraform
terraform init
terraform apply
```
After apply completes, retrieve the GUID directly from Terraform:
```
terraform output governance_instance_guid
```
If you already ran `terraform apply` before this change, run `terraform apply`
again — it will add only the new Governance instance without touching Orchestrate.

**Step 3 – Add Governance secrets to your `.env` file**
```
GOVERNANCE_API_KEY=<your-ibm-cloud-api-key>          # defaults to WATSONX_API_KEY if omitted
GOVERNANCE_INSTANCE_GUID=<value from terraform output governance_instance_guid>
GOVERNANCE_URL=https://aiopenscale.cloud.ibm.com      # default; change for CPD deployments
GOVERNANCE_ENABLED=true                                # set false to disable without removing code
```

**Step 4 – Register AI use cases and monitor subscriptions (run once per environment)**
```
source venv/bin/activate
python governance/register_factsheets.py
```
The script prints four subscription IDs. Add them to `.env`:
```
GOVERNANCE_SUB_BULLET_TRANSLATOR=<id-from-script>
GOVERNANCE_SUB_SKILL_MAPPER=<id-from-script>
GOVERNANCE_SUB_GAP_ANALYZER=<id-from-script>
GOVERNANCE_SUB_PLAN_BUILDER=<id-from-script>
```

**Step 5 – Deploy agents as normal**
No changes to the agent import or deploy commands are required.
Governance logging is activated automatically at inference time once the
environment variables above are set.

**Step 6 – View dashboards**
- Open your Governance instance in IBM Cloud.
- Navigate to **AI use cases** → select any Mission Veteran AI use case.
- Dashboards show: bias / fairness by service branch and career path,
  model drift over time, content safety alerts, and explainability records.
- To retrieve an explanation for a specific inference:
  ```python
  from ibm_aigov_facts_client import AIGovFactsClient
  client = AIGovFactsClient(api_key=..., instance_guid=..., service_url=...)
  client.get_explanation(record_id="<record_id_from_tool_response>")
  ```

**Re-baselining after updates**
Run `python governance/register_factsheets.py` again after:
- A planned Granite model version upgrade.
- A quarterly knowledge base refresh (O\*NET, SkillsBuild, SkillBridge).

---

Note: The following are additional orchestrate commands if needed.

### View orchestrate help:
- orchestrate –help
- orchestrate env --help
- orchestrate agents –help
- orchestrate agents remove --help
- etc

### Remove agent:
 orchestrate agents remove --name my-agent --kind native

### List agents:
- orchestrate agents list -v

### Import tools:
- orchestrate tools import -f my-file.py -k python

### Import knowledge bases:
- orchestrate knowledge-bases import -f my-kb.yaml

### Import agents:
- orchestrate agents import -f my-agent.yaml

---

# License

This application is licensed under the Apache License, Version 2.  Separate third-party code objects invoked by this application are licensed by their respective providers pursuant to their own separate licenses.  Contributions are subject to the [Developer Certificate of Origin, Version 1.1](https://developercertificate.org/) and the [Apache License, Version 2](https://www.apache.org/licenses/LICENSE-2.0.txt).

