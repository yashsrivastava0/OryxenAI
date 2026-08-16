## Discovery interaction

```json
{
  "mode": "ASK_QUESTIONS",
  "assistant_message": "Thanks, Arjun — this gives me a strong foundation for a technical portfolio focused on backend, cloud, and full-stack engineering. Before I build the Discovery Brief, I’d like to clarify a few choices that will affect the positioning and project storytelling.",
  "items": [
    {
      "id": "target_role_focus",
      "text": "Which direction should the portfolio prioritize: backend/platform engineering, full-stack product engineering, or an even balance of both?",
      "help_text": "Your experience supports all three, but the emphasis will change the headline, skills hierarchy, project order, and case-study framing.",
      "kind": "single_select",
      "options": [
        {
          "id": "backend_platform",
          "label": "Backend and platform engineering"
        },
        {
          "id": "full_stack",
          "label": "Full-stack product engineering"
        },
        {
          "id": "balanced",
          "label": "Balanced backend and full-stack profile"
        }
      ],
      "reason": null,
      "allow_skip": true,
      "allow_auto": false
    },
    {
      "id": "featured_project",
      "text": "Which project should lead the portfolio: DevConnect, ShopSphere, or CodePulse?",
      "help_text": "I can feature the other projects as supporting work, but the lead project should best match the roles you want next.",
      "kind": "single_select",
      "options": [
        {
          "id": "devconnect",
          "label": "DevConnect — full-stack networking platform"
        },
        {
          "id": "shopsphere",
          "label": "ShopSphere — scalable e-commerce backend"
        },
        {
          "id": "codepulse",
          "label": "CodePulse — GitHub engineering analytics dashboard"
        }
      ],
      "reason": null,
      "allow_skip": true,
      "allow_auto": true
    },
    {
      "id": "project_ownership",
      "text": "For the featured project, what did you personally design or implement, and was it built independently or with collaborators?",
      "help_text": "This helps distinguish your contribution from the overall product scope and keeps the case study accurate.",
      "kind": "text",
      "options": [],
      "reason": null,
      "allow_skip": true,
      "allow_auto": false
    },
    {
      "id": "public_contact",
      "text": "How should visitors be encouraged to get in touch: email, LinkedIn, GitHub, or a combination of these?",
      "help_text": "Your resume includes several public channels; I’ll use only the ones you want prominently shown.",
      "kind": "multi_select",
      "options": [
        {
          "id": "email",
          "label": "Email"
        },
        {
          "id": "linkedin",
          "label": "LinkedIn"
        },
        {
          "id": "github",
          "label": "GitHub"
        }
      ],
      "reason": null,
      "allow_skip": true,
      "allow_auto": false
    }
  ],
  "memory_update": {
    "open_items": [
      "Target-role emphasis is not yet selected.",
      "Featured project order is not yet selected.",
      "Personal ownership and collaboration context for the featured project are not explicitly stated.",
      "Public contact CTA preference is not yet selected.",
      "Project links and resume claims are user-supplied and should remain unverified references."
    ],
    "privacy_notes": [
      "Phone number, email, location, availability, work preferences, and external profile links were supplied by the user; confirm which should be public in the final brief.",
      "No confidentiality restrictions were stated."
    ],
    "confirmed_details": {
      "name": "Arjun Sharma",
      "location": "Bengaluru, Karnataka, India",
      "education": "B.Tech in Computer Science & Engineering, Rajasthan Technical University, 2019–2023, CGPA 8.4/10",
      "experience": "3+ years",
      "profession": "Software Engineer / Full-Stack Developer / Backend & Cloud",
      "current_role": "Software Engineer at TechNova Solutions Pvt. Ltd., July 2024–Present",
      "previous_role": "Associate Software Engineer at Infobyte Technologies Pvt. Ltd., August 2023–June 2024",
      "known_projects": [
        "DevConnect",
        "ShopSphere",
        "CodePulse"
      ],
      "preferred_roles": [
        "Software Engineer",
        "Backend Engineer",
        "Full-Stack Engineer"
      ],
      "contact_channels_supplied": [
        "email",
        "LinkedIn",
        "GitHub",
        "portfolio",
        "LeetCode",
        "GeeksforGeeks",
        "technical blog"
      ],
      "certifications_and_achievements": [
        "AWS Certified Cloud Practitioner, 2025",
        "600+ DSA problems",
        "LeetCode contest rating 1720+",
        "Spot Award at TechNova Solutions"
      ]
    },
    "presentation_preferences": {
      "safe_default": "Choose a polished technical editorial direction with moderate content density and restrained motion unless the user specifies otherwise.",
      "inferred_persona": "technical practitioner",
      "likely_visual_direction": "technical, systems-aware, clean professional"
    }
  }
}
```

# Portfolio Discovery Brief: Arjun Sharma

## 1. Portfolio direction at a glance

- **Primary goal:** Create a professional portfolio for job-search use.
- **Primary professional identity:** Software Engineer with backend, cloud, and full-stack development experience.
- **Recommended emphasis:** Backend and platform engineering, with visible evidence of API design, performance optimization, distributed processing, authentication, cloud deployment, databases, and production support.
- **Secondary credibility:** Full-stack delivery through React.js, Next.js, reusable frontend components, and end-to-end project ownership where supported.
- **Target audience:** Hiring managers, recruiters, engineering leads, and technical interviewers evaluating Software Engineer, Backend Engineer, and Full-Stack Engineer candidates.
- **Desired visitor action:** Contact Arjun through approved public channels, especially email, LinkedIn, or GitHub.
- **Leading portfolio story:** DevConnect should lead because it is the explicitly selected featured project and demonstrates full-stack delivery, authentication, caching, deployment, and developer-focused product thinking.
- **Confidence:** High confidence in the technical profile, employment history, listed projects, tools, education, and supplied metrics. Lower confidence remains around personal ownership versus team contribution for DevConnect and the other projects, public availability of project demos, and which claims have independently verifiable proof.

## 2. User intent and definition of success

The user asked to create a portfolio. The supplied material supports a portfolio designed primarily for employment and technical credibility rather than a personal blog or freelance-sales site.

A successful portfolio should quickly communicate that Arjun can build and operate production-oriented backend systems, not merely complete isolated coding exercises. It should make the following evidence easy to find:

1. Experience building REST APIs and backend modules.
2. Practical performance work involving SQL optimization, indexing, pagination, and Redis caching.
3. Security implementation through JWT authentication and role-based authorization.
4. Cloud and delivery experience with AWS, Docker, CI/CD, monitoring, and production support.
5. Ability to work across the stack when necessary, including React.js and TypeScript.
6. Structured technical thinking demonstrated through projects such as DevConnect, ShopSphere, and CodePulse.

No deadline was supplied. Preferred roles listed in the source are Software Engineer, Backend Engineer, and Full-Stack Engineer. The answered target-role focus is **backend_platform**, so that direction should guide hierarchy and project ordering.

## 3. Professional identity and positioning inputs

The supplied professional labels are “Software Engineer,” “Full-Stack Developer,” and “Backend & Cloud.” The current role is Software Engineer at TechNova Solutions Pvt. Ltd.

Supported strengths include Java and Spring Boot backend development, REST API design, PostgreSQL and MySQL work, Redis caching, AWS infrastructure, Docker, CI/CD, authentication and authorization, testing, and production troubleshooting. React.js, TypeScript, Node.js, and Next.js provide credible full-stack breadth.

The recommended positioning direction is a backend/platform-oriented engineer who can take features from requirements and technical design through implementation, testing, deployment, monitoring, and support. The portfolio should not imply that Arjun is exclusively a backend specialist if the full-stack experience remains important; instead, frontend capability should support the central backend narrative.

Do not create a final marketing headline in Discovery. Later content work should develop concise positioning from these verified inputs.

## 4. Source-derived professional profile

### Public-ready or potentially public content

- Name: Arjun Sharma.
- Location supplied: Bengaluru, Karnataka, India.
- Current role: Software Engineer, TechNova Solutions Pvt. Ltd., July 2024–Present.
- Previous role: Associate Software Engineer, Infobyte Technologies Pvt. Ltd., August 2023–June 2024.
- Education: Bachelor of Technology in Computer Science & Engineering, Rajasthan Technical University, Kota, 2019–2023, CGPA 8.4/10.
- Projects: DevConnect, ShopSphere, and CodePulse.
- Supplied public links: LinkedIn, GitHub, LeetCode, GeeksforGeeks, arjunsharma.dev, and technical blog.
- Supplied approved contact channels: email, LinkedIn, and GitHub.
- Languages: English — Professional Proficiency; Hindi — Native/Bilingual.
- Certification and achievements: AWS Certified Cloud Practitioner, 2025; 600+ DSA problems; LeetCode contest rating of 1,720+; Spot Award at TechNova Solutions; other achievements as supplied.

### Private or publication-controlled content

The phone number should be omitted by default because it is personal contact information and was not included in the answered public-contact channels. Availability, notice period, preferred cities, and work preference should be included only if Arjun explicitly wants them in the portfolio. Employer and project names are currently treated as publishable because no confidentiality restriction was stated, but this should remain an explicit user-controlled decision.

## 5. Experience and responsibility map

### TechNova Solutions Pvt. Ltd. — Software Engineer
**Bengaluru, India | July 2024–Present**

The supplied scope includes customer-facing applications used by 100,000+ registered users. Responsibilities and evidence include developing Java/Spring Boot and React.js features; designing 20+ REST endpoints covering profiles, orders, payments, notifications, and administrative workflows; implementing JWT authentication and RBAC; integrating payment and notification services; creating asynchronous background processing; optimizing PostgreSQL queries and indexes; using Redis caching; containerizing services with Docker; contributing to GitHub Actions workflows; operating with AWS EC2, RDS, S3, and CloudWatch; improving logging and monitoring; writing JUnit and Mockito tests; participating in Agile delivery and production incident analysis; and mentoring two developers.

Supplied outcomes include reducing a high-traffic API from approximately 850 ms to 320 ms and maintaining approximately 80% test coverage for newly developed backend modules. A Spot Award is also supplied for resolving a production performance issue affecting a critical customer workflow. Later content work should distinguish Arjun’s individual work from the broader eight-engineer team wherever possible.

### Infobyte Technologies Pvt. Ltd. — Associate Software Engineer
**Pune, India | August 2023–June 2024**

The role involved backend modules for an internal enterprise workflow management platform using Java, Spring Boot, MySQL, and REST APIs. Supplied responsibilities include CRUD APIs, responsive React.js pages, validation, centralized exception handling, pagination, filtering, standardized API responses, JUnit testing, regression support, Git workflows, Linux deployment assistance, troubleshooting, and translating business requirements into technical tasks.

The supplied outcomes include approximately 35% faster report generation through query and index optimization and resolution of 40+ functional and production defects. The platform’s internal status and any restrictions on naming it have not been confirmed.

## 6. Project and work-sample inventory

### DevConnect — Developer Networking Platform

- **Type:** Full-stack developer networking platform.
- **Context:** Users can create profiles, publish posts, follow users, comment, and participate in technical communities.
- **Technologies:** React.js, Node.js, Express.js, PostgreSQL, Redis, AWS, Docker.
- **Supplied contribution:** Built the platform, REST APIs, authentication and authorization, caching, pagination, database optimization, S3 image uploads, responsive interfaces, Docker setup, GitHub Actions workflows, and AWS deployment with Nginx.
- **Links:** GitHub link supplied; live demo link supplied as `devconnect-demo.example.com`.
- **Why it deserves space:** It is the selected featured project and covers product functionality, backend architecture, security, scalability considerations, frontend delivery, and deployment.
- **Missing evidence:** Personal ownership boundaries, usage or performance metrics, deployment status, and confirmation that the live demo is active and safe to publish.

### ShopSphere — Scalable E-Commerce Backend

- **Type:** Backend system and architecture project.
- **Context:** E-commerce workflows covering users, products, categories, carts, orders, inventory, payments, and notifications.
- **Technologies:** Java, Spring Boot, PostgreSQL, Redis, RabbitMQ, Docker.
- **Supplied contribution:** Layered REST services, relational schemas and indexes, caching, temporary cart data, asynchronous RabbitMQ notification processing, idempotency handling, JWT/RBAC, validation, logging, error responses, tests, OpenAPI documentation, and Docker setup.
- **Link:** GitHub link supplied.
- **Why it deserves space:** Strongest project for a backend/platform audience, particularly for discussing asynchronous processing, reliability, data modeling, and API design.
- **Missing evidence:** Personal ownership boundaries, scale or test results, and confirmation of public repository status.

### CodePulse — GitHub Engineering Analytics Dashboard

- **Type:** Analytics dashboard and data-integration project.
- **Context:** Analyzes repositories, commits, pull requests, contributors, issues, and development trends.
- **Technologies:** Next.js, TypeScript, Python, FastAPI, PostgreSQL, GitHub API.
- **Supplied contribution:** GitHub API integration, scheduled synchronization, analytics aggregation, interactive dashboard pages, background jobs, data modeling, rate-limit handling, retries, logging, and caching.
- **Link:** GitHub link supplied.
- **Why it deserves space:** Demonstrates API integration, data processing, background work, frontend visualization, and handling of external-service constraints.
- **Missing evidence:** Personal ownership boundaries, data volume, dashboard screenshots, and measurable outcomes.

## 7. Skills and capability groups

- **Strongly evidenced through experience:** Java, Spring Boot, REST APIs, React.js, PostgreSQL, MySQL, SQL optimization, database indexing, Redis, JWT authentication, RBAC, JUnit, Mockito, Git, Linux, Agile delivery, production troubleshooting, AWS, Docker, and CI/CD.
- **Supported through projects:** Node.js, Express.js, TypeScript, Next.js, MongoDB-related capability as listed, RabbitMQ, FastAPI, GitHub API integration, AWS S3, Nginx, Swagger/OpenAPI, background jobs, idempotency, and caching.
- **Listed tools or concepts needing contextual selection:** Python, C++, Tailwind CSS, Redux Toolkit, Material UI, WebSockets, Jenkins, Jest, React Testing Library, message queues generally, and several foundational computer-science concepts.
- **Capability themes for later content:** API and service development; performance and data access; security and access control; cloud delivery and observability; asynchronous and distributed workflows; full-stack implementation; testing and engineering quality; technical mentorship.

## 8. Achievements, evidence, and claims

Supported source claims include 100,000+ registered users, 20+ REST API endpoints, API latency improvement from approximately 850 ms to 320 ms, approximately 80% test coverage for newly developed backend modules, approximately 35% faster report generation, 40+ defects fixed, mentoring two developers, 600+ DSA problems, a 1,720+ LeetCode contest rating, 30+ programming contests, top-10% contest ranking, AWS Certified Cloud Practitioner in 2025, and a TechNova Spot Award.

These are user-supplied claims and should be retained as supplied unless Arjun confirms wording or provides supporting proof. The portfolio must not add revenue, adoption, uptime, throughput, team attribution, business impact, or personal ownership that is not provided. The “100,000+ registered users” figure describes the application scope and should not automatically be presented as Arjun’s individually generated user growth.

Open-source contributions, technical notes, starter projects, hackathon participation, university leadership, and mentoring are useful supporting evidence but need links or selected examples before receiving major visual emphasis.

## 9. Content priority

Lead with the backend/platform direction and a concise evidence block. DevConnect should be the first case study because it was selected. ShopSphere should follow as the most backend-architecture-focused project. CodePulse can support the story with external API integration and analytics.

The experience section should prioritize measurable technical decisions rather than reproduce every resume bullet. The strongest stories to develop are:

1. TechNova API performance improvement and production visibility.
2. DevConnect authentication, caching, deployment, and full-stack architecture.
3. ShopSphere asynchronous order notifications and idempotent backend workflows.

Education, DSA achievements, certification, open-source activity, and leadership should support credibility without displacing professional experience and project evidence. Unverified links, unsupported ownership claims, and generic skill lists should be shortened or deferred.

## 10. Audience and visitor journey

Visitors should first understand Arjun’s backend/platform focus, current experience, and strongest technical evidence. They should then see selected work showing how he designs APIs, works with data and caching, implements security, and deploys services.

A recommended journey is: positioning and contact CTA; selected technical strengths; TechNova and Infobyte experience; DevConnect; ShopSphere; CodePulse; achievements and certification; open-source and leadership; contact links.

The portfolio should make technical depth scannable while allowing interested engineering reviewers to explore architecture, trade-offs, and implementation details.

## 11. Design-direction signals

Use the supplied safe default: a polished technical editorial direction with moderate content density and restrained motion. The visual character should feel technical, systems-aware, clean, and professional rather than decorative or heavily cinematic.

A typography-led, project-led presentation with architecture diagrams, data-flow illustrations, code-adjacent visual language, or restrained system motifs is appropriate. Avoid generic developer-template styling, excessive gradients, noisy animations, and unsupported “dashboard” imagery. Use actual screenshots, diagrams, repository links, or project artifacts only when supplied or later created from confirmed project information.

No explicit light/dark preference, reference sites, disliked examples, imagery inventory, or brand colors were supplied. These should remain open or use neutral defaults in later stages.

## 12. Interaction, motion, and responsive priorities

Use restrained motion. Prioritize fast scanning, clear hierarchy, keyboard accessibility, readable technical content, and responsive behavior on mobile. Any later implementation should respect reduced-motion preferences.

Project stories may benefit from lightweight architecture diagrams, API-flow explanations, timelines, or technical decision callouts, but visuals must represent confirmed project facts. Avoid making long technical sections dependent on animation. Mobile layouts should preserve project names, outcomes, technologies, and CTA access without requiring horizontal scrolling.

## 13. Contact, CTA, and privacy

The answered public-contact preference approves **email, LinkedIn, and GitHub**. These should be the primary public contact options. The supplied portfolio, LeetCode, GeeksforGeeks, and technical-blog links may be shown as professional resources, subject to link verification by the user.

Omit the supplied phone number by default. Do not publish a street address; none was supplied. Location may be shown at the city/country level as Bengaluru, Karnataka, India. Availability, notice period, preferred cities, and remote-work preference are supplied but should be treated as optional job-search metadata, not automatic portfolio content.

No confidentiality restrictions were stated. Nevertheless, the user should confirm that TechNova, Infobyte, internal platform descriptions, metrics, and project names can be published. If any work is confidential, generalize the organization or product and remove internal business data.

## 14. Constraints, conflicts, and open items

- Personal ownership and collaboration context for DevConnect, ShopSphere, and CodePulse are not explicitly stated.
- The source contains strong metrics, but no supporting artifacts or verification were provided.
- Project links are user-supplied references and have not been opened or verified.
- The DevConnect live-demo domain appears supplied as written; its availability and publication safety require confirmation.
- No explicit target-company list, deadline, visual references, light/dark preference, or CTA wording was supplied.
- Current target emphasis is answered as backend/platform, while the preferred-role list also includes full-stack roles; the brief resolves this by making backend/platform primary and full-stack secondary.
- Phone publication is not approved; omit it.
- Do not invent project scale, business outcomes, uptime, revenue, traffic, architecture diagrams, testimonials, or additional credentials.
- Later agents must distinguish team scope from Arjun’s direct contribution.

## 15. Downstream handoff

### Content/story stage

Build the central story around a backend/platform-oriented Software Engineer with production experience in APIs, databases, performance, security, cloud delivery, observability, and asynchronous workflows. Develop TechNova performance work, DevConnect, and ShopSphere first. Use CodePulse as a supporting case study. Preserve supplied metrics cautiously, label them as confirmed by the user rather than independently verified, and avoid claiming ownership beyond the source. Use clear, technical, moderately dense language without generic praise.

### Visual-design stage

Design for recruiters and engineering reviewers who need fast evidence followed by optional technical depth. Use a clean technical-editorial character, moderate density, restrained motion, strong typography, and project-led hierarchy. Potential assets include architecture diagrams, API/data-flow visuals, performance comparison graphics, repository links, and project screenshots, but only when grounded in supplied or later-confirmed material. Prioritize mobile readability, accessible contrast, keyboard navigation, and reduced-motion support.

### Code-generation stage eventually preserves

Use approved public facts only. Include the approved email, LinkedIn, and GitHub contact paths; show other supplied links only after user verification. Preserve sections for experience, selected projects, skills, achievements, education, and contact. Omit the phone number by default and respect any later confidentiality decisions. Do not invent metrics, testimonials, project outcomes, ownership, client details, or fake visuals. Preserve accessibility and restrained-motion preferences.

Discovery does not write the code.

## 16. Approval summary

Confirmed decisions include the portfolio goal, backend/platform target emphasis, DevConnect as the featured project, email/LinkedIn/GitHub as approved contact channels, and a polished technical-editorial direction with moderate density and restrained motion.

Open items can be safely omitted for the next stage: personal ownership details, link verification, optional availability information, visual references, deadline, and confidentiality confirmation for employer/project material. They should remain documented as constraints rather than being filled with assumptions.

The brief is ready for approval. **NEXT** means: approve this exact brief to end Discovery and allow later content, visual-design, and code-generation stages to use it as the handoff.

---

## Structured profile

```json
{
  "name": "Arjun Sharma",
  "current_title": "Software Engineer",
  "location": "Bengaluru, Karnataka, India",
  "links": [
    {
      "label": "LinkedIn",
      "url": "linkedin.com/in/arjunsharma-dev"
    },
    {
      "label": "GitHub",
      "url": "github.com/arjunsharma-dev"
    },
    {
      "label": "Portfolio",
      "url": "arjunsharma.dev"
    },
    {
      "label": "LeetCode",
      "url": "leetcode.com/u/arjunsharma"
    },
    {
      "label": "GeeksforGeeks",
      "url": "geeksforgeeks.org/user/arjunsharma"
    },
    {
      "label": "Technical Blog",
      "url": "dev.to/arjunsharma-dev"
    }
  ],
  "experience": [
    {
      "organization": "TechNova Solutions Pvt. Ltd.",
      "role": "Software Engineer",
      "dates": "July 2024 – Present",
      "highlights": [
        "Developed customer-facing applications using Java, Spring Boot, React.js, PostgreSQL, Redis, and AWS.",
        "Implemented 20+ REST API endpoints.",
        "Reduced a high-traffic API from approximately 850 ms to 320 ms.",
        "Implemented JWT authentication and role-based access control.",
        "Used Docker, GitHub Actions, AWS EC2, RDS, S3, and CloudWatch.",
        "Maintained approximately 80% test coverage for newly developed backend modules.",
        "Mentored two new developers."
      ]
    },
    {
      "organization": "Infobyte Technologies Pvt. Ltd.",
      "role": "Associate Software Engineer",
      "dates": "August 2023 – June 2024",
      "highlights": [
        "Developed backend modules using Java, Spring Boot, MySQL, and REST APIs.",
        "Developed responsive frontend pages using React.js, JavaScript, HTML, CSS, and Material UI.",
        "Reduced report generation time by approximately 35% through query and index optimization.",
        "Fixed 40+ functional and production defects.",
        "Supported deployment and troubleshooting on Linux servers."
      ]
    }
  ],
  "education": [
    {
      "institution": "Rajasthan Technical University, Kota",
      "credential": "Bachelor of Technology (B.Tech) in Computer Science & Engineering; CGPA: 8.4/10",
      "dates": "2019 – 2023"
    }
  ],
  "projects": [
    {
      "name": "DevConnect",
      "summary": "Developer networking platform with profiles, posts, follows, comments, authentication, caching, image uploads, and AWS deployment.",
      "contribution": "Built full-stack functionality, REST APIs, authentication and authorization, caching, pagination, responsive interfaces, Docker setup, CI workflows, and deployment.",
      "tech": [
        "React.js",
        "Node.js",
        "Express.js",
        "PostgreSQL",
        "Redis",
        "AWS",
        "Docker"
      ],
      "link": "github.com/arjunsharma-dev/devconnect"
    },
    {
      "name": "ShopSphere",
      "summary": "E-commerce backend supporting products, carts, orders, inventory, payments, and notifications.",
      "contribution": "Designed REST services, database schemas and indexes, Redis caching, RabbitMQ processing, idempotency handling, JWT/RBAC, validation, logging, tests, OpenAPI documentation, and Docker setup.",
      "tech": [
        "Java",
        "Spring Boot",
        "PostgreSQL",
        "Redis",
        "RabbitMQ",
        "Docker"
      ],
      "link": "github.com/arjunsharma-dev/shopsphere"
    },
    {
      "name": "CodePulse",
      "summary": "GitHub engineering analytics dashboard displaying repository activity, contributors, issues, pull requests, and development trends.",
      "contribution": "Integrated the GitHub API, implemented synchronization and background jobs, built analytics processing and dashboard pages, and added rate-limit handling, retries, logging, and caching.",
      "tech": [
        "Next.js",
        "TypeScript",
        "Python",
        "FastAPI",
        "PostgreSQL",
        "GitHub API"
      ],
      "link": "github.com/arjunsharma-dev/codepulse"
    }
  ],
  "skills": [
    "Java",
    "JavaScript",
    "TypeScript",
    "Python",
    "SQL",
    "C++",
    "React.js",
    "Next.js",
    "HTML5",
    "CSS3",
    "Tailwind CSS",
    "Redux Toolkit",
    "Material UI",
    "Spring Boot",
    "Node.js",
    "Express.js",
    "REST APIs",
    "Microservices",
    "WebSockets",
    "PostgreSQL",
    "MySQL",
    "MongoDB",
    "Redis",
    "AWS EC2",
    "AWS S3",
    "AWS RDS",
    "AWS CloudWatch",
    "Docker",
    "GitHub Actions",
    "Jenkins",
    "Nginx",
    "JUnit",
    "Mockito",
    "Jest",
    "Postman",
    "React Testing Library",
    "Git",
    "GitHub",
    "Jira",
    "IntelliJ IDEA",
    "VS Code",
    "Linux",
    "Maven",
    "npm",
    "RabbitMQ",
    "FastAPI",
    "DSA",
    "OOP",
    "SOLID Principles",
    "Design Patterns",
    "System Design",
    "DBMS",
    "Operating Systems",
    "Computer Networks",
    "Authentication",
    "Authorization",
    "Caching",
    "Message Queues",
    "CI/CD",
    "Agile/Scrum"
  ],
  "spoken_languages": [
    "English — Professional Proficiency",
    "Hindi — Native/Bilingual"
  ],
  "private_omitted": [
    "Personal phone number",
    "Email address unless explicitly published through the approved email CTA",
    "Availability and 30-day notice period unless explicitly requested",
    "Preferred work locations and remote-work preference unless explicitly requested"
  ]
}
```