# **Mission Veteran AI** *by G3*

#### Local

##### What Local is in this solution

Option B is the local development and no-cloud-required execution path for the web/index.html front-end and src/server.py FastAPI bridge server. It is the mode used by all three team members during active development, and it is the first path any new contributor follows when setting up the project. The architecture label for it in mission-veteran-ai-architecture.html says it precisely: "Set WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL in .env · run python src/server.py · open web/index.html in browser · USE_MOCK=false · no cloud, no container required."

There is no container image to build, no IBM Cloud CLI to authenticate, no Kubernetes cluster, and no Railway account. If you have Python and an IBM Cloud API key, Option B works.

##### Two distinct local sub-modes

Option B actually covers two operating modes, each with its own make target:

1. make serve — pure static mock mode, no backend at all


```
python3 -m http.server 8080 --directory web
```

This serves web/index.html directly from Python's stdlib HTTP server. No server.py, no credentials, no network calls. The front-end's USE_MOCK flag is true, so every pipeline step returns pre-built mock responses with realistic simulated latency (await delay(1200–1800ms)). The entire seven-screen veteran career pipeline runs interactively — bullet translation, skill mapping, gap analysis, résumé draft with EVIDENCED/INFERRED/MISSING tags, export gate — entirely in-browser from static data. No IBM Cloud account needed. No watsonx.ai credits consumed.

2. make bridge-run / make bridge-run-live — local live server

```
# bridge-run: uvicorn with hot-reload, USE_MOCK=false in browser, real AI calls
uvicorn src.server:app --reload --port 8080

# bridge-run-live: simulates Railway locally — start.sh injects API_BASE into index.html
API_BASE=http://localhost:8080 sh start.sh
```

make bridge-run starts the FastAPI bridge with --reload (source changes are picked up without a restart), and the browser's const API_BASE = window.API_BASE || '' resolves to same-origin, so fetch('/api/translate') calls the local server. make bridge-run-live goes one step further and runs start.sh with an explicit API_BASE=http://localhost:8080, which sed-injects window.API_BASE into web/index.html and flips USE_MOCK to false — identically to what happens inside the Railway and Code Engine containers — so the local environment exactly replicates the production container behavior.

The bridge-run target explicitly warns if WATSONX_API_KEY is unset: "⚠ WATSONX_API_KEY not set — AI calls will fail. Check your .env file." bridge-run-live goes further and exits with a non-zero code if WATSONX_API_KEY is absent, since live mode without credentials is meaningless.

##### The .env file and credential loading

The project ships a .env.example file. To activate local live mode, the developer copies it to .env and fills in three values:

```
  WATSONX_API_KEY=<ibm-cloud-api-key>
  WATSONX_PROJECT_ID=<watsonx-ai-project-id>
  WATSONX_URL=https://us-south.ml.cloud.ibm.com   # default Dallas
``

Optionally:
``
  USAJOBS_API_KEY=<opm-api-key>           # enables live federal job search
  USAJOBS_USER_AGENT=<your-email>
  GOVERNANCE_INSTANCE_GUID=<guid>         # enables watsonx Governance logging
  GROQ_API_KEY=<groq-key>                 # enables Groq fallback
```

The .env file is in .gitignore — credentials never reach the repository. toolkits/shared/_common.py loads credentials with os.environ.get(), falling back gracefully so mock mode works without any env file at all.

##### How the USE_MOCK / API_BASE logic works in index.html

The front-end is designed around a single conditional branch per pipeline step:

```
  const API_BASE = window.API_BASE || '';   // empty = same-origin (local)
  
  if (USE_MOCK) {
      result = mockTranslateBullet(bullet, role);   // in-browser mock
  } else {
      result = await apiCall({ step: 'translate_resume', ... });   // real POST /api/translate
  }
```

In make serve mode: USE_MOCK = true, no network call is made, mock data is returned immediately.

In make bridge-run mode: USE_MOCK = false, API_BASE = '', fetch('/api/translate') calls the local uvicorn process.

In make bridge-run-live mode: USE_MOCK = false, API_BASE = 'http://localhost:8080', identical to Railway.

The mock data layer is not a stub returning empty objects — it returns structured, realistic responses: plausible civilian bullet translations, skill inventories with evidence quotes, gap analysis with coverage percentages, full tagged résumé sections with EVIDENCED/INFERRED/MISSING distributions. This means the front-end can be fully demonstrated, tested, and developed without ever calling watsonx.ai.

##### Why Option B is exactly the right choice to include

1. It is the development environment. Every line of Python in the four toolkit packages was written and tested locally before being pushed to Code Engine or imported into watsonx Orchestrate. make bridge-run --reload with live hot-reload is how the LLM prompts were iterated — change a prompt in translate_accomplishment.py, the server restarts, re-run the step in the browser, see the new output. This tight loop is not possible on a deployed container.

2. make serve makes the project accessible to anyone. A judge, reviewer, teammate, or future contributor with zero IBM Cloud access can clone the repository, run make serve, and immediately interact with the full veteran career pipeline. The mock responses are realistic enough to understand what the tool does and how the EVIDENCED/INFERRED/MISSING tagging system works. The barrier to evaluation is python3 -m http.server — that's it.

3. It validates that no server-side logic leaks into the front-end. The fact that the entire UI works identically in both mock mode (no server) and live mode (real watsonx.ai) proves that the front-end is a pure view layer. Business logic lives in server.py and the toolkit packages. This separation matters for maintainability, testability, and security.

4. make bridge-run-live closes the gap between local and production. Running start.sh locally with API_BASE=http://localhost:8080 means the developer can verify the exact same startup sequence, sed injection, and USE_MOCK flip that happens in the Railway and Code Engine containers — without needing to push an image. Environment-specific bugs are caught before they reach a deployed container.

5. It documents the credential requirements precisely. The bridge-run warning on missing WATSONX_API_KEY, the bridge-run-live hard exit, and the .env.example file together form a self-documenting credential contract. Any new team member knows exactly what secrets are required, where to get them (from GETTING_STARTED.md), and what will happen without them. That explicitness carries over into the Code Engine, OpenShift, and Railway deployments — they all use the same variable names.

---

# License

This application is licensed under the Apache License, Version 2.  Separate third-party code objects invoked by this application are licensed by their respective providers pursuant to their own separate licenses.  Contributions are subject to the [Developer Certificate of Origin, Version 1.1](https://developercertificate.org/) and the [Apache License, Version 2](https://www.apache.org/licenses/LICENSE-2.0.txt).
