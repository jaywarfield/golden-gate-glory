<!-- Slide number: 1 -->

# GOLDEN GATE GLORY
Veteran Career
Navigator Agent

PRESENTATION TEAM
Jay Warfield
Technical Lead and
Agent Architecture Lead
Technical presenter
Week 4 Technical Architecture
William
Proposed Pre-Build Architecture
User, UX, veteran perspective
and responsible AI presenter
IBM SkillsBuild AI Experiential Learning Lab
U.S. 2026 Fall Cohort
AI-Powered Government and Public Service
Corrine
Narrative and
presentation-flow lead
Confirmed: brief and presenter roles only. Architecture remains proposed.

### Notes:
Jay opens as technical presenter. William covers user experience, veteran perspective, and responsible AI. Corrine leads narrative and presentation flow. Full title: Golden Gate Glory: Veteran Career Navigator Agent Technical Architecture. This defines a proposed buildable flow, not deployed capabilities.
Source: user-provided architecture brief, 7 October 2026. All technical design details are proposed unless marked Open Decision or Future Backlog. No completed implementation, approved integration, security certification, or measured performance is claimed.

<!-- Slide number: 2 -->

What the Technical System Must Deliver
Proposed architecture. No implementation or approval implied.
Understand the veteran
Build grounded drafts
Keep the user in control
01
Receive selected career-transition information
01
Connect skill suggestions to supporting evidence
01
Identify unsupported claims and gaps
02
Ask adaptive clarification questions
02
Analyze a target job description
02
Create a prioritized action plan
03
Translate military experience into civilian language
03
Generate editable draft career materials
03
Route uncertain or high-risk outputs to human review
MINIMUM END-TO-END FLOW  /  PROPOSED

Input
Interpret
Clarify
Retrieve
Reason
Generate
Verify
Present
Human
Review
User
Agent
Retrieval
Trust Control
Human Review
Solid = required flow   Dashed = optional / future

02
Golden Gate Glory  /  Week 4 Technical Architecture

### Notes:
Jay explains the proposed end-to-end system contract. William emphasizes selected inputs, editable outputs, and user control. Human review follows the applicable review trigger rather than implying every request requires an external reviewer.
Source: user-provided architecture brief, 7 October 2026. All technical design details are proposed unless marked Open Decision or Future Backlog. No completed implementation, approved integration, security certification, or measured performance is claimed.

<!-- Slide number: 3 -->

Coordinated Agent Responsibilities
Proposed: one user-facing Veteran Career Navigator with coordinated internal capabilities.

Veteran Career Navigator Orchestrator
Coordinates session, workflow state, task routing, output combination and presentation

Intake and Clarification
Skills Evidence and Translation
Job Description Intelligence
Collect minimal information.
Ask adaptive follow-up questions.
Map experience to civilian skills.
Retain links to user evidence.
Compare role requirements with
verified experience and gaps.

Career Materials Builder
Action Plan Builder
Quality and Responsible AI Reviewer
Create editable resume bullets
and career-readiness drafts.
Prioritize gaps, resources,
next steps and review actions.
Check claims, jargon, overstatement,
confidence and boundaries.
Capability boundaries are logical. Separate deployed agents are not assumed.
Open Decision, owned by Jay: final number of agents and implementation pattern

03
Golden Gate Glory  /  Week 4 Technical Architecture

### Notes:
Jay owns the final agent count and implementation pattern. The seven roles describe responsibilities, not seven deployed services. An initial implementation could combine capabilities behind one orchestrator if that is the smallest feasible account-supported design. Each capability passes explicit artifacts, not unbounded session access.
Source: user-provided architecture brief, 7 October 2026. All technical design details are proposed unless marked Open Decision or Future Backlog. No completed implementation, approved integration, security certification, or measured performance is claimed.

<!-- Slide number: 4 -->

Clear Roles Prevent Conflicting Outputs
Proposed responsibility contract. Each capability receives only the fields needed for its task.
| Agent or Capability | Receives | Decides | Produces | Cannot Do | Escalation Trigger |
| --- | --- | --- | --- | --- | --- |
| Orchestrator | Consent, state, capability outputs | Next stage and allowed handoff | Combined result, review packet | Override consent or user rejection | Blocked gate or agent conflict |
| Intake and Clarification | Selected experience, open questions | Minimum useful follow-up | Clarified input, unresolved gaps | Request protected or classified data | Sensitive input or missing context |
| Skills Evidence and Translation | Experience and evidence references | Candidate skill and evidence status | Evidence-linked skill suggestions | Invent duties, results or credentials | Unsupported or ambiguous match |
| Job Description Intelligence | Target description, confirmed experience | Requirement match and evidence gaps | Alignment analysis, missing evidence | Make hiring or eligibility decisions | Conflicting or unclear requirement |
| Career Materials Builder | Confirmed skills, alignment findings | Draft wording and organization | Editable bullets and career drafts | Add unconfirmed accomplishments | Unsupported claim or overstatement |
| Action Plan Builder | Gaps, interests, review flags | Priority and next action | Ordered plan and review actions | Guarantee outcomes or official advice | Major decision or resource uncertainty |
| Quality and Responsible AI Reviewer | Drafts, evidence, source metadata | Release, flag or hold | Findings and review reasons | Silently rewrite confirmed facts | Low confidence or boundary violation |
Least necessary access. Explicit inputs and outputs. No invented accomplishments.
User confirmation before downstream reuse. Human escalation for unsupported or high-risk outputs.
PROPOSED TRUST RULES

04
Golden Gate Glory  /  Week 4 Technical Architecture

### Notes:
Jay presents the responsibility matrix as a proposed contract. William highlights least necessary access and confirmation before reuse. Evidence references should point to specific user statements or approved source passages. The quality reviewer can hold an output but cannot convert speculation into a confirmed fact.
Source: user-provided architecture brief, 7 October 2026. All technical design details are proposed unless marked Open Decision or Future Backlog. No completed implementation, approved integration, security certification, or measured performance is claimed.

<!-- Slide number: 5 -->

Proposed Orchestration Flow
Proposed gated sequence. Advance only when applicable gate conditions pass.

1  Consent
2  Start session
3  Collect input
4  Clarify context
Intake and evidence

Consent
confirmed?
Sufficient
evidence?

5  Suggest skills
6  Confirm / edit
     / reject
7  Analyze job
8  Draft materials
Confirm and build

User verification
complete?
Retrieval
grounded?

9  Prioritize plan
10  Audit outputs
11  User review
12  Prepare packet
Audit and handoff

Confidence
acceptable?
Human review
required?
No / unresolved: hold affected work, request correction or route to review. Do not guess.
User
Agent
Retrieval
Trust Control
Human Review
Solid = required flow   Dashed = optional / future

05
Golden Gate Glory  /  Week 4 Technical Architecture

### Notes:
Jay walks through the numbered required sequence. Gates apply before affected downstream actions: consent before intake, sufficient evidence before skill suggestions, user verification before job and draft reuse, retrieval grounding before sourced guidance, and confidence before release. Human-review-required determines packet routing. A negative gate holds affected output and offers clarification, retry, skip or review. External submission is not assumed.
Source: user-provided architecture brief, 7 October 2026. All technical design details are proposed unless marked Open Decision or Future Backlog. No completed implementation, approved integration, security certification, or measured performance is claimed.

<!-- Slide number: 6 -->

From Experience Description to Defensible Recommendation
Proposed explainable workflow. Show user-facing rationale, not hidden chain-of-thought.

User statement
Extract responsibilities,
actions, context,
outcomes
Identify missing
context
Ask targeted
clarification
Propose potential
civilian skill
Link skill to
user evidence

Permit downstream
use
Request user
confirmation
Explain
recommendation
Assign evidence
status
Compare with target-
job requirement
EVIDENCE STATUS  /  PROPOSED

Supported by
User Input
Needs
Clarification
Possible
Match
Unsupported
Human Review
Recommended
A skill label needs an evidence link, an explanation and user confirmation before reuse.

06
Golden Gate Glory  /  Week 4 Technical Architecture

### Notes:
Jay explains the observable reasoning workflow. William stresses that supported by user input means the user supplied supporting information, not that an external authority verified it. Possible Match remains provisional. Unsupported suggestions cannot enter career materials. Explain the evidence and relevant requirement without exposing or inventing hidden model reasoning.
Source: user-provided architecture brief, 7 October 2026. All technical design details are proposed unless marked Open Decision or Future Backlog. No completed implementation, approved integration, security certification, or measured performance is claimed.

<!-- Slide number: 7 -->

Trusted Retrieval and Grounded Guidance
Proposed RAG design. Specific data sources and IBM implementation choices need confirmation.
Find approved evidence
Check and assemble
Respond with boundaries

User or agent query
Relevant passage retrieval
Model-generated response

Query classification
Source-quality check
Source and confidence display

Approved-source search
Context assembly
User or human review

REQUIRED CONTROLS  /  PROPOSED
Approved-source list and source metadata
Relevance threshold and conflict detection
Explicit no-source-found response
No unsupported official guidance
Retrieved facts separate from generated suggestions
Thresholds and confidence method: Open Decision, Jay
Needs Technical and Team Confirmation

07
Golden Gate Glory  /  Week 4 Technical Architecture

### Notes:
Jay describes a proposed retrieval boundary rather than a selected service. Search only an approved-source list once the team confirms it. Preserve source identifier, passage, date where available, and relevance information. If no trustworthy result exists, say so and withhold official guidance. Confidence display is explanatory evidence status, not a calibrated score unless the team validates that method.
Source: user-provided architecture brief, 7 October 2026. All technical design details are proposed unless marked Open Decision or Future Backlog. No completed implementation, approved integration, security certification, or measured performance is claimed.

<!-- Slide number: 8 -->

What Information Moves Through the System
Proposed data contract. Persistence, deletion behavior and access controls require technical validation.

USER INPUTS
SESSION STATE
SYSTEM OUTPUTS
01
Selected experience
01
Completed workflow stage
01
Skills summary
02
Responsibilities and accomplishments
02
Confirmed skills
02
Job-alignment analysis
03
Training
03
Rejected suggestions
03
Draft resume bullets
04
Career interests
04
Evidence status
04
Evidence and skill gaps
05
Target job description
05
Open questions
05
Prioritized action plan
06
Corrections and confirmations
06
Human-review flags
06
Human-review packet

Collect only what is needed. Warn against classified or sensitive information.
Do not request protected characteristics. Allow correction and deletion.
Do not assume persistence beyond the approved prototype design.
PROPOSED PRIVACY RULES

08
Golden Gate Glory  /  Week 4 Technical Architecture

### Notes:
Jay explains artifact boundaries and state transitions. William covers privacy and user correction. The proposed handoff envelope contains stage, selected evidence references, confirmation state, open questions and review flags. Retention duration, storage location, deletion mechanism and implementation of access controls remain open decisions. Rejecting a suggestion removes it from eligible downstream content.
Source: user-provided architecture brief, 7 October 2026. All technical design details are proposed unless marked Open Decision or Future Backlog. No completed implementation, approved integration, security certification, or measured performance is claimed.

<!-- Slide number: 9 -->

Graceful Failure Is Part of the Architecture
Proposed failure policy. Stop unsafe downstream actions and preserve verified work where feasible.
| Failure | Detection | Automated Response | User Message | Escalation |
| --- | --- | --- | --- | --- |
| Missing context | Required field unclear | Hold dependent step, ask | Add detail or skip this item | Unresolved after clarification |
| Unsupported claim | No evidence reference | Block claim from drafts | Please support or remove it | User or career reviewer |
| Ambiguous terminology | Multiple plausible meanings | Ask for plain-language context | What did this term mean? | Career reviewer if unresolved |
| Retrieval timeout or failure | Request error or timeout | Bound retry, then continue without it | Search failed. Retry or skip | Technical owner |
| No trusted result | No passage meets threshold | Withhold sourced guidance | No trusted result found | Human or official referral |
| Conflicting sources | Incompatible source claims | Flag conflict, do not choose blindly | Sources disagree. Review needed | Appropriate human reviewer |
| Low-confidence match | Weak evidence alignment | Mark provisional, prevent reuse | Confirm or reject this match | Career reviewer |
| Disallowed sensitive content | User warning or content flag | Stop processing affected content | Remove sensitive details | Approved review process |
| Out-of-scope request | Scope or boundary check | Decline task, suggest referral | This needs an authorized adviser | Official referral |
| Agent disagreement | Inconsistent capability outputs | Hold result, compare evidence | Recommendations conflict | Quality reviewer, then human |
| Orchestration failure | Invalid state or failed handoff | Resume from verified stage if safe | Workflow paused. Retry or review | Technical owner |
| Incomplete final packet | Required section missing | Flag missing pieces, withhold final | Packet is incomplete. Edit or retry | User and technical owner |
Explain the failure. Offer retry, edit, skip or human review. Log the unresolved issue for review.

09
Golden Gate Glory  /  Week 4 Technical Architecture

### Notes:
Jay explains detection and recovery proposals, which are not implemented controls. William reviews the user messages. Never silently fill gaps. Preserve verified work only where the approved state design permits it. Proposed logs capture issue type, affected artifact and resolution state with minimal sensitive content. Retry limits, detection thresholds and the review process require team confirmation.
Source: user-provided architecture brief, 7 October 2026. All technical design details are proposed unless marked Open Decision or Future Backlog. No completed implementation, approved integration, security certification, or measured performance is claimed.

<!-- Slide number: 10 -->

Where Human Judgment Enters the Workflow
Proposed review levels. Career guidance does not replace official decisions or professional advice.

LEVEL 1
LEVEL 2
LEVEL 3
User Verification
Career or Workforce Review
Official Referral
01
Confirm skills
01
Validate civilian language
01
Benefits and eligibility
02
Correct experience
02
Strengthen career materials
02
Legal, medical and financial matters
03
Reject recommendations
03
Review target-role alignment
03
Hiring decisions
04
Edit draft materials
04
Discuss training or employment next steps
04
Official government determinations

Unsupported accomplishment, low confidence, conflicting evidence, major career decision,
official-guidance request, user-requested escalation or a quality-review flag.
HUMAN-REVIEW TRIGGERS
Proposed packet: selected drafts, evidence, unresolved questions and review reasons. User approves sharing.
User-approved packet
Future Backlog: external reviewer delivery integration

10
Golden Gate Glory  /  Week 4 Technical Architecture

### Notes:
William presents where human judgment enters the workflow. Jay clarifies that routing integrations and reviewer availability remain unconfirmed. Prepare a packet for user review before any sharing. The packet should include only selected materials and relevant evidence. Official referrals identify the appropriate type of authority without issuing benefits, legal, medical, financial or hiring determinations.
Source: user-provided architecture brief, 7 October 2026. All technical design details are proposed unless marked Open Decision or Future Backlog. No completed implementation, approved integration, security certification, or measured performance is claimed.

<!-- Slide number: 11 -->

Technology Choices Requiring Technical Validation
Candidate options only. Availability, suitability, integration effort and cohort access remain unconfirmed.
| Technology Area | Proposed Need | Options to Evaluate | Decision Owner | Status |
| --- | --- | --- | --- | --- |
| Foundation model or inference | Generate bounded drafts | IBM watsonx.ai, IBM Granite models | Jay | Open Decision |
| Orchestration | Stage routing and gates | Application workflow, IBM watsonx Orchestrate | Jay | Open Decision |
| RAG or retrieval service | Approved passage retrieval | Local search, available IBM-aligned service | Jay | Open Decision |
| Knowledge storage | Versioned approved content | Curated files, approved IBM Cloud storage | Jay | Open Decision |
| Session-state handling | Confirmed evidence and stage | Ephemeral state, approved persistence | Jay | Open Decision |
| User interface or prototype | Consent, editing, verification | Lightweight form or chat prototype | Jay with William | Open Decision |
| Logging and audit support | Issue and decision trace | Minimal local log, approved cloud service | Jay | Open Decision |
| Document ingestion | Selected text extraction | Pasted text, permitted file parser | Jay | Open Decision |
| Human-review packet generation | Portable review summary | Editable document or structured summary | Jay with William | Open Decision |
Jay will determine the smallest feasible IBM-aligned architecture supported by the team account and program constraints.

11
Golden Gate Glory  /  Week 4 Technical Architecture

### Notes:
Jay owns technology selection. Evaluate possible IBM watsonx.ai, IBM Granite models, IBM watsonx Orchestrate and approved IBM Cloud services available to the cohort. Naming a candidate does not assert a capability, approval or available license. Do not assign a product merely because it appears in the account. Validate documentation, account entitlement, cost and integration feasibility before deciding. Start with pasted text if ingestion adds unnecessary risk.
Source: user-provided architecture brief, 7 October 2026. All technical design details are proposed unless marked Open Decision or Future Backlog. No completed implementation, approved integration, security certification, or measured performance is claimed.

<!-- Slide number: 12 -->

Ready for Week 5 When the Core Flow Is Buildable
Proposed MVP acceptance criteria. Readiness targets, not achieved or tested results.
Architecture clarity
MVP readiness
01
Each capability has a defined responsibility
01
One complete end-to-end flow is selected
02
Data sources are available or responsibly simulated
02
Inputs and outputs are mapped
03
User verification is included
03
Orchestration decisions are documented
04
Unsupported claims are blocked or flagged
04
Retrieval requirements are defined
05
Human review is represented
05
Failure and escalation paths are visible
06
A fragile but demonstrable Week 5 flow is feasible

KEY DECISION FOR JAY AND THE TEAM
What is the smallest technically credible flow we can build and demonstrate from veteran intake through a verified and useful career-readiness output?
Future Backlog: broader automation and persistent multi-session support, only after a viable core flow.

12
Golden Gate Glory  /  Week 4 Technical Architecture

### Notes:
Jay closes on the smallest buildable flow. Suggested proposed demo: consent, selected experience, clarification, evidence-linked skill suggestion, user confirmation, target-job comparison, editable draft, quality check and review packet. Use clearly labeled simulated retrieval content if approved sources are not available. William checks usefulness and responsible AI boundaries. Corrine closes the narrative. These are readiness criteria, not test results or performance promises.
Source: user-provided architecture brief, 7 October 2026. All technical design details are proposed unless marked Open Decision or Future Backlog. No completed implementation, approved integration, security certification, or measured performance is claimed.