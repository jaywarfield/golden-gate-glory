# **Mission Veteran AI** *by G3*

#### GitHub Pages

##### What GitHub Pages is

GitHub Pages is Option C — a static CDN deployment of web/index.html that is triggered automatically on every git push origin main that touches web/** or .github/workflows/pages.yml. It publishes the front-end to https://<user>.github.io/golden-gate-glory with no server runtime, no container, and no IBM Cloud account required. The workflow is defined in .github/workflows/pages.yml and uses three official GitHub Actions: actions/checkout@v4, actions/upload-pages-artifact@v3, and actions/deploy-pages@v4.

##### How it works technically

The workflow is scoped to front-end changes only:

```
  on:
    push:
      branches: ["main"]
      paths:
        - "web/**"
        - ".github/workflows/pages.yml"
```

Pushing Python toolkit changes, Terraform files, agent YAML, or notebooks does not trigger a Pages redeploy. Only changes to the front-end (web/) or the workflow definition itself fire the pipeline. This keeps CI costs at zero for the overwhelming majority of commits.

API_BASE injection at build time:

The core mechanism is a sed injection step that runs during the GitHub Actions job:
```
  if [ -n "$API_BASE" ]; then
      # inject window.API_BASE into the HTML
      sed -i "s|</head>|<script>window.API_BASE='${API_BASE}';</script></head>|" _site/index.html
      # flip to live mode
      sed -i "s|const USE_MOCK = true;.*|const USE_MOCK = false; // live mode via bridge server|" _site/index.html
  else
      # no backend configured — stay in mock mode
      sed -i "s|const USE_MOCK = true;.*|const USE_MOCK = true; // no bridge configured|" _site/index.html
  fi
```

The API_BASE value comes from a GitHub repository secret (Settings → Secrets → Actions). If the secret is absent, the deployment falls back to USE_MOCK=true automatically — the page always deploys successfully, the UI always works. There is no failure mode where GitHub Pages returns a broken page.

make pages-secret closes the deployment loop:

After running make bridge-deploy (Code Engine), the developer runs make pages-secret. This target queries the deployed Code Engine app URL and prints the exact instructions — including the direct GitHub settings URL — to register it as the API_BASE secret:

```
  Bridge URL detected: https://mission-veteran-ai-bridge.us-south.codeengine.appdomain.cloud

  Add this secret to your GitHub repository:
    Repo: https://github.com/jaywarfield/golden-gate-glory/settings/secrets/actions/new
    Name:  API_BASE
    Value: https://mission-veteran-ai-bridge.us-south.codeengine.appdomain.cloud

  After setting the secret, push to main to redeploy Pages:
    git push origin main
```
The ALLOWED_ORIGINS value set during make bridge-deploy is derived from the GitHub repo owner:

```
  ALLOWED_ORIGINS="https://$(shell echo $(GITHUB_REPO) | cut -d/ -f1).github.io"
```

This locks the Code Engine bridge's CORS policy to the Pages domain, so the bridge will only accept requests from that specific Pages URL. Pages and Code Engine are configured as a matched pair.

##### The two-environment strategy Pages anchors

The .github/workflows/pages.yml header documents the design intent explicitly:

```
  TESTERS  →  https://<user>.github.io/golden-gate-glory   (this workflow)
              USE_MOCK=true — always works, no backend required

  LIVE DEV →  https://<railway-app>.up.railway.app          (Railway)
              USE_MOCK=false — start.sh injects API_BASE at container startup
```

Pages is the always-on, zero-maintenance tester URL. Railway (or Code Engine) is the live backend that Pages upgrades to once confirmed working. The upgrade path requires no code changes and no redeployment of the front-end code — just setting a GitHub secret and pushing to main. When the secret is removed (or the bridge is taken down), Pages automatically reverts to mock mode on the next push.

This means Pages serves two distinct audiences simultaneously depending on whether API_BASE is set:

| API_BASE secret | Pages behavior | Audience |
| :---:           | :---:          | :---:    |
| Not set | USE_MOCK=true — always works | Early testers, reviewers, competition judges without an IBM Cloud account |
| Set to Code Engine or Railway URL | USE_MOCK=false — real watsonx.ai calls | Live testers, demos, production review |

The concurrency guard

```
  concurrency:
    group: "pages"
    cancel-in-progress: true
```

If two pushes land close together, the second run cancels the first's deployment rather than queuing behind it. The final commit wins, the intermediate one is discarded. This prevents a stale intermediate deployment from ever becoming the live Pages version.

##### Why Option C is exactly the right choice to include

1. It is permanently accessible without any infrastructure running. Code Engine costs nothing at zero scale, but it still has a cold start. Railway's free tier sleeps. GitHub Pages has no cold start, no sleep, no cost, and no scale ceiling for a static file — it's served from GitHub's CDN to every visitor, instantly, as long as the repository exists. The mock-mode Pages URL never goes down.

2. It provides a URL judges can click without setup. A hackathon judge with no IBM Cloud account, no watsonx.ai credentials, and no Docker installation can open https://jaywarfield.github.io/golden-gate-glory and immediately interact with all seven steps of the veteran career pipeline. The mock data is detailed enough that the solution's full capability is evident. This is the single most important accessibility decision in the deployment strategy.

3. git push is the deployment command. There is no separate deploy step, no CLI to authenticate, no container to build. The moment a front-end change is merged to main, Pages redeploys automatically. The developer workflow for a front-end update is: edit → commit → push. For a team of three working in a competition window, this matters.

4. It demonstrates CI/CD discipline. The Pages workflow uses path filtering, concurrency cancellation, official versioned Actions, and a build step that modifies the artifact (not the source) before publishing. These are production-quality CI/CD patterns, not the minimal git push integration most static sites use.

5. The CDN + bridge split is architecturally correct. Static assets (HTML, inline CSS, inline JS) have different lifecycle, caching, and cost characteristics than dynamic API responses. Serving the front-end from GitHub's CDN and the AI backend from Code Engine or Railway is the right separation — it means the CDN handles all GET traffic at zero marginal cost, and the bridge only pays for compute when a veteran actually runs the pipeline.

6. The mock → live upgrade path is zero-downtime. Setting the API_BASE secret and pushing to main triggers a Pages rebuild that takes roughly 60 seconds. During those 60 seconds, the previous version (mock mode) is still live. The cutover to live mode is atomic — there is no window where the page returns an error or a broken experience.

---

# License

This application is licensed under the Apache License, Version 2.  Separate third-party code objects invoked by this application are licensed by their respective providers pursuant to their own separate licenses.  Contributions are subject to the [Developer Certificate of Origin, Version 1.1](https://developercertificate.org/) and the [Apache License, Version 2](https://www.apache.org/licenses/LICENSE-2.0.txt).
