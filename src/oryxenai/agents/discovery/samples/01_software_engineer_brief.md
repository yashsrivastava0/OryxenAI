# Portfolio Discovery Brief — Aarav Mehta

## Portfolio direction at a glance

**Primary goal:** Create a one-page professional portfolio that helps Aarav secure backend or platform engineering opportunities at early-stage and growth-stage technology companies.

**Primary professional identity:** Backend/platform-oriented software engineer with practical experience building Python services, PostgreSQL-backed workflows, durable background processing, internal operational tooling, containerized development environments, and supporting React interfaces.

**Primary audience:** Startup CTOs, hands-on engineering leaders, platform/backend hiring managers, and technically informed recruiters. The portfolio should assume that the strongest visitors value implementation ownership, reliability, clear engineering trade-offs, and the ability to work across an early-stage stack.

**Desired visitor action:** Contact Aarav about a backend or platform engineering role. GitHub should be a clear secondary action for visitors who want implementation proof.

**Recommended leading emphasis:** Reliable backend systems and production-oriented ownership. QueueGuard should be the central story because it combines architecture, data modeling, concurrency/claiming behavior, retries, stale recovery, tests, and Dockerized delivery. Frontend work should appear as useful product breadth rather than the primary identity.

**Current confidence:** The direction, audience, public contact choices, theme preference, and strongest project are clear. No reliable numerical performance metrics are available, so the portfolio must use concrete responsibilities, system behavior, test coverage, and technical decisions as evidence instead of invented numbers.

## User intent and definition of success

Aarav wants a portfolio for backend or platform engineering roles at startups. Success means that a technical visitor can quickly understand three things:

1. Aarav has built more than isolated API endpoints; he understands persistent job state, retries, failure recovery, database-backed coordination, and operational behavior.
2. He can own implementation across service code, database models, tests, Docker, CI, and a supporting frontend when required.
3. He is interested in production-oriented startup work rather than being positioned as a generic developer who lists many technologies without context.

The portfolio should be concise enough for a fast hiring review but detailed enough that an engineering leader can inspect the QueueGuard story and see genuine system-thinking. It should not depend on private employer data, fake performance claims, or screenshots that do not exist.

## Professional identity and positioning inputs

**Recommended positioning direction:** Present Aarav as a backend/platform engineer who turns operational requirements into dependable, testable services. The strongest differentiator is not merely Python or FastAPI knowledge; it is the combination of state modeling, failure handling, worker behavior, database coordination, and pragmatic full-stack delivery.

**Primary strengths:**

- Designing and implementing backend services with Python and FastAPI.
- Modeling durable workflow state in PostgreSQL.
- Building background-job behavior including claiming, retries, failure state, and stale recovery.
- Writing automated tests around stateful infrastructure.
- Containerizing application services and supporting repeatable development/runtime setup.
- Contributing to internal operational interfaces in React and TypeScript.

**Secondary strengths:**

- SQLAlchemy data access and schema-oriented application design.
- CI checks through GitHub Actions.
- Redis familiarity, although the supplied material does not yet provide a strong Redis project story.
- Full-stack collaboration when backend systems require an administrative interface.

**Positioning caution:** Do not market Aarav as a senior platform architect unless further evidence supports that level. Use accurate language such as "backend/platform-oriented software engineer," "production-focused engineer," or "engineer building reliable service workflows."

## Source-derived professional profile

### Current experience — Northstar Systems, Software Engineer, 2023–present

Aarav's current work includes FastAPI services, PostgreSQL data models, a database-backed background worker, retry and stale-recovery behavior, a React monitoring interface, Docker, and CI checks. The portfolio should synthesize these into a coherent systems story rather than presenting each technology as an isolated skill badge.

Strong portfolio angles:

- Translating operational workflow requirements into persisted states and explicit transitions.
- Preventing lost or permanently stuck jobs through retries and stale recovery.
- Connecting backend behavior to a monitoring/admin experience.
- Treating tests, Docker, and CI as part of delivery rather than afterthoughts.

Unknown or intentionally omitted:

- Employer-specific internal product name.
- User/customer counts.
- Throughput, latency, revenue, or time-saved metrics.
- Team size and exact production scale.

These details must not be guessed.

### Previous experience — PixelRoute, Junior Software Engineer, 2021–2023

The current material confirms a previous junior software-engineering role but does not yet include responsibilities or projects. It may appear in the experience timeline for continuity, but it should not consume major space unless the user later supplies a strong story from this period.

### Education and certifications

No education or certification details were supplied. Omit those sections rather than creating empty blocks. They can be added later if the user provides them.

### Public links and contact

Approved public items:

- Email.
- GitHub.
- Supplied DevShelf repository link.

Private by default:

- Phone number.
- Street address.

The final generated portfolio should not expose private contact details merely because they may exist in an uploaded resume.

## Experience and responsibility map

### Durable background-processing work

**Context:** Internal operational platform requiring work to continue outside the initiating HTTP request and remain recoverable across failures.

**Aarav's confirmed contribution:**

- Designed the persisted job schema.
- Implemented claim behavior.
- Implemented retry behavior.
- Implemented stale-job recovery.
- Added tests for the workflow.
- Added Docker setup.
- Contributed to the monitoring/admin interface.

**Portfolio value:** This is the clearest evidence of backend/platform thinking. It can show how Aarav models failure, concurrency, and recoverability rather than only successful request paths.

**Safe presentation:** Describe the system generically as a durable PostgreSQL-backed job platform. Do not reveal the employer's private internal product name or business data.

### API and data-model work

**Context:** FastAPI services and PostgreSQL-backed application behavior for internal operations.

**Portfolio value:** Supports Aarav's backend identity and gives the future content stage material for discussing API boundaries, data ownership, validation, state transitions, and operational endpoints.

**Missing evidence:** Specific endpoint examples, schema diagrams, or trade-off notes are not supplied. A later content stage may frame the story around the known responsibilities without inventing architecture details.

### Monitoring interface

**Context:** React and TypeScript interface for observing jobs and operational state.

**Portfolio value:** Demonstrates that Aarav can connect platform behavior to a usable internal product experience. It should remain supporting evidence, not redefine him as a frontend-first engineer.

## Project and work-sample inventory

### 1. QueueGuard — primary case study

**Type:** Backend/platform engineering case study.

**Context:** Durable job processing using Python, FastAPI, PostgreSQL, SQLAlchemy, Docker, and tests.

**Confirmed personal contribution:** Data schema, claiming logic, retries, stale recovery, automated tests, Docker setup, and supporting monitoring UI work.

**Why it should lead:** It directly matches the desired backend/platform roles and contains enough distinct engineering concerns to support a meaningful case study: state, failure, concurrency, persistence, observability, testing, and deployment setup.

**Recommended content angle:** Explain the problem of work that must survive request boundaries and process failures; show the lifecycle of a job; describe how retries and stale recovery prevent stuck work; discuss why PostgreSQL-backed durability was useful. The later content stage must avoid inventing exact locking algorithms or performance results unless Aarav supplies them.

**Possible visual evidence:** A simple lifecycle or architecture diagram is appropriate because no product screenshot is required. The diagram should be based only on confirmed concepts: API, PostgreSQL job table, worker, retry/failure state, stale recovery, and monitoring UI.

**Confidentiality:** Public description is allowed, but the employer's internal product name and business-specific details must be omitted.

**Missing information:** No public repository or live URL. That is acceptable; the case study should focus on engineering decisions and confirmed implementation ownership.

### 2. DevShelf — supporting personal project

**Type:** React/TypeScript personal project for organizing developer resources.

**Role in portfolio:** Smaller supporting project, not a full equal-weight case study. It can demonstrate product sensibility and personal initiative without distracting from the backend/platform position.

**Available proof:** GitHub link.

**Missing information:** The source does not yet describe the data model, features, user problem, or Aarav's most interesting implementation decision. Keep the summary modest until more detail exists.

### 3. Commerce dashboard — secondary team example

**Type:** Team product work.

**Confirmed contribution:** API endpoints and database queries.

**Role in portfolio:** A concise supporting entry showing team delivery and business-application experience.

**Caution:** Do not imply that Aarav designed or owned the entire dashboard. Separate the product scope from his backend contribution.

## Skills and capability groups

### Backend systems and APIs

Strongly evidenced:

- Python.
- FastAPI.
- API implementation.
- Workflow/state-oriented backend behavior.

### Data and persistence

Strongly evidenced:

- PostgreSQL.
- SQLAlchemy.
- Database-backed job state.
- Query and schema work.

### Reliability and operations

Strongly evidenced:

- Retry behavior.
- Stale-job recovery.
- Automated tests for stateful workflows.
- Dockerized service setup.
- CI checks.

### Frontend and product support

Evidenced as supporting breadth:

- React.
- TypeScript.
- Internal monitoring/admin interfaces.
- Personal frontend project.

### Listed but currently under-contextualized

- Redis.

Redis may remain in the skills inventory, but it should not be presented as a defining strength until a concrete use case is provided.

## Achievements, evidence, and claims

There are no reliable numerical metrics in the supplied material. This is not a weakness that should be hidden with fabricated numbers.

Credibility should come from:

- explicit ownership of schema, claiming, retries, stale recovery, tests, and Docker;
- the number of system concerns handled in one project;
- clear explanation of failure modes;
- a public personal-project repository;
- continuity from junior to software-engineer roles.

Claims that must not appear:

- percentage performance improvements;
- throughput figures;
- uptime claims;
- number of jobs processed;
- revenue impact;
- "built the entire platform";
- senior/lead title;
- Redis expertise beyond what the source supports.

## Content priority

**Lead with:**

1. Backend/platform identity.
2. QueueGuard case study.
3. Current Northstar Systems responsibilities.

**Support with:**

4. React monitoring-interface breadth.
5. DevShelf as a smaller personal project.
6. Commerce dashboard as concise team delivery.
7. PixelRoute experience timeline entry.

**Shorten or omit:**

- Generic skill-logo walls.
- Empty education/certification section.
- Unsupported metrics.
- Detailed employer-internal context.
- Private phone and address.
- A large Redis claim.

**Future content work should focus on:**

- Turning QueueGuard into a clear problem/approach/responsibility/outcome story.
- Explaining reliable workflow behavior in accessible language.
- Keeping technical depth without overwhelming non-specialist recruiters.
- Showing that frontend work supports the platform story rather than competing with it.

## Audience and visitor journey

A startup CTO or engineering manager should understand the portfolio in this order:

1. Aarav is focused on backend/platform engineering.
2. He has concrete ownership of a durable job system.
3. He understands failure handling, persistence, testing, and delivery.
4. He can collaborate across a product stack when needed.
5. He is available for a relevant role and can be contacted easily.

The page should provide a fast overview first, then let technical visitors inspect the QueueGuard story in more depth.

## Design-direction signals

**Desired character:** Technical, dependable, focused, and modern without becoming a generic "hacker" portfolio.

**Theme:** Dark technical direction is preferred.

**Avoid:**

- Fake terminal as the dominant visual.
- Random glowing orbs.
- Excessive glassmorphism.
- Technology-logo carousel as the main proof.
- Fake analytics or invented dashboards.
- Animation on every element.

**Potential visual language:**

- Editorial typography combined with restrained system diagrams.
- Job-lifecycle/state-flow visual for QueueGuard.
- Clear section rhythm and strong spacing.
- Subtle grid, data-flow, or topology motifs when they reinforce the backend story.
- Code or schema fragments only when based on real public material and still readable.

**Content density:** Balanced. The top of the page should scan quickly; the main case study can contain deeper technical material.

**Imagery:** No portrait or project screenshots are required. A typography-led and diagram-led portfolio is appropriate.

## Interaction, motion, and responsive priorities

**Motion:** Moderate. Use motion to guide attention between sections or reveal a system diagram, not to delay reading.

**Reduced motion:** The later implementation should respect reduced-motion preferences.

**Mobile:**

- The primary role and CTA must remain immediately understandable.
- QueueGuard's architecture should simplify into a readable vertical flow.
- Long technical explanations should use short subsections or expandable detail rather than tiny text.
- Avoid horizontal diagrams that require side-scrolling.

**Interaction:** GitHub and email actions should be clear. The main case study may use a progressive narrative, but core facts must remain accessible without interaction.

## Contact, CTA, and privacy

**Primary CTA:** Contact Aarav about a backend or platform engineering opportunity.

**Secondary CTA:** View GitHub.

**Approved public contact:** Email and GitHub.

**Private/omitted:** Phone number and street address.

**Confidentiality:** The durable-job system may be described generically, but internal employer product names, business data, and unprovided architecture details must not appear.

## Constraints, conflicts, and open items

- No reliable numerical metrics are available.
- QueueGuard has no public repository or live URL.
- The exact scale and production environment are unknown.
- PixelRoute responsibilities are not described.
- DevShelf needs more project detail before it can become a full case study.
- Redis is listed but lacks a supporting story.
- Education and certifications were not supplied.

These items do not block approval. Later stages should omit them or use modest language rather than filling the gaps.

## Downstream handoff

### Content/story stage

Build the central narrative around reliable backend workflow ownership. Develop QueueGuard as the principal case study using confirmed responsibilities. Use DevShelf and the commerce dashboard as shorter supporting evidence. Avoid unsupported scale, performance, and seniority claims. Keep the tone technical, direct, and credible.

### Visual-design stage

Create a dark, technical-editorial one-page experience with strong hierarchy and restrained system-oriented visuals. Prioritize a clear job-lifecycle diagram or state-flow motif for QueueGuard. Keep motion moderate, avoid fake-terminal clichés, and ensure the case study remains readable on mobile.

### Code-generation stage

Eventually preserve only approved public facts and links. Include email and GitHub, omit phone/address, avoid remote/private assets, respect reduced motion, and do not create fake metrics, product screenshots, dashboards, or employer details.

## Approval summary

Confirmed:

- Backend/platform positioning.
- Startup CTO and engineering-manager audience.
- QueueGuard as the lead story.
- Supporting role for DevShelf and commerce dashboard.
- Dark technical direction without a fake terminal.
- Moderate motion.
- Email and GitHub public; phone/address private.
- No invented metrics.

Safe omissions:

- Education/certifications.
- Exact production scale.
- PixelRoute details.
- Unsupported Redis claims.

**Ready for user review:** Yes. NEXT should approve this exact brief revision and stop Discovery. It must not start another agent in this phase.
