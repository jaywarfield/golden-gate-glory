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
- `pip install pymupdf`
- `pip install ibm-watsonx-orchestrate`
- `orchestrate env add --name <your-env> --url <your-orchestrate-url>` — find the URL in the IBM Cloud console → Resource list → watsonx Orchestrate → Dashboard URL
- `orchestrate env activate <your-env>` — prompts for your IBM Cloud API key
- Note: Token will need to be reactivated when it expires.

### Setup Mission Veteran AI
- Browse to https://github.com/jaywarfield/golden-gate-glory
- Select Code and Open with GitHub Desktop.
- **(Optional) Provision IBM Cloud instances with Terraform** — skip if using an existing instance:
  - Copy `terraform/terraform.tfvars.example` → `terraform/terraform.tfvars` and fill in credentials
  - `cd terraform && terraform init`
  - `cd terraform && terraform apply`
  - Retrieve outputs: `terraform output` — copy `dashboard_url` for Orchestrate setup above and `governance_instance_guid` for Governance setup below
- Import agents to Draft: `make deploy`
- Promote to Live (test) environment: `make deploy-live`
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
python -m pip install -r requirements.txt
```
`ibm-watson-openscale` and `pyyaml` are included.
Use `python -m pip` (not bare `pip`) to ensure packages install into the correct Python version inside your venv.

**Step 2 – Find your Governance instance GUID**

In the IBM Cloud console:
- Go to **Resource list** → **AI / Machine Learning**
- Click your watsonx Governance instance (e.g. *watsonx-Hackathon GOV*)
- The **GUID** is shown in the right-hand details panel

**Step 3 – Add Governance secrets to your environment**
```
GOVERNANCE_INSTANCE_GUID=<guid-from-resource-list>
GOVERNANCE_API_KEY=<your-ibm-cloud-api-key>          # defaults to WATSONX_API_KEY if omitted
```

**Step 4 – Verify connectivity (run once)**
```
make register-governance
```
The script connects to your instance and lists available data marts and service providers.
Then create AI use cases and attach monitors (bias, drift, content safety, explainability)
via the watsonx.governance UI → AI use cases → Evaluations tab.

**Step 5 – Deploy agents as normal**
No changes to the agent import or deploy commands are required.

**Step 6 – View dashboards**
- Open watsonx.governance in the watsonx.ai UI.
- Navigate to **AI use cases** → select any Mission Veteran AI use case.
- Dashboards show: bias / fairness by service branch and career path,
  model drift over time, content safety alerts, and explainability records.
- Explanations and audit records are accessed via the watsonx.governance UI.

**Re-baselining after updates**
Run `make register-governance` again after:
- A planned Granite model version upgrade.
- A quarterly knowledge base refresh (O\*NET, SkillsBuild, SkillBridge).

---

### Make command reference

`make` is used only for Orchestrate import/deploy steps. Terraform is run directly (see below).

| Command | What it does |
|---|---|
| `make deploy` | Import toolkits + agents to Draft (safe — does not touch Live) |
| `make deploy-live` | Import to Draft and immediately promote to Live |
| `make promote` | Promote current Draft snapshot to Live (skip re-import) |
| `make destroy` | Remove all agents from the Orchestrate instance |
| `make test` | Run unit tests: `pytest tests/ -v --tb=short` (all mocked) |
| `make lint` | Lint toolkit Python files with flake8 |
| `make governance` | Verify watsonx Governance connectivity |
| `make register-governance` | Alias for `make governance` |
| `make help` | List all available targets |

### Terraform command reference

Terraform provisions IBM Cloud infrastructure. Run these directly from the `terraform/` directory — they are not wired into `make`.

```sh
# One-time setup
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# edit terraform/terraform.tfvars with your IBM Cloud credentials

# Download providers and modules
cd terraform && terraform init

# Preview infrastructure changes without applying
cd terraform && terraform plan

# Create or update IBM Cloud instances
cd terraform && terraform apply

# Tear down all provisioned IBM Cloud instances
cd terraform && terraform destroy
```

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

