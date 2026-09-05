export const PUBLIC_SITE = {
  "site": {
    "criteria": [
      {
        "criterion_id": "criterion:home:hero",
        "route_id": "home",
        "section_id": "home:hero",
        "text": "Introduce Arjun's role, positioning, and primary portfolio action."
      },
      {
        "criterion_id": "criterion:home:selected-work",
        "route_id": "home",
        "section_id": "home:selected-work",
        "text": "Show the range of product problems Arjun has contributed to without implying full case-study depth."
      },
      {
        "criterion_id": "criterion:home:approach",
        "route_id": "home",
        "section_id": "home:approach",
        "text": "Explain the repeatable design approach behind the project range."
      },
      {
        "criterion_id": "criterion:home:experience",
        "route_id": "home",
        "section_id": "home:experience",
        "text": "Provide concise professional context and connect the portfolio narrative to real product work."
      },
      {
        "criterion_id": "criterion:home:design-systems",
        "route_id": "home",
        "section_id": "home:design-systems",
        "text": "Highlight systems thinking and implementation awareness as a differentiator."
      },
      {
        "criterion_id": "criterion:home:about-connect",
        "route_id": "home",
        "section_id": "home:about-connect",
        "text": "Close with concise personal context and a safe invitation to connect."
      }
    ],
    "facts": [],
    "freedoms": [
      {
        "freedom_id": "freedom:composition",
        "key": "composition",
        "value": "Code Generator may adapt visual suggestions without changing approved copy."
      }
    ],
    "navigation_contract": {
      "allowed_destinations": [
        "home",
        "home:hero",
        "home:selected-work",
        "home:approach",
        "home:experience",
        "home:design-systems",
        "home:about-connect"
      ],
      "allowed_hrefs": [
        "/",
        "#hero",
        "#selected-work",
        "#approach",
        "#experience",
        "#design-systems",
        "#about-connect"
      ],
      "closed": true,
      "resolved_destinations": [
        {
          "destination_id": "home",
          "href": "/",
          "kind": "route"
        },
        {
          "destination_id": "home:hero",
          "href": "#hero",
          "kind": "section"
        },
        {
          "destination_id": "home:selected-work",
          "href": "#selected-work",
          "kind": "section"
        },
        {
          "destination_id": "home:approach",
          "href": "#approach",
          "kind": "section"
        },
        {
          "destination_id": "home:experience",
          "href": "#experience",
          "kind": "section"
        },
        {
          "destination_id": "home:design-systems",
          "href": "#design-systems",
          "kind": "section"
        },
        {
          "destination_id": "home:about-connect",
          "href": "#about-connect",
          "kind": "section"
        }
      ]
    },
    "public_content": [
      {
        "route_id": "home",
        "sections": [
          {
            "claim_ids": [],
            "content": {
              "body": "I'm Arjun Mehta, a UI/UX and Product Designer based in Bengaluru. I use research, iteration, accessible interaction design, and scalable systems to clarify the workflows people rely on.",
              "eyebrow": "Senior UI/UX Designer",
              "headline": "Making complex product experiences easier to use.",
              "primary_cta": {
                "href": "#selected-work",
                "kind": "internal",
                "label": "Explore selected work"
              },
              "secondary_cta": {
                "href": "https://linkedin.com/in/arjunmehta-design",
                "kind": "external",
                "label": "Connect on LinkedIn"
              }
            },
            "priority": "primary",
            "purpose": "Introduce Arjun's role, positioning, and primary portfolio action.",
            "section_id": "home:hero"
          },
          {
            "claim_ids": [],
            "content": {
              "headline": "Designing for moments where clarity matters.",
              "intro": "Across payments, commerce, logistics, and healthcare, I focus on understanding friction and shaping clearer paths through the product.",
              "projects": [
                {
                  "contribution": "Research, funnel analysis, flow redesign, prototyping, and usability testing.",
                  "description": "Android and iOS experiences addressing lengthy verification, unclear progress, and unnecessary interaction steps.",
                  "domain": "Payments",
                  "title": "Payments and onboarding"
                },
                {
                  "contribution": "Analytics, heatmaps, usability testing, hierarchy, validation, and progressive disclosure.",
                  "description": "A responsive checkout experience addressing unnecessary fields, weak error handling, delivery choices, and mobile interaction issues.",
                  "domain": "E-commerce",
                  "title": "E-commerce checkout"
                },
                {
                  "contribution": "Operations-user interviews, workflow mapping, tables, filtering, tracking, and reusable components.",
                  "description": "A desktop platform for shipments, drivers, routes, delivery exceptions, and performance management.",
                  "domain": "Logistics",
                  "title": "Logistics operations"
                },
                {
                  "contribution": "Information architecture, search filters, availability indicators, booking flow, and accessibility patterns.",
                  "description": "Mobile and responsive web experiences for discovering doctors, comparing availability, selecting consultation types, and booking visits.",
                  "domain": "Healthcare",
                  "title": "Healthcare appointments"
                }
              ],
              "section_label": "Selected work"
            },
            "priority": "primary",
            "purpose": "Show the range of product problems Arjun has contributed to without implying full case-study depth.",
            "section_id": "home:selected-work"
          },
          {
            "claim_ids": [],
            "content": {
              "headline": "From friction to a system people can trust.",
              "section_label": "Approach",
              "steps": [
                {
                  "text": "Use interviews, analytics, journey mapping, and workflow analysis to identify where people hesitate or lose context.",
                  "title": "Understand"
                },
                {
                  "text": "Clarify information architecture, user flows, hierarchy, interaction patterns, and responsive behavior.",
                  "title": "Shape"
                },
                {
                  "text": "Prototype and test key paths so decisions respond to observed behavior rather than assumption.",
                  "title": "Test"
                },
                {
                  "text": "Document reusable patterns and support design-to-development handoff so improvements remain consistent.",
                  "title": "Scale"
                }
              ]
            },
            "priority": "supporting",
            "purpose": "Explain the repeatable design approach behind the project range.",
            "section_id": "home:approach"
          },
          {
            "claim_ids": [],
            "content": {
              "roles": [
                {
                  "dates": "Jul 2024 – Present",
                  "organization": "NovaPay Technologies",
                  "role": "Senior UI/UX Designer",
                  "summary": "Lead end-to-end product design for consumer payment and merchant products, from research and flow definition through prototyping, testing, and system-supported delivery."
                },
                {
                  "dates": "Jan 2022 – Jun 2024",
                  "organization": "PixelCraft Labs",
                  "role": "UI/UX Designer",
                  "summary": "Designed web and mobile product experiences across SaaS, e-commerce, logistics, healthcare, and consumer technology, collaborating with product and engineering teams through implementation and design QA."
                }
              ],
              "section_label": "Experience"
            },
            "priority": "supporting",
            "purpose": "Provide concise professional context and connect the portfolio narrative to real product work.",
            "section_id": "home:experience"
          },
          {
            "claim_ids": [],
            "content": {
              "body": "I work across research, information architecture, interaction design, visual design, accessibility, prototyping, and design systems. The Nova Design System brought together tokens, components, variants, accessibility specifications, documentation, and a closer connection between Figma and production component architecture.",
              "capabilities": [
                "User research and usability testing",
                "Information architecture and user flows",
                "Responsive web and mobile UI",
                "Interaction and visual design",
                "Design systems and component libraries",
                "Accessibility and design-to-development handoff"
              ],
              "headline": "Patterns that help good decisions travel further.",
              "section_label": "Systems and craft",
              "tools": "Figma, FigJam, Framer, ProtoPie, Miro, Maze, Hotjar, Mixpanel, Notion, Jira, HTML/CSS, and Git/GitHub"
            },
            "priority": "supporting",
            "purpose": "Highlight systems thinking and implementation awareness as a differentiator.",
            "section_id": "home:design-systems"
          },
          {
            "claim_ids": [],
            "content": {
              "body": "Based in Bengaluru, I bring an interaction-design background and a practical interest in making digital products clearer, more inclusive, and easier to build.",
              "cta": "If you're working on a product that needs a clearer path through complexity, connect with me on LinkedIn.",
              "education": [
                "Bachelor of Design (B.Des) — Interaction Design, MIT Institute of Design, Pune, 2017 – 2021",
                "Google UX Design Professional Certificate, 2022",
                "Accessibility for Designers, Interaction Design Foundation, 2023",
                "Advanced Figma: Design Systems & Prototyping, 2024"
              ],
              "headline": "Thoughtful about people, precise about the details.",
              "languages": [
                "English — Professional proficiency",
                "Hindi — Native proficiency"
              ],
              "links": [
                {
                  "href": "https://linkedin.com/in/arjunmehta-design",
                  "kind": "external",
                  "label": "LinkedIn"
                },
                {
                  "href": "https://arjunmehta.design",
                  "kind": "external",
                  "label": "Portfolio"
                },
                {
                  "href": "https://arjunmehta.design/resume",
                  "kind": "external",
                  "label": "Resume"
                }
              ],
              "section_label": "About"
            },
            "priority": "supporting",
            "purpose": "Close with concise personal context and a safe invitation to connect.",
            "section_id": "home:about-connect"
          }
        ]
      }
    ],
    "public_content_manifest": {
      "nav": [
        {
          "href": "/",
          "label": "Arjun Mehta — Senior UI/UX Designer",
          "target": "home"
        },
        {
          "href": "#hero",
          "label": "Hero",
          "target": "home:hero"
        },
        {
          "href": "#selected-work",
          "label": "Selected Work",
          "target": "home:selected-work"
        },
        {
          "href": "#approach",
          "label": "Approach",
          "target": "home:approach"
        },
        {
          "href": "#experience",
          "label": "Experience",
          "target": "home:experience"
        },
        {
          "href": "#design-systems",
          "label": "Design Systems",
          "target": "home:design-systems"
        },
        {
          "href": "#about-connect",
          "label": "About Connect",
          "target": "home:about-connect"
        }
      ]
    },
    "routes": [
      {
        "path": "/",
        "purpose": "Present a focused professional narrative, selected project work, design approach, systems capability, and a safe contact path on one page.",
        "route_id": "home",
        "section_sequence": [
          "home:hero",
          "home:selected-work",
          "home:approach",
          "home:experience",
          "home:design-systems",
          "home:about-connect"
        ],
        "sections": [
          {
            "section_id": "home:hero"
          },
          {
            "section_id": "home:selected-work"
          },
          {
            "section_id": "home:approach"
          },
          {
            "section_id": "home:experience"
          },
          {
            "section_id": "home:design-systems"
          },
          {
            "section_id": "home:about-connect"
          }
        ],
        "storage_key": "routes/home",
        "title": "Arjun Mehta — Senior UI/UX Designer"
      }
    ],
    "runtime_requirements": [
      {
        "key": "offline",
        "runtime_id": "runtime:offline",
        "value": true
      },
      {
        "key": "closed_navigation",
        "runtime_id": "runtime:closed-navigation",
        "value": true
      }
    ],
    "schema_version": "build-preparation-brief-v1",
    "source": {
      "content_architect_content_hash": "e51436bedcaf41a4f583aa4630519eb1485bf52cdc7f034d9c76b0f0df7d2530",
      "content_brief_sha256": "00d4f0ad5e6018067da750ef455a0cf2d215105ac9f160a48c5976a3504368ea",
      "run_id": "94ae4a9c-d63c-4bcc-b994-b12dc56ac62c"
    }
  },
  "target": {
    "allowed_dependencies": [
      "react",
      "react-dom"
    ],
    "forbidden_runtime_capabilities": [
      "remote-fonts",
      "remote-runtime-assets"
    ],
    "target_id": "react-vite-v1"
  }
} as const;
