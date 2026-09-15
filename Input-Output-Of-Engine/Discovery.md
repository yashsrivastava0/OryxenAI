{
  "understand_and_question": {
    "mode": "ASK_QUESTIONS",
    "operation": "understand_and_question",
    "questions": [
      {
        "id": "confirm_ownership_and_accuracy",
        "kind": "text",
        "text": "Is this information genuinely yours and approved for use in a public portfolio, or is it an example/template? If it is yours, should I treat all listed roles, dates, metrics, awards, credentials, and contact links as confirmed, or are there specific claims I should omit or flag for verification?",
        "reason": "The material contains identity-sensitive claims and several highly consequential professional assertions, so ownership and publication permission must be confirmed before building the brief.",
        "options": [],
        "help_text": "This determines whether the portfolio can safely use the names, accomplishments, metrics, and public contact details included in the source.",
        "allow_auto": false,
        "allow_skip": true
      }
    ],
    "memory_update": {
      "persona": "Technical executive/operator with broad engineering and company-building experience, pending ownership confirmation.",
      "open_items": [
        "Ownership and authenticity of the supplied identity and professional claims are unconfirmed.",
        "Publication permission for the supplied contact details and other personal information is unconfirmed.",
        "All metrics, awards, credentials, dates, role descriptions, and outcomes should remain unverified until the user confirms them.",
        "The document may be an example or template rather than the user's own material."
      ],
      "privacy_notes": [
        "The source includes phone number, email address, social/profile links, locations, citizenship, and operational hubs; do not use these publicly until the user confirms they are theirs and approves publication."
      ],
      "source_summary": "A detailed executive/technical portfolio draft covering SpaceX, Tesla, xAI, X Corp., Neuralink, The Boring Company, PayPal/X.com, and Zip2, plus selected projects, technical disciplines, education, honors, contact channels, and personal locations.",
      "confirmed_details": []
    },
    "assistant_message": "Thanks — you provided substantial portfolio material spanning executive leadership, aerospace, electric vehicles, AI, communications, and neurotechnology. Before I turn it into a brief, I need to confirm one important point because the material contains highly specific identity, employment, achievement, and contact claims."
  },
  "build_or_revise_brief": {
    "mode": "BRIEF_READY",
    "profile": {
      "name": "Elon Musk",
      "links": [
        {
          "url": "https://x.com/elonmusk",
          "label": "X / Twitter"
        },
        {
          "url": "https://www.google.com/search?q=https://linkedin.com/in/elon-musk-official",
          "label": "LinkedIn"
        },
        {
          "url": "https://github.com/elonmusk",
          "label": "GitHub"
        },
        {
          "url": "https://x.com",
          "label": "Website"
        }
      ],
      "skills": [
        "First-Principles Physics Decomposition",
        "Vertical Integration",
        "Rapid Prototyping Loops",
        "High-Volume Manufacturing",
        "Capital Allocation",
        "Cross-Disciplinary R&D Leadership",
        "Reusable Orbital Launch Vehicles",
        "Cryogenic Liquid Rocket Propulsion",
        "Orbital Mechanics",
        "Heat Shield Aerodynamics",
        "Autonomous Recovery Systems",
        "Satellite Constellation Architecture",
        "Deep Neural Networks",
        "Computer Vision",
        "Supercluster Compute Topologies",
        "Transformer Foundations",
        "High-Throughput Inference Engines",
        "Humanoid Robotics",
        "Structural Battery Pack Design",
        "Lithium-Ion Cell Engineering",
        "High-Voltage Power Electronics",
        "Megawatt Charging Infrastructure",
        "Grid-Scale Battery Storage",
        "Solar Integration",
        "LEO Phased Array Telecommunications",
        "Distributed Global Messaging Architectures",
        "High-Concurrency Real-Time Systems",
        "Microservices Refactoring",
        "Thermodynamics",
        "Heat Transfer",
        "Structural Mechanics",
        "Embedded Compute",
        "Firmware",
        "RTOS",
        "CAN bus",
        "Automotive Ethernet",
        "Distributed Systems",
        "Optical Interconnects"
      ],
      "location": "",
      "projects": [
        {
          "link": "",
          "name": "Starship & Super Heavy Launch Architecture",
          "tech": [
            "Methane/LOX Raptor Engines",
            "Stainless Steel 304L/321",
            "Aerodynamic Flaps",
            "Thermal Protection Systems"
          ],
          "summary": "Launch-system and recovery architecture involving methane/LOX propulsion, stainless-steel structures, aerodynamic control, thermal protection, and launch/recovery systems.",
          "contribution": "Chief Engineer, as supplied"
        },
        {
          "link": "",
          "name": "Tesla Full Self-Driving — End-to-End Neural Network",
          "tech": [
            "PyTorch",
            "Tesla Vision",
            "HW3/HW4",
            "Dojo",
            "Transformer Encoders"
          ],
          "summary": "Autonomy architecture involving computer vision, custom vehicle compute, neural networks, and Dojo.",
          "contribution": "Product Architect & Executive Sponsor, as supplied"
        },
        {
          "link": "",
          "name": "Colossus AI Supercluster",
          "tech": [
            "Nvidia H100 GPUs",
            "Liquid Cooling Infrastructure",
            "RoCE Networking"
          ],
          "summary": "AI compute infrastructure involving GPU systems, liquid cooling, networking, power, and data-center deployment.",
          "contribution": "Lead Architect & Executive Sponsor, as supplied"
        }
      ],
      "education": [
        {
          "dates": "1992 – 1997",
          "credential": "Bachelor of Science in Economics; Bachelor of Arts in Physics",
          "institution": "University of Pennsylvania"
        },
        {
          "dates": "1995",
          "credential": "Graduate program in Materials Science and Applied Physics, deferred",
          "institution": "Stanford University"
        },
        {
          "dates": "1990 – 1992",
          "credential": "Undergraduate coursework in computing, physics, and economics",
          "institution": "Queen’s University"
        }
      ],
      "experience": [
        {
          "role": "Founder, Chief Executive Officer & Chief Engineer",
          "dates": "May 2002 – Present",
          "highlights": [
            "Leadership across launch systems, propulsion, manufacturing, crewed spacecraft, and satellite communications"
          ],
          "organization": "SpaceX"
        },
        {
          "role": "Technoking, Chief Executive Officer & Product Architect",
          "dates": "Oct 2008 – Present; joined as Chairman/Lead Investor Feb 2004",
          "highlights": [
            "Vehicle engineering, manufacturing, battery systems, autonomous driving, robotics, and energy storage"
          ],
          "organization": "Tesla, Inc."
        },
        {
          "role": "Founder & Chief Executive Officer",
          "dates": "Mar 2023 – Present",
          "highlights": [
            "Frontier AI systems, AI compute infrastructure, and Grok model development"
          ],
          "organization": "xAI"
        },
        {
          "role": "Executive Chairman & Chief Technology Officer; CEO",
          "dates": "Oct 2022 – Present; CEO Oct 2022 – Jun 2023",
          "highlights": [
            "Platform acquisition, software restructuring, monetization, recommendation systems, and moderation infrastructure"
          ],
          "organization": "X Corp. (formerly Twitter)"
        },
        {
          "role": "Co-Founder & Executive Director",
          "dates": "Jul 2016 – Present",
          "highlights": [
            "Implantable neural interfaces, surgical robotics, and clinical development"
          ],
          "organization": "Neuralink"
        },
        {
          "role": "Founder",
          "dates": "Dec 2016 – Present",
          "highlights": [
            "Tunneling technologies and the Las Vegas Convention Center Loop"
          ],
          "organization": "The Boring Company"
        },
        {
          "role": "Co-Founder & Chief Executive Officer",
          "dates": "Mar 1999 – Oct 2002",
          "highlights": [
            "Online financial services and electronic payment infrastructure"
          ],
          "organization": "PayPal / X.com"
        },
        {
          "role": "Co-Founder & Chief Technology Officer",
          "dates": "1995 – 1999",
          "highlights": [
            "Online city guides, directory software, mapping, and database-backed systems"
          ],
          "organization": "Zip2 Corporation"
        }
      ],
      "current_title": "Chief Executive Officer",
      "private_omitted": [
        "Phone number",
        "Email address",
        "Exact primary base and operational hubs",
        "Citizenship details",
        "Specific internal KPIs and business data",
        "Unverified contact and profile-link ownership"
      ],
      "spoken_languages": []
    },
    "operation": "build_or_revise_brief",
    "open_items": [
      "Confirm identity ownership and authority to publish.",
      "Confirm which roles, dates, credentials, awards, metrics, and technical claims are approved for public use.",
      "Clarify personal contribution versus team/company contribution for each case study.",
      "Verify public-link ownership and URL accuracy, especially the LinkedIn entry.",
      "Choose visual mood, light/dark preference, motion level, imagery permissions, audience priority, and CTA.",
      "Do not distribute as a verified production portfolio until the above items are resolved."
    ],
    "brief_title": "Portfolio Discovery Brief — Technical Executive and Systems Builder",
    "user_summary": "This brief organizes the supplied profile around cross-domain systems leadership: aerospace, electric vehicles, AI infrastructure, communications, neurotechnology, tunneling, and early internet payments. The strongest potential portfolio stories are Starship and Super Heavy, Tesla autonomy or manufacturing, and the Colossus AI supercluster, with emphasis on documented contribution rather than broad company-level claims.\n\nBecause the material is described as a platform-testing synthesis, it is not treated as a verified production portfolio. Phone and email details are excluded, and metrics, awards, technical claims, public links, ownership, and publication authority still need confirmation. The brief also recommends avoiding fabricated visuals, unsupported superlatives, and claims that blur executive sponsorship with direct implementation.\n\nThe full detailed brief has been prepared and is ready for review. Approving it would approve this testing-only handoff and stop Discovery; it would not authorize public distribution.",
    "memory_update": {
      "persona": "Technical executive/operator profile supplied for platform testing; not approved as a verified production portfolio.",
      "open_items": [
        "Identity and publication authority require confirmation.",
        "Metrics, awards, credentials, dates, outcomes, and technical claims require verification.",
        "Contact details and sensitive location information must remain omitted.",
        "Public links require ownership and URL verification.",
        "Individual contribution versus company/team contribution remains unclear."
      ],
      "privacy_notes": [
        "Do not publish the supplied phone number or email address.",
        "Omit citizenship, exact base, operational hubs, internal KPIs, and confidential business data by default.",
        "Do not distribute as a verified production portfolio."
      ],
      "source_summary": "Testing-oriented portfolio synthesis covering supplied roles associated with SpaceX, Tesla, xAI, X Corp., Neuralink, The Boring Company, PayPal/X.com, and Zip2, plus selected engineering and AI infrastructure projects."
    },
    "brief_markdown": "# 1. Portfolio direction at a glance\n\n- **Primary goal:** Create a portfolio for a technical executive/operator whose supplied profile spans aerospace, electric vehicles, artificial intelligence, communications, neurotechnology, tunneling, and early internet payments.\n- **Primary identity in the source:** Chief Executive Officer, Chief Engineer, technologist, founder, and product architect.\n- **Target audience:** Technical leaders, investors, engineers, policymakers, technology media, prospective partners, and visitors evaluating large-scale systems-building experience.\n- **Desired visitor action:** Review the strongest documented work and follow approved public profile links. No production contact CTA should be activated until ownership and publication permissions are confirmed.\n- **Leading emphasis:** Cross-company systems thinking, engineering iteration, company building, and the connection between physical infrastructure and software/AI systems.\n- **Confidence:** The submitted answer states that the roles, companies, degrees, and major milestones reflect publicly documented biographical records. Exact metrics, awards, contact information, and some detailed technical claims remain unverified or explicitly marked as mockup material.\n\n# 2. User intent and definition of success\n\nThe request is to create a portfolio from the supplied executive biography and technical work history. The material is unusually broad and should be treated as a profile synthesis for platform testing, not as a verified production portfolio. Success would mean producing a coherent, evidence-aware structure that helps visitors understand the subject’s work across multiple technology domains without presenting unverified claims as fact.\n\nNo deadline, employment objective, freelance objective, or school-admissions objective was supplied. The portfolio should therefore remain adaptable and should not assume a recruiting or commercial conversion goal.\n\n# 3. Professional identity and positioning inputs\n\nThe source supports a positioning direction around high-scale engineering leadership, first-principles problem solving, vertically integrated manufacturing, rapid iteration, and company formation. The strongest differentiator is the breadth of systems represented: launch infrastructure, electric mobility, AI compute, digital platforms, neural interfaces, communications, and financial technology.\n\nThe final public positioning should avoid unsupported superlatives such as “world’s first,” “fastest,” or “largest” unless each claim is independently verified and approved. It should also distinguish executive sponsorship, product architecture, engineering direction, and direct implementation.\n\n# 4. Source-derived professional profile\n\nThe supplied material names Elon Musk and lists roles associated with SpaceX, Tesla, xAI, X Corp., Neuralink, The Boring Company, PayPal/X.com, and Zip2. It also supplies education at the University of Pennsylvania, Stanford University, and Queen’s University; a large technical skills inventory; public links; and recognition claims.\n\nThe source is not approved as a verified production portfolio. Public-ready material should be limited to facts the owner later confirms and approves. Phone, email, citizenship, operational hubs, exact home/base information, and sensitive internal business details should be omitted by default.\n\n# 5. Experience and responsibility map\n\n- **SpaceX — Founder, Chief Executive Officer & Chief Engineer, May 2002–Present:** Source describes leadership across launch vehicles, propulsion, manufacturing, crewed spacecraft, satellite communications, and Starship. Specific mission counts, market share, subscriber counts, and cost reductions require verification.\n- **Tesla — Technoking, Chief Executive Officer & Product Architect, Oct 2008–Present; joined as Chairman/Lead Investor in Feb 2004:** Source describes vehicle engineering, manufacturing, battery systems, autonomy, robotics, and energy storage. Ownership boundaries between executive sponsorship and hands-on engineering require clarification.\n- **xAI — Founder & Chief Executive Officer, Mar 2023–Present:** Source describes frontier AI systems, the Colossus compute facility, and Grok model development. GPU counts, construction timelines, and performance claims require verification.\n- **X Corp. — Executive Chairman & Chief Technology Officer; CEO Oct 2022–Jun 2023:** Source describes acquisition, platform restructuring, monetization, recommendation systems, and moderation infrastructure. Detailed internal implementation claims should be treated as unverified.\n- **Neuralink — Co-Founder & Executive Director, Jul 2016–Present:** Source describes implantable neural interfaces, surgical robotics, and clinical development. Regulatory and clinical claims require confirmation before publication.\n- **The Boring Company — Founder, Dec 2016–Present:** Source describes tunneling technology and the Las Vegas Convention Center Loop. Passenger and operational claims require verification.\n- **PayPal/X.com — Co-Founder & Chief Executive Officer, Mar 1999–Oct 2002:** Source describes online financial services, payment infrastructure, and the PayPal acquisition history.\n- **Zip2 — Co-Founder & Chief Technology Officer, 1995–1999:** Source describes online city guides, directory software, mapping, and the acquisition by Compaq/AltaVista.\n\n# 6. Project and case-study inventory\n\n- **Starship & Super Heavy Launch Architecture:** A launch-system and recovery case study involving Raptor engines, stainless-steel structures, aerodynamic control, thermal protection, and the launch/recovery tower. The source attributes chief-engineer and architecture responsibilities; exact outcomes and technical comparisons need evidence.\n- **Tesla Full Self-Driving:** An autonomy and software/hardware architecture case study involving computer vision, custom silicon, neural networks, and Dojo. The source identifies product-architecture and executive-sponsor roles; direct authorship and mileage claims require confirmation.\n- **Colossus AI Supercluster:** An infrastructure case study involving GPU compute, liquid cooling, networking, power, and data-center deployment. The source identifies lead-architect and executive-sponsor roles; facility scale, schedule, and performance claims require verification.\n- **Additional potential stories:** SpaceX reusable launch operations, Starlink, Tesla manufacturing and energy systems, Neuralink implant technology, X platform restructuring, The Boring Company Loop, PayPal/X.com, and Zip2. These should be developed only from approved evidence and clearly attributed contribution.\n\n# 7. Skills and capability groups\n\n- **Strongly represented in the supplied material:** executive leadership, systems engineering, first-principles analysis, product architecture, rapid prototyping, manufacturing, propulsion, orbital systems, electric vehicles, energy storage, distributed systems, AI infrastructure, and platform operations.\n- **Listed technical areas needing context or validation:** PyTorch, transformer encoders, RTOS, CAN bus, automotive Ethernet, RoCE networking, custom ASICs, neural spike sorting, optical satellite links, and specific vehicle, rocket, and implant technologies.\n- **Capabilities to emphasize if confirmed:** translating ambitious system goals into integrated hardware/software programs; compressing design-to-test cycles; coordinating multidisciplinary engineering; and scaling infrastructure from prototype to operation.\n\n# 8. Achievements, evidence, and claims\n\nThe source includes numerous metrics, awards, patents, valuations, production totals, subscriber counts, mission counts, market-share claims, and regulatory milestones. The accompanying answer explicitly identifies direct contact numbers, email addresses, and specific internal KPIs as unverified mockup placeholders. All other precise figures and recognition claims should also be independently confirmed before publication.\n\nDo not use unsupported superlatives, confidential internal data, fabricated testimonials, or claims that imply direct individual implementation where only organizational leadership is documented. Evidence should include approved public sources, dated announcements, technical documentation, filings, or project artifacts where available.\n\n# 9. Content priority\n\nLead with a concise systems-building overview, followed by three deeply developed case studies: Starship/Super Heavy, Tesla autonomy or manufacturing, and Colossus AI infrastructure. Support these with a chronological experience map and a compact technical capability index. Shorten the long undifferentiated skills list and omit private contact data, exact operational locations, and unverified metrics. A later content stage should develop contribution boundaries and evidence for each case study.\n\n# 10. Audience and visitor journey\n\nVisitors should first understand the subject’s cross-domain engineering and company-building scope. They then need a clear explanation of the selected systems, the problem each addressed, the person’s documented contribution, the team context, and the evidence supporting outcomes. The recommended journey is overview → flagship case studies → experience timeline → capabilities and philosophy → approved public links. The primary action should initially be “Explore the work” rather than a contact conversion.\n\n# 11. Design-direction signals\n\nNo explicit visual preference was supplied. A suitable recommendation is a restrained, systems-led, editorial direction: strong typography, technical diagrams where evidence exists, clear chronology, and visual separation between confirmed facts and pending verification. Avoid generic futuristic imagery, fabricated dashboards, fake engineering renders, and spectacle that implies unsupported results. Light/dark preference, imagery availability, references, and density remain open.\n\n# 12. Interaction, motion, and responsive priorities\n\nUse restrained motion and prioritize scanning over prolonged exploration. Case studies may benefit from diagrams, timelines, architecture maps, or media only when supplied or properly approved. Preserve readability for long technical content, support mobile-first layouts, and include reduced-motion behavior. Do not create simulated telemetry, performance charts, or technical visuals that could be mistaken for evidence.\n\n# 13. Contact, CTA, and privacy\n\nNo public contact method is approved. The supplied phone number and email address are mockup placeholders and must not be published. The supplied social links may be retained as unverified references only after ownership and URL accuracy are confirmed; the LinkedIn entry should receive particular verification because the supplied URL redirects through a search URL.\n\nOmit or generalize personal citizenship, exact base, operational hubs, and other sensitive location details by default. Do not publish internal product names, business data, KPIs, or confidential material without explicit permission. Until approval is obtained, use a non-production “view approved public profile” CTA or no CTA.\n\n# 14. Constraints, conflicts, and open items\n\n- Identity ownership and authority to publish are not fully confirmed; the answer frames the material as platform testing.\n- Exact metrics, awards, patents, dates, titles, outcomes, and technical claims remain unverified.\n- Individual contribution versus team or company contribution is unclear in several roles.\n- Contact information is explicitly unverified mockup data and must be omitted.\n- Public-link ownership and URL accuracy require confirmation.\n- No visual preferences, motion level, imagery permissions, deadline, or audience priority were supplied.\n- The portfolio must not be distributed as a verified production portfolio.\n\n# 15. Downstream handoff\n\n## Content/story stage\nBuild the central story around cross-domain systems leadership and evidence-backed engineering decisions. Develop Starship/Super Heavy, Tesla autonomy or manufacturing, and Colossus as the initial stories. Confirm ownership, contribution, dates, metrics, and sources before writing definitive outcomes. Keep tone precise and avoid unsupported superlatives.\n\n## Visual-design stage\nUse a systems-led editorial hierarchy with technical clarity, restrained motion, strong typography, and optional approved diagrams. Prioritize mobile readability and distinguish documented facts from pending verification. Avoid generic sci-fi styling and fabricated visuals.\n\n## Code-generation stage eventually preserves\nUse only approved public facts and links; omit phone, email, sensitive locations, confidential information, and unverified KPIs. Preserve the selected case studies, evidence labels, responsive readability, accessibility, and reduced-motion preferences. Do not invent metrics, testimonials, diagrams, or visual evidence.\n\n# 16. Approval summary\n\nConfirmed for this brief: the material is a testing-oriented public-profile synthesis; roles, companies, degrees, and major milestones are described as publicly documented; direct contact details and specific internal KPIs are unverified mockup placeholders; and the material must not be treated as a verified production portfolio. Open items are safely omitted from publishable recommendations. The brief is ready for review, but approval means approval of this exact testing-only brief and does not authorize public distribution or production publication. **NEXT:** approve this exact brief to stop Discovery.\n",
    "assistant_message": "The Portfolio Discovery Brief is prepared as a testing-only, non-production handoff. It preserves the supplied professional profile while clearly separating source claims from verified or publication-approved facts. Contact details, specific KPIs, and other sensitive or unverified information are excluded from public-ready recommendations."
  }
}