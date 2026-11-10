# **Mission Veteran AI** *by G3*

<p align="center">
  <img src="docs/images/missionveteranlogo1.png" alt="First Image" width="50%" />
</p>

Mission Veteran AI is an AI-powered career chatbot, made with IBM Bob, for veterans and transitioning service members with military computer and IT experience.  Veterans describe their responsibilities and achievements, the chatbot then identifies transferable skills in computer systems, IT support, data analysis, and cybersecurity, and drafts clear, civilian-ready résumé accomplishments, preserving measurable results and allowing veterans to review and approve each statement, helping veterans market their technical experience and improve their opportunities to obtain civilian IT jobs.

<p align="center">
  <img src="docs/images/ibmbobusage.png" alt="First Image" width="85%" />
</p>

| Index | Component | Document | Products Used | IBM Bob Contributions |
| :---: | :---:     | :---:    | :---:         | :---: |
| 1 | Main Agent & Subagents | [Agents](docs/agents.md) | IBM Bob, watsonx Orchestrate | Created coordinator agent & 4 subagents. |
| 2 | Toolkits/Tools | [Tools](docs/tools.md) | IBM Bob, watsonx Orchestrate | Created 7 tools R& repackaged into toolkits. |
| 3 | Guards & Safety | [Guards](docs/guards.md) | IBM Bob, watsonx.governance | Created PII guard (regex) & Content Safety Monitor. |
| 4 | UI Screens | [Screens](docs/screens.md) | IBM Bob | Created 7 screens corresponding to steps. | 
| 5 | Factsheets & Monitors | [Monitors](docs/monitors.md) | IBM Bob, watsonx.governance | Created AI Factsheets & monitors. |
| 6 | Granite & RAG | [RAG](docs/rag.md) | IBM Bob, watsonx Orchestrate | Found 12 RAG sources including SkillsBuild. |
| 7 | Jupyter Notebooks | [Notebooks](docs/notebooks.md) | IBM Bob, watsonx.ai | Created 7 notebooks. |
| 8 | Environments | [Environment](docs/environment.md) | IBM Bob | Created separate build & test environments for parallel use. |
| 9 | Deployment | [Deployment](docs/deployment.md) | IBM Bob, Make, Terraform | Created make files, scripts & Terraform files to easily deploy everything. |
| 10 | Public Hosting | [Hosting](docs/hosting.md) | IBM Bob, GitHub Pages, OpenShift | Created static SPA hosted on GitHub Pages and OpenShift. |
| 11 | Diagrams | [Architecture](docs/architecture.md)<br>[Environment](docs/environment.md) | IBM Bob | Created low-level architecture diagram and environment diagram showing layout of development and test environments. |

---

# License

This application is licensed under the Apache License, Version 2.  Separate third-party code objects invoked by this application are licensed by their respective providers pursuant to their own separate licenses.  Contributions are subject to the [Developer Certificate of Origin, Version 1.1](https://developercertificate.org/) and the [Apache License, Version 2](https://www.apache.org/licenses/LICENSE-2.0.txt).

