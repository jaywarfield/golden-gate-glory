# **Mission Veteran AI** *by G3*

#### Railway

##### What Railway is in this solution

Railway is Option F — the simplest possible path from a local Dockerfile to a live public HTTPS URL with no IBM Cloud account, no CLI plugins, no ibmcloud login, and no Kubernetes YAML. It is the deployment target that requires the least operational overhead, and it carries a specific, well-thought-out role in the project's two-environment strategy described in .github/workflows/pages.yml:

```
    "LIVE DEV → https://<railway-app>.up.railway.app — USE_MOCK=false — start.sh injects API_BASE at container startup using RAILWAY_PUBLIC_DOMAIN (set automatically by Railway)"
```

##### How it works

Railway builds and runs the same Dockerfile used by every other container target. The only Railway-specific integration point is a single environment variable it auto-injects into every container at startup:

```
  RAILWAY_PUBLIC_DOMAIN=golden-gate-glory-production.up.railway.app
```

start.sh detects this variable and derives API_BASE from it:

```
    if [ -z "$API_BASE" ] && [ -n "$RAILWAY_PUBLIC_DOMAIN" ]; then
      API_BASE="https://${RAILWAY_PUBLIC_DOMAIN}"
    fi
```

It then sed-injects window.API_BASE into web/index.html and flips const USE_MOCK = true → const USE_MOCK = false before uvicorn starts. The result: the container serves both the front-end (GET /) and the AI API (POST /api/translate) at the correct public URL, with no manual configuration. Railway just needs three secrets set in its dashboard: WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL — and optionally USAJOBS_API_KEY. Push to main, and it redeploys automatically.

##### Its role in the GitHub Pages ↔ backend coupling

Railway is explicitly named in .github/workflows/pages.yml as the bridge target that unlocks GitHub Pages live mode:

```
  "When Railway is confirmed working: 1. Set API_BASE secret to the Railway URL. 2. Push to main → Pages redeploys with USE_MOCK=false. Testers seamlessly get the live version, zero downtime."
```

The workflow is designed so that Pages runs in USE_MOCK=true (always works, no backend required) until Railway is confirmed healthy — at which point one secret and one git push flips Pages into live mode. Railway provides the cheap, fast-to-stand-up backend that makes the GitHub Pages CDN layer viable.

Railway also handles PORT dynamically: it sets the port as an env var at runtime and start.sh honours it: exec uvicorn src.server:app --host 0.0.0.0 --port "${PORT:-8080}". No hardcoding, no container rebuild required.

##### Railway vs Code Engine vs OpenShift — the honest comparison

| Dimension | Railway |
| :---:     | :---:   |
| Account requirement | Free tier, no credit card for small workloads |
| CLI required | No — git push triggers deploy |
| Image registry | None — Railway builds from the Dockerfile in the repo |
| Env var management | Dashboard UI — set three values, done |
| HTTPS	| Automatic, no cert management |
| Cold start | Warm by default on paid tier; sleeps on free tier |
| IBM Cloud dependency | Zero — works entirely independently |
| Best for | Demos, hackathons, quick external reviewer access |

Railway's key differentiator here is that RAILWAY_PUBLIC_DOMAIN is auto-injected, which means start.sh can resolve the correct public URL at container startup with zero manual configuration. No Code Engine equivalent of this exists — on Code Engine, ALLOWED_ORIGINS and API_BASE must be passed explicitly at deploy time. Railway eliminates that manual step entirely.

The practical value for this project: a judge or external reviewer who does not have an IBM Cloud account can spin up a fully live instance in under ten minutes using only a GitHub account and a Railway free tier. That accessibility matters enormously for a hackathon.

##### IBM Code Engine — the right choice within IBM Cloud

| Dimension | Code Engine |
| :---:     | :---:       |
| Account requirement | IBM Cloud account required |
| CLI required | Yes — ibmcloud ce plugin |
| Image registry | IBM Container Registry (ICR) — private, IAM-controlled |
| Env var management | Injected at deploy time via ibmcloud ce app create/update |
| HTTPS | Automatic — CE assigns a *.us-south.codeengine.appdomain.cloud URL |
| Scale	| min-scale=0 / max-scale=3 — genuinely serverless, billed per request |
| IBM Cloud integration | First-class — same IAM, same resource group as Orchestrate and Governance |
| Best for | IBM-native production, hackathon judging within IBM Cloud, cost-sensitive sustained workloads |

Code Engine's decisive advantage over Railway in this context is IBM Cloud-nativeness. The watsonx Governance audit trail, the IAM-based access control, and the ability to scope ALLOWED_ORIGINS to the GitHub Pages domain are all naturally aligned with the rest of the IBM stack. The image in ICR benefits from the same IAM policy that controls the Orchestrate instance. The Makefile makes Code Engine as easy to operate as Railway — make bridge-deploy handles create-or-update detection, injects all credentials, and prints the URL — while keeping everything within the IBM Cloud boundary.

For a government or defense customer that requires data residency within IBM Cloud regions, Code Engine is the correct production target. Railway is not.

##### Red Hat OpenShift — the enterprise and air-gapped target

| Dimension | OpenShift |
| :---:     | :---:     |
| Account requirement | Cluster access (on-prem, ROKS, or managed) |
| CLI required | Yes — oc |
| Image registry | ICR, Quay, or any internal registry |
| Env var management | OpenShift Secrets + ConfigMaps |
| HTTPS | Routes with optional TLS termination |
| Network policy | Full Kubernetes NetworkPolicy support — can be fully air-gapped |
| IBM Cloud dependency | Optional — can run entirely on-prem or on ROKS |
| Best for | Enterprise clusters, government on-prem, air-gapped environments, organizations that already run OpenShift |

OpenShift's strength is exactly where Railway and Code Engine are weakest: when the workload cannot touch the public internet, when the organization mandates that all container images come from an internal Quay registry, or when the security posture requires a NetworkPolicy that blocks all egress except to watsonx.ai endpoints. Code Engine is IBM Cloud SaaS — it doesn't support air-gapped or private cluster deployment. Railway is a fully external platform. OpenShift covers both on-prem and IBM's managed ROKS (Red Hat OpenShift on IBM Cloud), which means the same oc apply commands work whether the cluster is in a government data center or in us-south.

The GETTING_STARTED.md correctly characterizes OpenShift as "best for enterprise cluster or air-gapped deployment" — that's not hedging, it's precisely accurate.

##### Why all three together is the strongest possible signal

The fact that the solution supports Railway, Code Engine, and OpenShift from the same Dockerfile and the same start.sh entrypoint demonstrates several things simultaneously:

1. Platform neutrality — the application is not architecturally tied to any single host. The bridge server is a standard Python container. The RAILWAY_PUBLIC_DOMAIN / API_BASE abstraction in start.sh means the same image runs on Railway, Code Engine, OpenShift, or locally with no changes.

2. Right tool for the right context — Railway for the reviewer who needs a URL in ten minutes; Code Engine for the IBM Cloud deployment that sits alongside Orchestrate and Governance under the same IAM; OpenShift for the DoD agency or VA hospital that cannot put veteran data on a public SaaS platform.

3. Judges and stakeholders — a government evaluator sees OpenShift and recognizes enterprise readiness. A technical judge sees Code Engine and recognizes IBM Cloud-native integration. An external reviewer sees Railway and can actually test the live product without an IBM Cloud account. Supporting all three means no evaluator is locked out.

4. Production pathway is clear — Railway is the fast demo path; Code Engine is the natural IBM Cloud production path; OpenShift is the path to customers who run managed or on-prem Kubernetes. The solution grows with the deployment context, rather than requiring a rewrite when the context changes.

---

# License

This application is licensed under the Apache License, Version 2.  Separate third-party code objects invoked by this application are licensed by their respective providers pursuant to their own separate licenses.  Contributions are subject to the [Developer Certificate of Origin, Version 1.1](https://developercertificate.org/) and the [Apache License, Version 2](https://www.apache.org/licenses/LICENSE-2.0.txt).
