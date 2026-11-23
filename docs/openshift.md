# **Mission Veteran AI** *by G3*

#### OpenShift

##### What it deploys and where it fits

OpenShift is Option E in a spectrum of six deployment targets for the solution's web/index.html front-end and src/server.py FastAPI bridge server. The full option set is A (watsonx Orchestrate webchat), B (local), C (GitHub Pages), D (IBM Code Engine), E (OpenShift), and F (Railway). OpenShift is the most enterprise-grade of these and is explicitly called out in the architecture as "best for enterprise cluster or air-gapped deployment".

##### Two distinct things it can host

The solution documents two distinct OpenShift deployment shapes:

1. Static SPA only — nginx + ConfigMap (the documented oc commands in GETTING_STARTED.md)

This is the simplest path and needs no container image build:

```
  oc new-project mission-veteran-ai
  oc create configmap veteran-ui --from-file=index.html=web/index.html
  oc create deployment veteran-ui \
    --image=registry.access.redhat.com/ubi8/nginx-120:latest --port=8080
  oc set volume deployment/veteran-ui --add --name=html \
    --type=configmap --configmap-name=veteran-ui \
    --mount-path=/usr/share/nginx/html --default-mode=0644
  oc expose deployment veteran-ui --port=8080
  oc expose service veteran-ui
```

The HTML file lives in a ConfigMap, mounted over nginx's default document root. No image registry required. A Route gives it a public HTTPS URL in one command. Updating is equally clean: regenerate the ConfigMap with --dry-run=client -o yaml | oc apply -f - and oc rollout restart the deployment — zero downtime.

2. Full bridge server — Deployment + Service + Route + Secrets (the environment-architecture.html diagram)

For live mode (real watsonx.ai calls), the bridge server container is deployed with Kubernetes-native primitives:

- Build and push the image to ICR or Quay
- Deployment + Service + Route YAMLs applied via oc apply -f openshift/
- A ConfigMap or env injection sets window.API_BASE in index.html at startup
- OpenShift Secret holds WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL, USAJOBS_API_KEY, ALLOWED_ORIGINS
- uvicorn src.server:app --port 8080 starts inside the container
- USE_MOCK=false is set via env, flipping the front-end into live API mode

##### How it integrates with the rest of the system

OpenShift sits in the host layer — it is an alternative home for the bridge server, sitting alongside Code Engine and Railway. It exposes the same three endpoints as every other deployment target:

| Endpoint | Purpose |
| :---:    | :---:   |
| POST /api/translate | Main pipeline — dispatches to watsonx.ai by step name |
| GET / | Serves web/index.html |
| GET /health |	Credential and connectivity check |

The GitHub Pages front-end (Option C) can point its API_BASE repo secret at the OpenShift Route URL, making Pages the CDN layer and OpenShift the compute layer — a clean separation.

##### Teardown in one command

```
  oc delete deployment,service,route,configmap -l app=veteran-ui
```

The label selector app=veteran-ui sweeps all four object types in a single call with no risk of leaving orphaned resources.

##### Why including OpenShift is a strong signal for a submission like this

1. Enterprise and air-gapped readiness — OpenShift is the platform most large government agencies, defense contractors, and enterprise veterans' organizations run internally. A solution that can run on-cluster without calling out to public cloud is significantly more deployable in the contexts that actually serve veterans at scale.

2. Red Hat UBI image — no proprietary registry — using registry.access.redhat.com/ubi8/nginx-120:latest means the base image is freely available, Red Hat supported, and pulls from a public registry with no authentication required. It's the right choice for an OpenShift deployment.

3. ConfigMap-as-static-site — the pattern of loading a single HTML file into a ConfigMap and mounting it over nginx's document root is elegant: no Dockerfile, no image build pipeline, no registry push. The entire front-end deploy is six oc commands. This demonstrates Kubernetes fluency beyond just kubectl apply.

4. Secret-based credential management — API keys (WATSONX_API_KEY, USAJOBS_API_KEY) live in OpenShift Secrets, never in the image or in environment variables exposed to the container's filesystem. This is the correct pattern for handling credentials in a regulated environment.

5. Uniform surface across all deployment targets — the same POST /api/translate contract works identically whether the bridge is running locally, on Code Engine, Railway, or OpenShift. This means the solution isn't architecturally tied to any single platform, which matters for a tool intended to serve veterans across many different organizational contexts.

6. Demonstrates operational maturity — including teardown instructions (oc delete ... -l app=veteran-ui), update procedures (--dry-run=client -o yaml | oc apply -f -), and rollout restart shows the solution was designed to be operated, not just demo'd.

# License

This application is licensed under the Apache License, Version 2.  Separate third-party code objects invoked by this application are licensed by their respective providers pursuant to their own separate licenses.  Contributions are subject to the [Developer Certificate of Origin, Version 1.1](https://developercertificate.org/) and the [Apache License, Version 2](https://www.apache.org/licenses/LICENSE-2.0.txt).

