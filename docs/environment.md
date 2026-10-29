# **Mission Veteran AI** *by G3*

![Environment](images/environment.png)

<!--
<a href="environment.png" target="_blank">
   <img src="images/environment.png"
        alt="Mission Veteran AI Environment Architecture"
        style="width:100%; height:auto;">
</a>
-->

#### Environments

watsonx Orchestrate has two environments inside a single instance:

| Environment | Purpose | Who uses it |
| :---:       | :---:   | :---:       |
| Draft | Development — safe to iterate | Developer |
| Live | Test / tester-facing — immutable until promoted | Tester |

They are completely independent. Importing to Draft never touches Live, and promoting to Live never re-imports — it snapshots Draft as-is.

#### Import to Draft only (development)

```
make deploy
# or directly:
./deploy.sh
```

- Imports all tools, agents → Draft
- Runs governance registration (if GOVERNANCE_INSTANCE_GUID is set)
- Live is not touched

#### Import to Live only (test) — without re-importing to Draft

```
make promote
# or directly:
./deploy.sh --live-only
```

- Promotes the current Draft snapshot → Live
- Skips all tool/agent import steps entirely
- Draft is not touched

#### Governance — Draft vs Live

Governance (watsonx Governance / AI Factsheets) is not environment-scoped in the same way — it tracks inference facts at the tool level regardless of which Orchestrate environment called the tool. Registration is a one-time step per instance:

# Set the GUID first (from terraform output or IBM Cloud console)
export GOVERNANCE_INSTANCE_GUID=$(cd terraform && terraform output -raw governance_instance_guid)

```
# Then register
make governance
# or:
make register-governance   # same thing — it's an alias
```

This registers the AI use cases and monitor subscriptions once. After that, governance logging is automatic at inference time — every tool call logs facts regardless of whether it was called from Draft or Live. No separate governance import is needed per environment.

---

# License

This application is licensed under the Apache License, Version 2.  Separate third-party code objects invoked by this application are licensed by their respective providers pursuant to their own separate licenses.  Contributions are subject to the [Developer Certificate of Origin, Version 1.1](https://developercertificate.org/) and the [Apache License, Version 2](https://www.apache.org/licenses/LICENSE-2.0.txt).

