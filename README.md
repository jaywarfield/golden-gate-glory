# **Mission Veteran AI** *by G3*

<p align="center">
  <img src="docs/images/missionveteranqr.png" alt="QR Image" width="75"/>
</p>

<p align="center">
  <img src="docs/images/missionveteranlogo1.png" alt="Logo Image" width="400"/>
</p>

<p>
Mission Veteran AI (by Golden Gate Glory or G3) is an AI-powered career chatbot, made with IBM Bob, for veterans and transitioning service members with military computer and IT experience.  Veterans describe responsibilities and achievements, the chatbot then identifies transferable skills in computer systems, IT support, data analysis, and cybersecurity, and drafts civilian-ready résumé accomplishments, preserving measurable results and allowing veterans to market their technical experience and improve opportunities to obtain civilian jobs.
</p>`

<p align="center">
  <img src="docs/images/ibmbobusage.png" alt="First Image" width="60%" />
</p>

<p align="center">
  <img src="docs/images/architecturecondensed.png" alt="Condensed Image" width="80%"/>
</p>

| Index | IBM Product | Description | Document |
| :---: | :---:       | :---:       | :---: |
| 1 | Bob | Development assistant throughout. | |
| 2 | watsonx Orchestrate | Coordinator agent, four subagents, four toolkits. | [Agents](docs/agents.md), [Tools](docs/tools.md) | 
| 3 | watsonx.governance | Monitoring, Drift detection, Content Safety, Explainability, Audit Trail. | [Guards](docs/guards.md), [Monitors](docs/monitors.md) |
| 4 | watsonx.ai | Model host and REST inference API. |
| 5 | Granite & RAG | Primary LLM and 12 RAG sources. | [RAG](docs/rag.md) |
| 6 | Code Engine | Optional container for FastAPI bridge server. | |
| 7 | OpenShift | Optional container for FastAPI bridge server. | |
| 8 | SkillsBuild | RAG knowledge source for course recommendations. | |
| 9 | Terraform | Agents, Toolkits, Governance, deployment targets provisioned with Terraform. | |
| 10 | Jupyter Notebooks | Seven notebooks used for standalone step testing. | [Notebooks](docs/notebooks.md) |

<!--
| Index | Component | Document | Products Used | IBM Bob Contributions |
| :---: | :---:     | :---:    | :---:         | :---: |
| 4 | UI Screens | [Screens](docs/screens.md) | IBM Bob | Created 7 screens corresponding to steps. | 
| 8 | Environments | [Environment](docs/environment.md) | IBM Bob | Created separate build & test environments for parallel use. |
| 9 | Deployment | [Deployment](docs/deployment.md) | IBM Bob, Make, Terraform | Created make files, scripts & Terraform files to easily deploy everything. |
| 10 | Public Hosting | [Hosting](docs/hosting.md) | IBM Bob, GitHub Pages, OpenShift | Created static SPA hosted on GitHub Pages and OpenShift. |
| 11 | Diagrams | [Architecture](docs/architecture.md)<br>[Environment](docs/environment.md) | IBM Bob | Created low-level architecture diagram and environment diagram showing layout of development and test environments. |
-->

---

# License

This application is licensed under the Apache License, Version 2.  Separate third-party code objects invoked by this application are licensed by their respective providers pursuant to their own separate licenses.  Contributions are subject to the [Developer Certificate of Origin, Version 1.1](https://developercertificate.org/) and the [Apache License, Version 2](https://www.apache.org/licenses/LICENSE-2.0.txt).

