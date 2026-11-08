# **Mission Veteran AI** *by G3*

#### Industry

AI-Powered Government & Public Service

#### Description

An AI-powered career-transition chatbot for veterans and transitioning service members with military computer and IT experience. Veterans describe their actual responsibilities and achievements in their own words. The chatbot is designed to identify transferable skills in computer systems, IT support, data analysis, and cybersecurity, then draft clear, civilian-ready résumé accomplishments. It aims to preserve measurable results, avoid invented qualifications, and allow veterans to review and approve each statement before use. Our mission is to help veterans market their genuine technical experience and improve their opportunities to obtain civilian IT jobs.

#### Proposition

Veterans deserve to turn their hard-earned military skills into rewarding civilian careers.  Mission Veteran AI transforms their real experience and achievements into powerful, employer-ready résumé statements.  Through guided questions transferable skills are highlighted, military jargon removed, and accuracy preserved without inventing qualifications.  Mission Veteran AI helps veterans stand out, apply confidently, and move closer to getting hired.

#### AI-Use Justification

Without AI a veteran manually translates their military experience into a civilian resume using a generic template and manually guessing at civilian equivalents for MOS/AFSC code, pays a resume writer with no military context, invents plausible-sounding skills, and spends weeks researching O*NET crosswalks, courses, and ATS keyword patterns manually. The output is unverified, inconsistent, and has no accountability trail for what was invented vs what was earned.

With AI the veteran process is automated to translate their military experience into a civilian resume, uses O*NET crosswalk + RAG corpus to produce grounded translations, prompting the model explicitly against the job description’s required/preferred skills, computes coverage percentage and surfaces specific skill gaps in seconds, and tags sentences as EVIDENCED / INFERRED / MISSING so veteran knows exactly what to verify, and the output is grounded, enforcing accountability, and blocking until INFERRED and MISSING tags are resolved.

With Orchestrate Agents specifically, while monolithic LLM calls can produce unverifiable results, with Orchestrate we break the problem into 4 focused agents, specialization with accountability, toolkit containers are stable, connections are credential-scoped, and the coordinator pattern scales.

AI is not better than humans at judgment, but AI is better at consistent, traceable, fast first drafts ready for review.

#### IBM Products Used

- Map veteran technical gaps to IBM SkillsBuild courses
- IBM Bob
- IBM Cloud
- watsonx Orchestrate
- watsonx.governance
- watsonx.ai
- Terraform (IBM / HashiCorp)
- OpenShift (IBM / Red Hat)

#### IBM Bob Uses

- Creating entire implementation with Orchestrate, Governance, watsonx.ai.
- Creating seven UI screens, Coordinator Agent, 4 subagents, LLM usage, and finding and utilizing 12 RAG sources including SkillsBuild.
- Creating entire build/make/terraform process simplifying updating and importing everything to IBM Cloud and promoting to Live when ready.
- Creating separate development and test environments to enable parallel development and testing.
- Creating 7 Jupyter Notebooks to enable exploratory engineering, prototyping, and research.
- Creating static SPA hosted on GitHub Pages for demos, sharing, and hackathon judging.
- Creating static SPA hosted on OpenShift for enterprise cluster, air-gapped, and OpenShift AI integration.
- Creating low-level architecture diagram and environment diagram showing layout of development and test environments.

---

# License

This application is licensed under the Apache License, Version 2.  Separate third-party code objects invoked by this application are licensed by their respective providers pursuant to their own separate licenses.  Contributions are subject to the [Developer Certificate of Origin, Version 1.1](https://developercertificate.org/) and the [Apache License, Version 2](https://www.apache.org/licenses/LICENSE-2.0.txt).

