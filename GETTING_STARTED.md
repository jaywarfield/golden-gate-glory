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
- Copy `terraform/terraform.tfvars.example` → `terraform/terraform.tfvars` and fill in credentials.
- Run `make all` to provision IBM Cloud instances and import agents to Draft.
- Run `make deploy-live` to also promote Draft to the Live (test) environment.
- Test in UI via the watsonx Orchestrate dashboard URL in your IBM Cloud console.

### Setup IBM Bob
- Go to bob.ibm.com and select Download for your OS.
- Open downloaded file, accept license agreement, and follow prompts.
- Launch IBM Bob application (a standalone IDE integrated with VS Code features).
- Log into IBM Bob with IBMid or SSO.
- Activate Trial or Subscription (such as IBM Lab).
- Configure workspace (clone a Git repository in previous step).

### Reset IBM Bob Workspace
- Remove user folder: /User/.bob
- Remove user folder: /User/.bobide folder
- Remove user library folder: /User/Library/Application Support/IBM Bob
- Remove system library folder: /Library/Application Support/IBM Bob

### Copy IBM Bob Workspace (e.g. Reuse what a colleague has started)
- Copy user folder: /User/.bob
- Copy user folder: /User/.bobide folder
- Copy user library folder: /User/Library/Application Support/IBM Bob
- Copy system library folder: /Library/Application Support/IBM Bob

---

### Setup watsonx Governance

watsonx Governance adds bias monitoring, model drift detection, content safety
(ML-based PII), explainability, and an immutable inference audit trail to all
four agent toolkits.

**Step 1 – Install the Governance client**
```
pip install -r requirements.txt
```
`ibm-aigov-facts-client>=2.0.0` and `pyyaml>=6.0.0` are now included.

**Step 2 – Find your Governance instance GUID**

Retrieve the GUID using the IBM Cloud CLI:
```
ibmcloud login --sso
ibmcloud resource service-instance '<Your Watson OpenScale instance name>'
```
The `GUID` field in the output is your value. The service name in the IBM Cloud resource list is **Watson OpenScale** (service: `aiopenscale`).

**Step 3 – Add Governance secrets to your `.env` file**
```
GOVERNANCE_API_KEY=<your-ibm-cloud-api-key>          # defaults to WATSONX_API_KEY if omitted
GOVERNANCE_INSTANCE_GUID=<guid-from-ibmcloud-cli>
GOVERNANCE_URL=https://aiopenscale.cloud.ibm.com      # default; change for CPD deployments
GOVERNANCE_ENABLED=true                                # set false to disable without removing code
```

**Step 4 – Register AI use cases and monitor subscriptions (run once per environment)**
```
make register-governance
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
Run `make register-governance` again after:
- A planned Granite model version upgrade.
- A quarterly knowledge base refresh (O\*NET, SkillsBuild, SkillBridge).

---

### Make command reference

| Command | What it does |
|---|---|
| `make all` | Provision IBM Cloud instances (Terraform) + import agents to Draft |
| `make init` | `terraform init` — download providers and modules |
| `make plan` | Preview infrastructure changes without applying |
| `make provision` | `terraform apply` — create or update IBM Cloud instances |
| `make deploy` | Import toolkits + agents to Draft (safe — does not touch Live) |
| `make deploy-live` | Import to Draft and immediately promote to Live |
| `make promote` | Promote current Draft snapshot to Live (skip re-import) |
| `make destroy` | `terraform destroy` — remove all instances and agents |
| `make test` | Run unit tests: `pytest tests/ -v --tb=short` (all mocked) |
| `make lint` | Lint toolkit Python files with flake8 |
| `make register-governance` | Register AI Factsheets and monitors (run once after provision) |
| `make help` | List all available targets |

### Additional orchestrate CLI commands (if needed)

- `orchestrate --help`
- `orchestrate env --help`
- `orchestrate agents --help`
- `orchestrate agents list -v`
- `orchestrate agents remove --name my-agent --kind native`
- `orchestrate tools import --file my-file.py -k python`
- `orchestrate knowledge-bases import --file my-kb.yaml`
- `orchestrate agents import --file my-agent.yaml`

---

# License

This application is licensed under the Apache License, Version 2.  Separate third-party code objects invoked by this application are licensed by their respective providers pursuant to their own separate licenses.  Contributions are subject to the [Developer Certificate of Origin, Version 1.1](https://developercertificate.org/) and the [Apache License, Version 2](https://www.apache.org/licenses/LICENSE-2.0.txt).

