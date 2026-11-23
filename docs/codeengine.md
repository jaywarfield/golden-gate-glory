# **Mission Veteran AI** *by G3*

#### Code Engine

##### What Code Engine is in this solution

Code Engine is Option D — the primary cloud deployment target for src/server.py, the FastAPI bridge server. It is the most tightly integrated of the hosted deployment options, with its own dedicated block of Makefile targets, configurable variables, and a full create/update/destroy lifecycle wired into the project's toolchain.

##### The image pipeline

The bridge server runs as a Docker container. The pipeline has three discrete steps, each a make target:

| Target | What it does |
| :---:  | :---:        | 
| make bridge-build | docker build -t $(ICR_REGION)/$(ICR_NAMESPACE)/$(IMAGE_NAME):$(IMAGE_TAG) . |
| make bridge-push | ibmcloud cr login && docker push $(IMAGE) — pushes to IBM Container Registry (ICR) |
| make bridge-deploy | Selects or creates the CE project, then ibmcloud ce app create/update with the image |

The image is built from Dockerfile using python:3.11-slim, copies src/, toolkits/, knowledge-bases/, and web/ into the container, and uses start.sh as the entrypoint.

##### What start.sh does at container startup

start.sh runs before uvicorn starts and handles the API_BASE injection problem — the static web/index.html ships with USE_MOCK = true hardcoded, but the production container needs to call its own bridge endpoint. The script:

1. Checks for RAILWAY_PUBLIC_DOMAIN (auto-set by Railway) or an explicit API_BASE env var
2. sed-injects window.API_BASE='<url>' into index.html just before </head>
3. Flips const USE_MOCK = true → const USE_MOCK = false in the same file
4. Execs uvicorn src.server:app --host 0.0.0.0 --port ${PORT:-8080}

This means the container serves both the front-end (GET /) and the AI API (POST /api/translate) from the same process — no separate static host required on Code Engine.

##### The bridge-deploy Makefile target in detail

The Makefile target is production-ready:

```
  CE_MIN_SCALE  ?= 0       # scale to zero when idle — no charge at rest
  CE_MAX_SCALE  ?= 3       # handles burst traffic from a demo or judging panel
  CE_CPU        ?= 0.5
  CE_MEMORY     ?= 1G
  CE_PORT       ?= 8080
```

It detects whether the app already exists (ibmcloud ce app get) and branches to app create or app update accordingly — idempotent on every invocation. Environment variables (WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL, ALLOWED_ORIGINS) are injected directly at deploy time, never baked into the image. After deploy, it calls make bridge-url automatically to print the live URL.

The ALLOWED_ORIGINS value is derived from the GitHub repo name:

```
  ALLOWED_ORIGINS="https://$(shell echo $(GITHUB_REPO) | cut -d/ -f1).github.io"
```

This locks CORS to the GitHub Pages URL so the bridge won't accept requests from arbitrary origins in production.

##### The GitHub Pages ↔ Code Engine coupling

The two are designed to work together as a split architecture:

1. make bridge-deploy deploys the bridge to Code Engine and prints its URL
2. make pages-secret reads that URL and prints the exact instructions to set it as the API_BASE GitHub Actions secret
3. On the next git push origin main, the GitHub Actions workflow injects API_BASE into the Pages build, flipping it into live mode and pointing it at Code Engine

This means Pages serves the HTML cheaply via CDN, and Code Engine provides the compute for watsonx.ai calls — a genuinely clean separation of concerns with no server costs at idle.

##### Operational targets

| Target | Purpose |
| :---:  | :---:   |
| make bridge-logs | ibmcloud ce app logs --follow — tails live container logs |
| make bridge-url | Queries the deployed app's JSON status and prints its public URL |
| make bridge-destroy | Deletes the CE app and the ICR image (requires confirmation) |

All variables are overridable on the command line: make bridge-deploy CE_REGION=eu-de CE_MAX_SCALE=5.

##### Why including Code Engine is a strong signal

1. Scale-to-zero is the right cost model for a hackathon — CE_MIN_SCALE=0 means the container is billed only when it handles requests. During judging and demos it scales up; at 2am it costs nothing. This is the fiscally responsible choice for a competition project.

2. It's fully IBM Cloud-native — the container image lives in ICR, the app runs on Code Engine, credentials come from the IBM Cloud API key. The entire hosting stack stays within the IBM Cloud boundary, which matters for the watsonx Governance audit trail and for any government customer that requires data residency.

3. The Makefile removes the operational complexity — a competitor looking at the solution can run make bridge-build bridge-push bridge-deploy and have a live cloud deployment in under five minutes. No Kubernetes YAML, no manual console clicks, no configuration guesswork.

4. Idempotent deploy — app create/update detection means make bridge-deploy is safe to run repeatedly. CI/CD could call it on every push to main without risk of creating duplicate apps or erroring on first run.

5. The image is minimal and dependency-correct — Dockerfile installs only src/requirements.txt (the bridge's deps) plus openpyxl and pandas, explicitly not the full governance/RAG requirements that only run in watsonx.ai Studio notebooks. A smaller image means faster cold-start and a smaller attack surface.

6. Demonstrates full container discipline — building, tagging with a registry path (us.icr.io/mission-veteran-ai/mission-veteran-ai-bridge:latest), pushing to a private registry, and deploying from that registry is the full enterprise container workflow. It's a materially different level of maturity than docker run locally.

# License

This application is licensed under the Apache License, Version 2.  Separate third-party code objects invoked by this application are licensed by their respective providers pursuant to their own separate licenses.  Contributions are subject to the [Developer Certificate of Origin, Version 1.1](https://developercertificate.org/) and the [Apache License, Version 2](https://www.apache.org/licenses/LICENSE-2.0.txt).

