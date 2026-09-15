{
  "events": [
    {
      "level": "info",
      "stage": "stage_0",
      "details": {},
      "message": "Validated the Visual Design Director structure.",
      "event_id": "input_validated",
      "timestamp": "2026-09-08T15:14:30.769955+00:00"
    },
    {
      "level": "info",
      "stage": "stage_0",
      "details": {
        "assumptions": [
          "Editorial imagery is decorative and non-evidentiary.",
          "No portrait, screenshot, dashboard, logo, or project proof is allowed.",
          "Component roles are derived from approved route sections and interaction needs.",
          "All visual resources must be local, attributed, and usable without runtime provider calls.",
          "Reduced motion receives a complete static equivalent."
        ],
        "route_count": 4,
        "dropped_routes": [],
        "assumption_hash": "84cb9c3b154af69a979f1ebec585eb3fdce15f276e5abcfa3aa9a5c99fa519bb",
        "resource_targets": {
          "image_target": 5,
          "component_target": 4
        },
        "visual_input_mode": "merged_vdd_assumptions",
        "resource_need_count": 40
      },
      "message": "Compiled approved route scope and structured resource needs.",
      "event_id": "scope_compiled",
      "timestamp": "2026-09-08T15:14:30.776866+00:00"
    },
    {
      "level": "info",
      "stage": "stage_0",
      "details": {},
      "message": "Stage 0 completed without model or provider calls.",
      "event_id": "stage_0_complete",
      "timestamp": "2026-09-08T15:14:30.776936+00:00"
    },
    {
      "level": "info",
      "stage": "resource_research",
      "details": {
        "provider_calls": 36
      },
      "message": "Discovered candidates for 23 resource role(s) and 13 component role(s).",
      "event_id": "resource_research:e075a2ad",
      "timestamp": "2026-09-08T15:15:25.237782+00:00"
    },
    {
      "level": "info",
      "stage": "compose_visual_brief",
      "details": {
        "model_calls": 1
      },
      "message": "Composed both Markdown briefs.",
      "event_id": "compose_visual_brief:e3bc7699",
      "timestamp": "2026-09-08T15:16:30.253042+00:00"
    }
  ],
  "routes": [
    {
      "path": "/",
      "title": "Maya Bennett — End User Computing & Endpoint Engineering",
      "purpose": "Introduce Maya's professional positioning, strongest evidence, capabilities, experience, and selected work for recruiter review.",
      "route_id": "home",
      "asset_ids": [
        "home-operating-chain",
        "home-workflow-abstract",
        "assumed-image:home:hero:0",
        "assumed-image:home:capabilities:1",
        "assumed-image:home:experience:2",
        "assumed-image:home:featured-work:3",
        "assumed-image:home:proof-points:4",
        "assumed-image:home:contact:16",
        "assumed-image:home:credentials:17"
      ],
      "scene_ids": [
        "home-positioning",
        "home-proof-capabilities",
        "home-experience-work",
        "home-closing-invitation"
      ],
      "section_ids": [
        "home:hero",
        "home:proof-points",
        "home:capabilities",
        "home:experience",
        "home:featured-work",
        "home:credentials",
        "home:contact"
      ],
      "resource_ids": [
        "hero_asymmetric_text_dominant",
        "diagram_before_after",
        "navigation_sticky_minimal_top",
        "assumed-component:home:capabilities:capability-grouping",
        "assumed-component:home:experience:experience-timeline",
        "assumed-component:home:featured-work:selected-work-detail"
      ],
      "publication_status": "approved"
    },
    {
      "path": "/work/workspace360",
      "title": "WorkSpace360",
      "purpose": "Show how Maya designed a standardized endpoint management and device provisioning framework for a hybrid workforce.",
      "route_id": "workspace360",
      "asset_ids": [
        "workspace360-process-visual",
        "assumed-image:workspace360:approach:5",
        "assumed-image:workspace360:challenge:6",
        "assumed-image:workspace360:outcome:7",
        "assumed-image:workspace360:overview:8",
        "assumed-image:workspace360:technology:9"
      ],
      "scene_ids": [
        "workspace360-overview",
        "workspace360-need-approach",
        "workspace360-result-context"
      ],
      "section_ids": [
        "workspace360:overview",
        "workspace360:challenge",
        "workspace360:approach",
        "workspace360:outcome",
        "workspace360:technology"
      ],
      "resource_ids": [
        "diagram_before_after",
        "diagram_process_flow",
        "assumed-component:workspace360:approach:selected-work-detail",
        "assumed-component:workspace360:approach:process-sequence",
        "assumed-component:workspace360:technology:selected-work-detail"
      ],
      "publication_status": "approved"
    },
    {
      "path": "/work/secureendpoint",
      "title": "SecureEndpoint",
      "purpose": "Explain Maya's contribution to an endpoint compliance and security program centered on policy, encryption, patch visibility, and remediation.",
      "route_id": "secureendpoint",
      "asset_ids": [
        "secureendpoint-control-chain",
        "assumed-image:secureendpoint:approach:11",
        "assumed-image:secureendpoint:challenge:18",
        "assumed-image:secureendpoint:outcome:19",
        "assumed-image:secureendpoint:overview:20",
        "assumed-image:secureendpoint:technology:21"
      ],
      "scene_ids": [
        "secureendpoint-overview",
        "secureendpoint-need-approach",
        "secureendpoint-result-context"
      ],
      "section_ids": [
        "secureendpoint:overview",
        "secureendpoint:challenge",
        "secureendpoint:approach",
        "secureendpoint:outcome",
        "secureendpoint:technology"
      ],
      "resource_ids": [
        "diagram_before_after",
        "diagram_process_flow",
        "assumed-component:secureendpoint:approach:process-sequence"
      ],
      "publication_status": "approved"
    },
    {
      "path": "/work/employeeconnect",
      "title": "EmployeeConnect",
      "purpose": "Present Maya's role in a Microsoft 365 migration involving account migration, automation, adoption support, and documentation.",
      "route_id": "employeeconnect",
      "asset_ids": [
        "employeeconnect-migration-path",
        "assumed-image:employeeconnect:approach:10",
        "assumed-image:employeeconnect:challenge:12",
        "assumed-image:employeeconnect:outcome:13",
        "assumed-image:employeeconnect:overview:14",
        "assumed-image:employeeconnect:technology:15"
      ],
      "scene_ids": [
        "employeeconnect-overview",
        "employeeconnect-need-approach",
        "employeeconnect-result-context"
      ],
      "section_ids": [
        "employeeconnect:overview",
        "employeeconnect:challenge",
        "employeeconnect:approach",
        "employeeconnect:outcome",
        "employeeconnect:technology"
      ],
      "resource_ids": [
        "diagram_process_flow",
        "assumed-component:employeeconnect:approach:process-sequence"
      ],
      "publication_status": "approved"
    }
  ],
  "warnings": [
    "Visual direction is explicitly based on merged VDD assumptions rather than a fully independent visual specification; keep defaults restrained and professional.",
    "No supplied project images, diagrams, screenshots, or case-study media are approved as evidence; resolve visuals with text-led custom treatment.",
    "Most editorial image candidates are decorative and semantically weak for the assigned roles, so they have been declined.",
    "Avoid presenting approved program outcomes as solely individual achievements.",
    "The homepage has moderate recruiter-scannable density, while case studies need deeper reading; preserve clear entry points and avoid walls of prose.",
    "Any animated component must have an immediate static equivalent and must not imply live telemetry or stronger evidence."
  ],
  "scope_hash": "623f00a2f092466049e4c0a74366caa6d73c0ed4537e4eb0fc4cda604ec5eb53",
  "assumptions": [
    "Editorial imagery is decorative and non-evidentiary.",
    "No portrait, screenshot, dashboard, logo, or project proof is allowed.",
    "Component roles are derived from approved route sections and interaction needs.",
    "All visual resources must be local, attributed, and usable without runtime provider calls.",
    "Reduced motion receives a complete static equivalent."
  ],
  "model_calls": 1,
  "provider_calls": 36,
  "resource_index": [
    {
      "status": "candidates_found",
      "need_id": "need-6c7010157537a7aa0002",
      "purpose": "Editorial opening atmosphere for the approved professional practice; no person or product interface.",
      "role_id": "assumed-image:home:hero:0",
      "category": "editorial_photo",
      "guidance": "No editorial photo is necessary for the hero; prefer the approved text-led composition and abstract static motif. If decoration is retained, keep it non-identifying and clearly non-evidentiary.",
      "route_ids": [
        "home"
      ],
      "candidates": [
        {
          "url": "https://pixabay.com/get/g16a58532f1aa5dee22ec8cab417aca0dc897c444b1c72e282969bd5fd0f43a602d7cc66b9aed4c44a1fea1afabcee0f27de34e17c86383c3cc89ab40fc50cf56_1280.jpg",
          "title": "home office, person, work, web design, business, workplace, monitor, computer, keyboard, screen, laptop, office work, independent, freelancer, success, graphic designer, designer, digital, nomad",
          "width": 6720,
          "height": 4480,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "cocoandwifi",
          "preview_url": "https://cdn.pixabay.com/photo/2020/04/02/22/05/home-office-4996834_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "4996834"
        },
        {
          "url": "https://pixabay.com/get/gffa96fca37cfe2ffb33571bdf8aa5767c87f8fa0fc76f25f759fc72501fd571af30489421d5efad823f1d1127aa547b3fe015f335f7803c00121326f675ba4a5_1280.jpg",
          "title": "artist, studio, art, sculpture, workshop, old man, tools, sculptor, creation, exhibit, working, professional, artwork",
          "width": 5524,
          "height": 3687,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "ottawagraphics",
          "preview_url": "https://cdn.pixabay.com/photo/2019/11/12/23/00/artist-4622221_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "4622221"
        },
        {
          "url": "https://pixabay.com/get/g268c1af865bcda8474e70454be6031c1f7da75943fe6afbec4fc831e0ecf123341ed9c8524fdaca10072233be8ec683dedaa5cd4f4c395a9e163901870471706_1280.jpg",
          "title": "office desk, man, business, workplace, workspace, desktop",
          "width": 6720,
          "height": 4480,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "reallywellmadedesks",
          "preview_url": "https://cdn.pixabay.com/photo/2022/01/20/17/51/office-desk-6952919_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "6952919"
        }
      ],
      "primary_candidate_index": null
    },
    {
      "status": "candidates_found",
      "need_id": "need-9b3860cb6dd5f936882d",
      "purpose": "Decorative modular atmosphere for approved capability groups; not evidence or a real interface.",
      "role_id": "assumed-image:home:capabilities:1",
      "category": "editorial_photo",
      "guidance": "Prefer grouped capability text and tonal surfaces over decorative craft imagery; any image must remain subordinate and non-evidentiary.",
      "route_ids": [
        "home"
      ],
      "candidates": [
        {
          "url": "https://pixabay.com/get/g940d2972d6eeb18033f42f74ab4e53a2e99910e9401c7900fca46cada55f5f4ebcad0dd4cfdca0bde046307aed2a228d3ef805212a209c379c7dca6cb7ff51d5_1280.jpg",
          "title": "painting, pencils, paint, pens, watercolor, acrylic, watercolor painting, art tools, art materials",
          "width": 4608,
          "height": 2592,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "bodobe",
          "preview_url": "https://cdn.pixabay.com/photo/2015/08/28/11/37/painting-911804_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "911804"
        },
        {
          "url": "https://pixabay.com/get/gacde75deee8a7ced96a91cd314c468bf9789c44d9d9c862a53a8822d06e0ff911dc7ee36ba08aca6f69201ba90d2d978906527b0e58f3adbdd73e824a8f5363e_1280.jpg",
          "title": "embroidery thread, colorful yarn, crochet, knitting, craft supplies, handmade, needlework, textile art, vibrant colors, yarn balls, sewing, embroidery, thread spools, hobby, diy crafts, home crafts, textile threads, fiber arts, colorful threads, yarn closeup, craft materials, wool, cotton thread, multicolor yarn, creative tools",
          "width": 6000,
          "height": 4000,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "Van3ssa_",
          "preview_url": "https://cdn.pixabay.com/photo/2020/06/01/19/52/embroidery-thread-5248183_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "5248183"
        },
        {
          "url": "https://pixabay.com/get/gac80168a474783d4df0a81734d6eabdccb14d6001a58c860c65f5b1ecd1150c7cb4b0647213297bab56fef7e2e356b1acd7acb62febea3e8e8e224046f082445_1280.jpg",
          "title": "brushes, chalks, colorful, art materials, art supplies, coloring materials, paint, pens, art, artistic, creative",
          "width": 4592,
          "height": 3064,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "fietzfotos",
          "preview_url": "https://cdn.pixabay.com/photo/2017/11/07/18/40/brushes-2927793_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "2927793"
        }
      ],
      "primary_candidate_index": null
    },
    {
      "status": "candidates_found",
      "need_id": "need-62fd6ffaa64f9ab35457",
      "purpose": "Editorial collaboration atmosphere supporting an approved experience timeline.",
      "role_id": "assumed-image:home:experience:2",
      "category": "editorial_photo",
      "guidance": "Use the experience progression as structured text. Omit editorial collaboration imagery unless it is unmistakably decorative and does not imply a specific event or person.",
      "route_ids": [
        "home"
      ],
      "candidates": [
        {
          "url": "https://pixabay.com/get/gfde84b274b6ef0426f9580c47691f734d0d0e6df487158af39aeebed929dff5c7a4b2c6c501c17563da8e73885f57d548fee84afe6f31365adb5d8bf30d621f1_1280.jpg",
          "title": "agreement, brainstorming, coffee, business, cafe, coffee shop, collaboration, corporate, deal, laptop, man, meeting, men, mobile phone, networking, online, planning, table, talking, togetherness, woman, working",
          "width": 6000,
          "height": 4004,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "rawpixel",
          "preview_url": "https://cdn.pixabay.com/photo/2017/07/28/09/35/agreement-2548138_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "2548138"
        },
        {
          "url": "https://pixabay.com/get/g46d8d83de447bddb5b677daa1386f3cca365ffb614ae37b3324cf2f9b4c203abd89ca17ab2f7b3c0ea6ae30e3b737c0725d52f9633419a34d36d5b278d4399e0_1280.jpg",
          "title": "startup, start-up, people, silicon valley, teamwork, business, team, office, group, meeting, corporate, conference, company, men, partnership, table, technology, casual, successful, seminar, colleagues, working, planning, network, strategy, cooperation, professional, notes, notepad, writing, laptop, computer, drinks",
          "width": 5472,
          "height": 3648,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "StartupStockPhotos",
          "preview_url": "https://cdn.pixabay.com/photo/2015/01/08/18/27/startup-593341_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "593341"
        },
        {
          "url": "https://pixabay.com/get/g785dbe04e6eae2bc9d135b2a3b72ecb647ab15da474dde291b02b20091d1dbee979166567e2c5f88a0bd345c8756bf1c0edd5ad3e6534b3a4b506b4463b5157d_1280.jpg",
          "title": "space, interior, design, architecture, wall, frame, meeting, furniture, old, floor, vintage, retro, window",
          "width": 4493,
          "height": 3370,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "uh_yeah_20101995",
          "preview_url": "https://cdn.pixabay.com/photo/2019/11/29/08/34/space-4660847_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "4660847"
        }
      ],
      "primary_candidate_index": null
    },
    {
      "status": "candidates_found",
      "need_id": "need-5b00cc1f3f31408ac825",
      "purpose": "Decorative craft-and-process atmosphere for selected work; no dashboard or screenshot.",
      "role_id": "assumed-image:home:featured-work:3",
      "category": "editorial_photo",
      "guidance": "Selected work should be represented with route labels and abstract treatment, not craft photography that could be mistaken for project evidence.",
      "route_ids": [
        "home"
      ],
      "candidates": [
        {
          "url": "https://pixabay.com/get/g36848d6628c9611faaddd821c53a0e3e2e68eb2403d055345acfec29c78c19c0f1de1a3d92293315094af4560d4cbf267157aa8cd551b91dae2b1f939a9cb273_1280.jpg",
          "title": "silk, yellow, woman, process, work, hand made",
          "width": 5003,
          "height": 3335,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "11153496",
          "preview_url": "https://cdn.pixabay.com/photo/2020/07/24/09/55/silk-5433442_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "5433442"
        },
        {
          "url": "https://pixabay.com/get/g68fcd10c8a4fb30ca8cf94f2dd48901a10cac777d3d2aa5a2d1c54e976680ab5b78d36c700d388a23abc3324c31842ef099adf0a21c3b4319f1f0eb38ecba32e_1280.jpg",
          "title": "cloth, fabrics, fashion design, work, mockup, chaos, tailor, crafts, wallpaper for girls",
          "width": 4096,
          "height": 2730,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "Pexels",
          "preview_url": "https://cdn.pixabay.com/photo/2016/11/18/17/14/cloth-1835894_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "1835894"
        },
        {
          "url": "https://pixabay.com/get/g1226707b68c39c97a88c22707ec40b7757639b961db810e97c0bd50177ea2f6a43112f1b2ef24d310e86ec9bf8a9e5ba75101163cca8abac71c5a60d4782449e_1280.jpg",
          "title": "jeans, trousers, trouser buttons, clothing, blue jeans, blue, fashion, detail shot, textiles, seam, washed out, close up, buttons, style, material, natural substance, denim, work pants",
          "width": 4608,
          "height": 3072,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "652234",
          "preview_url": "https://cdn.pixabay.com/photo/2017/11/26/19/50/jeans-2979818_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "2979818"
        }
      ],
      "primary_candidate_index": null
    },
    {
      "status": "candidates_found",
      "need_id": "need-9b29f305c2aecd039e14",
      "purpose": "Decorative craft-and-process atmosphere for selected work; no dashboard or screenshot.",
      "role_id": "assumed-image:home:proof-points:4",
      "category": "editorial_photo",
      "guidance": "Keep proof values as labelled text and static comparisons; omit decorative imagery if it competes with evidence.",
      "route_ids": [
        "home"
      ],
      "candidates": [
        {
          "url": "https://pixabay.com/get/g36848d6628c9611faaddd821c53a0e3e2e68eb2403d055345acfec29c78c19c0f1de1a3d92293315094af4560d4cbf267157aa8cd551b91dae2b1f939a9cb273_1280.jpg",
          "title": "silk, yellow, woman, process, work, hand made",
          "width": 5003,
          "height": 3335,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "11153496",
          "preview_url": "https://cdn.pixabay.com/photo/2020/07/24/09/55/silk-5433442_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "5433442"
        },
        {
          "url": "https://pixabay.com/get/g68fcd10c8a4fb30ca8cf94f2dd48901a10cac777d3d2aa5a2d1c54e976680ab5b78d36c700d388a23abc3324c31842ef099adf0a21c3b4319f1f0eb38ecba32e_1280.jpg",
          "title": "cloth, fabrics, fashion design, work, mockup, chaos, tailor, crafts, wallpaper for girls",
          "width": 4096,
          "height": 2730,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "Pexels",
          "preview_url": "https://cdn.pixabay.com/photo/2016/11/18/17/14/cloth-1835894_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "1835894"
        },
        {
          "url": "https://pixabay.com/get/g1226707b68c39c97a88c22707ec40b7757639b961db810e97c0bd50177ea2f6a43112f1b2ef24d310e86ec9bf8a9e5ba75101163cca8abac71c5a60d4782449e_1280.jpg",
          "title": "jeans, trousers, trouser buttons, clothing, blue jeans, blue, fashion, detail shot, textiles, seam, washed out, close up, buttons, style, material, natural substance, denim, work pants",
          "width": 4608,
          "height": 3072,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "652234",
          "preview_url": "https://cdn.pixabay.com/photo/2017/11/26/19/50/jeans-2979818_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "2979818"
        }
      ],
      "primary_candidate_index": null
    },
    {
      "status": "candidates_found",
      "need_id": "need-1245adde715aa2c70864",
      "purpose": "Decorative craft-and-process atmosphere for selected work; no dashboard or screenshot.",
      "role_id": "assumed-image:workspace360:approach:5",
      "category": "editorial_photo",
      "guidance": "Do not use this decorative candidate to depict the WorkSpace360 approach. Prefer the words-first process visual.",
      "route_ids": [
        "workspace360"
      ],
      "candidates": [
        {
          "url": "https://pixabay.com/get/g36848d6628c9611faaddd821c53a0e3e2e68eb2403d055345acfec29c78c19c0f1de1a3d92293315094af4560d4cbf267157aa8cd551b91dae2b1f939a9cb273_1280.jpg",
          "title": "silk, yellow, woman, process, work, hand made",
          "width": 5003,
          "height": 3335,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "11153496",
          "preview_url": "https://cdn.pixabay.com/photo/2020/07/24/09/55/silk-5433442_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "5433442"
        },
        {
          "url": "https://pixabay.com/get/g68fcd10c8a4fb30ca8cf94f2dd48901a10cac777d3d2aa5a2d1c54e976680ab5b78d36c700d388a23abc3324c31842ef099adf0a21c3b4319f1f0eb38ecba32e_1280.jpg",
          "title": "cloth, fabrics, fashion design, work, mockup, chaos, tailor, crafts, wallpaper for girls",
          "width": 4096,
          "height": 2730,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "Pexels",
          "preview_url": "https://cdn.pixabay.com/photo/2016/11/18/17/14/cloth-1835894_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "1835894"
        },
        {
          "url": "https://pixabay.com/get/g1226707b68c39c97a88c22707ec40b7757639b961db810e97c0bd50177ea2f6a43112f1b2ef24d310e86ec9bf8a9e5ba75101163cca8abac71c5a60d4782449e_1280.jpg",
          "title": "jeans, trousers, trouser buttons, clothing, blue jeans, blue, fashion, detail shot, textiles, seam, washed out, close up, buttons, style, material, natural substance, denim, work pants",
          "width": 4608,
          "height": 3072,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "652234",
          "preview_url": "https://cdn.pixabay.com/photo/2017/11/26/19/50/jeans-2979818_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "2979818"
        }
      ],
      "primary_candidate_index": null
    },
    {
      "status": "candidates_found",
      "need_id": "need-ce4959e396c7d4459465",
      "purpose": "Decorative craft-and-process atmosphere for selected work; no dashboard or screenshot.",
      "role_id": "assumed-image:workspace360:challenge:6",
      "category": "editorial_photo",
      "guidance": "Keep the challenge scene abstract and textual; omit decorative craft imagery.",
      "route_ids": [
        "workspace360"
      ],
      "candidates": [
        {
          "url": "https://pixabay.com/get/g36848d6628c9611faaddd821c53a0e3e2e68eb2403d055345acfec29c78c19c0f1de1a3d92293315094af4560d4cbf267157aa8cd551b91dae2b1f939a9cb273_1280.jpg",
          "title": "silk, yellow, woman, process, work, hand made",
          "width": 5003,
          "height": 3335,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "11153496",
          "preview_url": "https://cdn.pixabay.com/photo/2020/07/24/09/55/silk-5433442_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "5433442"
        },
        {
          "url": "https://pixabay.com/get/g68fcd10c8a4fb30ca8cf94f2dd48901a10cac777d3d2aa5a2d1c54e976680ab5b78d36c700d388a23abc3324c31842ef099adf0a21c3b4319f1f0eb38ecba32e_1280.jpg",
          "title": "cloth, fabrics, fashion design, work, mockup, chaos, tailor, crafts, wallpaper for girls",
          "width": 4096,
          "height": 2730,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "Pexels",
          "preview_url": "https://cdn.pixabay.com/photo/2016/11/18/17/14/cloth-1835894_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "1835894"
        },
        {
          "url": "https://pixabay.com/get/g1226707b68c39c97a88c22707ec40b7757639b961db810e97c0bd50177ea2f6a43112f1b2ef24d310e86ec9bf8a9e5ba75101163cca8abac71c5a60d4782449e_1280.jpg",
          "title": "jeans, trousers, trouser buttons, clothing, blue jeans, blue, fashion, detail shot, textiles, seam, washed out, close up, buttons, style, material, natural substance, denim, work pants",
          "width": 4608,
          "height": 3072,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "652234",
          "preview_url": "https://cdn.pixabay.com/photo/2017/11/26/19/50/jeans-2979818_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "2979818"
        }
      ],
      "primary_candidate_index": null
    },
    {
      "status": "candidates_found",
      "need_id": "need-37b42d749a51d7474de4",
      "purpose": "Decorative craft-and-process atmosphere for selected work; no dashboard or screenshot.",
      "role_id": "assumed-image:workspace360:outcome:7",
      "category": "editorial_photo",
      "guidance": "The result needs a clear static comparison, not decorative photography.",
      "route_ids": [
        "workspace360"
      ],
      "candidates": [
        {
          "url": "https://pixabay.com/get/g36848d6628c9611faaddd821c53a0e3e2e68eb2403d055345acfec29c78c19c0f1de1a3d92293315094af4560d4cbf267157aa8cd551b91dae2b1f939a9cb273_1280.jpg",
          "title": "silk, yellow, woman, process, work, hand made",
          "width": 5003,
          "height": 3335,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "11153496",
          "preview_url": "https://cdn.pixabay.com/photo/2020/07/24/09/55/silk-5433442_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "5433442"
        },
        {
          "url": "https://pixabay.com/get/g68fcd10c8a4fb30ca8cf94f2dd48901a10cac777d3d2aa5a2d1c54e976680ab5b78d36c700d388a23abc3324c31842ef099adf0a21c3b4319f1f0eb38ecba32e_1280.jpg",
          "title": "cloth, fabrics, fashion design, work, mockup, chaos, tailor, crafts, wallpaper for girls",
          "width": 4096,
          "height": 2730,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "Pexels",
          "preview_url": "https://cdn.pixabay.com/photo/2016/11/18/17/14/cloth-1835894_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "1835894"
        },
        {
          "url": "https://pixabay.com/get/g1226707b68c39c97a88c22707ec40b7757639b961db810e97c0bd50177ea2f6a43112f1b2ef24d310e86ec9bf8a9e5ba75101163cca8abac71c5a60d4782449e_1280.jpg",
          "title": "jeans, trousers, trouser buttons, clothing, blue jeans, blue, fashion, detail shot, textiles, seam, washed out, close up, buttons, style, material, natural substance, denim, work pants",
          "width": 4608,
          "height": 3072,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "652234",
          "preview_url": "https://cdn.pixabay.com/photo/2017/11/26/19/50/jeans-2979818_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "2979818"
        }
      ],
      "primary_candidate_index": null
    },
    {
      "status": "candidates_found",
      "need_id": "need-347d4e372dd15c465512",
      "purpose": "Decorative craft-and-process atmosphere for selected work; no dashboard or screenshot.",
      "role_id": "assumed-image:workspace360:overview:8",
      "category": "editorial_photo",
      "guidance": "Use the overview copy and abstract workflow treatment; omit unrelated editorial imagery.",
      "route_ids": [
        "workspace360"
      ],
      "candidates": [
        {
          "url": "https://pixabay.com/get/g36848d6628c9611faaddd821c53a0e3e2e68eb2403d055345acfec29c78c19c0f1de1a3d92293315094af4560d4cbf267157aa8cd551b91dae2b1f939a9cb273_1280.jpg",
          "title": "silk, yellow, woman, process, work, hand made",
          "width": 5003,
          "height": 3335,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "11153496",
          "preview_url": "https://cdn.pixabay.com/photo/2020/07/24/09/55/silk-5433442_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "5433442"
        },
        {
          "url": "https://pixabay.com/get/g68fcd10c8a4fb30ca8cf94f2dd48901a10cac777d3d2aa5a2d1c54e976680ab5b78d36c700d388a23abc3324c31842ef099adf0a21c3b4319f1f0eb38ecba32e_1280.jpg",
          "title": "cloth, fabrics, fashion design, work, mockup, chaos, tailor, crafts, wallpaper for girls",
          "width": 4096,
          "height": 2730,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "Pexels",
          "preview_url": "https://cdn.pixabay.com/photo/2016/11/18/17/14/cloth-1835894_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "1835894"
        },
        {
          "url": "https://pixabay.com/get/g1226707b68c39c97a88c22707ec40b7757639b961db810e97c0bd50177ea2f6a43112f1b2ef24d310e86ec9bf8a9e5ba75101163cca8abac71c5a60d4782449e_1280.jpg",
          "title": "jeans, trousers, trouser buttons, clothing, blue jeans, blue, fashion, detail shot, textiles, seam, washed out, close up, buttons, style, material, natural substance, denim, work pants",
          "width": 4608,
          "height": 3072,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "652234",
          "preview_url": "https://cdn.pixabay.com/photo/2017/11/26/19/50/jeans-2979818_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "2979818"
        }
      ],
      "primary_candidate_index": null
    },
    {
      "status": "candidates_found",
      "need_id": "need-0153c0bebc4e182c61e3",
      "purpose": "Decorative craft-and-process atmosphere for selected work; no dashboard or screenshot.",
      "role_id": "assumed-image:workspace360:technology:9",
      "category": "editorial_photo",
      "guidance": "Keep technology context compact and text-led; no decorative image is needed.",
      "route_ids": [
        "workspace360"
      ],
      "candidates": [
        {
          "url": "https://pixabay.com/get/g36848d6628c9611faaddd821c53a0e3e2e68eb2403d055345acfec29c78c19c0f1de1a3d92293315094af4560d4cbf267157aa8cd551b91dae2b1f939a9cb273_1280.jpg",
          "title": "silk, yellow, woman, process, work, hand made",
          "width": 5003,
          "height": 3335,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "11153496",
          "preview_url": "https://cdn.pixabay.com/photo/2020/07/24/09/55/silk-5433442_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "5433442"
        },
        {
          "url": "https://pixabay.com/get/g68fcd10c8a4fb30ca8cf94f2dd48901a10cac777d3d2aa5a2d1c54e976680ab5b78d36c700d388a23abc3324c31842ef099adf0a21c3b4319f1f0eb38ecba32e_1280.jpg",
          "title": "cloth, fabrics, fashion design, work, mockup, chaos, tailor, crafts, wallpaper for girls",
          "width": 4096,
          "height": 2730,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "Pexels",
          "preview_url": "https://cdn.pixabay.com/photo/2016/11/18/17/14/cloth-1835894_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "1835894"
        },
        {
          "url": "https://pixabay.com/get/g1226707b68c39c97a88c22707ec40b7757639b961db810e97c0bd50177ea2f6a43112f1b2ef24d310e86ec9bf8a9e5ba75101163cca8abac71c5a60d4782449e_1280.jpg",
          "title": "jeans, trousers, trouser buttons, clothing, blue jeans, blue, fashion, detail shot, textiles, seam, washed out, close up, buttons, style, material, natural substance, denim, work pants",
          "width": 4608,
          "height": 3072,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "652234",
          "preview_url": "https://cdn.pixabay.com/photo/2017/11/26/19/50/jeans-2979818_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "2979818"
        }
      ],
      "primary_candidate_index": null
    },
    {
      "status": "candidates_found",
      "need_id": "need-ce945df3392dd866ff08",
      "purpose": "Editorial process atmosphere for the approved working approach; no invented project evidence.",
      "role_id": "assumed-image:employeeconnect:approach:10",
      "category": "editorial_photo",
      "guidance": "Prefer the custom migration sequence. Any process photo would be decorative only and should not imply project evidence.",
      "route_ids": [
        "employeeconnect"
      ],
      "candidates": [
        {
          "url": "https://pixabay.com/get/gb8bb7ce988ee6f470fa14614a945fd4c52f4eea180ed289d18fbc89862c51b93a31e68b6263a270c206209181949c5da8d409f1604839896a107007d7ad5264f_1280.jpg",
          "title": "kanban, work, team, work process, to organize, business, office, structure, organization, workflow, development, planning, management, success, company",
          "width": 6000,
          "height": 4000,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "geralt",
          "preview_url": "https://cdn.pixabay.com/photo/2019/03/14/08/21/kanban-4054380_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "4054380"
        },
        {
          "url": "https://pixabay.com/get/g8fff350c5f2720ed4803cd5cc805f360307db8d575b95ee0ceb0e44292146f06c33e2d4083c6c12a42322ab374366224101fd0d6bbff6f355b043de604481922_1280.jpg",
          "title": "whiteboard, kanban, work, work process, to organize, structure, workflow, development, business, planning, management, success, company",
          "width": 3704,
          "height": 2413,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "geralt",
          "preview_url": "https://cdn.pixabay.com/photo/2019/03/14/08/21/whiteboard-4054377_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "4054377"
        },
        {
          "url": "https://pixabay.com/get/gddb15110b5a71c5ec5f2d7d785c3f2872ab401b08db1cdc09e269b50567c2d0f73abc533f6bcdaa20191bdb9e109c76b6472643fe0027349558e6a1f6e3621ee_1280.jpg",
          "title": "work, work process, to organize, business, office, team, structure, organization, workflow, development, planning, management, success, company",
          "width": 4200,
          "height": 2578,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "geralt",
          "preview_url": "https://cdn.pixabay.com/photo/2019/03/12/20/27/work-4051777_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "4051777"
        }
      ],
      "primary_candidate_index": null
    },
    {
      "status": "candidates_found",
      "need_id": "need-e0ce25ddcdf2ad5b70fa",
      "purpose": "Editorial process atmosphere for the approved working approach; no invented project evidence.",
      "role_id": "assumed-image:secureendpoint:approach:11",
      "category": "editorial_photo",
      "guidance": "Use the abstract control chain and supplied approach text rather than unrelated process photography.",
      "route_ids": [
        "secureendpoint"
      ],
      "candidates": [
        {
          "url": "https://pixabay.com/get/gb8bb7ce988ee6f470fa14614a945fd4c52f4eea180ed289d18fbc89862c51b93a31e68b6263a270c206209181949c5da8d409f1604839896a107007d7ad5264f_1280.jpg",
          "title": "kanban, work, team, work process, to organize, business, office, structure, organization, workflow, development, planning, management, success, company",
          "width": 6000,
          "height": 4000,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "geralt",
          "preview_url": "https://cdn.pixabay.com/photo/2019/03/14/08/21/kanban-4054380_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "4054380"
        },
        {
          "url": "https://pixabay.com/get/g8fff350c5f2720ed4803cd5cc805f360307db8d575b95ee0ceb0e44292146f06c33e2d4083c6c12a42322ab374366224101fd0d6bbff6f355b043de604481922_1280.jpg",
          "title": "whiteboard, kanban, work, work process, to organize, structure, workflow, development, business, planning, management, success, company",
          "width": 3704,
          "height": 2413,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "geralt",
          "preview_url": "https://cdn.pixabay.com/photo/2019/03/14/08/21/whiteboard-4054377_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "4054377"
        },
        {
          "url": "https://pixabay.com/get/gddb15110b5a71c5ec5f2d7d785c3f2872ab401b08db1cdc09e269b50567c2d0f73abc533f6bcdaa20191bdb9e109c76b6472643fe0027349558e6a1f6e3621ee_1280.jpg",
          "title": "work, work process, to organize, business, office, team, structure, organization, workflow, development, planning, management, success, company",
          "width": 4200,
          "height": 2578,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "geralt",
          "preview_url": "https://cdn.pixabay.com/photo/2019/03/12/20/27/work-4051777_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "4051777"
        }
      ],
      "primary_candidate_index": null
    },
    {
      "status": "candidates_found",
      "need_id": "need-4ad70a6d615bdfe3ce52",
      "purpose": "Non-evidentiary closing atmosphere for a professional connection CTA.",
      "role_id": "assumed-image:employeeconnect:challenge:12",
      "category": "editorial_photo",
      "guidance": "No closing atmosphere is needed for the challenge role; keep the scene focused on approved content.",
      "route_ids": [
        "employeeconnect"
      ],
      "candidates": [
        {
          "url": "https://pixabay.com/get/g898505a95163175cf602fd5f2ed3e1ae81575060084751e3a6cecc0bbf94ef5e600672567f2a7efeaf01786102fcdec53b4eb8c3d249ab33e1bf7a51687b0f80_1280.jpg",
          "title": "team, friendship, group, hands, cooperation, people, community, connection, relationship, friendship day",
          "width": 5616,
          "height": 3744,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "ua_Bob_Dmyt_ua",
          "preview_url": "https://cdn.pixabay.com/photo/2019/10/06/10/03/team-4529717_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "4529717"
        },
        {
          "url": "https://pixabay.com/get/ge342bff28f9557eb26cc1f22e64ad876416e9db673d2735ecf159223639c1dfdc49cdbda91180fdf8c040a95f48060b13df94f4edacc94248cbb9ec0a50d0d38_1280.jpg",
          "title": "team, group, people, motivation, teamwork, together, community, group work, cooperation, cooperate, group of people, collective, hands, feet",
          "width": 2560,
          "height": 1920,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "Henning_W",
          "preview_url": "https://cdn.pixabay.com/photo/2014/07/08/10/47/team-386673_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "386673"
        },
        {
          "url": "https://pixabay.com/get/geb3815420506902283ac01b16fc5f2f21a26af559d5a1adf7900595fd9328a6297f63ed7adc4cdda699b04ddb937b90355e52a8a563f9a5621027d40f3db6aa6_1280.jpg",
          "title": "people, group, friends, concept, agreement, fist bump, lifestyle, team, teamwork, cooperation, cooperate, together, togetherness",
          "width": 2592,
          "height": 1769,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "StockSnap",
          "preview_url": "https://cdn.pixabay.com/photo/2017/08/02/00/49/people-2569234_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "2569234"
        }
      ],
      "primary_candidate_index": null
    },
    {
      "status": "candidates_found",
      "need_id": "need-a2d889f2cc5739b5b00e",
      "purpose": "Non-evidentiary closing atmosphere for a professional connection CTA.",
      "role_id": "assumed-image:employeeconnect:outcome:13",
      "category": "editorial_photo",
      "guidance": "Keep the outcome focused on the approved scale and context; omit generic teamwork imagery if it adds unsupported implication.",
      "route_ids": [
        "employeeconnect"
      ],
      "candidates": [
        {
          "url": "https://pixabay.com/get/gff5a10491c2e3671a9a237f5bd52faf19cfe99056ee0762f03f685ca699896d6b052463462e739a1a2104d9cd0d294deb80d2465a29be7405e4b16a7fc092cb0_1280.jpg",
          "title": "startup, start-up, people, silicon valley, teamwork, business, team, office, group, meeting, corporate, conference, company, men, partnership, table, technology, casual, successful, seminar, colleagues, working, planning, network, strategy, cooperation, professional, notes, notepad, writing, laptop, computer, drinks",
          "width": 5472,
          "height": 3648,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "StartupStockPhotos",
          "preview_url": "https://cdn.pixabay.com/photo/2015/01/08/18/27/startup-593341_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "593341"
        },
        {
          "url": "https://pixabay.com/get/g898505a95163175cf602fd5f2ed3e1ae81575060084751e3a6cecc0bbf94ef5e600672567f2a7efeaf01786102fcdec53b4eb8c3d249ab33e1bf7a51687b0f80_1280.jpg",
          "title": "team, friendship, group, hands, cooperation, people, community, connection, relationship, friendship day",
          "width": 5616,
          "height": 3744,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "ua_Bob_Dmyt_ua",
          "preview_url": "https://cdn.pixabay.com/photo/2019/10/06/10/03/team-4529717_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "4529717"
        },
        {
          "url": "https://pixabay.com/get/ge342bff28f9557eb26cc1f22e64ad876416e9db673d2735ecf159223639c1dfdc49cdbda91180fdf8c040a95f48060b13df94f4edacc94248cbb9ec0a50d0d38_1280.jpg",
          "title": "team, group, people, motivation, teamwork, together, community, group work, cooperation, cooperate, group of people, collective, hands, feet",
          "width": 2560,
          "height": 1920,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "Henning_W",
          "preview_url": "https://cdn.pixabay.com/photo/2014/07/08/10/47/team-386673_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "386673"
        }
      ],
      "primary_candidate_index": null
    },
    {
      "status": "candidates_found",
      "need_id": "need-60cfe22b273f2fba7ed1",
      "purpose": "Non-evidentiary closing atmosphere for a professional connection CTA.",
      "role_id": "assumed-image:employeeconnect:overview:14",
      "category": "editorial_photo",
      "guidance": "Use text-led overview and abstract migration treatment; decorative teamwork imagery is optional and non-evidentiary only.",
      "route_ids": [
        "employeeconnect"
      ],
      "candidates": [
        {
          "url": "https://pixabay.com/get/gff5a10491c2e3671a9a237f5bd52faf19cfe99056ee0762f03f685ca699896d6b052463462e739a1a2104d9cd0d294deb80d2465a29be7405e4b16a7fc092cb0_1280.jpg",
          "title": "startup, start-up, people, silicon valley, teamwork, business, team, office, group, meeting, corporate, conference, company, men, partnership, table, technology, casual, successful, seminar, colleagues, working, planning, network, strategy, cooperation, professional, notes, notepad, writing, laptop, computer, drinks",
          "width": 5472,
          "height": 3648,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "StartupStockPhotos",
          "preview_url": "https://cdn.pixabay.com/photo/2015/01/08/18/27/startup-593341_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "593341"
        },
        {
          "url": "https://pixabay.com/get/g898505a95163175cf602fd5f2ed3e1ae81575060084751e3a6cecc0bbf94ef5e600672567f2a7efeaf01786102fcdec53b4eb8c3d249ab33e1bf7a51687b0f80_1280.jpg",
          "title": "team, friendship, group, hands, cooperation, people, community, connection, relationship, friendship day",
          "width": 5616,
          "height": 3744,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "ua_Bob_Dmyt_ua",
          "preview_url": "https://cdn.pixabay.com/photo/2019/10/06/10/03/team-4529717_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "4529717"
        },
        {
          "url": "https://pixabay.com/get/ge342bff28f9557eb26cc1f22e64ad876416e9db673d2735ecf159223639c1dfdc49cdbda91180fdf8c040a95f48060b13df94f4edacc94248cbb9ec0a50d0d38_1280.jpg",
          "title": "team, group, people, motivation, teamwork, together, community, group work, cooperation, cooperate, group of people, collective, hands, feet",
          "width": 2560,
          "height": 1920,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "Henning_W",
          "preview_url": "https://cdn.pixabay.com/photo/2014/07/08/10/47/team-386673_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "386673"
        }
      ],
      "primary_candidate_index": null
    },
    {
      "status": "candidates_found",
      "need_id": "need-89d35155ec0741b0f255",
      "purpose": "Non-evidentiary closing atmosphere for a professional connection CTA.",
      "role_id": "assumed-image:employeeconnect:technology:15",
      "category": "editorial_photo",
      "guidance": "Technology context should remain compact and textual; omit unrelated editorial imagery.",
      "route_ids": [
        "employeeconnect"
      ],
      "candidates": [
        {
          "url": "https://pixabay.com/get/gff5a10491c2e3671a9a237f5bd52faf19cfe99056ee0762f03f685ca699896d6b052463462e739a1a2104d9cd0d294deb80d2465a29be7405e4b16a7fc092cb0_1280.jpg",
          "title": "startup, start-up, people, silicon valley, teamwork, business, team, office, group, meeting, corporate, conference, company, men, partnership, table, technology, casual, successful, seminar, colleagues, working, planning, network, strategy, cooperation, professional, notes, notepad, writing, laptop, computer, drinks",
          "width": 5472,
          "height": 3648,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "StartupStockPhotos",
          "preview_url": "https://cdn.pixabay.com/photo/2015/01/08/18/27/startup-593341_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "593341"
        },
        {
          "url": "https://pixabay.com/get/g898505a95163175cf602fd5f2ed3e1ae81575060084751e3a6cecc0bbf94ef5e600672567f2a7efeaf01786102fcdec53b4eb8c3d249ab33e1bf7a51687b0f80_1280.jpg",
          "title": "team, friendship, group, hands, cooperation, people, community, connection, relationship, friendship day",
          "width": 5616,
          "height": 3744,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "ua_Bob_Dmyt_ua",
          "preview_url": "https://cdn.pixabay.com/photo/2019/10/06/10/03/team-4529717_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "4529717"
        },
        {
          "url": "https://pixabay.com/get/ge342bff28f9557eb26cc1f22e64ad876416e9db673d2735ecf159223639c1dfdc49cdbda91180fdf8c040a95f48060b13df94f4edacc94248cbb9ec0a50d0d38_1280.jpg",
          "title": "team, group, people, motivation, teamwork, together, community, group work, cooperation, cooperate, group of people, collective, hands, feet",
          "width": 2560,
          "height": 1920,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "Henning_W",
          "preview_url": "https://cdn.pixabay.com/photo/2014/07/08/10/47/team-386673_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "386673"
        }
      ],
      "primary_candidate_index": null
    },
    {
      "status": "candidates_found",
      "need_id": "need-75544073a0565c50677b",
      "purpose": "Non-evidentiary closing atmosphere for a professional connection CTA.",
      "role_id": "assumed-image:home:contact:16",
      "category": "editorial_photo",
      "guidance": "Close with the approved action and quiet surfaces; generic teamwork imagery is unnecessary.",
      "route_ids": [
        "home"
      ],
      "candidates": [
        {
          "url": "https://pixabay.com/get/gff5a10491c2e3671a9a237f5bd52faf19cfe99056ee0762f03f685ca699896d6b052463462e739a1a2104d9cd0d294deb80d2465a29be7405e4b16a7fc092cb0_1280.jpg",
          "title": "startup, start-up, people, silicon valley, teamwork, business, team, office, group, meeting, corporate, conference, company, men, partnership, table, technology, casual, successful, seminar, colleagues, working, planning, network, strategy, cooperation, professional, notes, notepad, writing, laptop, computer, drinks",
          "width": 5472,
          "height": 3648,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "StartupStockPhotos",
          "preview_url": "https://cdn.pixabay.com/photo/2015/01/08/18/27/startup-593341_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "593341"
        },
        {
          "url": "https://pixabay.com/get/g898505a95163175cf602fd5f2ed3e1ae81575060084751e3a6cecc0bbf94ef5e600672567f2a7efeaf01786102fcdec53b4eb8c3d249ab33e1bf7a51687b0f80_1280.jpg",
          "title": "team, friendship, group, hands, cooperation, people, community, connection, relationship, friendship day",
          "width": 5616,
          "height": 3744,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "ua_Bob_Dmyt_ua",
          "preview_url": "https://cdn.pixabay.com/photo/2019/10/06/10/03/team-4529717_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "4529717"
        },
        {
          "url": "https://pixabay.com/get/ge342bff28f9557eb26cc1f22e64ad876416e9db673d2735ecf159223639c1dfdc49cdbda91180fdf8c040a95f48060b13df94f4edacc94248cbb9ec0a50d0d38_1280.jpg",
          "title": "team, group, people, motivation, teamwork, together, community, group work, cooperation, cooperate, group of people, collective, hands, feet",
          "width": 2560,
          "height": 1920,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "Henning_W",
          "preview_url": "https://cdn.pixabay.com/photo/2014/07/08/10/47/team-386673_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "386673"
        }
      ],
      "primary_candidate_index": null
    },
    {
      "status": "candidates_found",
      "need_id": "need-7518cc20ca7e14d1e9e5",
      "purpose": "Quiet decorative atmosphere for a supporting section whose subject is not one of the named roles above; kept profession-neutral rather than assumed technical.",
      "role_id": "assumed-image:home:credentials:17",
      "category": "editorial_photo",
      "guidance": "Credentials should remain profession-neutral and supporting; prefer a quiet surface or omit the decorative image.",
      "route_ids": [
        "home"
      ],
      "candidates": [
        {
          "url": "https://pixabay.com/get/g802c42ced1fcee2d81abc510ed78310c8be3bab5158a398eb1ff2fdb767c2a0ee7b2a73b280d0e3c1708429e349383f3e67b24f5a59b347843dd096b046000c3_1280.jpg",
          "title": "library, wisdom, reading, knowledge, education, study, read, book",
          "width": 5000,
          "height": 3333,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "mirkostoedter",
          "preview_url": "https://cdn.pixabay.com/photo/2023/01/15/16/20/library-7720589_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "7720589"
        },
        {
          "url": "https://pixabay.com/get/gdbb82afc2b894c3d0adb3d71a08052d87aafbfd834a23a593691d332e9140f65bf3ed93eb3a5fd4e87b1910c31142106b6fb5628396d1830b51e3727d7e47a77_1280.jpg",
          "title": "aluminum foil, abstract, texture, material, shine, aluminum",
          "width": 6000,
          "height": 4000,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "analogicus",
          "preview_url": "https://cdn.pixabay.com/photo/2022/01/23/18/37/aluminum-foil-6961638_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "6961638"
        },
        {
          "url": "https://pixabay.com/get/gd62df20451de88949c0c2131f63062c6b15d1684d351cdf186f280b011d7aeb82f6b20ba76b411c35d09917bc7a6febe48f28ba18d1a2161909e73c03515eaaf_1280.jpg",
          "title": "paper, beautiful wallpaper, texture, free background, wrapping paper, 4k wallpaper, 4k wallpaper 1920x1080, wallpaper hd, hd wallpaper, windows wallpaper, full hd wallpaper, background, crumples, collage, mac wallpaper, free wallpaper, laptop wallpaper, desktop backgrounds, wallpaper 4k, cool backgrounds, structure, unlabeled",
          "width": 5184,
          "height": 3456,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "KAVOWO",
          "preview_url": "https://cdn.pixabay.com/photo/2018/02/15/14/37/paper-3155438_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "3155438"
        }
      ],
      "primary_candidate_index": null
    },
    {
      "status": "candidates_found",
      "need_id": "need-f6bcecdd26d4469c08c5",
      "purpose": "Quiet decorative atmosphere for a supporting section whose subject is not one of the named roles above; kept profession-neutral rather than assumed technical.",
      "role_id": "assumed-image:secureendpoint:challenge:18",
      "category": "editorial_photo",
      "guidance": "Keep the security challenge textual and abstract; do not use a generic texture as evidence.",
      "route_ids": [
        "secureendpoint"
      ],
      "candidates": [
        {
          "url": "https://pixabay.com/get/g802c42ced1fcee2d81abc510ed78310c8be3bab5158a398eb1ff2fdb767c2a0ee7b2a73b280d0e3c1708429e349383f3e67b24f5a59b347843dd096b046000c3_1280.jpg",
          "title": "library, wisdom, reading, knowledge, education, study, read, book",
          "width": 5000,
          "height": 3333,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "mirkostoedter",
          "preview_url": "https://cdn.pixabay.com/photo/2023/01/15/16/20/library-7720589_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "7720589"
        },
        {
          "url": "https://pixabay.com/get/gdbb82afc2b894c3d0adb3d71a08052d87aafbfd834a23a593691d332e9140f65bf3ed93eb3a5fd4e87b1910c31142106b6fb5628396d1830b51e3727d7e47a77_1280.jpg",
          "title": "aluminum foil, abstract, texture, material, shine, aluminum",
          "width": 6000,
          "height": 4000,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "analogicus",
          "preview_url": "https://cdn.pixabay.com/photo/2022/01/23/18/37/aluminum-foil-6961638_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "6961638"
        },
        {
          "url": "https://pixabay.com/get/gd62df20451de88949c0c2131f63062c6b15d1684d351cdf186f280b011d7aeb82f6b20ba76b411c35d09917bc7a6febe48f28ba18d1a2161909e73c03515eaaf_1280.jpg",
          "title": "paper, beautiful wallpaper, texture, free background, wrapping paper, 4k wallpaper, 4k wallpaper 1920x1080, wallpaper hd, hd wallpaper, windows wallpaper, full hd wallpaper, background, crumples, collage, mac wallpaper, free wallpaper, laptop wallpaper, desktop backgrounds, wallpaper 4k, cool backgrounds, structure, unlabeled",
          "width": 5184,
          "height": 3456,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "KAVOWO",
          "preview_url": "https://cdn.pixabay.com/photo/2018/02/15/14/37/paper-3155438_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "3155438"
        }
      ],
      "primary_candidate_index": null
    },
    {
      "status": "candidates_found",
      "need_id": "need-2af5fc8d108ec85b1d08",
      "purpose": "Quiet decorative atmosphere for a supporting section whose subject is not one of the named roles above; kept profession-neutral rather than assumed technical.",
      "role_id": "assumed-image:secureendpoint:outcome:19",
      "category": "editorial_photo",
      "guidance": "Use the approved result comparison and explanation; no decorative image is needed.",
      "route_ids": [
        "secureendpoint"
      ],
      "candidates": [
        {
          "url": "https://pixabay.com/get/g802c42ced1fcee2d81abc510ed78310c8be3bab5158a398eb1ff2fdb767c2a0ee7b2a73b280d0e3c1708429e349383f3e67b24f5a59b347843dd096b046000c3_1280.jpg",
          "title": "library, wisdom, reading, knowledge, education, study, read, book",
          "width": 5000,
          "height": 3333,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "mirkostoedter",
          "preview_url": "https://cdn.pixabay.com/photo/2023/01/15/16/20/library-7720589_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "7720589"
        },
        {
          "url": "https://pixabay.com/get/gdbb82afc2b894c3d0adb3d71a08052d87aafbfd834a23a593691d332e9140f65bf3ed93eb3a5fd4e87b1910c31142106b6fb5628396d1830b51e3727d7e47a77_1280.jpg",
          "title": "aluminum foil, abstract, texture, material, shine, aluminum",
          "width": 6000,
          "height": 4000,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "analogicus",
          "preview_url": "https://cdn.pixabay.com/photo/2022/01/23/18/37/aluminum-foil-6961638_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "6961638"
        },
        {
          "url": "https://pixabay.com/get/gd62df20451de88949c0c2131f63062c6b15d1684d351cdf186f280b011d7aeb82f6b20ba76b411c35d09917bc7a6febe48f28ba18d1a2161909e73c03515eaaf_1280.jpg",
          "title": "paper, beautiful wallpaper, texture, free background, wrapping paper, 4k wallpaper, 4k wallpaper 1920x1080, wallpaper hd, hd wallpaper, windows wallpaper, full hd wallpaper, background, crumples, collage, mac wallpaper, free wallpaper, laptop wallpaper, desktop backgrounds, wallpaper 4k, cool backgrounds, structure, unlabeled",
          "width": 5184,
          "height": 3456,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "KAVOWO",
          "preview_url": "https://cdn.pixabay.com/photo/2018/02/15/14/37/paper-3155438_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "3155438"
        }
      ],
      "primary_candidate_index": null
    },
    {
      "status": "candidates_found",
      "need_id": "need-989bb622f62c86c0ee1c",
      "purpose": "Quiet decorative atmosphere for a supporting section whose subject is not one of the named roles above; kept profession-neutral rather than assumed technical.",
      "role_id": "assumed-image:secureendpoint:overview:20",
      "category": "editorial_photo",
      "guidance": "Keep the security overview words-first and clearly non-dashboard-like.",
      "route_ids": [
        "secureendpoint"
      ],
      "candidates": [
        {
          "url": "https://pixabay.com/get/g802c42ced1fcee2d81abc510ed78310c8be3bab5158a398eb1ff2fdb767c2a0ee7b2a73b280d0e3c1708429e349383f3e67b24f5a59b347843dd096b046000c3_1280.jpg",
          "title": "library, wisdom, reading, knowledge, education, study, read, book",
          "width": 5000,
          "height": 3333,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "mirkostoedter",
          "preview_url": "https://cdn.pixabay.com/photo/2023/01/15/16/20/library-7720589_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "7720589"
        },
        {
          "url": "https://pixabay.com/get/gdbb82afc2b894c3d0adb3d71a08052d87aafbfd834a23a593691d332e9140f65bf3ed93eb3a5fd4e87b1910c31142106b6fb5628396d1830b51e3727d7e47a77_1280.jpg",
          "title": "aluminum foil, abstract, texture, material, shine, aluminum",
          "width": 6000,
          "height": 4000,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "analogicus",
          "preview_url": "https://cdn.pixabay.com/photo/2022/01/23/18/37/aluminum-foil-6961638_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "6961638"
        },
        {
          "url": "https://pixabay.com/get/gd62df20451de88949c0c2131f63062c6b15d1684d351cdf186f280b011d7aeb82f6b20ba76b411c35d09917bc7a6febe48f28ba18d1a2161909e73c03515eaaf_1280.jpg",
          "title": "paper, beautiful wallpaper, texture, free background, wrapping paper, 4k wallpaper, 4k wallpaper 1920x1080, wallpaper hd, hd wallpaper, windows wallpaper, full hd wallpaper, background, crumples, collage, mac wallpaper, free wallpaper, laptop wallpaper, desktop backgrounds, wallpaper 4k, cool backgrounds, structure, unlabeled",
          "width": 5184,
          "height": 3456,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "KAVOWO",
          "preview_url": "https://cdn.pixabay.com/photo/2018/02/15/14/37/paper-3155438_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "3155438"
        }
      ],
      "primary_candidate_index": null
    },
    {
      "status": "candidates_found",
      "need_id": "need-4421d6f4a49adbf70e30",
      "purpose": "Quiet decorative atmosphere for a supporting section whose subject is not one of the named roles above; kept profession-neutral rather than assumed technical.",
      "role_id": "assumed-image:secureendpoint:technology:21",
      "category": "editorial_photo",
      "guidance": "Technology context should be a compact textual close, without decorative imagery.",
      "route_ids": [
        "secureendpoint"
      ],
      "candidates": [
        {
          "url": "https://pixabay.com/get/g802c42ced1fcee2d81abc510ed78310c8be3bab5158a398eb1ff2fdb767c2a0ee7b2a73b280d0e3c1708429e349383f3e67b24f5a59b347843dd096b046000c3_1280.jpg",
          "title": "library, wisdom, reading, knowledge, education, study, read, book",
          "width": 5000,
          "height": 3333,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "mirkostoedter",
          "preview_url": "https://cdn.pixabay.com/photo/2023/01/15/16/20/library-7720589_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "7720589"
        },
        {
          "url": "https://pixabay.com/get/gdbb82afc2b894c3d0adb3d71a08052d87aafbfd834a23a593691d332e9140f65bf3ed93eb3a5fd4e87b1910c31142106b6fb5628396d1830b51e3727d7e47a77_1280.jpg",
          "title": "aluminum foil, abstract, texture, material, shine, aluminum",
          "width": 6000,
          "height": 4000,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "analogicus",
          "preview_url": "https://cdn.pixabay.com/photo/2022/01/23/18/37/aluminum-foil-6961638_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "6961638"
        },
        {
          "url": "https://pixabay.com/get/gd62df20451de88949c0c2131f63062c6b15d1684d351cdf186f280b011d7aeb82f6b20ba76b411c35d09917bc7a6febe48f28ba18d1a2161909e73c03515eaaf_1280.jpg",
          "title": "paper, beautiful wallpaper, texture, free background, wrapping paper, 4k wallpaper, 4k wallpaper 1920x1080, wallpaper hd, hd wallpaper, windows wallpaper, full hd wallpaper, background, crumples, collage, mac wallpaper, free wallpaper, laptop wallpaper, desktop backgrounds, wallpaper 4k, cool backgrounds, structure, unlabeled",
          "width": 5184,
          "height": 3456,
          "license": "Pixabay Content License",
          "provider": "pixabay",
          "attribution": "KAVOWO",
          "preview_url": "https://cdn.pixabay.com/photo/2018/02/15/14/37/paper-3155438_150.jpg",
          "additional_urls": {},
          "license_reference": "https://pixabay.com/service/license-summary/",
          "provider_asset_id": "3155438"
        }
      ],
      "primary_candidate_index": null
    },
    {
      "status": "candidates_found",
      "need_id": "need-016331262cb7124422e4",
      "purpose": "A distinctive display/body font family for the approved visual language, vendored locally with Latin glyph coverage.",
      "role_id": "typography-font",
      "category": "font",
      "guidance": "Use Space Grotesk as the locally vendored versatile family for display and reading roles, while preserving comfortable body measure and strong contrast.",
      "route_ids": [
        "home",
        "workspace360",
        "secureendpoint",
        "employeeconnect"
      ],
      "candidates": [
        {
          "url": "https://cdn.jsdelivr.net/fontsource/fonts/space-grotesk@latest/latin-400-normal.woff2",
          "title": "Space Grotesk",
          "width": 0,
          "height": 0,
          "license": "OFL-1.1",
          "provider": "fontsource",
          "attribution": "",
          "preview_url": "",
          "additional_urls": {
            "500-normal": "https://cdn.jsdelivr.net/fontsource/fonts/space-grotesk@latest/latin-500-normal.woff2",
            "600-normal": "https://cdn.jsdelivr.net/fontsource/fonts/space-grotesk@latest/latin-600-normal.woff2",
            "700-normal": "https://cdn.jsdelivr.net/fontsource/fonts/space-grotesk@latest/latin-700-normal.woff2"
          },
          "license_reference": "https://scripts.sil.org/OFL",
          "provider_asset_id": "space-grotesk"
        },
        {
          "url": "https://cdn.jsdelivr.net/fontsource/fonts/familjen-grotesk@latest/latin-400-normal.woff2",
          "title": "Familjen Grotesk",
          "width": 0,
          "height": 0,
          "license": "OFL-1.1",
          "provider": "fontsource",
          "attribution": "",
          "preview_url": "",
          "additional_urls": {
            "500-normal": "https://cdn.jsdelivr.net/fontsource/fonts/familjen-grotesk@latest/latin-500-normal.woff2",
            "600-normal": "https://cdn.jsdelivr.net/fontsource/fonts/familjen-grotesk@latest/latin-600-normal.woff2",
            "700-normal": "https://cdn.jsdelivr.net/fontsource/fonts/familjen-grotesk@latest/latin-700-normal.woff2"
          },
          "license_reference": "https://scripts.sil.org/OFL",
          "provider_asset_id": "familjen-grotesk"
        },
        {
          "url": "https://cdn.jsdelivr.net/fontsource/fonts/fusion-pixel-10px-monospaced-jp@latest/latin-400-normal.woff2",
          "title": "Fusion Pixel 10px Monospaced JP",
          "width": 0,
          "height": 0,
          "license": "OFL-1.1",
          "provider": "fontsource",
          "attribution": "",
          "preview_url": "",
          "additional_urls": {},
          "license_reference": "https://scripts.sil.org/OFL",
          "provider_asset_id": "fusion-pixel-10px-monospaced-jp"
        }
      ],
      "primary_candidate_index": 0
    }
  ],
  "resource_needs": [
    {
      "kind": "resource",
      "details": {
        "placement": "Quiet counterweight to text-dominant hero",
        "style_mood": "",
        "focal_point": "Small chain of connected nodes beside hero copy",
        "orientation": "Flexible landscape abstract composition",
        "aspect_ratio": "",
        "theme_colors": [],
        "minimum_width": 0,
        "minimum_height": 0,
        "provider_terms": [],
        "alt_text_intent": "Abstract connected workflow motif representing dependable operations; no evidence or real system implied.",
        "expected_exports": [
          "static abstract visual",
          "reduced-motion static state"
        ],
        "interaction_class": "",
        "negative_concepts": [],
        "interaction_outcome": "",
        "responsive_behavior": "Place below action at reduced emphasis or omit",
        "reduced_motion_behavior": "Render the complete image treatment statically."
      },
      "need_id": "need-ffaff9238945207f5816",
      "purpose": "Lightweight abstract connected-workflow visual balancing the homepage hero and representing complexity becoming dependable.",
      "category": "visual_component",
      "fallback": "Typography with a static line motif",
      "route_ids": [
        "home"
      ],
      "scene_ids": [
        "home-positioning"
      ],
      "source_id": "home-operating-chain",
      "importance": "optional",
      "query_terms": [
        "visual_component",
        "Quiet counterweight to text-dominant hero"
      ],
      "section_ids": [],
      "source_policy": "generated_local_visual",
      "source_status": "unavailable",
      "component_intent": null,
      "required_for_handoff": false
    },
    {
      "kind": "resource",
      "details": {
        "placement": "Atmospheric bridge between experience and project routes",
        "style_mood": "",
        "focal_point": "Three separated but connected outcome nodes",
        "orientation": "Wide or flexible editorial composition",
        "aspect_ratio": "",
        "theme_colors": [],
        "minimum_width": 0,
        "minimum_height": 0,
        "provider_terms": [],
        "alt_text_intent": "Decorative abstract workflow connection; no additional information beyond adjacent text.",
        "expected_exports": [
          "static workflow motif"
        ],
        "interaction_class": "",
        "negative_concepts": [],
        "interaction_outcome": "",
        "responsive_behavior": "Reduce to divider motif or omit",
        "reduced_motion_behavior": "Render the complete image treatment statically."
      },
      "need_id": "need-8ac3b90c9d5812edd926",
      "purpose": "Abstract words-first workflow motif supporting the transition from career experience to selected work.",
      "category": "visual_component",
      "fallback": "Project entries and directional rules without separate visual",
      "route_ids": [
        "home"
      ],
      "scene_ids": [
        "home-experience-work"
      ],
      "source_id": "home-workflow-abstract",
      "importance": "optional",
      "query_terms": [
        "visual_component",
        "Atmospheric bridge between experience and project routes"
      ],
      "section_ids": [],
      "source_policy": "generated_local_visual",
      "source_status": "unavailable",
      "component_intent": null,
      "required_for_handoff": false
    },
    {
      "kind": "resource",
      "details": {
        "placement": "Explanatory process visual, not production architecture",
        "style_mood": "",
        "focal_point": "Three approved approach stages",
        "orientation": "Horizontal sequence with mobile vertical variant",
        "aspect_ratio": "",
        "theme_colors": [],
        "minimum_width": 0,
        "minimum_height": 0,
        "provider_terms": [],
        "alt_text_intent": "Abstract representative sequence of WorkSpace360's three approved operating stages.",
        "expected_exports": [
          "desktop process sequence",
          "mobile stacked sequence",
          "static reduced-motion state"
        ],
        "interaction_class": "",
        "negative_concepts": [],
        "interaction_outcome": "",
        "responsive_behavior": "Three stacked labelled stages with minimal connectors",
        "reduced_motion_behavior": "Render the complete image treatment statically."
      },
      "need_id": "need-009f78480992358fdee8",
      "purpose": "Words-first abstract representation of the approved WorkSpace360 operating stages.",
      "category": "visual_component",
      "fallback": "Ordered text blocks with dividers",
      "route_ids": [
        "workspace360"
      ],
      "scene_ids": [
        "workspace360-need-approach",
        "workspace360-overview"
      ],
      "source_id": "workspace360-process-visual",
      "importance": "important",
      "query_terms": [
        "visual_component",
        "Explanatory process visual, not production architecture"
      ],
      "section_ids": [],
      "source_policy": "generated_local_visual",
      "source_status": "unavailable",
      "component_intent": null,
      "required_for_handoff": true
    },
    {
      "kind": "resource",
      "details": {
        "placement": "Abstract explanatory visual for coordinated endpoint security work",
        "style_mood": "",
        "focal_point": "Three approved approach stages",
        "orientation": "Horizontal sequence with simplified vertical mobile version",
        "aspect_ratio": "",
        "theme_colors": [],
        "minimum_width": 0,
        "minimum_height": 0,
        "provider_terms": [],
        "alt_text_intent": "Abstract representative chain for SecureEndpoint controls, visibility, and remediation.",
        "expected_exports": [
          "desktop control chain",
          "mobile simplified sequence",
          "static reduced-motion state"
        ],
        "interaction_class": "",
        "negative_concepts": [
          "warning colors",
          "threat effects",
          "live status"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Three labelled stages with plain dividers",
        "reduced_motion_behavior": "Render the complete image treatment statically."
      },
      "need_id": "need-15fc7788e7c478618112",
      "purpose": "Words-first representative chain connecting security controls, visibility, and remediation.",
      "category": "visual_component",
      "fallback": "Ordered list of titled approach steps",
      "route_ids": [
        "secureendpoint"
      ],
      "scene_ids": [
        "secureendpoint-need-approach",
        "secureendpoint-overview"
      ],
      "source_id": "secureendpoint-control-chain",
      "importance": "important",
      "query_terms": [
        "visual_component",
        "Abstract explanatory visual for coordinated endpoint security work"
      ],
      "section_ids": [],
      "source_policy": "generated_local_visual",
      "source_status": "unavailable",
      "component_intent": null,
      "required_for_handoff": true
    },
    {
      "kind": "resource",
      "details": {
        "placement": "Explanatory migration-support visual, never a platform screenshot",
        "style_mood": "",
        "focal_point": "Three approved stages balancing technical administration and human adoption",
        "orientation": "Horizontal or gently stepped sequence with vertical mobile variant",
        "aspect_ratio": "",
        "theme_colors": [],
        "minimum_width": 0,
        "minimum_height": 0,
        "provider_terms": [],
        "alt_text_intent": "Abstract representative migration-support path covering administration, adoption, and documentation.",
        "expected_exports": [
          "desktop migration path",
          "mobile stacked path",
          "static reduced-motion state"
        ],
        "interaction_class": "",
        "negative_concepts": [
          "platform screenshot",
          "product logo",
          "unsupported migration detail"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack stages with simple separators",
        "reduced_motion_behavior": "Render the complete image treatment statically."
      },
      "need_id": "need-c60c81649b07900c657a",
      "purpose": "Words-first abstract migration path balancing administration, adoption, and documentation.",
      "category": "visual_component",
      "fallback": "Ordered text sequence with directional rules",
      "route_ids": [
        "employeeconnect"
      ],
      "scene_ids": [
        "employeeconnect-need-approach",
        "employeeconnect-overview"
      ],
      "source_id": "employeeconnect-migration-path",
      "importance": "important",
      "query_terms": [
        "visual_component",
        "Explanatory migration-support visual, never a platform screenshot"
      ],
      "section_ids": [],
      "source_policy": "generated_local_visual",
      "source_status": "unavailable",
      "component_intent": null,
      "required_for_handoff": true
    },
    {
      "kind": "asset",
      "details": {
        "placement": "hero",
        "style_mood": "quiet, distinctive, high-contrast",
        "focal_point": "",
        "orientation": "landscape",
        "aspect_ratio": "16:9",
        "theme_colors": [],
        "minimum_width": 1200,
        "minimum_height": 700,
        "provider_terms": [
          "creative professional workspace",
          "editorial opening atmosphere",
          "abstract material"
        ],
        "alt_text_intent": "Decorative atmosphere; empty alt text unless the final composition gives it semantic meaning.",
        "expected_exports": [],
        "interaction_class": "",
        "negative_concepts": [
          "portrait",
          "face",
          "screenshot",
          "dashboard",
          "logo",
          "project proof",
          "employer imagery",
          "private media",
          "testimonial"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack below essential copy and crop without hiding content.",
        "reduced_motion_behavior": "Render the complete image treatment statically."
      },
      "need_id": "need-6c7010157537a7aa0002",
      "purpose": "Editorial opening atmosphere for the approved professional practice; no person or product interface.",
      "category": "editorial_photo",
      "fallback": "Use the approved text-led/static composition without stock substitution.",
      "route_ids": [
        "home"
      ],
      "scene_ids": [
        "home-positioning"
      ],
      "source_id": "assumed-image:home:hero:0",
      "importance": "important",
      "query_terms": [
        "creative professional workspace editorial opening atmosphere abstract material",
        "quiet, distinctive, high-contrast",
        "16:9",
        "editorial_photo",
        "hero"
      ],
      "section_ids": [
        "home:hero"
      ],
      "source_policy": "optional_external_acquisition",
      "source_status": "needs_acquisition",
      "component_intent": null,
      "required_for_handoff": true
    },
    {
      "kind": "asset",
      "details": {
        "placement": "capabilities",
        "style_mood": "structured, analytical, restrained",
        "focal_point": "",
        "orientation": "landscape",
        "aspect_ratio": "3:2",
        "theme_colors": [],
        "minimum_width": 1200,
        "minimum_height": 700,
        "provider_terms": [
          "modular craft materials",
          "organized creative tools",
          "structured editorial grid"
        ],
        "alt_text_intent": "Decorative atmosphere; empty alt text unless the final composition gives it semantic meaning.",
        "expected_exports": [],
        "interaction_class": "",
        "negative_concepts": [
          "portrait",
          "face",
          "screenshot",
          "dashboard",
          "logo",
          "project proof",
          "employer imagery",
          "private media",
          "testimonial"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack below essential copy and crop without hiding content.",
        "reduced_motion_behavior": "Render the complete image treatment statically."
      },
      "need_id": "need-9b3860cb6dd5f936882d",
      "purpose": "Decorative modular atmosphere for approved capability groups; not evidence or a real interface.",
      "category": "editorial_photo",
      "fallback": "Use the approved text-led/static composition without stock substitution.",
      "route_ids": [
        "home"
      ],
      "scene_ids": [
        "home-proof-capabilities"
      ],
      "source_id": "assumed-image:home:capabilities:1",
      "importance": "supporting",
      "query_terms": [
        "modular craft materials organized creative tools structured editorial grid",
        "structured, analytical, restrained",
        "3:2",
        "editorial_photo",
        "capabilities"
      ],
      "section_ids": [
        "home:capabilities"
      ],
      "source_policy": "optional_external_acquisition",
      "source_status": "needs_acquisition",
      "component_intent": null,
      "required_for_handoff": false
    },
    {
      "kind": "asset",
      "details": {
        "placement": "experience",
        "style_mood": "calm, collaborative, editorial",
        "focal_point": "",
        "orientation": "landscape",
        "aspect_ratio": "3:2",
        "theme_colors": [],
        "minimum_width": 1200,
        "minimum_height": 700,
        "provider_terms": [
          "professional collaboration workspace",
          "studio teamwork",
          "editorial progression"
        ],
        "alt_text_intent": "Decorative atmosphere; empty alt text unless the final composition gives it semantic meaning.",
        "expected_exports": [],
        "interaction_class": "",
        "negative_concepts": [
          "portrait",
          "face",
          "screenshot",
          "dashboard",
          "logo",
          "project proof",
          "employer imagery",
          "private media",
          "testimonial"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack below essential copy and crop without hiding content.",
        "reduced_motion_behavior": "Render the complete image treatment statically."
      },
      "need_id": "need-62fd6ffaa64f9ab35457",
      "purpose": "Editorial collaboration atmosphere supporting an approved experience timeline.",
      "category": "editorial_photo",
      "fallback": "Use the approved text-led/static composition without stock substitution.",
      "route_ids": [
        "home"
      ],
      "scene_ids": [
        "home-experience-work"
      ],
      "source_id": "assumed-image:home:experience:2",
      "importance": "supporting",
      "query_terms": [
        "professional collaboration workspace studio teamwork editorial progression",
        "calm, collaborative, editorial",
        "3:2",
        "editorial_photo",
        "experience"
      ],
      "section_ids": [
        "home:experience"
      ],
      "source_policy": "optional_external_acquisition",
      "source_status": "needs_acquisition",
      "component_intent": null,
      "required_for_handoff": false
    },
    {
      "kind": "asset",
      "details": {
        "placement": "selected-work",
        "style_mood": "precise, tactile, considered",
        "focal_point": "",
        "orientation": "landscape",
        "aspect_ratio": "4:3",
        "theme_colors": [],
        "minimum_width": 1200,
        "minimum_height": 700,
        "provider_terms": [
          "creative work process",
          "project materials detail",
          "portfolio craft atmosphere"
        ],
        "alt_text_intent": "Decorative atmosphere; empty alt text unless the final composition gives it semantic meaning.",
        "expected_exports": [],
        "interaction_class": "",
        "negative_concepts": [
          "portrait",
          "face",
          "screenshot",
          "dashboard",
          "logo",
          "project proof",
          "employer imagery",
          "private media",
          "testimonial"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack below essential copy and crop without hiding content.",
        "reduced_motion_behavior": "Render the complete image treatment statically."
      },
      "need_id": "need-5b00cc1f3f31408ac825",
      "purpose": "Decorative craft-and-process atmosphere for selected work; no dashboard or screenshot.",
      "category": "editorial_photo",
      "fallback": "Use the approved text-led/static composition without stock substitution.",
      "route_ids": [
        "home"
      ],
      "scene_ids": [
        "home-experience-work"
      ],
      "source_id": "assumed-image:home:featured-work:3",
      "importance": "important",
      "query_terms": [
        "creative work process project materials detail portfolio craft atmosphere",
        "precise, tactile, considered",
        "4:3",
        "editorial_photo",
        "selected-work"
      ],
      "section_ids": [
        "home:featured-work"
      ],
      "source_policy": "optional_external_acquisition",
      "source_status": "needs_acquisition",
      "component_intent": null,
      "required_for_handoff": true
    },
    {
      "kind": "asset",
      "details": {
        "placement": "selected-work",
        "style_mood": "precise, tactile, considered",
        "focal_point": "",
        "orientation": "landscape",
        "aspect_ratio": "4:3",
        "theme_colors": [],
        "minimum_width": 1200,
        "minimum_height": 700,
        "provider_terms": [
          "creative work process",
          "project materials detail",
          "portfolio craft atmosphere"
        ],
        "alt_text_intent": "Decorative atmosphere; empty alt text unless the final composition gives it semantic meaning.",
        "expected_exports": [],
        "interaction_class": "",
        "negative_concepts": [
          "portrait",
          "face",
          "screenshot",
          "dashboard",
          "logo",
          "project proof",
          "employer imagery",
          "private media",
          "testimonial"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack below essential copy and crop without hiding content.",
        "reduced_motion_behavior": "Render the complete image treatment statically."
      },
      "need_id": "need-9b29f305c2aecd039e14",
      "purpose": "Decorative craft-and-process atmosphere for selected work; no dashboard or screenshot.",
      "category": "editorial_photo",
      "fallback": "Use the approved text-led/static composition without stock substitution.",
      "route_ids": [
        "home"
      ],
      "scene_ids": [
        "home-proof-capabilities"
      ],
      "source_id": "assumed-image:home:proof-points:4",
      "importance": "important",
      "query_terms": [
        "creative work process project materials detail portfolio craft atmosphere",
        "precise, tactile, considered",
        "4:3",
        "editorial_photo",
        "selected-work"
      ],
      "section_ids": [
        "home:proof-points"
      ],
      "source_policy": "optional_external_acquisition",
      "source_status": "needs_acquisition",
      "component_intent": null,
      "required_for_handoff": true
    },
    {
      "kind": "asset",
      "details": {
        "placement": "selected-work",
        "style_mood": "precise, tactile, considered",
        "focal_point": "",
        "orientation": "landscape",
        "aspect_ratio": "4:3",
        "theme_colors": [],
        "minimum_width": 1200,
        "minimum_height": 700,
        "provider_terms": [
          "creative work process",
          "project materials detail",
          "portfolio craft atmosphere"
        ],
        "alt_text_intent": "Decorative atmosphere; empty alt text unless the final composition gives it semantic meaning.",
        "expected_exports": [],
        "interaction_class": "",
        "negative_concepts": [
          "portrait",
          "face",
          "screenshot",
          "dashboard",
          "logo",
          "project proof",
          "employer imagery",
          "private media",
          "testimonial"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack below essential copy and crop without hiding content.",
        "reduced_motion_behavior": "Render the complete image treatment statically."
      },
      "need_id": "need-1245adde715aa2c70864",
      "purpose": "Decorative craft-and-process atmosphere for selected work; no dashboard or screenshot.",
      "category": "editorial_photo",
      "fallback": "Use the approved text-led/static composition without stock substitution.",
      "route_ids": [
        "workspace360"
      ],
      "scene_ids": [
        "workspace360-need-approach"
      ],
      "source_id": "assumed-image:workspace360:approach:5",
      "importance": "important",
      "query_terms": [
        "creative work process project materials detail portfolio craft atmosphere",
        "precise, tactile, considered",
        "4:3",
        "editorial_photo",
        "selected-work"
      ],
      "section_ids": [
        "workspace360:approach"
      ],
      "source_policy": "optional_external_acquisition",
      "source_status": "needs_acquisition",
      "component_intent": null,
      "required_for_handoff": true
    },
    {
      "kind": "asset",
      "details": {
        "placement": "selected-work",
        "style_mood": "precise, tactile, considered",
        "focal_point": "",
        "orientation": "landscape",
        "aspect_ratio": "4:3",
        "theme_colors": [],
        "minimum_width": 1200,
        "minimum_height": 700,
        "provider_terms": [
          "creative work process",
          "project materials detail",
          "portfolio craft atmosphere"
        ],
        "alt_text_intent": "Decorative atmosphere; empty alt text unless the final composition gives it semantic meaning.",
        "expected_exports": [],
        "interaction_class": "",
        "negative_concepts": [
          "portrait",
          "face",
          "screenshot",
          "dashboard",
          "logo",
          "project proof",
          "employer imagery",
          "private media",
          "testimonial"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack below essential copy and crop without hiding content.",
        "reduced_motion_behavior": "Render the complete image treatment statically."
      },
      "need_id": "need-ce4959e396c7d4459465",
      "purpose": "Decorative craft-and-process atmosphere for selected work; no dashboard or screenshot.",
      "category": "editorial_photo",
      "fallback": "Use the approved text-led/static composition without stock substitution.",
      "route_ids": [
        "workspace360"
      ],
      "scene_ids": [
        "workspace360-need-approach"
      ],
      "source_id": "assumed-image:workspace360:challenge:6",
      "importance": "important",
      "query_terms": [
        "creative work process project materials detail portfolio craft atmosphere",
        "precise, tactile, considered",
        "4:3",
        "editorial_photo",
        "selected-work"
      ],
      "section_ids": [
        "workspace360:challenge"
      ],
      "source_policy": "optional_external_acquisition",
      "source_status": "needs_acquisition",
      "component_intent": null,
      "required_for_handoff": true
    },
    {
      "kind": "asset",
      "details": {
        "placement": "selected-work",
        "style_mood": "precise, tactile, considered",
        "focal_point": "",
        "orientation": "landscape",
        "aspect_ratio": "4:3",
        "theme_colors": [],
        "minimum_width": 1200,
        "minimum_height": 700,
        "provider_terms": [
          "creative work process",
          "project materials detail",
          "portfolio craft atmosphere"
        ],
        "alt_text_intent": "Decorative atmosphere; empty alt text unless the final composition gives it semantic meaning.",
        "expected_exports": [],
        "interaction_class": "",
        "negative_concepts": [
          "portrait",
          "face",
          "screenshot",
          "dashboard",
          "logo",
          "project proof",
          "employer imagery",
          "private media",
          "testimonial"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack below essential copy and crop without hiding content.",
        "reduced_motion_behavior": "Render the complete image treatment statically."
      },
      "need_id": "need-37b42d749a51d7474de4",
      "purpose": "Decorative craft-and-process atmosphere for selected work; no dashboard or screenshot.",
      "category": "editorial_photo",
      "fallback": "Use the approved text-led/static composition without stock substitution.",
      "route_ids": [
        "workspace360"
      ],
      "scene_ids": [
        "workspace360-result-context"
      ],
      "source_id": "assumed-image:workspace360:outcome:7",
      "importance": "important",
      "query_terms": [
        "creative work process project materials detail portfolio craft atmosphere",
        "precise, tactile, considered",
        "4:3",
        "editorial_photo",
        "selected-work"
      ],
      "section_ids": [
        "workspace360:outcome"
      ],
      "source_policy": "optional_external_acquisition",
      "source_status": "needs_acquisition",
      "component_intent": null,
      "required_for_handoff": true
    },
    {
      "kind": "asset",
      "details": {
        "placement": "selected-work",
        "style_mood": "precise, tactile, considered",
        "focal_point": "",
        "orientation": "landscape",
        "aspect_ratio": "4:3",
        "theme_colors": [],
        "minimum_width": 1200,
        "minimum_height": 700,
        "provider_terms": [
          "creative work process",
          "project materials detail",
          "portfolio craft atmosphere"
        ],
        "alt_text_intent": "Decorative atmosphere; empty alt text unless the final composition gives it semantic meaning.",
        "expected_exports": [],
        "interaction_class": "",
        "negative_concepts": [
          "portrait",
          "face",
          "screenshot",
          "dashboard",
          "logo",
          "project proof",
          "employer imagery",
          "private media",
          "testimonial"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack below essential copy and crop without hiding content.",
        "reduced_motion_behavior": "Render the complete image treatment statically."
      },
      "need_id": "need-347d4e372dd15c465512",
      "purpose": "Decorative craft-and-process atmosphere for selected work; no dashboard or screenshot.",
      "category": "editorial_photo",
      "fallback": "Use the approved text-led/static composition without stock substitution.",
      "route_ids": [
        "workspace360"
      ],
      "scene_ids": [
        "workspace360-overview"
      ],
      "source_id": "assumed-image:workspace360:overview:8",
      "importance": "important",
      "query_terms": [
        "creative work process project materials detail portfolio craft atmosphere",
        "precise, tactile, considered",
        "4:3",
        "editorial_photo",
        "selected-work"
      ],
      "section_ids": [
        "workspace360:overview"
      ],
      "source_policy": "optional_external_acquisition",
      "source_status": "needs_acquisition",
      "component_intent": null,
      "required_for_handoff": true
    },
    {
      "kind": "asset",
      "details": {
        "placement": "selected-work",
        "style_mood": "precise, tactile, considered",
        "focal_point": "",
        "orientation": "landscape",
        "aspect_ratio": "4:3",
        "theme_colors": [],
        "minimum_width": 1200,
        "minimum_height": 700,
        "provider_terms": [
          "creative work process",
          "project materials detail",
          "portfolio craft atmosphere"
        ],
        "alt_text_intent": "Decorative atmosphere; empty alt text unless the final composition gives it semantic meaning.",
        "expected_exports": [],
        "interaction_class": "",
        "negative_concepts": [
          "portrait",
          "face",
          "screenshot",
          "dashboard",
          "logo",
          "project proof",
          "employer imagery",
          "private media",
          "testimonial"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack below essential copy and crop without hiding content.",
        "reduced_motion_behavior": "Render the complete image treatment statically."
      },
      "need_id": "need-0153c0bebc4e182c61e3",
      "purpose": "Decorative craft-and-process atmosphere for selected work; no dashboard or screenshot.",
      "category": "editorial_photo",
      "fallback": "Use the approved text-led/static composition without stock substitution.",
      "route_ids": [
        "workspace360"
      ],
      "scene_ids": [
        "workspace360-result-context"
      ],
      "source_id": "assumed-image:workspace360:technology:9",
      "importance": "important",
      "query_terms": [
        "creative work process project materials detail portfolio craft atmosphere",
        "precise, tactile, considered",
        "4:3",
        "editorial_photo",
        "selected-work"
      ],
      "section_ids": [
        "workspace360:technology"
      ],
      "source_policy": "optional_external_acquisition",
      "source_status": "needs_acquisition",
      "component_intent": null,
      "required_for_handoff": true
    },
    {
      "kind": "asset",
      "details": {
        "placement": "approach",
        "style_mood": "methodical, human, clear",
        "focal_point": "",
        "orientation": "landscape",
        "aspect_ratio": "3:2",
        "theme_colors": [],
        "minimum_width": 1200,
        "minimum_height": 700,
        "provider_terms": [
          "process sketches planning",
          "creative workflow materials",
          "collaborative planning table"
        ],
        "alt_text_intent": "Decorative atmosphere; empty alt text unless the final composition gives it semantic meaning.",
        "expected_exports": [],
        "interaction_class": "",
        "negative_concepts": [
          "portrait",
          "face",
          "screenshot",
          "dashboard",
          "logo",
          "project proof",
          "employer imagery",
          "private media",
          "testimonial"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack below essential copy and crop without hiding content.",
        "reduced_motion_behavior": "Render the complete image treatment statically."
      },
      "need_id": "need-ce945df3392dd866ff08",
      "purpose": "Editorial process atmosphere for the approved working approach; no invented project evidence.",
      "category": "editorial_photo",
      "fallback": "Use the approved text-led/static composition without stock substitution.",
      "route_ids": [
        "employeeconnect"
      ],
      "scene_ids": [
        "employeeconnect-need-approach"
      ],
      "source_id": "assumed-image:employeeconnect:approach:10",
      "importance": "supporting",
      "query_terms": [
        "process sketches planning creative workflow materials collaborative planning table",
        "methodical, human, clear",
        "3:2",
        "editorial_photo",
        "approach"
      ],
      "section_ids": [
        "employeeconnect:approach"
      ],
      "source_policy": "optional_external_acquisition",
      "source_status": "needs_acquisition",
      "component_intent": null,
      "required_for_handoff": false
    },
    {
      "kind": "asset",
      "details": {
        "placement": "approach",
        "style_mood": "methodical, human, clear",
        "focal_point": "",
        "orientation": "landscape",
        "aspect_ratio": "3:2",
        "theme_colors": [],
        "minimum_width": 1200,
        "minimum_height": 700,
        "provider_terms": [
          "process sketches planning",
          "creative workflow materials",
          "collaborative planning table"
        ],
        "alt_text_intent": "Decorative atmosphere; empty alt text unless the final composition gives it semantic meaning.",
        "expected_exports": [],
        "interaction_class": "",
        "negative_concepts": [
          "portrait",
          "face",
          "screenshot",
          "dashboard",
          "logo",
          "project proof",
          "employer imagery",
          "private media",
          "testimonial"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack below essential copy and crop without hiding content.",
        "reduced_motion_behavior": "Render the complete image treatment statically."
      },
      "need_id": "need-e0ce25ddcdf2ad5b70fa",
      "purpose": "Editorial process atmosphere for the approved working approach; no invented project evidence.",
      "category": "editorial_photo",
      "fallback": "Use the approved text-led/static composition without stock substitution.",
      "route_ids": [
        "secureendpoint"
      ],
      "scene_ids": [
        "secureendpoint-need-approach"
      ],
      "source_id": "assumed-image:secureendpoint:approach:11",
      "importance": "supporting",
      "query_terms": [
        "process sketches planning creative workflow materials collaborative planning table",
        "methodical, human, clear",
        "3:2",
        "editorial_photo",
        "approach"
      ],
      "section_ids": [
        "secureendpoint:approach"
      ],
      "source_policy": "optional_external_acquisition",
      "source_status": "needs_acquisition",
      "component_intent": null,
      "required_for_handoff": false
    },
    {
      "kind": "asset",
      "details": {
        "placement": "connect",
        "style_mood": "open, focused, restrained",
        "focal_point": "",
        "orientation": "landscape",
        "aspect_ratio": "16:9",
        "theme_colors": [],
        "minimum_width": 1200,
        "minimum_height": 700,
        "provider_terms": [
          "professional connection abstract",
          "human collaboration details",
          "editorial closing field"
        ],
        "alt_text_intent": "Decorative atmosphere; empty alt text unless the final composition gives it semantic meaning.",
        "expected_exports": [],
        "interaction_class": "",
        "negative_concepts": [
          "portrait",
          "face",
          "screenshot",
          "dashboard",
          "logo",
          "project proof",
          "employer imagery",
          "private media",
          "testimonial"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack below essential copy and crop without hiding content.",
        "reduced_motion_behavior": "Render the complete image treatment statically."
      },
      "need_id": "need-4ad70a6d615bdfe3ce52",
      "purpose": "Non-evidentiary closing atmosphere for a professional connection CTA.",
      "category": "editorial_photo",
      "fallback": "Use the approved text-led/static composition without stock substitution.",
      "route_ids": [
        "employeeconnect"
      ],
      "scene_ids": [
        "employeeconnect-need-approach"
      ],
      "source_id": "assumed-image:employeeconnect:challenge:12",
      "importance": "supporting",
      "query_terms": [
        "professional connection abstract human collaboration details editorial closing field",
        "open, focused, restrained",
        "16:9",
        "editorial_photo",
        "connect"
      ],
      "section_ids": [
        "employeeconnect:challenge"
      ],
      "source_policy": "optional_external_acquisition",
      "source_status": "needs_acquisition",
      "component_intent": null,
      "required_for_handoff": false
    },
    {
      "kind": "asset",
      "details": {
        "placement": "connect",
        "style_mood": "open, focused, restrained",
        "focal_point": "",
        "orientation": "landscape",
        "aspect_ratio": "16:9",
        "theme_colors": [],
        "minimum_width": 1200,
        "minimum_height": 700,
        "provider_terms": [
          "professional connection abstract",
          "human collaboration details",
          "editorial closing field"
        ],
        "alt_text_intent": "Decorative atmosphere; empty alt text unless the final composition gives it semantic meaning.",
        "expected_exports": [],
        "interaction_class": "",
        "negative_concepts": [
          "portrait",
          "face",
          "screenshot",
          "dashboard",
          "logo",
          "project proof",
          "employer imagery",
          "private media",
          "testimonial"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack below essential copy and crop without hiding content.",
        "reduced_motion_behavior": "Render the complete image treatment statically."
      },
      "need_id": "need-a2d889f2cc5739b5b00e",
      "purpose": "Non-evidentiary closing atmosphere for a professional connection CTA.",
      "category": "editorial_photo",
      "fallback": "Use the approved text-led/static composition without stock substitution.",
      "route_ids": [
        "employeeconnect"
      ],
      "scene_ids": [
        "employeeconnect-result-context"
      ],
      "source_id": "assumed-image:employeeconnect:outcome:13",
      "importance": "supporting",
      "query_terms": [
        "professional connection abstract human collaboration details editorial closing field",
        "open, focused, restrained",
        "16:9",
        "editorial_photo",
        "connect"
      ],
      "section_ids": [
        "employeeconnect:outcome"
      ],
      "source_policy": "optional_external_acquisition",
      "source_status": "needs_acquisition",
      "component_intent": null,
      "required_for_handoff": false
    },
    {
      "kind": "asset",
      "details": {
        "placement": "connect",
        "style_mood": "open, focused, restrained",
        "focal_point": "",
        "orientation": "landscape",
        "aspect_ratio": "16:9",
        "theme_colors": [],
        "minimum_width": 1200,
        "minimum_height": 700,
        "provider_terms": [
          "professional connection abstract",
          "human collaboration details",
          "editorial closing field"
        ],
        "alt_text_intent": "Decorative atmosphere; empty alt text unless the final composition gives it semantic meaning.",
        "expected_exports": [],
        "interaction_class": "",
        "negative_concepts": [
          "portrait",
          "face",
          "screenshot",
          "dashboard",
          "logo",
          "project proof",
          "employer imagery",
          "private media",
          "testimonial"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack below essential copy and crop without hiding content.",
        "reduced_motion_behavior": "Render the complete image treatment statically."
      },
      "need_id": "need-60cfe22b273f2fba7ed1",
      "purpose": "Non-evidentiary closing atmosphere for a professional connection CTA.",
      "category": "editorial_photo",
      "fallback": "Use the approved text-led/static composition without stock substitution.",
      "route_ids": [
        "employeeconnect"
      ],
      "scene_ids": [
        "employeeconnect-overview"
      ],
      "source_id": "assumed-image:employeeconnect:overview:14",
      "importance": "supporting",
      "query_terms": [
        "professional connection abstract human collaboration details editorial closing field",
        "open, focused, restrained",
        "16:9",
        "editorial_photo",
        "connect"
      ],
      "section_ids": [
        "employeeconnect:overview"
      ],
      "source_policy": "optional_external_acquisition",
      "source_status": "needs_acquisition",
      "component_intent": null,
      "required_for_handoff": false
    },
    {
      "kind": "asset",
      "details": {
        "placement": "connect",
        "style_mood": "open, focused, restrained",
        "focal_point": "",
        "orientation": "landscape",
        "aspect_ratio": "16:9",
        "theme_colors": [],
        "minimum_width": 1200,
        "minimum_height": 700,
        "provider_terms": [
          "professional connection abstract",
          "human collaboration details",
          "editorial closing field"
        ],
        "alt_text_intent": "Decorative atmosphere; empty alt text unless the final composition gives it semantic meaning.",
        "expected_exports": [],
        "interaction_class": "",
        "negative_concepts": [
          "portrait",
          "face",
          "screenshot",
          "dashboard",
          "logo",
          "project proof",
          "employer imagery",
          "private media",
          "testimonial"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack below essential copy and crop without hiding content.",
        "reduced_motion_behavior": "Render the complete image treatment statically."
      },
      "need_id": "need-89d35155ec0741b0f255",
      "purpose": "Non-evidentiary closing atmosphere for a professional connection CTA.",
      "category": "editorial_photo",
      "fallback": "Use the approved text-led/static composition without stock substitution.",
      "route_ids": [
        "employeeconnect"
      ],
      "scene_ids": [
        "employeeconnect-result-context"
      ],
      "source_id": "assumed-image:employeeconnect:technology:15",
      "importance": "supporting",
      "query_terms": [
        "professional connection abstract human collaboration details editorial closing field",
        "open, focused, restrained",
        "16:9",
        "editorial_photo",
        "connect"
      ],
      "section_ids": [
        "employeeconnect:technology"
      ],
      "source_policy": "optional_external_acquisition",
      "source_status": "needs_acquisition",
      "component_intent": null,
      "required_for_handoff": false
    },
    {
      "kind": "asset",
      "details": {
        "placement": "connect",
        "style_mood": "open, focused, restrained",
        "focal_point": "",
        "orientation": "landscape",
        "aspect_ratio": "16:9",
        "theme_colors": [],
        "minimum_width": 1200,
        "minimum_height": 700,
        "provider_terms": [
          "professional connection abstract",
          "human collaboration details",
          "editorial closing field"
        ],
        "alt_text_intent": "Decorative atmosphere; empty alt text unless the final composition gives it semantic meaning.",
        "expected_exports": [],
        "interaction_class": "",
        "negative_concepts": [
          "portrait",
          "face",
          "screenshot",
          "dashboard",
          "logo",
          "project proof",
          "employer imagery",
          "private media",
          "testimonial"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack below essential copy and crop without hiding content.",
        "reduced_motion_behavior": "Render the complete image treatment statically."
      },
      "need_id": "need-75544073a0565c50677b",
      "purpose": "Non-evidentiary closing atmosphere for a professional connection CTA.",
      "category": "editorial_photo",
      "fallback": "Use the approved text-led/static composition without stock substitution.",
      "route_ids": [
        "home"
      ],
      "scene_ids": [
        "home-closing-invitation"
      ],
      "source_id": "assumed-image:home:contact:16",
      "importance": "supporting",
      "query_terms": [
        "professional connection abstract human collaboration details editorial closing field",
        "open, focused, restrained",
        "16:9",
        "editorial_photo",
        "connect"
      ],
      "section_ids": [
        "home:contact"
      ],
      "source_policy": "optional_external_acquisition",
      "source_status": "needs_acquisition",
      "component_intent": null,
      "required_for_handoff": false
    },
    {
      "kind": "asset",
      "details": {
        "placement": "context",
        "style_mood": "quiet, restrained, unobtrusive",
        "focal_point": "",
        "orientation": "landscape",
        "aspect_ratio": "3:2",
        "theme_colors": [],
        "minimum_width": 1200,
        "minimum_height": 700,
        "provider_terms": [
          "abstract editorial texture",
          "quiet material study",
          "neutral atmospheric backdrop"
        ],
        "alt_text_intent": "Decorative atmosphere; empty alt text unless the final composition gives it semantic meaning.",
        "expected_exports": [],
        "interaction_class": "",
        "negative_concepts": [
          "portrait",
          "face",
          "screenshot",
          "dashboard",
          "logo",
          "project proof",
          "employer imagery",
          "private media",
          "testimonial"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack below essential copy and crop without hiding content.",
        "reduced_motion_behavior": "Render the complete image treatment statically."
      },
      "need_id": "need-7518cc20ca7e14d1e9e5",
      "purpose": "Quiet decorative atmosphere for a supporting section whose subject is not one of the named roles above; kept profession-neutral rather than assumed technical.",
      "category": "editorial_photo",
      "fallback": "Use the approved text-led/static composition without stock substitution.",
      "route_ids": [
        "home"
      ],
      "scene_ids": [
        "home-closing-invitation"
      ],
      "source_id": "assumed-image:home:credentials:17",
      "importance": "supporting",
      "query_terms": [
        "abstract editorial texture quiet material study neutral atmospheric backdrop",
        "quiet, restrained, unobtrusive",
        "3:2",
        "editorial_photo",
        "context"
      ],
      "section_ids": [
        "home:credentials"
      ],
      "source_policy": "optional_external_acquisition",
      "source_status": "needs_acquisition",
      "component_intent": null,
      "required_for_handoff": false
    },
    {
      "kind": "asset",
      "details": {
        "placement": "context",
        "style_mood": "quiet, restrained, unobtrusive",
        "focal_point": "",
        "orientation": "landscape",
        "aspect_ratio": "3:2",
        "theme_colors": [],
        "minimum_width": 1200,
        "minimum_height": 700,
        "provider_terms": [
          "abstract editorial texture",
          "quiet material study",
          "neutral atmospheric backdrop"
        ],
        "alt_text_intent": "Decorative atmosphere; empty alt text unless the final composition gives it semantic meaning.",
        "expected_exports": [],
        "interaction_class": "",
        "negative_concepts": [
          "portrait",
          "face",
          "screenshot",
          "dashboard",
          "logo",
          "project proof",
          "employer imagery",
          "private media",
          "testimonial"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack below essential copy and crop without hiding content.",
        "reduced_motion_behavior": "Render the complete image treatment statically."
      },
      "need_id": "need-f6bcecdd26d4469c08c5",
      "purpose": "Quiet decorative atmosphere for a supporting section whose subject is not one of the named roles above; kept profession-neutral rather than assumed technical.",
      "category": "editorial_photo",
      "fallback": "Use the approved text-led/static composition without stock substitution.",
      "route_ids": [
        "secureendpoint"
      ],
      "scene_ids": [
        "secureendpoint-need-approach"
      ],
      "source_id": "assumed-image:secureendpoint:challenge:18",
      "importance": "supporting",
      "query_terms": [
        "abstract editorial texture quiet material study neutral atmospheric backdrop",
        "quiet, restrained, unobtrusive",
        "3:2",
        "editorial_photo",
        "context"
      ],
      "section_ids": [
        "secureendpoint:challenge"
      ],
      "source_policy": "optional_external_acquisition",
      "source_status": "needs_acquisition",
      "component_intent": null,
      "required_for_handoff": false
    },
    {
      "kind": "asset",
      "details": {
        "placement": "context",
        "style_mood": "quiet, restrained, unobtrusive",
        "focal_point": "",
        "orientation": "landscape",
        "aspect_ratio": "3:2",
        "theme_colors": [],
        "minimum_width": 1200,
        "minimum_height": 700,
        "provider_terms": [
          "abstract editorial texture",
          "quiet material study",
          "neutral atmospheric backdrop"
        ],
        "alt_text_intent": "Decorative atmosphere; empty alt text unless the final composition gives it semantic meaning.",
        "expected_exports": [],
        "interaction_class": "",
        "negative_concepts": [
          "portrait",
          "face",
          "screenshot",
          "dashboard",
          "logo",
          "project proof",
          "employer imagery",
          "private media",
          "testimonial"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack below essential copy and crop without hiding content.",
        "reduced_motion_behavior": "Render the complete image treatment statically."
      },
      "need_id": "need-2af5fc8d108ec85b1d08",
      "purpose": "Quiet decorative atmosphere for a supporting section whose subject is not one of the named roles above; kept profession-neutral rather than assumed technical.",
      "category": "editorial_photo",
      "fallback": "Use the approved text-led/static composition without stock substitution.",
      "route_ids": [
        "secureendpoint"
      ],
      "scene_ids": [
        "secureendpoint-result-context"
      ],
      "source_id": "assumed-image:secureendpoint:outcome:19",
      "importance": "supporting",
      "query_terms": [
        "abstract editorial texture quiet material study neutral atmospheric backdrop",
        "quiet, restrained, unobtrusive",
        "3:2",
        "editorial_photo",
        "context"
      ],
      "section_ids": [
        "secureendpoint:outcome"
      ],
      "source_policy": "optional_external_acquisition",
      "source_status": "needs_acquisition",
      "component_intent": null,
      "required_for_handoff": false
    },
    {
      "kind": "asset",
      "details": {
        "placement": "context",
        "style_mood": "quiet, restrained, unobtrusive",
        "focal_point": "",
        "orientation": "landscape",
        "aspect_ratio": "3:2",
        "theme_colors": [],
        "minimum_width": 1200,
        "minimum_height": 700,
        "provider_terms": [
          "abstract editorial texture",
          "quiet material study",
          "neutral atmospheric backdrop"
        ],
        "alt_text_intent": "Decorative atmosphere; empty alt text unless the final composition gives it semantic meaning.",
        "expected_exports": [],
        "interaction_class": "",
        "negative_concepts": [
          "portrait",
          "face",
          "screenshot",
          "dashboard",
          "logo",
          "project proof",
          "employer imagery",
          "private media",
          "testimonial"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack below essential copy and crop without hiding content.",
        "reduced_motion_behavior": "Render the complete image treatment statically."
      },
      "need_id": "need-989bb622f62c86c0ee1c",
      "purpose": "Quiet decorative atmosphere for a supporting section whose subject is not one of the named roles above; kept profession-neutral rather than assumed technical.",
      "category": "editorial_photo",
      "fallback": "Use the approved text-led/static composition without stock substitution.",
      "route_ids": [
        "secureendpoint"
      ],
      "scene_ids": [
        "secureendpoint-overview"
      ],
      "source_id": "assumed-image:secureendpoint:overview:20",
      "importance": "supporting",
      "query_terms": [
        "abstract editorial texture quiet material study neutral atmospheric backdrop",
        "quiet, restrained, unobtrusive",
        "3:2",
        "editorial_photo",
        "context"
      ],
      "section_ids": [
        "secureendpoint:overview"
      ],
      "source_policy": "optional_external_acquisition",
      "source_status": "needs_acquisition",
      "component_intent": null,
      "required_for_handoff": false
    },
    {
      "kind": "asset",
      "details": {
        "placement": "context",
        "style_mood": "quiet, restrained, unobtrusive",
        "focal_point": "",
        "orientation": "landscape",
        "aspect_ratio": "3:2",
        "theme_colors": [],
        "minimum_width": 1200,
        "minimum_height": 700,
        "provider_terms": [
          "abstract editorial texture",
          "quiet material study",
          "neutral atmospheric backdrop"
        ],
        "alt_text_intent": "Decorative atmosphere; empty alt text unless the final composition gives it semantic meaning.",
        "expected_exports": [],
        "interaction_class": "",
        "negative_concepts": [
          "portrait",
          "face",
          "screenshot",
          "dashboard",
          "logo",
          "project proof",
          "employer imagery",
          "private media",
          "testimonial"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack below essential copy and crop without hiding content.",
        "reduced_motion_behavior": "Render the complete image treatment statically."
      },
      "need_id": "need-4421d6f4a49adbf70e30",
      "purpose": "Quiet decorative atmosphere for a supporting section whose subject is not one of the named roles above; kept profession-neutral rather than assumed technical.",
      "category": "editorial_photo",
      "fallback": "Use the approved text-led/static composition without stock substitution.",
      "route_ids": [
        "secureendpoint"
      ],
      "scene_ids": [
        "secureendpoint-result-context"
      ],
      "source_id": "assumed-image:secureendpoint:technology:21",
      "importance": "supporting",
      "query_terms": [
        "abstract editorial texture quiet material study neutral atmospheric backdrop",
        "quiet, restrained, unobtrusive",
        "3:2",
        "editorial_photo",
        "context"
      ],
      "section_ids": [
        "secureendpoint:technology"
      ],
      "source_policy": "optional_external_acquisition",
      "source_status": "needs_acquisition",
      "component_intent": null,
      "required_for_handoff": false
    },
    {
      "kind": "resource",
      "details": {
        "placement": "home / home-positioning",
        "lookup_status": "verified",
        "provider_terms": [],
        "adaptation_notes": "Keep the abstract visual small, preserve headline hierarchy, and avoid turning the composition into a generic template.",
        "interaction_role": "",
        "interaction_class": "",
        "negative_concepts": [],
        "interaction_outcome": "",
        "responsive_behavior": "",
        "required_for_handoff": null,
        "reduced_motion_behavior": ""
      },
      "need_id": "need-6b0208477661a71dfff5",
      "purpose": "Adapt as the text-led homepage hero.",
      "category": "hero_pattern",
      "fallback": "Plain text-led hero with a static line motif.",
      "route_ids": [
        "home"
      ],
      "scene_ids": [
        "home-positioning"
      ],
      "source_id": "hero_asymmetric_text_dominant",
      "importance": "recommended",
      "query_terms": [
        "hero_pattern",
        "Adapt as the text-led homepage hero.",
        "The homepage has a strong concise positioning statement and no approved hero image, allowing typography to carry the first impression."
      ],
      "section_ids": [],
      "source_policy": "",
      "source_status": "",
      "component_intent": null,
      "required_for_handoff": false
    },
    {
      "kind": "resource",
      "details": {
        "placement": "home / home-proof-capabilities; workspace360 / workspace360-overview and workspace360-result-context; secureendpoint / secureendpoint-overview and secureendpoint-result-context",
        "lookup_status": "verified",
        "provider_terms": [],
        "adaptation_notes": "Use only supplied values and contexts; pair each comparison with plain-language explanation and never imply live telemetry.",
        "interaction_role": "",
        "interaction_class": "",
        "negative_concepts": [],
        "interaction_outcome": "",
        "responsive_behavior": "",
        "required_for_handoff": null,
        "reduced_motion_behavior": ""
      },
      "need_id": "need-902f5f32af160f3530d8",
      "purpose": "Adapt as labelled comparisons that make approved outcomes legible.",
      "category": "diagram_primitive",
      "fallback": "Text-only metric blocks with explanatory paragraphs.",
      "route_ids": [
        "home",
        "secureendpoint",
        "workspace360"
      ],
      "scene_ids": [
        "home-proof-capabilities",
        "secureendpoint-overview",
        "secureendpoint-result-context",
        "workspace360-overview",
        "workspace360-result-context"
      ],
      "source_id": "diagram_before_after",
      "importance": "recommended",
      "query_terms": [
        "diagram_primitive",
        "Adapt as labelled comparisons that make approved outcomes legible.",
        "WorkSpace360 and SecureEndpoint contain approved measurable outcomes that benefit from labelled static comparisons without screenshots or charts."
      ],
      "section_ids": [],
      "source_policy": "",
      "source_status": "",
      "component_intent": null,
      "required_for_handoff": false
    },
    {
      "kind": "resource",
      "details": {
        "placement": "workspace360 / workspace360-need-approach; secureendpoint / secureendpoint-need-approach; employeeconnect / employeeconnect-overview and employeeconnect-need-approach",
        "lookup_status": "verified",
        "provider_terms": [],
        "adaptation_notes": "Keep step counts low, preserve supplied titles and contribution boundaries, and simplify rather than shrink on mobile.",
        "interaction_role": "",
        "interaction_class": "",
        "negative_concepts": [],
        "interaction_outcome": "",
        "responsive_behavior": "",
        "required_for_handoff": null,
        "reduced_motion_behavior": ""
      },
      "need_id": "need-ed9585639f0ba7f22051",
      "purpose": "Adapt as a sparse sequence beside or behind approved approach copy.",
      "category": "diagram_primitive",
      "fallback": "Ordered text blocks with dividers and no diagram layer.",
      "route_ids": [
        "employeeconnect",
        "secureendpoint",
        "workspace360"
      ],
      "scene_ids": [
        "employeeconnect-need-approach",
        "employeeconnect-overview",
        "secureendpoint-need-approach",
        "workspace360-need-approach"
      ],
      "source_id": "diagram_process_flow",
      "importance": "recommended",
      "query_terms": [
        "diagram_primitive",
        "Adapt as a sparse sequence beside or behind approved approach copy.",
        "All three case studies contain approved three-step contribution sequences suited to simple words-first process diagrams."
      ],
      "section_ids": [],
      "source_policy": "",
      "source_status": "",
      "component_intent": null,
      "required_for_handoff": false
    },
    {
      "kind": "resource",
      "details": {
        "placement": "home / home-experience-work and all case-study routes",
        "lookup_status": "verified",
        "provider_terms": [],
        "adaptation_notes": "Define narrow-screen collapse and use current-route text or structural cues in addition to color.",
        "interaction_role": "",
        "interaction_class": "",
        "negative_concepts": [],
        "interaction_outcome": "",
        "responsive_behavior": "",
        "required_for_handoff": null,
        "reduced_motion_behavior": ""
      },
      "need_id": "need-d912bac698033b12ba70",
      "purpose": "Adapt as persistent route navigation and LinkedIn action.",
      "category": "navigation_pattern",
      "fallback": "Compact non-sticky navigation at the beginning and end of each route.",
      "route_ids": [
        "home"
      ],
      "scene_ids": [
        "home-experience-work"
      ],
      "source_id": "navigation_sticky_minimal_top",
      "importance": "optional",
      "query_terms": [
        "navigation_pattern",
        "Adapt as persistent route navigation and LinkedIn action.",
        "Four public routes benefit from persistent cross-route orientation with a restrained primary external action."
      ],
      "section_ids": [],
      "source_policy": "",
      "source_status": "",
      "component_intent": null,
      "required_for_handoff": false
    },
    {
      "kind": "resource",
      "details": {
        "placement": "home / home:capabilities",
        "lookup_status": "assumed_intent",
        "provider_terms": [
          "accordion",
          "collapsible",
          "disclosure",
          "expandable",
          "progressive disclosure",
          "tabs"
        ],
        "adaptation_notes": "Use real registry source only; preserve keyboard access, responsive behavior, and reduced-motion static state.",
        "interaction_role": "capability-grouping",
        "interaction_class": "",
        "negative_concepts": [
          "screenshot",
          "invented project detail",
          "faq",
          "pricing",
          "dashboard",
          "login",
          "signup"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack controls and keep every approved item reachable without hover.",
        "required_for_handoff": false,
        "reduced_motion_behavior": "Keep the full interaction available without sequencing or animation."
      },
      "need_id": "need-45306d9f9ef14e8b68fb",
      "purpose": "Group capability items with progressive disclosure.",
      "category": "visual_component",
      "fallback": "Use the approved semantic section structure without a registry component.",
      "route_ids": [
        "home"
      ],
      "scene_ids": [
        "home-proof-capabilities"
      ],
      "source_id": "assumed-component:home:capabilities:capability-grouping",
      "importance": "optional",
      "query_terms": [
        "visual_component",
        "Group capability items with progressive disclosure."
      ],
      "section_ids": [
        "home:capabilities"
      ],
      "source_policy": "",
      "source_status": "",
      "component_intent": {
        "purpose": "Group capability items with progressive disclosure.",
        "role_id": "capability-grouping",
        "required": false,
        "route_id": "home",
        "scene_id": "home-proof-capabilities",
        "placement": "home / home:capabilities",
        "section_id": "home:capabilities",
        "prohibitions": [
          "Do not add an interaction to a section that does not contain the approved items."
        ],
        "fallback_type": "semantic_local",
        "provider_terms": [
          "accordion",
          "collapsible",
          "disclosure",
          "expandable",
          "progressive disclosure",
          "tabs"
        ],
        "expected_exports": [],
        "interaction_class": "disclosure",
        "negative_concepts": [
          "screenshot",
          "invented project detail",
          "faq",
          "pricing",
          "dashboard",
          "login",
          "signup"
        ],
        "interaction_outcome": "Group capability items with progressive disclosure.",
        "responsive_behavior": "Stack controls and keep every approved item reachable without hover.",
        "reduced_motion_behavior": "Keep the full interaction available without sequencing or animation."
      },
      "required_for_handoff": false
    },
    {
      "kind": "resource",
      "details": {
        "placement": "home / home:experience",
        "lookup_status": "assumed_intent",
        "provider_terms": [
          "timeline",
          "milestones",
          "chronology",
          "work history",
          "career progression"
        ],
        "adaptation_notes": "Use real registry source only; preserve keyboard access, responsive behavior, and reduced-motion static state.",
        "interaction_role": "experience-timeline",
        "interaction_class": "",
        "negative_concepts": [
          "screenshot",
          "invented project detail",
          "wizard",
          "onboarding",
          "checkout",
          "form",
          "dashboard"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack controls and keep every approved item reachable without hover.",
        "required_for_handoff": false,
        "reduced_motion_behavior": "Keep the full interaction available without sequencing or animation."
      },
      "need_id": "need-a365fadb22111a2140db",
      "purpose": "Show chronological experience progression.",
      "category": "visual_component",
      "fallback": "Use the approved semantic section structure without a registry component.",
      "route_ids": [
        "home"
      ],
      "scene_ids": [
        "home-experience-work"
      ],
      "source_id": "assumed-component:home:experience:experience-timeline",
      "importance": "optional",
      "query_terms": [
        "visual_component",
        "Show chronological experience progression."
      ],
      "section_ids": [
        "home:experience"
      ],
      "source_policy": "",
      "source_status": "",
      "component_intent": {
        "purpose": "Show chronological experience progression.",
        "role_id": "experience-timeline",
        "required": false,
        "route_id": "home",
        "scene_id": "home-experience-work",
        "placement": "home / home:experience",
        "section_id": "home:experience",
        "prohibitions": [
          "Do not add an interaction to a section that does not contain the approved items."
        ],
        "fallback_type": "semantic_local",
        "provider_terms": [
          "timeline",
          "milestones",
          "chronology",
          "work history",
          "career progression"
        ],
        "expected_exports": [],
        "interaction_class": "progression",
        "negative_concepts": [
          "screenshot",
          "invented project detail",
          "wizard",
          "onboarding",
          "checkout",
          "form",
          "dashboard"
        ],
        "interaction_outcome": "Show chronological experience progression.",
        "responsive_behavior": "Stack controls and keep every approved item reachable without hover.",
        "reduced_motion_behavior": "Keep the full interaction available without sequencing or animation."
      },
      "required_for_handoff": false
    },
    {
      "kind": "resource",
      "details": {
        "placement": "home / home:featured-work",
        "lookup_status": "assumed_intent",
        "provider_terms": [
          "project detail",
          "expandable cards",
          "dialog",
          "drawer",
          "tabs",
          "case study"
        ],
        "adaptation_notes": "Use real registry source only; preserve keyboard access, responsive behavior, and reduced-motion static state.",
        "interaction_role": "selected-work-detail",
        "interaction_class": "",
        "negative_concepts": [
          "screenshot",
          "invented project detail",
          "video player",
          "login",
          "signup",
          "dashboard"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack controls and keep every approved item reachable without hover.",
        "required_for_handoff": false,
        "reduced_motion_behavior": "Keep the full interaction available without sequencing or animation."
      },
      "need_id": "need-f46a8c73b1f9fb728fcf",
      "purpose": "Let visitors explore approved work details.",
      "category": "visual_component",
      "fallback": "Use the approved semantic section structure without a registry component.",
      "route_ids": [
        "home"
      ],
      "scene_ids": [
        "home-experience-work"
      ],
      "source_id": "assumed-component:home:featured-work:selected-work-detail",
      "importance": "optional",
      "query_terms": [
        "visual_component",
        "Let visitors explore approved work details."
      ],
      "section_ids": [
        "home:featured-work"
      ],
      "source_policy": "",
      "source_status": "",
      "component_intent": {
        "purpose": "Let visitors explore approved work details.",
        "role_id": "selected-work-detail",
        "required": false,
        "route_id": "home",
        "scene_id": "home-experience-work",
        "placement": "home / home:featured-work",
        "section_id": "home:featured-work",
        "prohibitions": [
          "Do not add an interaction to a section that does not contain the approved items."
        ],
        "fallback_type": "semantic_local",
        "provider_terms": [
          "project detail",
          "expandable cards",
          "dialog",
          "drawer",
          "tabs",
          "case study"
        ],
        "expected_exports": [],
        "interaction_class": "detail-exploration",
        "negative_concepts": [
          "screenshot",
          "invented project detail",
          "video player",
          "login",
          "signup",
          "dashboard"
        ],
        "interaction_outcome": "Let visitors explore approved work details.",
        "responsive_behavior": "Stack controls and keep every approved item reachable without hover.",
        "reduced_motion_behavior": "Keep the full interaction available without sequencing or animation."
      },
      "required_for_handoff": false
    },
    {
      "kind": "resource",
      "details": {
        "placement": "workspace360 / workspace360:approach",
        "lookup_status": "assumed_intent",
        "provider_terms": [
          "project detail",
          "expandable cards",
          "dialog",
          "drawer",
          "tabs",
          "case study"
        ],
        "adaptation_notes": "Use real registry source only; preserve keyboard access, responsive behavior, and reduced-motion static state.",
        "interaction_role": "selected-work-detail",
        "interaction_class": "",
        "negative_concepts": [
          "screenshot",
          "invented project detail",
          "video player",
          "login",
          "signup",
          "dashboard"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack controls and keep every approved item reachable without hover.",
        "required_for_handoff": false,
        "reduced_motion_behavior": "Keep the full interaction available without sequencing or animation."
      },
      "need_id": "need-424ae2c2a52dc37bcb48",
      "purpose": "Let visitors explore approved work details.",
      "category": "visual_component",
      "fallback": "Use the approved semantic section structure without a registry component.",
      "route_ids": [
        "workspace360"
      ],
      "scene_ids": [
        "workspace360-need-approach"
      ],
      "source_id": "assumed-component:workspace360:approach:selected-work-detail",
      "importance": "optional",
      "query_terms": [
        "visual_component",
        "Let visitors explore approved work details."
      ],
      "section_ids": [
        "workspace360:approach"
      ],
      "source_policy": "",
      "source_status": "",
      "component_intent": {
        "purpose": "Let visitors explore approved work details.",
        "role_id": "selected-work-detail",
        "required": false,
        "route_id": "workspace360",
        "scene_id": "workspace360-need-approach",
        "placement": "workspace360 / workspace360:approach",
        "section_id": "workspace360:approach",
        "prohibitions": [
          "Do not add an interaction to a section that does not contain the approved items."
        ],
        "fallback_type": "semantic_local",
        "provider_terms": [
          "project detail",
          "expandable cards",
          "dialog",
          "drawer",
          "tabs",
          "case study"
        ],
        "expected_exports": [],
        "interaction_class": "detail-exploration",
        "negative_concepts": [
          "screenshot",
          "invented project detail",
          "video player",
          "login",
          "signup",
          "dashboard"
        ],
        "interaction_outcome": "Let visitors explore approved work details.",
        "responsive_behavior": "Stack controls and keep every approved item reachable without hover.",
        "reduced_motion_behavior": "Keep the full interaction available without sequencing or animation."
      },
      "required_for_handoff": false
    },
    {
      "kind": "resource",
      "details": {
        "placement": "workspace360 / workspace360:approach",
        "lookup_status": "assumed_intent",
        "provider_terms": [
          "process steps",
          "stepper",
          "workflow",
          "sequence",
          "progress steps",
          "method"
        ],
        "adaptation_notes": "Use real registry source only; preserve keyboard access, responsive behavior, and reduced-motion static state.",
        "interaction_role": "process-sequence",
        "interaction_class": "",
        "negative_concepts": [
          "screenshot",
          "invented project detail",
          "wizard",
          "onboarding",
          "checkout",
          "form",
          "dashboard"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack controls and keep every approved item reachable without hover.",
        "required_for_handoff": false,
        "reduced_motion_behavior": "Keep the full interaction available without sequencing or animation."
      },
      "need_id": "need-e48f569b72b8f8a3e232",
      "purpose": "Present the approved working approach as a complete sequence.",
      "category": "visual_component",
      "fallback": "Use the approved semantic section structure without a registry component.",
      "route_ids": [
        "workspace360"
      ],
      "scene_ids": [
        "workspace360-need-approach"
      ],
      "source_id": "assumed-component:workspace360:approach:process-sequence",
      "importance": "optional",
      "query_terms": [
        "visual_component",
        "Present the approved working approach as a complete sequence."
      ],
      "section_ids": [
        "workspace360:approach"
      ],
      "source_policy": "",
      "source_status": "",
      "component_intent": {
        "purpose": "Present the approved working approach as a complete sequence.",
        "role_id": "process-sequence",
        "required": false,
        "route_id": "workspace360",
        "scene_id": "workspace360-need-approach",
        "placement": "workspace360 / workspace360:approach",
        "section_id": "workspace360:approach",
        "prohibitions": [
          "Do not add an interaction to a section that does not contain the approved items."
        ],
        "fallback_type": "semantic_local",
        "provider_terms": [
          "process steps",
          "stepper",
          "workflow",
          "sequence",
          "progress steps",
          "method"
        ],
        "expected_exports": [],
        "interaction_class": "process-sequence",
        "negative_concepts": [
          "screenshot",
          "invented project detail",
          "wizard",
          "onboarding",
          "checkout",
          "form",
          "dashboard"
        ],
        "interaction_outcome": "Present the approved working approach as a complete sequence.",
        "responsive_behavior": "Stack controls and keep every approved item reachable without hover.",
        "reduced_motion_behavior": "Keep the full interaction available without sequencing or animation."
      },
      "required_for_handoff": false
    },
    {
      "kind": "resource",
      "details": {
        "placement": "workspace360 / workspace360:technology",
        "lookup_status": "assumed_intent",
        "provider_terms": [
          "project detail",
          "expandable cards",
          "dialog",
          "drawer",
          "tabs",
          "case study"
        ],
        "adaptation_notes": "Use real registry source only; preserve keyboard access, responsive behavior, and reduced-motion static state.",
        "interaction_role": "selected-work-detail",
        "interaction_class": "",
        "negative_concepts": [
          "screenshot",
          "invented project detail",
          "video player",
          "login",
          "signup",
          "dashboard"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack controls and keep every approved item reachable without hover.",
        "required_for_handoff": false,
        "reduced_motion_behavior": "Keep the full interaction available without sequencing or animation."
      },
      "need_id": "need-04cb2e11cbd88d33a174",
      "purpose": "Let visitors explore approved work details.",
      "category": "visual_component",
      "fallback": "Use the approved semantic section structure without a registry component.",
      "route_ids": [
        "workspace360"
      ],
      "scene_ids": [
        "workspace360-result-context"
      ],
      "source_id": "assumed-component:workspace360:technology:selected-work-detail",
      "importance": "optional",
      "query_terms": [
        "visual_component",
        "Let visitors explore approved work details."
      ],
      "section_ids": [
        "workspace360:technology"
      ],
      "source_policy": "",
      "source_status": "",
      "component_intent": {
        "purpose": "Let visitors explore approved work details.",
        "role_id": "selected-work-detail",
        "required": false,
        "route_id": "workspace360",
        "scene_id": "workspace360-result-context",
        "placement": "workspace360 / workspace360:technology",
        "section_id": "workspace360:technology",
        "prohibitions": [
          "Do not add an interaction to a section that does not contain the approved items."
        ],
        "fallback_type": "semantic_local",
        "provider_terms": [
          "project detail",
          "expandable cards",
          "dialog",
          "drawer",
          "tabs",
          "case study"
        ],
        "expected_exports": [],
        "interaction_class": "detail-exploration",
        "negative_concepts": [
          "screenshot",
          "invented project detail",
          "video player",
          "login",
          "signup",
          "dashboard"
        ],
        "interaction_outcome": "Let visitors explore approved work details.",
        "responsive_behavior": "Stack controls and keep every approved item reachable without hover.",
        "reduced_motion_behavior": "Keep the full interaction available without sequencing or animation."
      },
      "required_for_handoff": false
    },
    {
      "kind": "resource",
      "details": {
        "placement": "secureendpoint / secureendpoint:approach",
        "lookup_status": "assumed_intent",
        "provider_terms": [
          "process steps",
          "stepper",
          "workflow",
          "sequence",
          "progress steps",
          "method"
        ],
        "adaptation_notes": "Use real registry source only; preserve keyboard access, responsive behavior, and reduced-motion static state.",
        "interaction_role": "process-sequence",
        "interaction_class": "",
        "negative_concepts": [
          "screenshot",
          "invented project detail",
          "wizard",
          "onboarding",
          "checkout",
          "form",
          "dashboard"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack controls and keep every approved item reachable without hover.",
        "required_for_handoff": false,
        "reduced_motion_behavior": "Keep the full interaction available without sequencing or animation."
      },
      "need_id": "need-b9f7c79d6599934cd4af",
      "purpose": "Present the approved working approach as a complete sequence.",
      "category": "visual_component",
      "fallback": "Use the approved semantic section structure without a registry component.",
      "route_ids": [
        "secureendpoint"
      ],
      "scene_ids": [
        "secureendpoint-need-approach"
      ],
      "source_id": "assumed-component:secureendpoint:approach:process-sequence",
      "importance": "optional",
      "query_terms": [
        "visual_component",
        "Present the approved working approach as a complete sequence."
      ],
      "section_ids": [
        "secureendpoint:approach"
      ],
      "source_policy": "",
      "source_status": "",
      "component_intent": {
        "purpose": "Present the approved working approach as a complete sequence.",
        "role_id": "process-sequence",
        "required": false,
        "route_id": "secureendpoint",
        "scene_id": "secureendpoint-need-approach",
        "placement": "secureendpoint / secureendpoint:approach",
        "section_id": "secureendpoint:approach",
        "prohibitions": [
          "Do not add an interaction to a section that does not contain the approved items."
        ],
        "fallback_type": "semantic_local",
        "provider_terms": [
          "process steps",
          "stepper",
          "workflow",
          "sequence",
          "progress steps",
          "method"
        ],
        "expected_exports": [],
        "interaction_class": "process-sequence",
        "negative_concepts": [
          "screenshot",
          "invented project detail",
          "wizard",
          "onboarding",
          "checkout",
          "form",
          "dashboard"
        ],
        "interaction_outcome": "Present the approved working approach as a complete sequence.",
        "responsive_behavior": "Stack controls and keep every approved item reachable without hover.",
        "reduced_motion_behavior": "Keep the full interaction available without sequencing or animation."
      },
      "required_for_handoff": false
    },
    {
      "kind": "resource",
      "details": {
        "placement": "employeeconnect / employeeconnect:approach",
        "lookup_status": "assumed_intent",
        "provider_terms": [
          "process steps",
          "stepper",
          "workflow",
          "sequence",
          "progress steps",
          "method"
        ],
        "adaptation_notes": "Use real registry source only; preserve keyboard access, responsive behavior, and reduced-motion static state.",
        "interaction_role": "process-sequence",
        "interaction_class": "",
        "negative_concepts": [
          "screenshot",
          "invented project detail",
          "wizard",
          "onboarding",
          "checkout",
          "form",
          "dashboard"
        ],
        "interaction_outcome": "",
        "responsive_behavior": "Stack controls and keep every approved item reachable without hover.",
        "required_for_handoff": false,
        "reduced_motion_behavior": "Keep the full interaction available without sequencing or animation."
      },
      "need_id": "need-ffed398e056befccc34a",
      "purpose": "Present the approved working approach as a complete sequence.",
      "category": "visual_component",
      "fallback": "Use the approved semantic section structure without a registry component.",
      "route_ids": [
        "employeeconnect"
      ],
      "scene_ids": [
        "employeeconnect-need-approach"
      ],
      "source_id": "assumed-component:employeeconnect:approach:process-sequence",
      "importance": "optional",
      "query_terms": [
        "visual_component",
        "Present the approved working approach as a complete sequence."
      ],
      "section_ids": [
        "employeeconnect:approach"
      ],
      "source_policy": "",
      "source_status": "",
      "component_intent": {
        "purpose": "Present the approved working approach as a complete sequence.",
        "role_id": "process-sequence",
        "required": false,
        "route_id": "employeeconnect",
        "scene_id": "employeeconnect-need-approach",
        "placement": "employeeconnect / employeeconnect:approach",
        "section_id": "employeeconnect:approach",
        "prohibitions": [
          "Do not add an interaction to a section that does not contain the approved items."
        ],
        "fallback_type": "semantic_local",
        "provider_terms": [
          "process steps",
          "stepper",
          "workflow",
          "sequence",
          "progress steps",
          "method"
        ],
        "expected_exports": [],
        "interaction_class": "process-sequence",
        "negative_concepts": [
          "screenshot",
          "invented project detail",
          "wizard",
          "onboarding",
          "checkout",
          "form",
          "dashboard"
        ],
        "interaction_outcome": "Present the approved working approach as a complete sequence.",
        "responsive_behavior": "Stack controls and keep every approved item reachable without hover.",
        "reduced_motion_behavior": "Keep the full interaction available without sequencing or animation."
      },
      "required_for_handoff": false
    },
    {
      "kind": "resource",
      "details": {
        "subsets": [
          "latin"
        ],
        "weights": [
          "400",
          "500",
          "600",
          "700"
        ],
        "font_profile": "editorial_technical"
      },
      "need_id": "need-016331262cb7124422e4",
      "purpose": "A distinctive display/body font family for the approved visual language, vendored locally with Latin glyph coverage.",
      "category": "font",
      "fallback": "Use the typed local system font recipe with the declared weights.",
      "route_ids": [
        "home",
        "workspace360",
        "secureendpoint",
        "employeeconnect"
      ],
      "scene_ids": [],
      "source_id": "typography-font",
      "importance": "important",
      "query_terms": [
        "space grotesk",
        "manrope",
        "technical sans"
      ],
      "section_ids": [],
      "source_policy": "optional_external_acquisition",
      "source_status": "needs_acquisition",
      "component_intent": null,
      "required_for_handoff": true
    }
  ],
  "assumption_hash": "84cb9c3b154af69a979f1ebec585eb3fdce15f276e5abcfa3aa9a5c99fa519bb",
  "component_index": [
    {
      "need_id": "need-ffaff9238945207f5816",
      "purpose": "Lightweight abstract connected-workflow visual balancing the homepage hero and representing complexity becoming dependable.",
      "role_id": "home-operating-chain",
      "guidance": "None of the listed chart or checkbox examples genuinely represents the connected workflow. Build a lightweight custom words-first motif instead.",
      "route_ids": [
        "home"
      ],
      "suggestions": [
        {
          "name": "chart-pie-donut-text",
          "title": "chart-pie-donut-text",
          "item_url": "https://ui.shadcn.com/r/styles/new-york-v4/chart-pie-donut-text.json",
          "provider": "shadcn",
          "description": ""
        },
        {
          "name": "chart-radial-text",
          "title": "chart-radial-text",
          "item_url": "https://ui.shadcn.com/r/styles/new-york-v4/chart-radial-text.json",
          "provider": "shadcn",
          "description": ""
        },
        {
          "name": "checkbox-with-text",
          "title": "checkbox-with-text",
          "item_url": "https://ui.shadcn.com/r/styles/new-york-v4/checkbox-with-text.json",
          "provider": "shadcn",
          "description": ""
        }
      ],
      "primary_suggestion_index": null
    },
    {
      "need_id": "need-8ac3b90c9d5812edd926",
      "purpose": "Abstract words-first workflow motif supporting the transition from career experience to selected work.",
      "role_id": "home-workflow-abstract",
      "guidance": "The listed dashboard, login, and sidebar examples are not a good semantic fit. Use a custom abstract workflow treatment.",
      "route_ids": [
        "home"
      ],
      "suggestions": [
        {
          "name": "dashboard-01",
          "title": "dashboard-01",
          "item_url": "https://ui.shadcn.com/r/styles/new-york-v4/dashboard-01.json",
          "provider": "shadcn",
          "description": "A dashboard with sidebar, charts and data table."
        },
        {
          "name": "login-04",
          "title": "login-04",
          "item_url": "https://ui.shadcn.com/r/styles/new-york-v4/login-04.json",
          "provider": "shadcn",
          "description": "A login page with form and image."
        },
        {
          "name": "sidebar-15",
          "title": "sidebar-15",
          "item_url": "https://ui.shadcn.com/r/styles/new-york-v4/sidebar-15.json",
          "provider": "shadcn",
          "description": "A left and right sidebar."
        }
      ],
      "primary_suggestion_index": null
    },
    {
      "need_id": "need-009f78480992358fdee8",
      "purpose": "Words-first abstract representation of the approved WorkSpace360 operating stages.",
      "role_id": "workspace360-process-visual",
      "guidance": "A circular progress component could overstate the process or imply a metric. Prefer a custom ordered stage visual.",
      "route_ids": [
        "workspace360"
      ],
      "suggestions": [
        {
          "name": "animated-circular-progress-bar",
          "title": "Animated Circular Progress Bar",
          "item_url": "https://magicui.design/r/animated-circular-progress-bar.json",
          "provider": "magicui",
          "description": "Animated Circular Progress Bar is a component that displays a circular gauge with a percentage value."
        },
        {
          "name": "backlight-image-demo",
          "title": "backlight-image-demo",
          "item_url": "https://magicui.design/r/backlight-image-demo.json",
          "provider": "magicui",
          "description": "An example of the backlight component with a image."
        },
        {
          "name": "backlight-svg-demo",
          "title": "backlight-svg-demo",
          "item_url": "https://magicui.design/r/backlight-svg-demo.json",
          "provider": "magicui",
          "description": "An example of the backlight component with SVGs."
        }
      ],
      "primary_suggestion_index": null
    },
    {
      "need_id": "need-15fc7788e7c478618112",
      "purpose": "Words-first representative chain connecting security controls, visibility, and remediation.",
      "role_id": "secureendpoint-control-chain",
      "guidance": "An animated beam can support a restrained connector relationship if static labels remain complete and motion is optional; avoid making it resemble live security telemetry.",
      "route_ids": [
        "secureendpoint"
      ],
      "suggestions": [
        {
          "name": "morphing-text",
          "title": "Morphing Text",
          "item_url": "https://magicui.design/r/morphing-text.json",
          "provider": "magicui",
          "description": "A dynamic text morphing component for Magic UI."
        },
        {
          "name": "spinning-text",
          "title": "Spinning Text",
          "item_url": "https://magicui.design/r/spinning-text.json",
          "provider": "magicui",
          "description": "The Spinning Text component animates text in a circular motion with customizable speed, direction, color, and transitions for dynamic and engaging effects."
        },
        {
          "name": "animated-beam",
          "title": "Animated Beam",
          "item_url": "https://magicui.design/r/animated-beam.json",
          "provider": "magicui",
          "description": "An animated beam of light which travels along a path. Useful for showcasing the integration features of a website."
        }
      ],
      "primary_suggestion_index": 2
    },
    {
      "need_id": "need-c60c81649b07900c657a",
      "purpose": "Words-first abstract migration path balancing administration, adoption, and documentation.",
      "role_id": "employeeconnect-migration-path",
      "guidance": "The listed progress and backlight examples are not a strong migration-path fit. Prefer a custom words-first sequence.",
      "route_ids": [
        "employeeconnect"
      ],
      "suggestions": [
        {
          "name": "animated-circular-progress-bar",
          "title": "Animated Circular Progress Bar",
          "item_url": "https://magicui.design/r/animated-circular-progress-bar.json",
          "provider": "magicui",
          "description": "Animated Circular Progress Bar is a component that displays a circular gauge with a percentage value."
        },
        {
          "name": "backlight-image-demo",
          "title": "backlight-image-demo",
          "item_url": "https://magicui.design/r/backlight-image-demo.json",
          "provider": "magicui",
          "description": "An example of the backlight component with a image."
        },
        {
          "name": "backlight-svg-demo",
          "title": "backlight-svg-demo",
          "item_url": "https://magicui.design/r/backlight-svg-demo.json",
          "provider": "magicui",
          "description": "An example of the backlight component with SVGs."
        }
      ],
      "primary_suggestion_index": null
    },
    {
      "need_id": "need-45306d9f9ef14e8b68fb",
      "purpose": "Group capability items with progressive disclosure.",
      "role_id": "assumed-component:home:capabilities:capability-grouping",
      "guidance": "Use an explicit grouped disclosure pattern for capability families, with visible expanded and collapsed labels and no hover dependency.",
      "route_ids": [
        "home"
      ],
      "suggestions": [
        {
          "name": "button-group",
          "title": "button-group",
          "item_url": "https://ui.shadcn.com/r/styles/new-york-v4/button-group.json",
          "provider": "shadcn",
          "description": ""
        },
        {
          "name": "button-group-demo",
          "title": "button-group-demo",
          "item_url": "https://ui.shadcn.com/r/styles/new-york-v4/button-group-demo.json",
          "provider": "shadcn",
          "description": ""
        },
        {
          "name": "button-group-dropdown",
          "title": "button-group-dropdown",
          "item_url": "https://ui.shadcn.com/r/styles/new-york-v4/button-group-dropdown.json",
          "provider": "shadcn",
          "description": ""
        }
      ],
      "primary_suggestion_index": 2
    },
    {
      "need_id": "need-a365fadb22111a2140db",
      "purpose": "Show chronological experience progression.",
      "role_id": "assumed-component:home:experience:experience-timeline",
      "guidance": "The listed visual examples do not semantically fit a chronological timeline. Use a readable ordered progression with restrained markers.",
      "route_ids": [
        "home"
      ],
      "suggestions": [
        {
          "name": "animated-circular-progress-bar",
          "title": "Animated Circular Progress Bar",
          "item_url": "https://magicui.design/r/animated-circular-progress-bar.json",
          "provider": "magicui",
          "description": "Animated Circular Progress Bar is a component that displays a circular gauge with a percentage value."
        },
        {
          "name": "backlight-image-demo",
          "title": "backlight-image-demo",
          "item_url": "https://magicui.design/r/backlight-image-demo.json",
          "provider": "magicui",
          "description": "An example of the backlight component with a image."
        },
        {
          "name": "backlight-svg-demo",
          "title": "backlight-svg-demo",
          "item_url": "https://magicui.design/r/backlight-svg-demo.json",
          "provider": "magicui",
          "description": "An example of the backlight component with SVGs."
        }
      ],
      "primary_suggestion_index": null
    },
    {
      "need_id": "need-f46a8c73b1f9fb728fcf",
      "purpose": "Let visitors explore approved work details.",
      "role_id": "assumed-component:home:featured-work:selected-work-detail",
      "guidance": "Use route entries and readable project summaries rather than a generic animated detail component.",
      "route_ids": [
        "home"
      ],
      "suggestions": [
        {
          "name": "animated-circular-progress-bar",
          "title": "Animated Circular Progress Bar",
          "item_url": "https://magicui.design/r/animated-circular-progress-bar.json",
          "provider": "magicui",
          "description": "Animated Circular Progress Bar is a component that displays a circular gauge with a percentage value."
        },
        {
          "name": "backlight-image-demo",
          "title": "backlight-image-demo",
          "item_url": "https://magicui.design/r/backlight-image-demo.json",
          "provider": "magicui",
          "description": "An example of the backlight component with a image."
        },
        {
          "name": "backlight-svg-demo",
          "title": "backlight-svg-demo",
          "item_url": "https://magicui.design/r/backlight-svg-demo.json",
          "provider": "magicui",
          "description": "An example of the backlight component with SVGs."
        }
      ],
      "primary_suggestion_index": null
    },
    {
      "need_id": "need-424ae2c2a52dc37bcb48",
      "purpose": "Let visitors explore approved work details.",
      "role_id": "assumed-component:workspace360:approach:selected-work-detail",
      "guidance": "Keep selected-work detail as structured content; none of the listed suggestions is a clear fit.",
      "route_ids": [
        "workspace360"
      ],
      "suggestions": [
        {
          "name": "animated-circular-progress-bar",
          "title": "Animated Circular Progress Bar",
          "item_url": "https://magicui.design/r/animated-circular-progress-bar.json",
          "provider": "magicui",
          "description": "Animated Circular Progress Bar is a component that displays a circular gauge with a percentage value."
        },
        {
          "name": "backlight-image-demo",
          "title": "backlight-image-demo",
          "item_url": "https://magicui.design/r/backlight-image-demo.json",
          "provider": "magicui",
          "description": "An example of the backlight component with a image."
        },
        {
          "name": "backlight-svg-demo",
          "title": "backlight-svg-demo",
          "item_url": "https://magicui.design/r/backlight-svg-demo.json",
          "provider": "magicui",
          "description": "An example of the backlight component with SVGs."
        }
      ],
      "primary_suggestion_index": null
    },
    {
      "need_id": "need-e48f569b72b8f8a3e232",
      "purpose": "Present the approved working approach as a complete sequence.",
      "role_id": "assumed-component:workspace360:approach:process-sequence",
      "guidance": "A side-oriented sequence can support complete approach content when it remains readable and collapses into ordered blocks on mobile.",
      "route_ids": [
        "workspace360"
      ],
      "suggestions": [
        {
          "name": "sidebar-14",
          "title": "sidebar-14",
          "item_url": "https://ui.shadcn.com/r/styles/new-york-v4/sidebar-14.json",
          "provider": "shadcn",
          "description": "A sidebar on the right."
        },
        {
          "name": "backlight-image-demo",
          "title": "backlight-image-demo",
          "item_url": "https://magicui.design/r/backlight-image-demo.json",
          "provider": "magicui",
          "description": "An example of the backlight component with a image."
        },
        {
          "name": "backlight-svg-demo",
          "title": "backlight-svg-demo",
          "item_url": "https://magicui.design/r/backlight-svg-demo.json",
          "provider": "magicui",
          "description": "An example of the backlight component with SVGs."
        }
      ],
      "primary_suggestion_index": 0
    },
    {
      "need_id": "need-04cb2e11cbd88d33a174",
      "purpose": "Let visitors explore approved work details.",
      "role_id": "assumed-component:workspace360:technology:selected-work-detail",
      "guidance": "Use a static technology context and approved result explanation; no listed animated detail example is necessary.",
      "route_ids": [
        "workspace360"
      ],
      "suggestions": [
        {
          "name": "animated-circular-progress-bar",
          "title": "Animated Circular Progress Bar",
          "item_url": "https://magicui.design/r/animated-circular-progress-bar.json",
          "provider": "magicui",
          "description": "Animated Circular Progress Bar is a component that displays a circular gauge with a percentage value."
        },
        {
          "name": "backlight-image-demo",
          "title": "backlight-image-demo",
          "item_url": "https://magicui.design/r/backlight-image-demo.json",
          "provider": "magicui",
          "description": "An example of the backlight component with a image."
        },
        {
          "name": "backlight-svg-demo",
          "title": "backlight-svg-demo",
          "item_url": "https://magicui.design/r/backlight-svg-demo.json",
          "provider": "magicui",
          "description": "An example of the backlight component with SVGs."
        }
      ],
      "primary_suggestion_index": null
    },
    {
      "need_id": "need-b9f7c79d6599934cd4af",
      "purpose": "Present the approved working approach as a complete sequence.",
      "role_id": "assumed-component:secureendpoint:approach:process-sequence",
      "guidance": "A side-oriented process sequence may frame the three stages, provided all labels and descriptions remain visible and the layout becomes stacked on mobile.",
      "route_ids": [
        "secureendpoint"
      ],
      "suggestions": [
        {
          "name": "sidebar-14",
          "title": "sidebar-14",
          "item_url": "https://ui.shadcn.com/r/styles/new-york-v4/sidebar-14.json",
          "provider": "shadcn",
          "description": "A sidebar on the right."
        },
        {
          "name": "backlight-image-demo",
          "title": "backlight-image-demo",
          "item_url": "https://magicui.design/r/backlight-image-demo.json",
          "provider": "magicui",
          "description": "An example of the backlight component with a image."
        },
        {
          "name": "backlight-svg-demo",
          "title": "backlight-svg-demo",
          "item_url": "https://magicui.design/r/backlight-svg-demo.json",
          "provider": "magicui",
          "description": "An example of the backlight component with SVGs."
        }
      ],
      "primary_suggestion_index": 0
    },
    {
      "need_id": "need-ffed398e056befccc34a",
      "purpose": "Present the approved working approach as a complete sequence.",
      "role_id": "assumed-component:employeeconnect:approach:process-sequence",
      "guidance": "Use the side-oriented sequence only as a presentation aid for the three stages; preserve both technical administration and adoption support in the static content.",
      "route_ids": [
        "employeeconnect"
      ],
      "suggestions": [
        {
          "name": "sidebar-14",
          "title": "sidebar-14",
          "item_url": "https://ui.shadcn.com/r/styles/new-york-v4/sidebar-14.json",
          "provider": "shadcn",
          "description": "A sidebar on the right."
        },
        {
          "name": "backlight-image-demo",
          "title": "backlight-image-demo",
          "item_url": "https://magicui.design/r/backlight-image-demo.json",
          "provider": "magicui",
          "description": "An example of the backlight component with a image."
        },
        {
          "name": "backlight-svg-demo",
          "title": "backlight-svg-demo",
          "item_url": "https://magicui.design/r/backlight-svg-demo.json",
          "provider": "magicui",
          "description": "An example of the backlight component with SVGs."
        }
      ],
      "primary_suggestion_index": 0
    }
  ],
  "target_contract": "react-vite-v1",
  "visual_input_mode": "merged_vdd_assumptions",
  "visual_brief_markdown": "# Visual & Build Brief\n\n```json build-preparation-visual-index\n{\n  \"components\": [\n    {\n      \"guidance\": \"None of the listed chart or checkbox examples genuinely represents the connected workflow. Build a lightweight custom words-first motif instead.\",\n      \"need_id\": \"need-ffaff9238945207f5816\",\n      \"primary_suggestion_index\": null,\n      \"purpose\": \"Lightweight abstract connected-workflow visual balancing the homepage hero and representing complexity becoming dependable.\",\n      \"role_id\": \"home-operating-chain\",\n      \"route_ids\": [\n        \"home\"\n      ],\n      \"suggestions\": [\n        {\n          \"description\": \"\",\n          \"item_url\": \"https://ui.shadcn.com/r/styles/new-york-v4/chart-pie-donut-text.json\",\n          \"name\": \"chart-pie-donut-text\",\n          \"provider\": \"shadcn\",\n          \"title\": \"chart-pie-donut-text\"\n        },\n        {\n          \"description\": \"\",\n          \"item_url\": \"https://ui.shadcn.com/r/styles/new-york-v4/chart-radial-text.json\",\n          \"name\": \"chart-radial-text\",\n          \"provider\": \"shadcn\",\n          \"title\": \"chart-radial-text\"\n        },\n        {\n          \"description\": \"\",\n          \"item_url\": \"https://ui.shadcn.com/r/styles/new-york-v4/checkbox-with-text.json\",\n          \"name\": \"checkbox-with-text\",\n          \"provider\": \"shadcn\",\n          \"title\": \"checkbox-with-text\"\n        }\n      ]\n    },\n    {\n      \"guidance\": \"The listed dashboard, login, and sidebar examples are not a good semantic fit. Use a custom abstract workflow treatment.\",\n      \"need_id\": \"need-8ac3b90c9d5812edd926\",\n      \"primary_suggestion_index\": null,\n      \"purpose\": \"Abstract words-first workflow motif supporting the transition from career experience to selected work.\",\n      \"role_id\": \"home-workflow-abstract\",\n      \"route_ids\": [\n        \"home\"\n      ],\n      \"suggestions\": [\n        {\n          \"description\": \"A dashboard with sidebar, charts and data table.\",\n          \"item_url\": \"https://ui.shadcn.com/r/styles/new-york-v4/dashboard-01.json\",\n          \"name\": \"dashboard-01\",\n          \"provider\": \"shadcn\",\n          \"title\": \"dashboard-01\"\n        },\n        {\n          \"description\": \"A login page with form and image.\",\n          \"item_url\": \"https://ui.shadcn.com/r/styles/new-york-v4/login-04.json\",\n          \"name\": \"login-04\",\n          \"provider\": \"shadcn\",\n          \"title\": \"login-04\"\n        },\n        {\n          \"description\": \"A left and right sidebar.\",\n          \"item_url\": \"https://ui.shadcn.com/r/styles/new-york-v4/sidebar-15.json\",\n          \"name\": \"sidebar-15\",\n          \"provider\": \"shadcn\",\n          \"title\": \"sidebar-15\"\n        }\n      ]\n    },\n    {\n      \"guidance\": \"A circular progress component could overstate the process or imply a metric. Prefer a custom ordered stage visual.\",\n      \"need_id\": \"need-009f78480992358fdee8\",\n      \"primary_suggestion_index\": null,\n      \"purpose\": \"Words-first abstract representation of the approved WorkSpace360 operating stages.\",\n      \"role_id\": \"workspace360-process-visual\",\n      \"route_ids\": [\n        \"workspace360\"\n      ],\n      \"suggestions\": [\n        {\n          \"description\": \"Animated Circular Progress Bar is a component that displays a circular gauge with a percentage value.\",\n          \"item_url\": \"https://magicui.design/r/animated-circular-progress-bar.json\",\n          \"name\": \"animated-circular-progress-bar\",\n          \"provider\": \"magicui\",\n          \"title\": \"Animated Circular Progress Bar\"\n        },\n        {\n          \"description\": \"An example of the backlight component with a image.\",\n          \"item_url\": \"https://magicui.design/r/backlight-image-demo.json\",\n          \"name\": \"backlight-image-demo\",\n          \"provider\": \"magicui\",\n          \"title\": \"backlight-image-demo\"\n        },\n        {\n          \"description\": \"An example of the backlight component with SVGs.\",\n          \"item_url\": \"https://magicui.design/r/backlight-svg-demo.json\",\n          \"name\": \"backlight-svg-demo\",\n          \"provider\": \"magicui\",\n          \"title\": \"backlight-svg-demo\"\n        }\n      ]\n    },\n    {\n      \"guidance\": \"An animated beam can support a restrained connector relationship if static labels remain complete and motion is optional; avoid making it resemble live security telemetry.\",\n      \"need_id\": \"need-15fc7788e7c478618112\",\n      \"primary_suggestion_index\": 2,\n      \"purpose\": \"Words-first representative chain connecting security controls, visibility, and remediation.\",\n      \"role_id\": \"secureendpoint-control-chain\",\n      \"route_ids\": [\n        \"secureendpoint\"\n      ],\n      \"suggestions\": [\n        {\n          \"description\": \"A dynamic text morphing component for Magic UI.\",\n          \"item_url\": \"https://magicui.design/r/morphing-text.json\",\n          \"name\": \"morphing-text\",\n          \"provider\": \"magicui\",\n          \"title\": \"Morphing Text\"\n        },\n        {\n          \"description\": \"The Spinning Text component animates text in a circular motion with customizable speed, direction, color, and transitions for dynamic and engaging effects.\",\n          \"item_url\": \"https://magicui.design/r/spinning-text.json\",\n          \"name\": \"spinning-text\",\n          \"provider\": \"magicui\",\n          \"title\": \"Spinning Text\"\n        },\n        {\n          \"description\": \"An animated beam of light which travels along a path. Useful for showcasing the integration features of a website.\",\n          \"item_url\": \"https://magicui.design/r/animated-beam.json\",\n          \"name\": \"animated-beam\",\n          \"provider\": \"magicui\",\n          \"title\": \"Animated Beam\"\n        }\n      ]\n    },\n    {\n      \"guidance\": \"The listed progress and backlight examples are not a strong migration-path fit. Prefer a custom words-first sequence.\",\n      \"need_id\": \"need-c60c81649b07900c657a\",\n      \"primary_suggestion_index\": null,\n      \"purpose\": \"Words-first abstract migration path balancing administration, adoption, and documentation.\",\n      \"role_id\": \"employeeconnect-migration-path\",\n      \"route_ids\": [\n        \"employeeconnect\"\n      ],\n      \"suggestions\": [\n        {\n          \"description\": \"Animated Circular Progress Bar is a component that displays a circular gauge with a percentage value.\",\n          \"item_url\": \"https://magicui.design/r/animated-circular-progress-bar.json\",\n          \"name\": \"animated-circular-progress-bar\",\n          \"provider\": \"magicui\",\n          \"title\": \"Animated Circular Progress Bar\"\n        },\n        {\n          \"description\": \"An example of the backlight component with a image.\",\n          \"item_url\": \"https://magicui.design/r/backlight-image-demo.json\",\n          \"name\": \"backlight-image-demo\",\n          \"provider\": \"magicui\",\n          \"title\": \"backlight-image-demo\"\n        },\n        {\n          \"description\": \"An example of the backlight component with SVGs.\",\n          \"item_url\": \"https://magicui.design/r/backlight-svg-demo.json\",\n          \"name\": \"backlight-svg-demo\",\n          \"provider\": \"magicui\",\n          \"title\": \"backlight-svg-demo\"\n        }\n      ]\n    },\n    {\n      \"guidance\": \"Use an explicit grouped disclosure pattern for capability families, with visible expanded and collapsed labels and no hover dependency.\",\n      \"need_id\": \"need-45306d9f9ef14e8b68fb\",\n      \"primary_suggestion_index\": 2,\n      \"purpose\": \"Group capability items with progressive disclosure.\",\n      \"role_id\": \"assumed-component:home:capabilities:capability-grouping\",\n      \"route_ids\": [\n        \"home\"\n      ],\n      \"suggestions\": [\n        {\n          \"description\": \"\",\n          \"item_url\": \"https://ui.shadcn.com/r/styles/new-york-v4/button-group.json\",\n          \"name\": \"button-group\",\n          \"provider\": \"shadcn\",\n          \"title\": \"button-group\"\n        },\n        {\n          \"description\": \"\",\n          \"item_url\": \"https://ui.shadcn.com/r/styles/new-york-v4/button-group-demo.json\",\n          \"name\": \"button-group-demo\",\n          \"provider\": \"shadcn\",\n          \"title\": \"button-group-demo\"\n        },\n        {\n          \"description\": \"\",\n          \"item_url\": \"https://ui.shadcn.com/r/styles/new-york-v4/button-group-dropdown.json\",\n          \"name\": \"button-group-dropdown\",\n          \"provider\": \"shadcn\",\n          \"title\": \"button-group-dropdown\"\n        }\n      ]\n    },\n    {\n      \"guidance\": \"The listed visual examples do not semantically fit a chronological timeline. Use a readable ordered progression with restrained markers.\",\n      \"need_id\": \"need-a365fadb22111a2140db\",\n      \"primary_suggestion_index\": null,\n      \"purpose\": \"Show chronological experience progression.\",\n      \"role_id\": \"assumed-component:home:experience:experience-timeline\",\n      \"route_ids\": [\n        \"home\"\n      ],\n      \"suggestions\": [\n        {\n          \"description\": \"Animated Circular Progress Bar is a component that displays a circular gauge with a percentage value.\",\n          \"item_url\": \"https://magicui.design/r/animated-circular-progress-bar.json\",\n          \"name\": \"animated-circular-progress-bar\",\n          \"provider\": \"magicui\",\n          \"title\": \"Animated Circular Progress Bar\"\n        },\n        {\n          \"description\": \"An example of the backlight component with a image.\",\n          \"item_url\": \"https://magicui.design/r/backlight-image-demo.json\",\n          \"name\": \"backlight-image-demo\",\n          \"provider\": \"magicui\",\n          \"title\": \"backlight-image-demo\"\n        },\n        {\n          \"description\": \"An example of the backlight component with SVGs.\",\n          \"item_url\": \"https://magicui.design/r/backlight-svg-demo.json\",\n          \"name\": \"backlight-svg-demo\",\n          \"provider\": \"magicui\",\n          \"title\": \"backlight-svg-demo\"\n        }\n      ]\n    },\n    {\n      \"guidance\": \"Use route entries and readable project summaries rather than a generic animated detail component.\",\n      \"need_id\": \"need-f46a8c73b1f9fb728fcf\",\n      \"primary_suggestion_index\": null,\n      \"purpose\": \"Let visitors explore approved work details.\",\n      \"role_id\": \"assumed-component:home:featured-work:selected-work-detail\",\n      \"route_ids\": [\n        \"home\"\n      ],\n      \"suggestions\": [\n        {\n          \"description\": \"Animated Circular Progress Bar is a component that displays a circular gauge with a percentage value.\",\n          \"item_url\": \"https://magicui.design/r/animated-circular-progress-bar.json\",\n          \"name\": \"animated-circular-progress-bar\",\n          \"provider\": \"magicui\",\n          \"title\": \"Animated Circular Progress Bar\"\n        },\n        {\n          \"description\": \"An example of the backlight component with a image.\",\n          \"item_url\": \"https://magicui.design/r/backlight-image-demo.json\",\n          \"name\": \"backlight-image-demo\",\n          \"provider\": \"magicui\",\n          \"title\": \"backlight-image-demo\"\n        },\n        {\n          \"description\": \"An example of the backlight component with SVGs.\",\n          \"item_url\": \"https://magicui.design/r/backlight-svg-demo.json\",\n          \"name\": \"backlight-svg-demo\",\n          \"provider\": \"magicui\",\n          \"title\": \"backlight-svg-demo\"\n        }\n      ]\n    },\n    {\n      \"guidance\": \"Keep selected-work detail as structured content; none of the listed suggestions is a clear fit.\",\n      \"need_id\": \"need-424ae2c2a52dc37bcb48\",\n      \"primary_suggestion_index\": null,\n      \"purpose\": \"Let visitors explore approved work details.\",\n      \"role_id\": \"assumed-component:workspace360:approach:selected-work-detail\",\n      \"route_ids\": [\n        \"workspace360\"\n      ],\n      \"suggestions\": [\n        {\n          \"description\": \"Animated Circular Progress Bar is a component that displays a circular gauge with a percentage value.\",\n          \"item_url\": \"https://magicui.design/r/animated-circular-progress-bar.json\",\n          \"name\": \"animated-circular-progress-bar\",\n          \"provider\": \"magicui\",\n          \"title\": \"Animated Circular Progress Bar\"\n        },\n        {\n          \"description\": \"An example of the backlight component with a image.\",\n          \"item_url\": \"https://magicui.design/r/backlight-image-demo.json\",\n          \"name\": \"backlight-image-demo\",\n          \"provider\": \"magicui\",\n          \"title\": \"backlight-image-demo\"\n        },\n        {\n          \"description\": \"An example of the backlight component with SVGs.\",\n          \"item_url\": \"https://magicui.design/r/backlight-svg-demo.json\",\n          \"name\": \"backlight-svg-demo\",\n          \"provider\": \"magicui\",\n          \"title\": \"backlight-svg-demo\"\n        }\n      ]\n    },\n    {\n      \"guidance\": \"A side-oriented sequence can support complete approach content when it remains readable and collapses into ordered blocks on mobile.\",\n      \"need_id\": \"need-e48f569b72b8f8a3e232\",\n      \"primary_suggestion_index\": 0,\n      \"purpose\": \"Present the approved working approach as a complete sequence.\",\n      \"role_id\": \"assumed-component:workspace360:approach:process-sequence\",\n      \"route_ids\": [\n        \"workspace360\"\n      ],\n      \"suggestions\": [\n        {\n          \"description\": \"A sidebar on the right.\",\n          \"item_url\": \"https://ui.shadcn.com/r/styles/new-york-v4/sidebar-14.json\",\n          \"name\": \"sidebar-14\",\n          \"provider\": \"shadcn\",\n          \"title\": \"sidebar-14\"\n        },\n        {\n          \"description\": \"An example of the backlight component with a image.\",\n          \"item_url\": \"https://magicui.design/r/backlight-image-demo.json\",\n          \"name\": \"backlight-image-demo\",\n          \"provider\": \"magicui\",\n          \"title\": \"backlight-image-demo\"\n        },\n        {\n          \"description\": \"An example of the backlight component with SVGs.\",\n          \"item_url\": \"https://magicui.design/r/backlight-svg-demo.json\",\n          \"name\": \"backlight-svg-demo\",\n          \"provider\": \"magicui\",\n          \"title\": \"backlight-svg-demo\"\n        }\n      ]\n    },\n    {\n      \"guidance\": \"Use a static technology context and approved result explanation; no listed animated detail example is necessary.\",\n      \"need_id\": \"need-04cb2e11cbd88d33a174\",\n      \"primary_suggestion_index\": null,\n      \"purpose\": \"Let visitors explore approved work details.\",\n      \"role_id\": \"assumed-component:workspace360:technology:selected-work-detail\",\n      \"route_ids\": [\n        \"workspace360\"\n      ],\n      \"suggestions\": [\n        {\n          \"description\": \"Animated Circular Progress Bar is a component that displays a circular gauge with a percentage value.\",\n          \"item_url\": \"https://magicui.design/r/animated-circular-progress-bar.json\",\n          \"name\": \"animated-circular-progress-bar\",\n          \"provider\": \"magicui\",\n          \"title\": \"Animated Circular Progress Bar\"\n        },\n        {\n          \"description\": \"An example of the backlight component with a image.\",\n          \"item_url\": \"https://magicui.design/r/backlight-image-demo.json\",\n          \"name\": \"backlight-image-demo\",\n          \"provider\": \"magicui\",\n          \"title\": \"backlight-image-demo\"\n        },\n        {\n          \"description\": \"An example of the backlight component with SVGs.\",\n          \"item_url\": \"https://magicui.design/r/backlight-svg-demo.json\",\n          \"name\": \"backlight-svg-demo\",\n          \"provider\": \"magicui\",\n          \"title\": \"backlight-svg-demo\"\n        }\n      ]\n    },\n    {\n      \"guidance\": \"A side-oriented process sequence may frame the three stages, provided all labels and descriptions remain visible and the layout becomes stacked on mobile.\",\n      \"need_id\": \"need-b9f7c79d6599934cd4af\",\n      \"primary_suggestion_index\": 0,\n      \"purpose\": \"Present the approved working approach as a complete sequence.\",\n      \"role_id\": \"assumed-component:secureendpoint:approach:process-sequence\",\n      \"route_ids\": [\n        \"secureendpoint\"\n      ],\n      \"suggestions\": [\n        {\n          \"description\": \"A sidebar on the right.\",\n          \"item_url\": \"https://ui.shadcn.com/r/styles/new-york-v4/sidebar-14.json\",\n          \"name\": \"sidebar-14\",\n          \"provider\": \"shadcn\",\n          \"title\": \"sidebar-14\"\n        },\n        {\n          \"description\": \"An example of the backlight component with a image.\",\n          \"item_url\": \"https://magicui.design/r/backlight-image-demo.json\",\n          \"name\": \"backlight-image-demo\",\n          \"provider\": \"magicui\",\n          \"title\": \"backlight-image-demo\"\n        },\n        {\n          \"description\": \"An example of the backlight component with SVGs.\",\n          \"item_url\": \"https://magicui.design/r/backlight-svg-demo.json\",\n          \"name\": \"backlight-svg-demo\",\n          \"provider\": \"magicui\",\n          \"title\": \"backlight-svg-demo\"\n        }\n      ]\n    },\n    {\n      \"guidance\": \"Use the side-oriented sequence only as a presentation aid for the three stages; preserve both technical administration and adoption support in the static content.\",\n      \"need_id\": \"need-ffed398e056befccc34a\",\n      \"primary_suggestion_index\": 0,\n      \"purpose\": \"Present the approved working approach as a complete sequence.\",\n      \"role_id\": \"assumed-component:employeeconnect:approach:process-sequence\",\n      \"route_ids\": [\n        \"employeeconnect\"\n      ],\n      \"suggestions\": [\n        {\n          \"description\": \"A sidebar on the right.\",\n          \"item_url\": \"https://ui.shadcn.com/r/styles/new-york-v4/sidebar-14.json\",\n          \"name\": \"sidebar-14\",\n          \"provider\": \"shadcn\",\n          \"title\": \"sidebar-14\"\n        },\n        {\n          \"description\": \"An example of the backlight component with a image.\",\n          \"item_url\": \"https://magicui.design/r/backlight-image-demo.json\",\n          \"name\": \"backlight-image-demo\",\n          \"provider\": \"magicui\",\n          \"title\": \"backlight-image-demo\"\n        },\n        {\n          \"description\": \"An example of the backlight component with SVGs.\",\n          \"item_url\": \"https://magicui.design/r/backlight-svg-demo.json\",\n          \"name\": \"backlight-svg-demo\",\n          \"provider\": \"magicui\",\n          \"title\": \"backlight-svg-demo\"\n        }\n      ]\n    }\n  ],\n  \"kind\": \"visual_index\",\n  \"recommended_dependencies\": [],\n  \"resources\": [\n    {\n      \"candidates\": [\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"cocoandwifi\",\n          \"height\": 4480,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2020/04/02/22/05/home-office-4996834_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"4996834\",\n          \"title\": \"home office, person, work, web design, business, workplace, monitor, computer, keyboard, screen, laptop, office work, independent, freelancer, success, graphic designer, designer, digital, nomad\",\n          \"url\": \"https://pixabay.com/get/g16a58532f1aa5dee22ec8cab417aca0dc897c444b1c72e282969bd5fd0f43a602d7cc66b9aed4c44a1fea1afabcee0f27de34e17c86383c3cc89ab40fc50cf56_1280.jpg\",\n          \"width\": 6720\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"ottawagraphics\",\n          \"height\": 3687,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2019/11/12/23/00/artist-4622221_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"4622221\",\n          \"title\": \"artist, studio, art, sculpture, workshop, old man, tools, sculptor, creation, exhibit, working, professional, artwork\",\n          \"url\": \"https://pixabay.com/get/gffa96fca37cfe2ffb33571bdf8aa5767c87f8fa0fc76f25f759fc72501fd571af30489421d5efad823f1d1127aa547b3fe015f335f7803c00121326f675ba4a5_1280.jpg\",\n          \"width\": 5524\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"reallywellmadedesks\",\n          \"height\": 4480,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2022/01/20/17/51/office-desk-6952919_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"6952919\",\n          \"title\": \"office desk, man, business, workplace, workspace, desktop\",\n          \"url\": \"https://pixabay.com/get/g268c1af865bcda8474e70454be6031c1f7da75943fe6afbec4fc831e0ecf123341ed9c8524fdaca10072233be8ec683dedaa5cd4f4c395a9e163901870471706_1280.jpg\",\n          \"width\": 6720\n        }\n      ],\n      \"category\": \"editorial_photo\",\n      \"guidance\": \"No editorial photo is necessary for the hero; prefer the approved text-led composition and abstract static motif. If decoration is retained, keep it non-identifying and clearly non-evidentiary.\",\n      \"need_id\": \"need-6c7010157537a7aa0002\",\n      \"primary_candidate_index\": null,\n      \"purpose\": \"Editorial opening atmosphere for the approved professional practice; no person or product interface.\",\n      \"role_id\": \"assumed-image:home:hero:0\",\n      \"route_ids\": [\n        \"home\"\n      ],\n      \"status\": \"candidates_found\"\n    },\n    {\n      \"candidates\": [\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"bodobe\",\n          \"height\": 2592,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2015/08/28/11/37/painting-911804_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"911804\",\n          \"title\": \"painting, pencils, paint, pens, watercolor, acrylic, watercolor painting, art tools, art materials\",\n          \"url\": \"https://pixabay.com/get/g940d2972d6eeb18033f42f74ab4e53a2e99910e9401c7900fca46cada55f5f4ebcad0dd4cfdca0bde046307aed2a228d3ef805212a209c379c7dca6cb7ff51d5_1280.jpg\",\n          \"width\": 4608\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"Van3ssa_\",\n          \"height\": 4000,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2020/06/01/19/52/embroidery-thread-5248183_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"5248183\",\n          \"title\": \"embroidery thread, colorful yarn, crochet, knitting, craft supplies, handmade, needlework, textile art, vibrant colors, yarn balls, sewing, embroidery, thread spools, hobby, diy crafts, home crafts, textile threads, fiber arts, colorful threads, yarn closeup, craft materials, wool, cotton thread, multicolor yarn, creative tools\",\n          \"url\": \"https://pixabay.com/get/gacde75deee8a7ced96a91cd314c468bf9789c44d9d9c862a53a8822d06e0ff911dc7ee36ba08aca6f69201ba90d2d978906527b0e58f3adbdd73e824a8f5363e_1280.jpg\",\n          \"width\": 6000\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"fietzfotos\",\n          \"height\": 3064,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2017/11/07/18/40/brushes-2927793_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"2927793\",\n          \"title\": \"brushes, chalks, colorful, art materials, art supplies, coloring materials, paint, pens, art, artistic, creative\",\n          \"url\": \"https://pixabay.com/get/gac80168a474783d4df0a81734d6eabdccb14d6001a58c860c65f5b1ecd1150c7cb4b0647213297bab56fef7e2e356b1acd7acb62febea3e8e8e224046f082445_1280.jpg\",\n          \"width\": 4592\n        }\n      ],\n      \"category\": \"editorial_photo\",\n      \"guidance\": \"Prefer grouped capability text and tonal surfaces over decorative craft imagery; any image must remain subordinate and non-evidentiary.\",\n      \"need_id\": \"need-9b3860cb6dd5f936882d\",\n      \"primary_candidate_index\": null,\n      \"purpose\": \"Decorative modular atmosphere for approved capability groups; not evidence or a real interface.\",\n      \"role_id\": \"assumed-image:home:capabilities:1\",\n      \"route_ids\": [\n        \"home\"\n      ],\n      \"status\": \"candidates_found\"\n    },\n    {\n      \"candidates\": [\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"rawpixel\",\n          \"height\": 4004,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2017/07/28/09/35/agreement-2548138_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"2548138\",\n          \"title\": \"agreement, brainstorming, coffee, business, cafe, coffee shop, collaboration, corporate, deal, laptop, man, meeting, men, mobile phone, networking, online, planning, table, talking, togetherness, woman, working\",\n          \"url\": \"https://pixabay.com/get/gfde84b274b6ef0426f9580c47691f734d0d0e6df487158af39aeebed929dff5c7a4b2c6c501c17563da8e73885f57d548fee84afe6f31365adb5d8bf30d621f1_1280.jpg\",\n          \"width\": 6000\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"StartupStockPhotos\",\n          \"height\": 3648,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2015/01/08/18/27/startup-593341_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"593341\",\n          \"title\": \"startup, start-up, people, silicon valley, teamwork, business, team, office, group, meeting, corporate, conference, company, men, partnership, table, technology, casual, successful, seminar, colleagues, working, planning, network, strategy, cooperation, professional, notes, notepad, writing, laptop, computer, drinks\",\n          \"url\": \"https://pixabay.com/get/g46d8d83de447bddb5b677daa1386f3cca365ffb614ae37b3324cf2f9b4c203abd89ca17ab2f7b3c0ea6ae30e3b737c0725d52f9633419a34d36d5b278d4399e0_1280.jpg\",\n          \"width\": 5472\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"uh_yeah_20101995\",\n          \"height\": 3370,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2019/11/29/08/34/space-4660847_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"4660847\",\n          \"title\": \"space, interior, design, architecture, wall, frame, meeting, furniture, old, floor, vintage, retro, window\",\n          \"url\": \"https://pixabay.com/get/g785dbe04e6eae2bc9d135b2a3b72ecb647ab15da474dde291b02b20091d1dbee979166567e2c5f88a0bd345c8756bf1c0edd5ad3e6534b3a4b506b4463b5157d_1280.jpg\",\n          \"width\": 4493\n        }\n      ],\n      \"category\": \"editorial_photo\",\n      \"guidance\": \"Use the experience progression as structured text. Omit editorial collaboration imagery unless it is unmistakably decorative and does not imply a specific event or person.\",\n      \"need_id\": \"need-62fd6ffaa64f9ab35457\",\n      \"primary_candidate_index\": null,\n      \"purpose\": \"Editorial collaboration atmosphere supporting an approved experience timeline.\",\n      \"role_id\": \"assumed-image:home:experience:2\",\n      \"route_ids\": [\n        \"home\"\n      ],\n      \"status\": \"candidates_found\"\n    },\n    {\n      \"candidates\": [\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"11153496\",\n          \"height\": 3335,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2020/07/24/09/55/silk-5433442_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"5433442\",\n          \"title\": \"silk, yellow, woman, process, work, hand made\",\n          \"url\": \"https://pixabay.com/get/g36848d6628c9611faaddd821c53a0e3e2e68eb2403d055345acfec29c78c19c0f1de1a3d92293315094af4560d4cbf267157aa8cd551b91dae2b1f939a9cb273_1280.jpg\",\n          \"width\": 5003\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"Pexels\",\n          \"height\": 2730,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2016/11/18/17/14/cloth-1835894_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"1835894\",\n          \"title\": \"cloth, fabrics, fashion design, work, mockup, chaos, tailor, crafts, wallpaper for girls\",\n          \"url\": \"https://pixabay.com/get/g68fcd10c8a4fb30ca8cf94f2dd48901a10cac777d3d2aa5a2d1c54e976680ab5b78d36c700d388a23abc3324c31842ef099adf0a21c3b4319f1f0eb38ecba32e_1280.jpg\",\n          \"width\": 4096\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"652234\",\n          \"height\": 3072,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2017/11/26/19/50/jeans-2979818_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"2979818\",\n          \"title\": \"jeans, trousers, trouser buttons, clothing, blue jeans, blue, fashion, detail shot, textiles, seam, washed out, close up, buttons, style, material, natural substance, denim, work pants\",\n          \"url\": \"https://pixabay.com/get/g1226707b68c39c97a88c22707ec40b7757639b961db810e97c0bd50177ea2f6a43112f1b2ef24d310e86ec9bf8a9e5ba75101163cca8abac71c5a60d4782449e_1280.jpg\",\n          \"width\": 4608\n        }\n      ],\n      \"category\": \"editorial_photo\",\n      \"guidance\": \"Selected work should be represented with route labels and abstract treatment, not craft photography that could be mistaken for project evidence.\",\n      \"need_id\": \"need-5b00cc1f3f31408ac825\",\n      \"primary_candidate_index\": null,\n      \"purpose\": \"Decorative craft-and-process atmosphere for selected work; no dashboard or screenshot.\",\n      \"role_id\": \"assumed-image:home:featured-work:3\",\n      \"route_ids\": [\n        \"home\"\n      ],\n      \"status\": \"candidates_found\"\n    },\n    {\n      \"candidates\": [\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"11153496\",\n          \"height\": 3335,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2020/07/24/09/55/silk-5433442_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"5433442\",\n          \"title\": \"silk, yellow, woman, process, work, hand made\",\n          \"url\": \"https://pixabay.com/get/g36848d6628c9611faaddd821c53a0e3e2e68eb2403d055345acfec29c78c19c0f1de1a3d92293315094af4560d4cbf267157aa8cd551b91dae2b1f939a9cb273_1280.jpg\",\n          \"width\": 5003\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"Pexels\",\n          \"height\": 2730,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2016/11/18/17/14/cloth-1835894_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"1835894\",\n          \"title\": \"cloth, fabrics, fashion design, work, mockup, chaos, tailor, crafts, wallpaper for girls\",\n          \"url\": \"https://pixabay.com/get/g68fcd10c8a4fb30ca8cf94f2dd48901a10cac777d3d2aa5a2d1c54e976680ab5b78d36c700d388a23abc3324c31842ef099adf0a21c3b4319f1f0eb38ecba32e_1280.jpg\",\n          \"width\": 4096\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"652234\",\n          \"height\": 3072,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2017/11/26/19/50/jeans-2979818_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"2979818\",\n          \"title\": \"jeans, trousers, trouser buttons, clothing, blue jeans, blue, fashion, detail shot, textiles, seam, washed out, close up, buttons, style, material, natural substance, denim, work pants\",\n          \"url\": \"https://pixabay.com/get/g1226707b68c39c97a88c22707ec40b7757639b961db810e97c0bd50177ea2f6a43112f1b2ef24d310e86ec9bf8a9e5ba75101163cca8abac71c5a60d4782449e_1280.jpg\",\n          \"width\": 4608\n        }\n      ],\n      \"category\": \"editorial_photo\",\n      \"guidance\": \"Keep proof values as labelled text and static comparisons; omit decorative imagery if it competes with evidence.\",\n      \"need_id\": \"need-9b29f305c2aecd039e14\",\n      \"primary_candidate_index\": null,\n      \"purpose\": \"Decorative craft-and-process atmosphere for selected work; no dashboard or screenshot.\",\n      \"role_id\": \"assumed-image:home:proof-points:4\",\n      \"route_ids\": [\n        \"home\"\n      ],\n      \"status\": \"candidates_found\"\n    },\n    {\n      \"candidates\": [\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"11153496\",\n          \"height\": 3335,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2020/07/24/09/55/silk-5433442_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"5433442\",\n          \"title\": \"silk, yellow, woman, process, work, hand made\",\n          \"url\": \"https://pixabay.com/get/g36848d6628c9611faaddd821c53a0e3e2e68eb2403d055345acfec29c78c19c0f1de1a3d92293315094af4560d4cbf267157aa8cd551b91dae2b1f939a9cb273_1280.jpg\",\n          \"width\": 5003\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"Pexels\",\n          \"height\": 2730,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2016/11/18/17/14/cloth-1835894_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"1835894\",\n          \"title\": \"cloth, fabrics, fashion design, work, mockup, chaos, tailor, crafts, wallpaper for girls\",\n          \"url\": \"https://pixabay.com/get/g68fcd10c8a4fb30ca8cf94f2dd48901a10cac777d3d2aa5a2d1c54e976680ab5b78d36c700d388a23abc3324c31842ef099adf0a21c3b4319f1f0eb38ecba32e_1280.jpg\",\n          \"width\": 4096\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"652234\",\n          \"height\": 3072,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2017/11/26/19/50/jeans-2979818_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"2979818\",\n          \"title\": \"jeans, trousers, trouser buttons, clothing, blue jeans, blue, fashion, detail shot, textiles, seam, washed out, close up, buttons, style, material, natural substance, denim, work pants\",\n          \"url\": \"https://pixabay.com/get/g1226707b68c39c97a88c22707ec40b7757639b961db810e97c0bd50177ea2f6a43112f1b2ef24d310e86ec9bf8a9e5ba75101163cca8abac71c5a60d4782449e_1280.jpg\",\n          \"width\": 4608\n        }\n      ],\n      \"category\": \"editorial_photo\",\n      \"guidance\": \"Do not use this decorative candidate to depict the WorkSpace360 approach. Prefer the words-first process visual.\",\n      \"need_id\": \"need-1245adde715aa2c70864\",\n      \"primary_candidate_index\": null,\n      \"purpose\": \"Decorative craft-and-process atmosphere for selected work; no dashboard or screenshot.\",\n      \"role_id\": \"assumed-image:workspace360:approach:5\",\n      \"route_ids\": [\n        \"workspace360\"\n      ],\n      \"status\": \"candidates_found\"\n    },\n    {\n      \"candidates\": [\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"11153496\",\n          \"height\": 3335,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2020/07/24/09/55/silk-5433442_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"5433442\",\n          \"title\": \"silk, yellow, woman, process, work, hand made\",\n          \"url\": \"https://pixabay.com/get/g36848d6628c9611faaddd821c53a0e3e2e68eb2403d055345acfec29c78c19c0f1de1a3d92293315094af4560d4cbf267157aa8cd551b91dae2b1f939a9cb273_1280.jpg\",\n          \"width\": 5003\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"Pexels\",\n          \"height\": 2730,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2016/11/18/17/14/cloth-1835894_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"1835894\",\n          \"title\": \"cloth, fabrics, fashion design, work, mockup, chaos, tailor, crafts, wallpaper for girls\",\n          \"url\": \"https://pixabay.com/get/g68fcd10c8a4fb30ca8cf94f2dd48901a10cac777d3d2aa5a2d1c54e976680ab5b78d36c700d388a23abc3324c31842ef099adf0a21c3b4319f1f0eb38ecba32e_1280.jpg\",\n          \"width\": 4096\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"652234\",\n          \"height\": 3072,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2017/11/26/19/50/jeans-2979818_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"2979818\",\n          \"title\": \"jeans, trousers, trouser buttons, clothing, blue jeans, blue, fashion, detail shot, textiles, seam, washed out, close up, buttons, style, material, natural substance, denim, work pants\",\n          \"url\": \"https://pixabay.com/get/g1226707b68c39c97a88c22707ec40b7757639b961db810e97c0bd50177ea2f6a43112f1b2ef24d310e86ec9bf8a9e5ba75101163cca8abac71c5a60d4782449e_1280.jpg\",\n          \"width\": 4608\n        }\n      ],\n      \"category\": \"editorial_photo\",\n      \"guidance\": \"Keep the challenge scene abstract and textual; omit decorative craft imagery.\",\n      \"need_id\": \"need-ce4959e396c7d4459465\",\n      \"primary_candidate_index\": null,\n      \"purpose\": \"Decorative craft-and-process atmosphere for selected work; no dashboard or screenshot.\",\n      \"role_id\": \"assumed-image:workspace360:challenge:6\",\n      \"route_ids\": [\n        \"workspace360\"\n      ],\n      \"status\": \"candidates_found\"\n    },\n    {\n      \"candidates\": [\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"11153496\",\n          \"height\": 3335,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2020/07/24/09/55/silk-5433442_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"5433442\",\n          \"title\": \"silk, yellow, woman, process, work, hand made\",\n          \"url\": \"https://pixabay.com/get/g36848d6628c9611faaddd821c53a0e3e2e68eb2403d055345acfec29c78c19c0f1de1a3d92293315094af4560d4cbf267157aa8cd551b91dae2b1f939a9cb273_1280.jpg\",\n          \"width\": 5003\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"Pexels\",\n          \"height\": 2730,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2016/11/18/17/14/cloth-1835894_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"1835894\",\n          \"title\": \"cloth, fabrics, fashion design, work, mockup, chaos, tailor, crafts, wallpaper for girls\",\n          \"url\": \"https://pixabay.com/get/g68fcd10c8a4fb30ca8cf94f2dd48901a10cac777d3d2aa5a2d1c54e976680ab5b78d36c700d388a23abc3324c31842ef099adf0a21c3b4319f1f0eb38ecba32e_1280.jpg\",\n          \"width\": 4096\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"652234\",\n          \"height\": 3072,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2017/11/26/19/50/jeans-2979818_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"2979818\",\n          \"title\": \"jeans, trousers, trouser buttons, clothing, blue jeans, blue, fashion, detail shot, textiles, seam, washed out, close up, buttons, style, material, natural substance, denim, work pants\",\n          \"url\": \"https://pixabay.com/get/g1226707b68c39c97a88c22707ec40b7757639b961db810e97c0bd50177ea2f6a43112f1b2ef24d310e86ec9bf8a9e5ba75101163cca8abac71c5a60d4782449e_1280.jpg\",\n          \"width\": 4608\n        }\n      ],\n      \"category\": \"editorial_photo\",\n      \"guidance\": \"The result needs a clear static comparison, not decorative photography.\",\n      \"need_id\": \"need-37b42d749a51d7474de4\",\n      \"primary_candidate_index\": null,\n      \"purpose\": \"Decorative craft-and-process atmosphere for selected work; no dashboard or screenshot.\",\n      \"role_id\": \"assumed-image:workspace360:outcome:7\",\n      \"route_ids\": [\n        \"workspace360\"\n      ],\n      \"status\": \"candidates_found\"\n    },\n    {\n      \"candidates\": [\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"11153496\",\n          \"height\": 3335,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2020/07/24/09/55/silk-5433442_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"5433442\",\n          \"title\": \"silk, yellow, woman, process, work, hand made\",\n          \"url\": \"https://pixabay.com/get/g36848d6628c9611faaddd821c53a0e3e2e68eb2403d055345acfec29c78c19c0f1de1a3d92293315094af4560d4cbf267157aa8cd551b91dae2b1f939a9cb273_1280.jpg\",\n          \"width\": 5003\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"Pexels\",\n          \"height\": 2730,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2016/11/18/17/14/cloth-1835894_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"1835894\",\n          \"title\": \"cloth, fabrics, fashion design, work, mockup, chaos, tailor, crafts, wallpaper for girls\",\n          \"url\": \"https://pixabay.com/get/g68fcd10c8a4fb30ca8cf94f2dd48901a10cac777d3d2aa5a2d1c54e976680ab5b78d36c700d388a23abc3324c31842ef099adf0a21c3b4319f1f0eb38ecba32e_1280.jpg\",\n          \"width\": 4096\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"652234\",\n          \"height\": 3072,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2017/11/26/19/50/jeans-2979818_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"2979818\",\n          \"title\": \"jeans, trousers, trouser buttons, clothing, blue jeans, blue, fashion, detail shot, textiles, seam, washed out, close up, buttons, style, material, natural substance, denim, work pants\",\n          \"url\": \"https://pixabay.com/get/g1226707b68c39c97a88c22707ec40b7757639b961db810e97c0bd50177ea2f6a43112f1b2ef24d310e86ec9bf8a9e5ba75101163cca8abac71c5a60d4782449e_1280.jpg\",\n          \"width\": 4608\n        }\n      ],\n      \"category\": \"editorial_photo\",\n      \"guidance\": \"Use the overview copy and abstract workflow treatment; omit unrelated editorial imagery.\",\n      \"need_id\": \"need-347d4e372dd15c465512\",\n      \"primary_candidate_index\": null,\n      \"purpose\": \"Decorative craft-and-process atmosphere for selected work; no dashboard or screenshot.\",\n      \"role_id\": \"assumed-image:workspace360:overview:8\",\n      \"route_ids\": [\n        \"workspace360\"\n      ],\n      \"status\": \"candidates_found\"\n    },\n    {\n      \"candidates\": [\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"11153496\",\n          \"height\": 3335,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2020/07/24/09/55/silk-5433442_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"5433442\",\n          \"title\": \"silk, yellow, woman, process, work, hand made\",\n          \"url\": \"https://pixabay.com/get/g36848d6628c9611faaddd821c53a0e3e2e68eb2403d055345acfec29c78c19c0f1de1a3d92293315094af4560d4cbf267157aa8cd551b91dae2b1f939a9cb273_1280.jpg\",\n          \"width\": 5003\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"Pexels\",\n          \"height\": 2730,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2016/11/18/17/14/cloth-1835894_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"1835894\",\n          \"title\": \"cloth, fabrics, fashion design, work, mockup, chaos, tailor, crafts, wallpaper for girls\",\n          \"url\": \"https://pixabay.com/get/g68fcd10c8a4fb30ca8cf94f2dd48901a10cac777d3d2aa5a2d1c54e976680ab5b78d36c700d388a23abc3324c31842ef099adf0a21c3b4319f1f0eb38ecba32e_1280.jpg\",\n          \"width\": 4096\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"652234\",\n          \"height\": 3072,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2017/11/26/19/50/jeans-2979818_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"2979818\",\n          \"title\": \"jeans, trousers, trouser buttons, clothing, blue jeans, blue, fashion, detail shot, textiles, seam, washed out, close up, buttons, style, material, natural substance, denim, work pants\",\n          \"url\": \"https://pixabay.com/get/g1226707b68c39c97a88c22707ec40b7757639b961db810e97c0bd50177ea2f6a43112f1b2ef24d310e86ec9bf8a9e5ba75101163cca8abac71c5a60d4782449e_1280.jpg\",\n          \"width\": 4608\n        }\n      ],\n      \"category\": \"editorial_photo\",\n      \"guidance\": \"Keep technology context compact and text-led; no decorative image is needed.\",\n      \"need_id\": \"need-0153c0bebc4e182c61e3\",\n      \"primary_candidate_index\": null,\n      \"purpose\": \"Decorative craft-and-process atmosphere for selected work; no dashboard or screenshot.\",\n      \"role_id\": \"assumed-image:workspace360:technology:9\",\n      \"route_ids\": [\n        \"workspace360\"\n      ],\n      \"status\": \"candidates_found\"\n    },\n    {\n      \"candidates\": [\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"geralt\",\n          \"height\": 4000,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2019/03/14/08/21/kanban-4054380_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"4054380\",\n          \"title\": \"kanban, work, team, work process, to organize, business, office, structure, organization, workflow, development, planning, management, success, company\",\n          \"url\": \"https://pixabay.com/get/gb8bb7ce988ee6f470fa14614a945fd4c52f4eea180ed289d18fbc89862c51b93a31e68b6263a270c206209181949c5da8d409f1604839896a107007d7ad5264f_1280.jpg\",\n          \"width\": 6000\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"geralt\",\n          \"height\": 2413,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2019/03/14/08/21/whiteboard-4054377_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"4054377\",\n          \"title\": \"whiteboard, kanban, work, work process, to organize, structure, workflow, development, business, planning, management, success, company\",\n          \"url\": \"https://pixabay.com/get/g8fff350c5f2720ed4803cd5cc805f360307db8d575b95ee0ceb0e44292146f06c33e2d4083c6c12a42322ab374366224101fd0d6bbff6f355b043de604481922_1280.jpg\",\n          \"width\": 3704\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"geralt\",\n          \"height\": 2578,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2019/03/12/20/27/work-4051777_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"4051777\",\n          \"title\": \"work, work process, to organize, business, office, team, structure, organization, workflow, development, planning, management, success, company\",\n          \"url\": \"https://pixabay.com/get/gddb15110b5a71c5ec5f2d7d785c3f2872ab401b08db1cdc09e269b50567c2d0f73abc533f6bcdaa20191bdb9e109c76b6472643fe0027349558e6a1f6e3621ee_1280.jpg\",\n          \"width\": 4200\n        }\n      ],\n      \"category\": \"editorial_photo\",\n      \"guidance\": \"Prefer the custom migration sequence. Any process photo would be decorative only and should not imply project evidence.\",\n      \"need_id\": \"need-ce945df3392dd866ff08\",\n      \"primary_candidate_index\": null,\n      \"purpose\": \"Editorial process atmosphere for the approved working approach; no invented project evidence.\",\n      \"role_id\": \"assumed-image:employeeconnect:approach:10\",\n      \"route_ids\": [\n        \"employeeconnect\"\n      ],\n      \"status\": \"candidates_found\"\n    },\n    {\n      \"candidates\": [\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"geralt\",\n          \"height\": 4000,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2019/03/14/08/21/kanban-4054380_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"4054380\",\n          \"title\": \"kanban, work, team, work process, to organize, business, office, structure, organization, workflow, development, planning, management, success, company\",\n          \"url\": \"https://pixabay.com/get/gb8bb7ce988ee6f470fa14614a945fd4c52f4eea180ed289d18fbc89862c51b93a31e68b6263a270c206209181949c5da8d409f1604839896a107007d7ad5264f_1280.jpg\",\n          \"width\": 6000\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"geralt\",\n          \"height\": 2413,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2019/03/14/08/21/whiteboard-4054377_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"4054377\",\n          \"title\": \"whiteboard, kanban, work, work process, to organize, structure, workflow, development, business, planning, management, success, company\",\n          \"url\": \"https://pixabay.com/get/g8fff350c5f2720ed4803cd5cc805f360307db8d575b95ee0ceb0e44292146f06c33e2d4083c6c12a42322ab374366224101fd0d6bbff6f355b043de604481922_1280.jpg\",\n          \"width\": 3704\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"geralt\",\n          \"height\": 2578,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2019/03/12/20/27/work-4051777_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"4051777\",\n          \"title\": \"work, work process, to organize, business, office, team, structure, organization, workflow, development, planning, management, success, company\",\n          \"url\": \"https://pixabay.com/get/gddb15110b5a71c5ec5f2d7d785c3f2872ab401b08db1cdc09e269b50567c2d0f73abc533f6bcdaa20191bdb9e109c76b6472643fe0027349558e6a1f6e3621ee_1280.jpg\",\n          \"width\": 4200\n        }\n      ],\n      \"category\": \"editorial_photo\",\n      \"guidance\": \"Use the abstract control chain and supplied approach text rather than unrelated process photography.\",\n      \"need_id\": \"need-e0ce25ddcdf2ad5b70fa\",\n      \"primary_candidate_index\": null,\n      \"purpose\": \"Editorial process atmosphere for the approved working approach; no invented project evidence.\",\n      \"role_id\": \"assumed-image:secureendpoint:approach:11\",\n      \"route_ids\": [\n        \"secureendpoint\"\n      ],\n      \"status\": \"candidates_found\"\n    },\n    {\n      \"candidates\": [\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"ua_Bob_Dmyt_ua\",\n          \"height\": 3744,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2019/10/06/10/03/team-4529717_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"4529717\",\n          \"title\": \"team, friendship, group, hands, cooperation, people, community, connection, relationship, friendship day\",\n          \"url\": \"https://pixabay.com/get/g898505a95163175cf602fd5f2ed3e1ae81575060084751e3a6cecc0bbf94ef5e600672567f2a7efeaf01786102fcdec53b4eb8c3d249ab33e1bf7a51687b0f80_1280.jpg\",\n          \"width\": 5616\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"Henning_W\",\n          \"height\": 1920,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2014/07/08/10/47/team-386673_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"386673\",\n          \"title\": \"team, group, people, motivation, teamwork, together, community, group work, cooperation, cooperate, group of people, collective, hands, feet\",\n          \"url\": \"https://pixabay.com/get/ge342bff28f9557eb26cc1f22e64ad876416e9db673d2735ecf159223639c1dfdc49cdbda91180fdf8c040a95f48060b13df94f4edacc94248cbb9ec0a50d0d38_1280.jpg\",\n          \"width\": 2560\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"StockSnap\",\n          \"height\": 1769,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2017/08/02/00/49/people-2569234_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"2569234\",\n          \"title\": \"people, group, friends, concept, agreement, fist bump, lifestyle, team, teamwork, cooperation, cooperate, together, togetherness\",\n          \"url\": \"https://pixabay.com/get/geb3815420506902283ac01b16fc5f2f21a26af559d5a1adf7900595fd9328a6297f63ed7adc4cdda699b04ddb937b90355e52a8a563f9a5621027d40f3db6aa6_1280.jpg\",\n          \"width\": 2592\n        }\n      ],\n      \"category\": \"editorial_photo\",\n      \"guidance\": \"No closing atmosphere is needed for the challenge role; keep the scene focused on approved content.\",\n      \"need_id\": \"need-4ad70a6d615bdfe3ce52\",\n      \"primary_candidate_index\": null,\n      \"purpose\": \"Non-evidentiary closing atmosphere for a professional connection CTA.\",\n      \"role_id\": \"assumed-image:employeeconnect:challenge:12\",\n      \"route_ids\": [\n        \"employeeconnect\"\n      ],\n      \"status\": \"candidates_found\"\n    },\n    {\n      \"candidates\": [\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"StartupStockPhotos\",\n          \"height\": 3648,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2015/01/08/18/27/startup-593341_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"593341\",\n          \"title\": \"startup, start-up, people, silicon valley, teamwork, business, team, office, group, meeting, corporate, conference, company, men, partnership, table, technology, casual, successful, seminar, colleagues, working, planning, network, strategy, cooperation, professional, notes, notepad, writing, laptop, computer, drinks\",\n          \"url\": \"https://pixabay.com/get/gff5a10491c2e3671a9a237f5bd52faf19cfe99056ee0762f03f685ca699896d6b052463462e739a1a2104d9cd0d294deb80d2465a29be7405e4b16a7fc092cb0_1280.jpg\",\n          \"width\": 5472\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"ua_Bob_Dmyt_ua\",\n          \"height\": 3744,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2019/10/06/10/03/team-4529717_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"4529717\",\n          \"title\": \"team, friendship, group, hands, cooperation, people, community, connection, relationship, friendship day\",\n          \"url\": \"https://pixabay.com/get/g898505a95163175cf602fd5f2ed3e1ae81575060084751e3a6cecc0bbf94ef5e600672567f2a7efeaf01786102fcdec53b4eb8c3d249ab33e1bf7a51687b0f80_1280.jpg\",\n          \"width\": 5616\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"Henning_W\",\n          \"height\": 1920,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2014/07/08/10/47/team-386673_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"386673\",\n          \"title\": \"team, group, people, motivation, teamwork, together, community, group work, cooperation, cooperate, group of people, collective, hands, feet\",\n          \"url\": \"https://pixabay.com/get/ge342bff28f9557eb26cc1f22e64ad876416e9db673d2735ecf159223639c1dfdc49cdbda91180fdf8c040a95f48060b13df94f4edacc94248cbb9ec0a50d0d38_1280.jpg\",\n          \"width\": 2560\n        }\n      ],\n      \"category\": \"editorial_photo\",\n      \"guidance\": \"Keep the outcome focused on the approved scale and context; omit generic teamwork imagery if it adds unsupported implication.\",\n      \"need_id\": \"need-a2d889f2cc5739b5b00e\",\n      \"primary_candidate_index\": null,\n      \"purpose\": \"Non-evidentiary closing atmosphere for a professional connection CTA.\",\n      \"role_id\": \"assumed-image:employeeconnect:outcome:13\",\n      \"route_ids\": [\n        \"employeeconnect\"\n      ],\n      \"status\": \"candidates_found\"\n    },\n    {\n      \"candidates\": [\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"StartupStockPhotos\",\n          \"height\": 3648,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2015/01/08/18/27/startup-593341_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"593341\",\n          \"title\": \"startup, start-up, people, silicon valley, teamwork, business, team, office, group, meeting, corporate, conference, company, men, partnership, table, technology, casual, successful, seminar, colleagues, working, planning, network, strategy, cooperation, professional, notes, notepad, writing, laptop, computer, drinks\",\n          \"url\": \"https://pixabay.com/get/gff5a10491c2e3671a9a237f5bd52faf19cfe99056ee0762f03f685ca699896d6b052463462e739a1a2104d9cd0d294deb80d2465a29be7405e4b16a7fc092cb0_1280.jpg\",\n          \"width\": 5472\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"ua_Bob_Dmyt_ua\",\n          \"height\": 3744,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2019/10/06/10/03/team-4529717_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"4529717\",\n          \"title\": \"team, friendship, group, hands, cooperation, people, community, connection, relationship, friendship day\",\n          \"url\": \"https://pixabay.com/get/g898505a95163175cf602fd5f2ed3e1ae81575060084751e3a6cecc0bbf94ef5e600672567f2a7efeaf01786102fcdec53b4eb8c3d249ab33e1bf7a51687b0f80_1280.jpg\",\n          \"width\": 5616\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"Henning_W\",\n          \"height\": 1920,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2014/07/08/10/47/team-386673_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"386673\",\n          \"title\": \"team, group, people, motivation, teamwork, together, community, group work, cooperation, cooperate, group of people, collective, hands, feet\",\n          \"url\": \"https://pixabay.com/get/ge342bff28f9557eb26cc1f22e64ad876416e9db673d2735ecf159223639c1dfdc49cdbda91180fdf8c040a95f48060b13df94f4edacc94248cbb9ec0a50d0d38_1280.jpg\",\n          \"width\": 2560\n        }\n      ],\n      \"category\": \"editorial_photo\",\n      \"guidance\": \"Use text-led overview and abstract migration treatment; decorative teamwork imagery is optional and non-evidentiary only.\",\n      \"need_id\": \"need-60cfe22b273f2fba7ed1\",\n      \"primary_candidate_index\": null,\n      \"purpose\": \"Non-evidentiary closing atmosphere for a professional connection CTA.\",\n      \"role_id\": \"assumed-image:employeeconnect:overview:14\",\n      \"route_ids\": [\n        \"employeeconnect\"\n      ],\n      \"status\": \"candidates_found\"\n    },\n    {\n      \"candidates\": [\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"StartupStockPhotos\",\n          \"height\": 3648,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2015/01/08/18/27/startup-593341_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"593341\",\n          \"title\": \"startup, start-up, people, silicon valley, teamwork, business, team, office, group, meeting, corporate, conference, company, men, partnership, table, technology, casual, successful, seminar, colleagues, working, planning, network, strategy, cooperation, professional, notes, notepad, writing, laptop, computer, drinks\",\n          \"url\": \"https://pixabay.com/get/gff5a10491c2e3671a9a237f5bd52faf19cfe99056ee0762f03f685ca699896d6b052463462e739a1a2104d9cd0d294deb80d2465a29be7405e4b16a7fc092cb0_1280.jpg\",\n          \"width\": 5472\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"ua_Bob_Dmyt_ua\",\n          \"height\": 3744,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2019/10/06/10/03/team-4529717_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"4529717\",\n          \"title\": \"team, friendship, group, hands, cooperation, people, community, connection, relationship, friendship day\",\n          \"url\": \"https://pixabay.com/get/g898505a95163175cf602fd5f2ed3e1ae81575060084751e3a6cecc0bbf94ef5e600672567f2a7efeaf01786102fcdec53b4eb8c3d249ab33e1bf7a51687b0f80_1280.jpg\",\n          \"width\": 5616\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"Henning_W\",\n          \"height\": 1920,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2014/07/08/10/47/team-386673_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"386673\",\n          \"title\": \"team, group, people, motivation, teamwork, together, community, group work, cooperation, cooperate, group of people, collective, hands, feet\",\n          \"url\": \"https://pixabay.com/get/ge342bff28f9557eb26cc1f22e64ad876416e9db673d2735ecf159223639c1dfdc49cdbda91180fdf8c040a95f48060b13df94f4edacc94248cbb9ec0a50d0d38_1280.jpg\",\n          \"width\": 2560\n        }\n      ],\n      \"category\": \"editorial_photo\",\n      \"guidance\": \"Technology context should remain compact and textual; omit unrelated editorial imagery.\",\n      \"need_id\": \"need-89d35155ec0741b0f255\",\n      \"primary_candidate_index\": null,\n      \"purpose\": \"Non-evidentiary closing atmosphere for a professional connection CTA.\",\n      \"role_id\": \"assumed-image:employeeconnect:technology:15\",\n      \"route_ids\": [\n        \"employeeconnect\"\n      ],\n      \"status\": \"candidates_found\"\n    },\n    {\n      \"candidates\": [\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"StartupStockPhotos\",\n          \"height\": 3648,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2015/01/08/18/27/startup-593341_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"593341\",\n          \"title\": \"startup, start-up, people, silicon valley, teamwork, business, team, office, group, meeting, corporate, conference, company, men, partnership, table, technology, casual, successful, seminar, colleagues, working, planning, network, strategy, cooperation, professional, notes, notepad, writing, laptop, computer, drinks\",\n          \"url\": \"https://pixabay.com/get/gff5a10491c2e3671a9a237f5bd52faf19cfe99056ee0762f03f685ca699896d6b052463462e739a1a2104d9cd0d294deb80d2465a29be7405e4b16a7fc092cb0_1280.jpg\",\n          \"width\": 5472\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"ua_Bob_Dmyt_ua\",\n          \"height\": 3744,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2019/10/06/10/03/team-4529717_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"4529717\",\n          \"title\": \"team, friendship, group, hands, cooperation, people, community, connection, relationship, friendship day\",\n          \"url\": \"https://pixabay.com/get/g898505a95163175cf602fd5f2ed3e1ae81575060084751e3a6cecc0bbf94ef5e600672567f2a7efeaf01786102fcdec53b4eb8c3d249ab33e1bf7a51687b0f80_1280.jpg\",\n          \"width\": 5616\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"Henning_W\",\n          \"height\": 1920,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2014/07/08/10/47/team-386673_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"386673\",\n          \"title\": \"team, group, people, motivation, teamwork, together, community, group work, cooperation, cooperate, group of people, collective, hands, feet\",\n          \"url\": \"https://pixabay.com/get/ge342bff28f9557eb26cc1f22e64ad876416e9db673d2735ecf159223639c1dfdc49cdbda91180fdf8c040a95f48060b13df94f4edacc94248cbb9ec0a50d0d38_1280.jpg\",\n          \"width\": 2560\n        }\n      ],\n      \"category\": \"editorial_photo\",\n      \"guidance\": \"Close with the approved action and quiet surfaces; generic teamwork imagery is unnecessary.\",\n      \"need_id\": \"need-75544073a0565c50677b\",\n      \"primary_candidate_index\": null,\n      \"purpose\": \"Non-evidentiary closing atmosphere for a professional connection CTA.\",\n      \"role_id\": \"assumed-image:home:contact:16\",\n      \"route_ids\": [\n        \"home\"\n      ],\n      \"status\": \"candidates_found\"\n    },\n    {\n      \"candidates\": [\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"mirkostoedter\",\n          \"height\": 3333,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2023/01/15/16/20/library-7720589_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"7720589\",\n          \"title\": \"library, wisdom, reading, knowledge, education, study, read, book\",\n          \"url\": \"https://pixabay.com/get/g802c42ced1fcee2d81abc510ed78310c8be3bab5158a398eb1ff2fdb767c2a0ee7b2a73b280d0e3c1708429e349383f3e67b24f5a59b347843dd096b046000c3_1280.jpg\",\n          \"width\": 5000\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"analogicus\",\n          \"height\": 4000,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2022/01/23/18/37/aluminum-foil-6961638_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"6961638\",\n          \"title\": \"aluminum foil, abstract, texture, material, shine, aluminum\",\n          \"url\": \"https://pixabay.com/get/gdbb82afc2b894c3d0adb3d71a08052d87aafbfd834a23a593691d332e9140f65bf3ed93eb3a5fd4e87b1910c31142106b6fb5628396d1830b51e3727d7e47a77_1280.jpg\",\n          \"width\": 6000\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"KAVOWO\",\n          \"height\": 3456,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2018/02/15/14/37/paper-3155438_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"3155438\",\n          \"title\": \"paper, beautiful wallpaper, texture, free background, wrapping paper, 4k wallpaper, 4k wallpaper 1920x1080, wallpaper hd, hd wallpaper, windows wallpaper, full hd wallpaper, background, crumples, collage, mac wallpaper, free wallpaper, laptop wallpaper, desktop backgrounds, wallpaper 4k, cool backgrounds, structure, unlabeled\",\n          \"url\": \"https://pixabay.com/get/gd62df20451de88949c0c2131f63062c6b15d1684d351cdf186f280b011d7aeb82f6b20ba76b411c35d09917bc7a6febe48f28ba18d1a2161909e73c03515eaaf_1280.jpg\",\n          \"width\": 5184\n        }\n      ],\n      \"category\": \"editorial_photo\",\n      \"guidance\": \"Credentials should remain profession-neutral and supporting; prefer a quiet surface or omit the decorative image.\",\n      \"need_id\": \"need-7518cc20ca7e14d1e9e5\",\n      \"primary_candidate_index\": null,\n      \"purpose\": \"Quiet decorative atmosphere for a supporting section whose subject is not one of the named roles above; kept profession-neutral rather than assumed technical.\",\n      \"role_id\": \"assumed-image:home:credentials:17\",\n      \"route_ids\": [\n        \"home\"\n      ],\n      \"status\": \"candidates_found\"\n    },\n    {\n      \"candidates\": [\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"mirkostoedter\",\n          \"height\": 3333,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2023/01/15/16/20/library-7720589_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"7720589\",\n          \"title\": \"library, wisdom, reading, knowledge, education, study, read, book\",\n          \"url\": \"https://pixabay.com/get/g802c42ced1fcee2d81abc510ed78310c8be3bab5158a398eb1ff2fdb767c2a0ee7b2a73b280d0e3c1708429e349383f3e67b24f5a59b347843dd096b046000c3_1280.jpg\",\n          \"width\": 5000\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"analogicus\",\n          \"height\": 4000,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2022/01/23/18/37/aluminum-foil-6961638_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"6961638\",\n          \"title\": \"aluminum foil, abstract, texture, material, shine, aluminum\",\n          \"url\": \"https://pixabay.com/get/gdbb82afc2b894c3d0adb3d71a08052d87aafbfd834a23a593691d332e9140f65bf3ed93eb3a5fd4e87b1910c31142106b6fb5628396d1830b51e3727d7e47a77_1280.jpg\",\n          \"width\": 6000\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"KAVOWO\",\n          \"height\": 3456,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2018/02/15/14/37/paper-3155438_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"3155438\",\n          \"title\": \"paper, beautiful wallpaper, texture, free background, wrapping paper, 4k wallpaper, 4k wallpaper 1920x1080, wallpaper hd, hd wallpaper, windows wallpaper, full hd wallpaper, background, crumples, collage, mac wallpaper, free wallpaper, laptop wallpaper, desktop backgrounds, wallpaper 4k, cool backgrounds, structure, unlabeled\",\n          \"url\": \"https://pixabay.com/get/gd62df20451de88949c0c2131f63062c6b15d1684d351cdf186f280b011d7aeb82f6b20ba76b411c35d09917bc7a6febe48f28ba18d1a2161909e73c03515eaaf_1280.jpg\",\n          \"width\": 5184\n        }\n      ],\n      \"category\": \"editorial_photo\",\n      \"guidance\": \"Keep the security challenge textual and abstract; do not use a generic texture as evidence.\",\n      \"need_id\": \"need-f6bcecdd26d4469c08c5\",\n      \"primary_candidate_index\": null,\n      \"purpose\": \"Quiet decorative atmosphere for a supporting section whose subject is not one of the named roles above; kept profession-neutral rather than assumed technical.\",\n      \"role_id\": \"assumed-image:secureendpoint:challenge:18\",\n      \"route_ids\": [\n        \"secureendpoint\"\n      ],\n      \"status\": \"candidates_found\"\n    },\n    {\n      \"candidates\": [\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"mirkostoedter\",\n          \"height\": 3333,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2023/01/15/16/20/library-7720589_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"7720589\",\n          \"title\": \"library, wisdom, reading, knowledge, education, study, read, book\",\n          \"url\": \"https://pixabay.com/get/g802c42ced1fcee2d81abc510ed78310c8be3bab5158a398eb1ff2fdb767c2a0ee7b2a73b280d0e3c1708429e349383f3e67b24f5a59b347843dd096b046000c3_1280.jpg\",\n          \"width\": 5000\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"analogicus\",\n          \"height\": 4000,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2022/01/23/18/37/aluminum-foil-6961638_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"6961638\",\n          \"title\": \"aluminum foil, abstract, texture, material, shine, aluminum\",\n          \"url\": \"https://pixabay.com/get/gdbb82afc2b894c3d0adb3d71a08052d87aafbfd834a23a593691d332e9140f65bf3ed93eb3a5fd4e87b1910c31142106b6fb5628396d1830b51e3727d7e47a77_1280.jpg\",\n          \"width\": 6000\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"KAVOWO\",\n          \"height\": 3456,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2018/02/15/14/37/paper-3155438_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"3155438\",\n          \"title\": \"paper, beautiful wallpaper, texture, free background, wrapping paper, 4k wallpaper, 4k wallpaper 1920x1080, wallpaper hd, hd wallpaper, windows wallpaper, full hd wallpaper, background, crumples, collage, mac wallpaper, free wallpaper, laptop wallpaper, desktop backgrounds, wallpaper 4k, cool backgrounds, structure, unlabeled\",\n          \"url\": \"https://pixabay.com/get/gd62df20451de88949c0c2131f63062c6b15d1684d351cdf186f280b011d7aeb82f6b20ba76b411c35d09917bc7a6febe48f28ba18d1a2161909e73c03515eaaf_1280.jpg\",\n          \"width\": 5184\n        }\n      ],\n      \"category\": \"editorial_photo\",\n      \"guidance\": \"Use the approved result comparison and explanation; no decorative image is needed.\",\n      \"need_id\": \"need-2af5fc8d108ec85b1d08\",\n      \"primary_candidate_index\": null,\n      \"purpose\": \"Quiet decorative atmosphere for a supporting section whose subject is not one of the named roles above; kept profession-neutral rather than assumed technical.\",\n      \"role_id\": \"assumed-image:secureendpoint:outcome:19\",\n      \"route_ids\": [\n        \"secureendpoint\"\n      ],\n      \"status\": \"candidates_found\"\n    },\n    {\n      \"candidates\": [\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"mirkostoedter\",\n          \"height\": 3333,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2023/01/15/16/20/library-7720589_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"7720589\",\n          \"title\": \"library, wisdom, reading, knowledge, education, study, read, book\",\n          \"url\": \"https://pixabay.com/get/g802c42ced1fcee2d81abc510ed78310c8be3bab5158a398eb1ff2fdb767c2a0ee7b2a73b280d0e3c1708429e349383f3e67b24f5a59b347843dd096b046000c3_1280.jpg\",\n          \"width\": 5000\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"analogicus\",\n          \"height\": 4000,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2022/01/23/18/37/aluminum-foil-6961638_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"6961638\",\n          \"title\": \"aluminum foil, abstract, texture, material, shine, aluminum\",\n          \"url\": \"https://pixabay.com/get/gdbb82afc2b894c3d0adb3d71a08052d87aafbfd834a23a593691d332e9140f65bf3ed93eb3a5fd4e87b1910c31142106b6fb5628396d1830b51e3727d7e47a77_1280.jpg\",\n          \"width\": 6000\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"KAVOWO\",\n          \"height\": 3456,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2018/02/15/14/37/paper-3155438_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"3155438\",\n          \"title\": \"paper, beautiful wallpaper, texture, free background, wrapping paper, 4k wallpaper, 4k wallpaper 1920x1080, wallpaper hd, hd wallpaper, windows wallpaper, full hd wallpaper, background, crumples, collage, mac wallpaper, free wallpaper, laptop wallpaper, desktop backgrounds, wallpaper 4k, cool backgrounds, structure, unlabeled\",\n          \"url\": \"https://pixabay.com/get/gd62df20451de88949c0c2131f63062c6b15d1684d351cdf186f280b011d7aeb82f6b20ba76b411c35d09917bc7a6febe48f28ba18d1a2161909e73c03515eaaf_1280.jpg\",\n          \"width\": 5184\n        }\n      ],\n      \"category\": \"editorial_photo\",\n      \"guidance\": \"Keep the security overview words-first and clearly non-dashboard-like.\",\n      \"need_id\": \"need-989bb622f62c86c0ee1c\",\n      \"primary_candidate_index\": null,\n      \"purpose\": \"Quiet decorative atmosphere for a supporting section whose subject is not one of the named roles above; kept profession-neutral rather than assumed technical.\",\n      \"role_id\": \"assumed-image:secureendpoint:overview:20\",\n      \"route_ids\": [\n        \"secureendpoint\"\n      ],\n      \"status\": \"candidates_found\"\n    },\n    {\n      \"candidates\": [\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"mirkostoedter\",\n          \"height\": 3333,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2023/01/15/16/20/library-7720589_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"7720589\",\n          \"title\": \"library, wisdom, reading, knowledge, education, study, read, book\",\n          \"url\": \"https://pixabay.com/get/g802c42ced1fcee2d81abc510ed78310c8be3bab5158a398eb1ff2fdb767c2a0ee7b2a73b280d0e3c1708429e349383f3e67b24f5a59b347843dd096b046000c3_1280.jpg\",\n          \"width\": 5000\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"analogicus\",\n          \"height\": 4000,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2022/01/23/18/37/aluminum-foil-6961638_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"6961638\",\n          \"title\": \"aluminum foil, abstract, texture, material, shine, aluminum\",\n          \"url\": \"https://pixabay.com/get/gdbb82afc2b894c3d0adb3d71a08052d87aafbfd834a23a593691d332e9140f65bf3ed93eb3a5fd4e87b1910c31142106b6fb5628396d1830b51e3727d7e47a77_1280.jpg\",\n          \"width\": 6000\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"KAVOWO\",\n          \"height\": 3456,\n          \"license\": \"Pixabay Content License\",\n          \"license_reference\": \"https://pixabay.com/service/license-summary/\",\n          \"preview_url\": \"https://cdn.pixabay.com/photo/2018/02/15/14/37/paper-3155438_150.jpg\",\n          \"provider\": \"pixabay\",\n          \"provider_asset_id\": \"3155438\",\n          \"title\": \"paper, beautiful wallpaper, texture, free background, wrapping paper, 4k wallpaper, 4k wallpaper 1920x1080, wallpaper hd, hd wallpaper, windows wallpaper, full hd wallpaper, background, crumples, collage, mac wallpaper, free wallpaper, laptop wallpaper, desktop backgrounds, wallpaper 4k, cool backgrounds, structure, unlabeled\",\n          \"url\": \"https://pixabay.com/get/gd62df20451de88949c0c2131f63062c6b15d1684d351cdf186f280b011d7aeb82f6b20ba76b411c35d09917bc7a6febe48f28ba18d1a2161909e73c03515eaaf_1280.jpg\",\n          \"width\": 5184\n        }\n      ],\n      \"category\": \"editorial_photo\",\n      \"guidance\": \"Technology context should be a compact textual close, without decorative imagery.\",\n      \"need_id\": \"need-4421d6f4a49adbf70e30\",\n      \"primary_candidate_index\": null,\n      \"purpose\": \"Quiet decorative atmosphere for a supporting section whose subject is not one of the named roles above; kept profession-neutral rather than assumed technical.\",\n      \"role_id\": \"assumed-image:secureendpoint:technology:21\",\n      \"route_ids\": [\n        \"secureendpoint\"\n      ],\n      \"status\": \"candidates_found\"\n    },\n    {\n      \"candidates\": [\n        {\n          \"additional_urls\": {\n            \"500-normal\": \"https://cdn.jsdelivr.net/fontsource/fonts/space-grotesk@latest/latin-500-normal.woff2\",\n            \"600-normal\": \"https://cdn.jsdelivr.net/fontsource/fonts/space-grotesk@latest/latin-600-normal.woff2\",\n            \"700-normal\": \"https://cdn.jsdelivr.net/fontsource/fonts/space-grotesk@latest/latin-700-normal.woff2\"\n          },\n          \"attribution\": \"\",\n          \"height\": 0,\n          \"license\": \"OFL-1.1\",\n          \"license_reference\": \"https://scripts.sil.org/OFL\",\n          \"preview_url\": \"\",\n          \"provider\": \"fontsource\",\n          \"provider_asset_id\": \"space-grotesk\",\n          \"title\": \"Space Grotesk\",\n          \"url\": \"https://cdn.jsdelivr.net/fontsource/fonts/space-grotesk@latest/latin-400-normal.woff2\",\n          \"width\": 0\n        },\n        {\n          \"additional_urls\": {\n            \"500-normal\": \"https://cdn.jsdelivr.net/fontsource/fonts/familjen-grotesk@latest/latin-500-normal.woff2\",\n            \"600-normal\": \"https://cdn.jsdelivr.net/fontsource/fonts/familjen-grotesk@latest/latin-600-normal.woff2\",\n            \"700-normal\": \"https://cdn.jsdelivr.net/fontsource/fonts/familjen-grotesk@latest/latin-700-normal.woff2\"\n          },\n          \"attribution\": \"\",\n          \"height\": 0,\n          \"license\": \"OFL-1.1\",\n          \"license_reference\": \"https://scripts.sil.org/OFL\",\n          \"preview_url\": \"\",\n          \"provider\": \"fontsource\",\n          \"provider_asset_id\": \"familjen-grotesk\",\n          \"title\": \"Familjen Grotesk\",\n          \"url\": \"https://cdn.jsdelivr.net/fontsource/fonts/familjen-grotesk@latest/latin-400-normal.woff2\",\n          \"width\": 0\n        },\n        {\n          \"additional_urls\": {},\n          \"attribution\": \"\",\n          \"height\": 0,\n          \"license\": \"OFL-1.1\",\n          \"license_reference\": \"https://scripts.sil.org/OFL\",\n          \"preview_url\": \"\",\n          \"provider\": \"fontsource\",\n          \"provider_asset_id\": \"fusion-pixel-10px-monospaced-jp\",\n          \"title\": \"Fusion Pixel 10px Monospaced JP\",\n          \"url\": \"https://cdn.jsdelivr.net/fontsource/fonts/fusion-pixel-10px-monospaced-jp@latest/latin-400-normal.woff2\",\n          \"width\": 0\n        }\n      ],\n      \"category\": \"font\",\n      \"guidance\": \"Use Space Grotesk as the locally vendored versatile family for display and reading roles, while preserving comfortable body measure and strong contrast.\",\n      \"need_id\": \"need-016331262cb7124422e4\",\n      \"primary_candidate_index\": 0,\n      \"purpose\": \"A distinctive display/body font family for the approved visual language, vendored locally with Latin glyph coverage.\",\n      \"role_id\": \"typography-font\",\n      \"route_ids\": [\n        \"home\",\n        \"workspace360\",\n        \"secureendpoint\",\n        \"employeeconnect\"\n      ],\n      \"status\": \"candidates_found\"\n    }\n  ],\n  \"routes\": [\n    \"home\",\n    \"workspace360\",\n    \"secureendpoint\",\n    \"employeeconnect\"\n  ],\n  \"run_id\": \"6b899b90-f914-419d-badf-9a9f8f33b9fc\",\n  \"target_contract\": \"react-vite-v1\",\n  \"visual_input_mode\": \"merged_vdd_assumptions\"\n}\n```\n\n# Visual & Build Brief\n\n## 1. Design language\n\nThe visual direction is intentionally synthesized from approved assumptions (`merged_vdd_assumptions`), rather than from a fully specified visual system. Use professional defaults: a restrained neutral foundation, one confident technical accent, strong contrast, disciplined borders, and generous but controlled whitespace. Prefer a flexible editorial grid with a strong reading column and offset evidence or annotation areas. Keep left alignment dominant; reserve centered composition for a concise closing invitation or focused result moment.\n\nUse a crisp, highly legible typographic voice for headings and a neutral, comfortable reading treatment for body copy. Outcome figures and short labels should carry strong visual weight without becoming promotional. Technical names may receive a modest utility treatment, but the page should not resemble a code editor or dashboard. Build rhythm from compact label-to-value relationships, moderate paragraph spacing, and larger pauses around hero positioning, approach, and measurable results.\n\nThe recurring metaphor is a connected operating chain: inputs become controlled workflows, workflows become visible states, and visible states become dependable outcomes. Express this with sparse lines, grouped nodes, ordered steps, and static before/after relationships. Abstract visuals must remain representative and words-first; they must never imply a real product interface, live telemetry, screenshot, client mark, portrait, testimonial, or independently verified evidence.\n\nMotion should feel quiet, responsive, and process-oriented. Static meaning comes first; optional grouped reveals, restrained connector drawing, or a small directional emphasis may follow. Avoid looping spectacle, rapid counters, parallax-heavy backgrounds, auto-advancing content, threat-like pulsing, and repeated entrance choreography. Interactions should reward exploration without hiding information: explicit expanded states, persistent focus, clear route cues, and modest pressed, selected, or directional responses should replace hover-only behavior.\n\n## 2. Per-route direction\n\n### Home (`/`)\n\nFollow the approved rhythm of positioning, proof, capability groups, career progression, selected work, credentials, and contact. The hero is text-dominant and asymmetric: the positioning and LinkedIn action lead, while a small abstract connected-workflow visual provides balance. The proof scene should be an early, highly scannable pause with labelled values and context, followed by flatter capability families rather than a dense card grid. Capability groups may expand explicitly, but their labels and content must remain understandable without hover.\n\nMove from proof into a readable experience progression, then give selected-work entries stronger contrast and clear route destinations. The closing invitation should be quiet and generous, with credentials subordinate to the contact action. Scene transitions should use whitespace, short rules, and directional cues rather than theatrical movement. On mobile, turn the route into one ordered reading path: copy and action first, proof stacked, capability groups explicitly expandable, experience readable as structured progression, and project links large enough for touch.\n\nThe `home-positioning` scene should communicate identity before interaction, with any connector drawing delayed until the static content is clear. The `home-proof-capabilities` scene should keep proof values visible and prohibit animated counting. The `home-experience-work` scene should distinguish career progression from project outcomes and use only modest link emphasis. The `home-closing-invitation` scene should render completely without animation and preserve external-link semantics.\n\n### WorkSpace360 (`/work/workspace360`)\n\nUse the sequence overview, operating need, approach, result, and technology context. Lead with the approved deployment outcome and a words-first comparison, then explain the operating need before presenting the three contribution stages. Give the result the clearest tonal contrast and breathing room, while keeping technology context and return navigation subordinate.\n\nThe `workspace360-overview` scene should combine text-led scope with a compact representative comparison. In `workspace360-need-approach`, use a sparse three-stage process relationship; all stage titles and descriptions must remain exposed. In `workspace360-result-context`, make the approved result legible without a counter and clearly separate program outcome from individual contribution. On mobile, stack overview, challenge, approach, result, and technology; simplify connectors into labelled dividers rather than shrinking a wide diagram.\n\n### SecureEndpoint (`/work/secureendpoint`)\n\nUse the same overview, operating need, approach, result, and technology rhythm, but give the control-to-remediation motif the strongest process emphasis. The opening should place the approved compliance comparison beside a small abstract chain, never a security dashboard. The approach should progress conceptually from controls through visibility to remediation, with the challenge quieter than the contribution sequence.\n\nIn `secureendpoint-overview`, keep the comparison text-readable and avoid cyber-security spectacle. In `secureendpoint-need-approach`, use a connected but sparse three-stage sequence with no hover-only labels or automatic advancement. In `secureendpoint-result-context`, preserve the approved time context and keep technology secondary. Mobile should lead with the percentage change, then stack explanation, simplified chain, technology, and return action. No visual state should imply live security telemetry.\n\n### EmployeeConnect (`/work/employeeconnect`)\n\nBalance platform administration with employee adoption support. Follow overview, operating need, approach, result, and technology context, leading with the approved account scale and a representative migration path. The visual should feel human and operational without becoming a product console or simulating data transfer.\n\nThe `employeeconnect-overview` scene should pair scale with a quiet path motif. In `employeeconnect-need-approach`, alternate or balance technical administration, adoption support, and documentation as three readable stages. In `employeeconnect-result-context`, keep the approved scale and its technical-plus-human context together, with technology and return navigation compact. On mobile, lead with scale, stack the three stages with short descriptions and dividers, and avoid any sticky result panel.\n\nAcross all case-study routes, transitions should be editorial rather than cinematic: a divider or tonal shift should mark movement from need to approach and from approach to result. The final state must always work as static content, with route return links visible and understandable.\n\n## 3. Component and layout patterns\n\n- **`need-6b0208477661a71dfff5` — asymmetric text-dominant hero:** Use as an adaptable homepage opening because the approved positioning is concise and no approved hero image exists. Keep the abstract visual small, preserve headline hierarchy, and fall back to a plain text-led hero with a static line motif if the visual competes with the message.\n- **`need-902f5f32af160f3530d8` — labelled comparison primitive:** Use around approved outcomes on the homepage, WorkSpace360, and SecureEndpoint. Pair every comparison with its supplied label, context, contribution boundary, and plain-language explanation; use text-only metric blocks if a diagram would suggest live telemetry.\n- **`need-ed9585639f0ba7f22051` — sparse process-flow primitive:** Use beside or behind the approved approach copy on the three case studies. Keep the step count low, preserve supplied titles and boundaries, and simplify into ordered text blocks with dividers on small screens rather than shrinking the diagram.\n- **`need-d912bac698033b12ba70` — minimal route navigation:** This is optional. Use restrained persistent orientation and a recognizable external action when it improves cross-route context; define narrow-screen collapse and provide current-route text or structural cues in addition to color. A compact navigation at the beginning and end is a valid fallback.\n\n## 4. Resource guidance\n\nNo supplied project images, diagrams, or case-study media are approved as evidence. The Code Generator should favor lightweight custom abstract treatment and may omit decorative candidates when they distract from the content. The bounded selections and usage notes are recorded in the structured guidance below.\n\nFor the homepage hero, capabilities, experience, selected work, proof, contact, and credentials roles, treat any selected editorial imagery as optional decoration only: crop quietly, avoid identifiable people or implied evidence, and prefer omission in favor of static linework or tonal surfaces. For case-study roles, do not use decorative photographs to represent project facts; use them only if they remain clearly non-evidentiary and subordinate to words-first diagrams. The typography role may use the selected local font candidate consistently across routes, provided reading measure and contrast remain comfortable.\n\n## 5. Accessibility and performance\n\nUse a high-contrast neutral foundation and verify text, links, borders, and status cues independently. Never use the accent as the sole carrier of meaning. Navigation, CTAs, expandable groups, route links, and any interactive diagram state require a strong persistent focus indicator that remains visible across changing surfaces and does not depend on color alone.\n\nKeep all essential information visible in the document flow. Capability groups may collapse on small screens only through explicit buttons with expanded and collapsed labels. Approach sequences may receive emphasis, but must never hide steps or require hover. Replace hover-only behavior with pressed, selected, or expanded touch-safe states, and avoid swipe-dependent storytelling.\n\nPrefer text-led layouts, lightweight custom diagrams, and static-first CSS- or SVG-like motifs. Avoid background video, heavy raster artwork, continuous animation, unnecessary external media, and rapid metric counters. Lazy-load any future approved media. Every scene needs a complete static fallback; under reduced motion, show copy, diagrams, metrics, and route actions immediately and remove decorative movement or staged reveals.\n\nPreserve reading order, heading hierarchy, equivalent diagram explanations, descriptive external-link labels, and usable controls across touch-only mobile, tablet, laptop, desktop, and wide desktop layouts. Collapse columns and simplify diagrams rather than shrinking text. Keep evidence labels, contexts, and contribution boundaries attached to their values at every breakpoint.\n\n## 6. Authority\n\nCode Generator has final authority to adapt, replace, combine, or ignore any suggestion in this brief. Nothing here is a hard constraint except the approved content itself, which this brief does not repeat.\n\n## Resource guidance (reference table)\n\n| Role | Category | Status | Primary candidate | Provider | License |\n| --- | --- | --- | --- | --- | --- |\n| assumed-image:home:hero:0 | editorial_photo | candidates_found | (none) | - | - |\n| assumed-image:home:capabilities:1 | editorial_photo | candidates_found | (none) | - | - |\n| assumed-image:home:experience:2 | editorial_photo | candidates_found | (none) | - | - |\n| assumed-image:home:featured-work:3 | editorial_photo | candidates_found | (none) | - | - |\n| assumed-image:home:proof-points:4 | editorial_photo | candidates_found | (none) | - | - |\n| assumed-image:workspace360:approach:5 | editorial_photo | candidates_found | (none) | - | - |\n| assumed-image:workspace360:challenge:6 | editorial_photo | candidates_found | (none) | - | - |\n| assumed-image:workspace360:outcome:7 | editorial_photo | candidates_found | (none) | - | - |\n| assumed-image:workspace360:overview:8 | editorial_photo | candidates_found | (none) | - | - |\n| assumed-image:workspace360:technology:9 | editorial_photo | candidates_found | (none) | - | - |\n| assumed-image:employeeconnect:approach:10 | editorial_photo | candidates_found | (none) | - | - |\n| assumed-image:secureendpoint:approach:11 | editorial_photo | candidates_found | (none) | - | - |\n| assumed-image:employeeconnect:challenge:12 | editorial_photo | candidates_found | (none) | - | - |\n| assumed-image:employeeconnect:outcome:13 | editorial_photo | candidates_found | (none) | - | - |\n| assumed-image:employeeconnect:overview:14 | editorial_photo | candidates_found | (none) | - | - |\n| assumed-image:employeeconnect:technology:15 | editorial_photo | candidates_found | (none) | - | - |\n| assumed-image:home:contact:16 | editorial_photo | candidates_found | (none) | - | - |\n| assumed-image:home:credentials:17 | editorial_photo | candidates_found | (none) | - | - |\n| assumed-image:secureendpoint:challenge:18 | editorial_photo | candidates_found | (none) | - | - |\n| assumed-image:secureendpoint:outcome:19 | editorial_photo | candidates_found | (none) | - | - |\n| assumed-image:secureendpoint:overview:20 | editorial_photo | candidates_found | (none) | - | - |\n| assumed-image:secureendpoint:technology:21 | editorial_photo | candidates_found | (none) | - | - |\n| typography-font | font | candidates_found | https://cdn.jsdelivr.net/fontsource/fonts/space-grotesk@latest/latin-400-normal.woff2 | fontsource | OFL-1.1 |\n\n## Component suggestions (reference table)\n\n| Role | Primary suggestion | Provider | Reference |\n| --- | --- | --- | --- |\n| home-operating-chain | (none) | - | - |\n| home-workflow-abstract | (none) | - | - |\n| workspace360-process-visual | (none) | - | - |\n| secureendpoint-control-chain | animated-beam | magicui | https://magicui.design/r/animated-beam.json |\n| employeeconnect-migration-path | (none) | - | - |\n| assumed-component:home:capabilities:capability-grouping | button-group-dropdown | shadcn | https://ui.shadcn.com/r/styles/new-york-v4/button-group-dropdown.json |\n| assumed-component:home:experience:experience-timeline | (none) | - | - |\n| assumed-component:home:featured-work:selected-work-detail | (none) | - | - |\n| assumed-component:workspace360:approach:selected-work-detail | (none) | - | - |\n| assumed-component:workspace360:approach:process-sequence | sidebar-14 | shadcn | https://ui.shadcn.com/r/styles/new-york-v4/sidebar-14.json |\n| assumed-component:workspace360:technology:selected-work-detail | (none) | - | - |\n| assumed-component:secureendpoint:approach:process-sequence | sidebar-14 | shadcn | https://ui.shadcn.com/r/styles/new-york-v4/sidebar-14.json |\n| assumed-component:employeeconnect:approach:process-sequence | sidebar-14 | shadcn | https://ui.shadcn.com/r/styles/new-york-v4/sidebar-14.json |\n\n## Warnings\n\n- Visual direction is explicitly based on merged VDD assumptions rather than a fully independent visual specification; keep defaults restrained and professional.\n- No supplied project images, diagrams, screenshots, or case-study media are approved as evidence; resolve visuals with text-led custom treatment.\n- Most editorial image candidates are decorative and semantically weak for the assigned roles, so they have been declined.\n- Avoid presenting approved program outcomes as solely individual achievements.\n- The homepage has moderate recruiter-scannable density, while case studies need deeper reading; preserve clear entry points and avoid walls of prose.\n- Any animated component must have an immediate static equivalent and must not imply live telemetry or stronger evidence.\n\nCode Generator has final authority to adapt, replace, combine, or ignore any suggestion in this brief.\n",
  "content_brief_markdown": "# Content & Narrative Brief -- Maya Bennett — End User Computing & Endpoint Engineering\n\n```json build-preparation-content-index\n{\n  \"content_architect_content_hash\": \"d1cead1bc8396a6f1abc9329572d3f61bf7e308d764faa66a5c630d75a3bf1b3\",\n  \"kind\": \"content_index\",\n  \"navigation_contract\": {\n    \"allowed_destinations\": [\n      \"home\",\n      \"home:hero\",\n      \"home:proof-points\",\n      \"home:capabilities\",\n      \"home:experience\",\n      \"home:featured-work\",\n      \"home:credentials\",\n      \"home:contact\",\n      \"workspace360\",\n      \"workspace360:overview\",\n      \"workspace360:challenge\",\n      \"workspace360:approach\",\n      \"workspace360:outcome\",\n      \"workspace360:technology\",\n      \"secureendpoint\",\n      \"secureendpoint:overview\",\n      \"secureendpoint:challenge\",\n      \"secureendpoint:approach\",\n      \"secureendpoint:outcome\",\n      \"secureendpoint:technology\",\n      \"employeeconnect\",\n      \"employeeconnect:overview\",\n      \"employeeconnect:challenge\",\n      \"employeeconnect:approach\",\n      \"employeeconnect:outcome\",\n      \"employeeconnect:technology\"\n    ],\n    \"closed\": true\n  },\n  \"routes\": [\n    {\n      \"path\": \"/\",\n      \"route_id\": \"home\",\n      \"sections\": [\n        \"home:hero\",\n        \"home:proof-points\",\n        \"home:capabilities\",\n        \"home:experience\",\n        \"home:featured-work\",\n        \"home:credentials\",\n        \"home:contact\"\n      ],\n      \"title\": \"Maya Bennett — End User Computing & Endpoint Engineering\"\n    },\n    {\n      \"path\": \"/work/workspace360\",\n      \"route_id\": \"workspace360\",\n      \"sections\": [\n        \"workspace360:overview\",\n        \"workspace360:challenge\",\n        \"workspace360:approach\",\n        \"workspace360:outcome\",\n        \"workspace360:technology\"\n      ],\n      \"title\": \"WorkSpace360\"\n    },\n    {\n      \"path\": \"/work/secureendpoint\",\n      \"route_id\": \"secureendpoint\",\n      \"sections\": [\n        \"secureendpoint:overview\",\n        \"secureendpoint:challenge\",\n        \"secureendpoint:approach\",\n        \"secureendpoint:outcome\",\n        \"secureendpoint:technology\"\n      ],\n      \"title\": \"SecureEndpoint\"\n    },\n    {\n      \"path\": \"/work/employeeconnect\",\n      \"route_id\": \"employeeconnect\",\n      \"sections\": [\n        \"employeeconnect:overview\",\n        \"employeeconnect:challenge\",\n        \"employeeconnect:approach\",\n        \"employeeconnect:outcome\",\n        \"employeeconnect:technology\"\n      ],\n      \"title\": \"EmployeeConnect\"\n    }\n  ],\n  \"run_id\": \"6b899b90-f914-419d-badf-9a9f8f33b9fc\"\n}\n```\n\nThis file is the complete, approved public content for this portfolio. Every fact below is already approved for publication -- do not add, soften, or invent anything beyond it.\n\n## Positioning\n\n- **Positioning:** Senior End User Computing Specialist focused on endpoint engineering, Microsoft cloud administration, automation, compliance, and reliable employee technology experiences.\n- **Value proposition:** Maya Bennett helps organizations make endpoint and digital workplace operations more consistent, secure, and scalable through hands-on Microsoft platform administration, PowerShell automation, process improvement, and structured support practices.\n- **Central narrative:** Maya turns complex endpoint and workplace technology operations into repeatable, measurable services: faster provisioning, stronger compliance, clearer remediation, and better support at enterprise scale.\n- **Primary audience:** Recruiters and hiring managers evaluating senior end-user computing, endpoint engineering, digital workplace, and Microsoft 365 operations candidates.\n- **Secondary audience:** IT operations, endpoint management, workplace technology, and security leaders assessing practical automation and endpoint reliability experience.\n- **Main visitor action:** Connect with Maya on LinkedIn to discuss senior endpoint engineering and end-user computing opportunities.\n\n## Navigation contract\n\nThe navigation_contract above is the complete, closed set of valid navigation destinations. Do not add, infer, or invent any additional page, route, or navigation item beyond it.\n\n## Route: / (home)\n\n*Purpose: Introduce Maya's professional positioning, strongest evidence, capabilities, experience, and selected work for recruiter review.*\n\n### home:hero\n*Establish positioning and invite recruiter connection.*\n\n```json section-content\n{\n  \"body\": \"Maya Bennett works across endpoint engineering, Microsoft 365 administration, automation, and digital workplace operations. She helps distributed organizations standardize device management, strengthen compliance, and improve the employee technology experience.\",\n  \"eyebrow\": \"Senior End User Computing Specialist\",\n  \"headline\": \"Making endpoint operations faster, clearer, and more reliable.\",\n  \"primary_cta\": {\n    \"href\": \"https://linkedin.com/in/mayabennett-it\",\n    \"label\": \"Connect on LinkedIn\"\n  }\n}\n```\n\n### home:proof-points\n*Provide immediate evidence of scale and outcomes.*\n\n```json section-content\n{\n  \"intro\": \"Selected evidence from Maya's endpoint and workplace technology work.\",\n  \"points\": [\n    {\n      \"label\": \"employees supported across India, North America, and Europe\",\n      \"value\": \"4,500+\"\n    },\n    {\n      \"label\": \"new-device deployment improvement through WorkSpace360\",\n      \"value\": \"90 min → under 30 min\"\n    },\n    {\n      \"label\": \"compliant managed endpoints through SecureEndpoint\",\n      \"value\": \"81% → 97%\"\n    }\n  ]\n}\n```\n\n### home:capabilities\n*Group the technical breadth into recruiter-readable capability areas.*\n\n```json section-content\n{\n  \"groups\": [\n    {\n      \"items\": [\n        \"Microsoft Intune\",\n        \"Configuration Manager / MECM\",\n        \"Entra ID\",\n        \"Windows and macOS management\",\n        \"Microsoft Defender\",\n        \"BitLocker\"\n      ],\n      \"title\": \"Endpoint platforms\"\n    },\n    {\n      \"items\": [\n        \"PowerShell\",\n        \"Microsoft Graph API\",\n        \"Power Automate\",\n        \"Microsoft 365\",\n        \"Exchange Online\",\n        \"Teams\"\n      ],\n      \"title\": \"Automation and administration\"\n    },\n    {\n      \"items\": [\n        \"Endpoint compliance\",\n        \"Patch management\",\n        \"Incident and problem management\",\n        \"Root-cause analysis\",\n        \"Knowledge management\",\n        \"Asset management\"\n      ],\n      \"title\": \"Service reliability\"\n    }\n  ],\n  \"heading\": \"Endpoint engineering with an operations mindset.\"\n}\n```\n\n### home:experience\n*Show career progression and operating scale without duplicating the case studies.*\n\n```json section-content\n{\n  \"heading\": \"Experience across distributed technology environments.\",\n  \"roles\": [\n    {\n      \"dates\": \"Sep 2022 – Present\",\n      \"evidence\": [\n        \"More than 4,500 employees across India, North America, and Europe\",\n        \"More than 180 business applications automated\",\n        \"Repeat incidents reduced by 39%\"\n      ],\n      \"organization\": \"BluePeak Financial Services\",\n      \"role\": \"Senior End User Computing Specialist\",\n      \"summary\": \"Leads end-user computing services, manages Windows and macOS endpoint environments, automates application deployment and updates, improves repeat-incident performance, and mentors six IT support engineers.\"\n    },\n    {\n      \"dates\": \"Mar 2019 – Aug 2022\",\n      \"evidence\": [\n        \"Approximately 3,000 employees supported\",\n        \"More than 7,500 devices and peripherals tracked\",\n        \"Manual provisioning reduced by 45%\"\n      ],\n      \"organization\": \"Horizon Retail Systems\",\n      \"role\": \"End User Computing Engineer\",\n      \"summary\": \"Supported corporate, retail, warehouse, and remote environments across endpoint management, Microsoft 365, identity, deployment, refresh, and hardware lifecycle operations.\"\n    },\n    {\n      \"dates\": \"Jul 2018 – Feb 2019\",\n      \"organization\": \"Summit Healthcare Technologies\",\n      \"role\": \"IT Support Specialist\",\n      \"summary\": \"Provided Level 1 and Level 2 support across corporate and clinical technology environments, including endpoint, account, application, connectivity, onboarding, inventory, and knowledge-base work.\"\n    }\n  ]\n}\n```\n\n### home:featured-work\n*Introduce the three detailed case studies and route visitors to them.*\n\n```json section-content\n{\n  \"heading\": \"Selected work\",\n  \"intro\": \"Three examples of improving endpoint management, security, and workplace platform operations.\",\n  \"projects\": [\n    {\n      \"href\": \"/work/workspace360\",\n      \"name\": \"WorkSpace360\",\n      \"summary\": \"A standardized endpoint management framework for a hybrid workforce, reducing new-device deployment from approximately 90 minutes to under 30 minutes.\",\n      \"technologies\": [\n        \"Microsoft Intune\",\n        \"Entra ID\",\n        \"PowerShell\",\n        \"Microsoft Graph\",\n        \"Power Automate\",\n        \"Windows 11\"\n      ]\n    },\n    {\n      \"href\": \"/work/secureendpoint\",\n      \"name\": \"SecureEndpoint\",\n      \"summary\": \"An endpoint compliance and security program that increased compliant managed endpoints from 81% to 97% within two quarters.\",\n      \"technologies\": [\n        \"Intune\",\n        \"Microsoft Defender\",\n        \"Entra ID\",\n        \"PowerShell\",\n        \"BitLocker\"\n      ]\n    },\n    {\n      \"href\": \"/work/employeeconnect\",\n      \"name\": \"EmployeeConnect\",\n      \"summary\": \"A Microsoft 365 migration supporting more than 2,800 employee accounts through automation, adoption support, training, and documentation.\",\n      \"technologies\": [\n        \"Microsoft 365\",\n        \"Exchange Online\",\n        \"Teams\",\n        \"OneDrive\",\n        \"SharePoint\",\n        \"PowerShell\"\n      ]\n    }\n  ]\n}\n```\n\n### home:credentials\n*Reinforce formal preparation and platform credibility.*\n\n```json section-content\n{\n  \"credentials\": [\n    \"Microsoft Certified: Endpoint Administrator Associate · 2024\",\n    \"ITIL 4 Foundation · 2022\",\n    \"Microsoft Certified: Azure Fundamentals · 2021\",\n    \"Bachelor of Science in Information Technology · University of Colorado Denver · 2014–2018\"\n  ],\n  \"heading\": \"Foundations for reliable service delivery.\",\n  \"languages\": [\n    \"English\",\n    \"French\"\n  ]\n}\n```\n\n### home:contact\n*Offer a safe, direct next step for recruiters and hiring teams.*\n\n```json section-content\n{\n  \"body\": \"For recruiter and hiring conversations involving end-user computing, endpoint engineering, Microsoft 365, or digital workplace operations, connect with Maya on LinkedIn.\",\n  \"cta\": {\n    \"href\": \"https://linkedin.com/in/mayabennett-it\",\n    \"label\": \"Connect on LinkedIn\"\n  },\n  \"heading\": \"Let's talk about endpoint engineering.\"\n}\n```\n\n## Route: /work/workspace360 (workspace360)\n\n*Purpose: Show how Maya designed a standardized endpoint management and device provisioning framework for a hybrid workforce.*\n\n### workspace360:overview\n*Summarize the project and its outcome.*\n\n```json section-content\n{\n  \"heading\": \"Making hybrid-workforce deployment more repeatable.\",\n  \"label\": \"Endpoint management and device provisioning\",\n  \"outcome\": \"New-device deployment moved from approximately 90 minutes to under 30 minutes.\",\n  \"summary\": \"WorkSpace360 standardized endpoint management for a hybrid workforce by bringing enrollment, security profiles, application assignment, compliance reporting, remediation, and self-service workflows into a more consistent operating model.\",\n  \"technologies\": [\n    \"Microsoft Intune\",\n    \"Entra ID\",\n    \"PowerShell\",\n    \"Microsoft Graph\",\n    \"Power Automate\",\n    \"Windows 11\"\n  ]\n}\n```\n\n### workspace360:challenge\n*Explain the operational problem the work addressed.*\n\n```json section-content\n{\n  \"body\": \"A hybrid workforce needs device enrollment, security configuration, application delivery, compliance visibility, and employee self-service to work together. WorkSpace360 addressed that need through a standardized endpoint management framework rather than disconnected setup activities.\",\n  \"heading\": \"The operating need\"\n}\n```\n\n### workspace360:approach\n*Describe Maya's specific contribution and decisions.*\n\n```json section-content\n{\n  \"heading\": \"The approach\",\n  \"steps\": [\n    {\n      \"text\": \"Designed automated enrollment workflows for managed Windows devices.\",\n      \"title\": \"Standardize enrollment\"\n    },\n    {\n      \"text\": \"Built security profiles and role-based application assignment so device configuration and software access could follow defined requirements.\",\n      \"title\": \"Connect policy and delivery\"\n    },\n    {\n      \"text\": \"Created PowerShell remediation scripts, compliance reporting, and self-service workflows to reduce repetitive intervention and improve visibility.\",\n      \"title\": \"Automate operations\"\n    }\n  ]\n}\n```\n\n### workspace360:outcome\n*Make the measurable project result easy to understand.*\n\n```json section-content\n{\n  \"body\": \"The resulting framework reduced new-device deployment time from approximately 90 minutes to under 30 minutes, giving the organization a faster and more repeatable path from enrollment to a usable employee device.\",\n  \"heading\": \"The result\",\n  \"metric\": \"Approximately 90 minutes → under 30 minutes\"\n}\n```\n\n### workspace360:technology\n*Document the technology context without overwhelming the story.*\n\n```json section-content\n{\n  \"heading\": \"Technology context\",\n  \"items\": [\n    \"Microsoft Intune\",\n    \"Entra ID\",\n    \"PowerShell\",\n    \"Microsoft Graph\",\n    \"Power Automate\",\n    \"Windows 11\"\n  ]\n}\n```\n\n## Route: /work/secureendpoint (secureendpoint)\n\n*Purpose: Explain Maya's contribution to an endpoint compliance and security program centered on policy, encryption, patch visibility, and remediation.*\n\n### secureendpoint:overview\n*Summarize the security program and measurable outcome.*\n\n```json section-content\n{\n  \"heading\": \"Turning endpoint policy into visible compliance.\",\n  \"label\": \"Endpoint compliance and security\",\n  \"outcome\": \"Compliant managed endpoints increased from 81% to 97% within two quarters.\",\n  \"summary\": \"SecureEndpoint brought Windows security policies, encryption enforcement, compliance policies, patch visibility, and remediation workflows into a coordinated endpoint security program.\",\n  \"technologies\": [\n    \"Intune\",\n    \"Microsoft Defender\",\n    \"Entra ID\",\n    \"PowerShell\",\n    \"BitLocker\"\n  ]\n}\n```\n\n### secureendpoint:challenge\n*Explain the security and visibility need.*\n\n```json section-content\n{\n  \"body\": \"Managed endpoints need more than policy definitions: teams also need encryption enforcement, compliance visibility, patch awareness, and a practical path to remediate gaps. SecureEndpoint focused on connecting those operating needs.\",\n  \"heading\": \"The operating need\"\n}\n```\n\n### secureendpoint:approach\n*Describe the implementation work and collaboration.*\n\n```json section-content\n{\n  \"heading\": \"The approach\",\n  \"steps\": [\n    {\n      \"text\": \"Standardized Windows security policies and automated BitLocker enforcement.\",\n      \"title\": \"Standardize controls\"\n    },\n    {\n      \"text\": \"Implemented compliance policies and improved patch visibility across managed endpoints.\",\n      \"title\": \"Improve visibility\"\n    },\n    {\n      \"text\": \"Built remediation workflows and collaborated with security teams to address endpoint compliance needs.\",\n      \"title\": \"Create remediation paths\"\n    }\n  ]\n}\n```\n\n### secureendpoint:outcome\n*Present the program-level result accurately.*\n\n```json section-content\n{\n  \"body\": \"SecureEndpoint increased compliant managed endpoints from 81% to 97% within two quarters. The outcome reflects a coordinated program of policy, enforcement, visibility, and remediation work.\",\n  \"heading\": \"The result\",\n  \"metric\": \"81% → 97% compliant managed endpoints\"\n}\n```\n\n### secureendpoint:technology\n*Document the technical foundation.*\n\n```json section-content\n{\n  \"heading\": \"Technology context\",\n  \"items\": [\n    \"Intune\",\n    \"Microsoft Defender\",\n    \"Entra ID\",\n    \"PowerShell\",\n    \"BitLocker\"\n  ]\n}\n```\n\n## Route: /work/employeeconnect (employeeconnect)\n\n*Purpose: Present Maya's role in a Microsoft 365 migration involving account migration, automation, adoption support, and documentation.*\n\n### employeeconnect:overview\n*Summarize the migration and its people-centered scope.*\n\n```json section-content\n{\n  \"heading\": \"Supporting platform change at employee scale.\",\n  \"label\": \"Microsoft 365 migration\",\n  \"outcome\": \"The migration supported more than 2,800 employee accounts.\",\n  \"summary\": \"EmployeeConnect supported a Microsoft 365 migration from legacy collaboration platforms, combining account and license automation with communication, training, adoption support, and troubleshooting documentation.\",\n  \"technologies\": [\n    \"Microsoft 365\",\n    \"Exchange Online\",\n    \"Teams\",\n    \"OneDrive\",\n    \"SharePoint\",\n    \"PowerShell\"\n  ]\n}\n```\n\n### employeeconnect:challenge\n*Explain why migration required both technical and adoption work.*\n\n```json section-content\n{\n  \"body\": \"A collaboration-platform migration affects accounts, licenses, workflows, communication, and day-to-day employee habits. EmployeeConnect addressed the technical transition while supporting adoption through communication, training, and practical troubleshooting material.\",\n  \"heading\": \"The operating need\"\n}\n```\n\n### employeeconnect:approach\n*Describe Maya's technical and enablement contribution.*\n\n```json section-content\n{\n  \"heading\": \"The approach\",\n  \"steps\": [\n    {\n      \"text\": \"Automated account and license assignment to support a more consistent migration process.\",\n      \"title\": \"Automate administration\"\n    },\n    {\n      \"text\": \"Developed communication and training materials and supported employees through the platform change.\",\n      \"title\": \"Support adoption\"\n    },\n    {\n      \"text\": \"Created troubleshooting documentation to help users and support teams handle recurring questions.\",\n      \"title\": \"Document the path forward\"\n    }\n  ]\n}\n```\n\n### employeeconnect:outcome\n*Present the migration scale and outcome without overstating individual ownership.*\n\n```json section-content\n{\n  \"body\": \"EmployeeConnect supported migration for more than 2,800 employee accounts. The work paired administrative automation with communication, training, adoption support, and documentation so the technical change had an operational support layer.\",\n  \"heading\": \"The result\",\n  \"metric\": \"2,800+ employee accounts supported\"\n}\n```\n\n### employeeconnect:technology\n*Document the platform context.*\n\n```json section-content\n{\n  \"heading\": \"Technology context\",\n  \"items\": [\n    \"Microsoft 365\",\n    \"Exchange Online\",\n    \"Teams\",\n    \"OneDrive\",\n    \"SharePoint\",\n    \"PowerShell\"\n  ]\n}\n```\n\n## Approved claims\n\n- **claim:current_scale:** Leads enterprise end-user computing services for more than 4,500 employees across India, North America, and Europe.\n- **claim:workspace360_speed:** WorkSpace360 reduced new-device deployment time from approximately 90 minutes to under 30 minutes.\n- **claim:workspace360_contribution:** Designed enrollment workflows, security profiles, PowerShell remediation scripts, role-based application assignment, compliance reporting, and self-service workflows for WorkSpace360.\n- **claim:secureendpoint_compliance:** SecureEndpoint increased compliant managed endpoints from 81% to 97% within two quarters.\n- **claim:secureendpoint_contribution:** Standardized Windows security policies, automated BitLocker enforcement, implemented compliance policies, improved patch visibility, created remediation workflows, and collaborated with security teams.\n- **claim:employeeconnect_scale:** EmployeeConnect supported migration of more than 2,800 employee accounts.\n- **claim:employeeconnect_contribution:** Automated account and license assignment, developed communication and training materials, supported adoption, and created troubleshooting documentation for EmployeeConnect.\n- **claim:bluepeak_apps:** Automated deployment and update processes for more than 180 business applications.\n- **claim:bluepeak_incidents:** Reduced repeat incidents by 39% through root-cause analysis and knowledge improvements.\n- **claim:bluepeak_mentoring:** Mentors six IT support engineers.\n- **claim:horizon_scope:** Supported approximately 3,000 employees and maintained asset records covering more than 7,500 devices and peripherals at Horizon Retail Systems.\n- **claim:horizon_provisioning:** Reduced manual provisioning activities by 45% at Horizon Retail Systems.\n- **claim:certifications:** Holds Microsoft Certified: Endpoint Administrator Associate, ITIL 4 Foundation, and Microsoft Certified: Azure Fundamentals credentials.\n\n## Never fabricate / privacy\n\n- Metrics, employers, dates, awards, testimonials, project links, media, client names, ownership, outcomes, or technical details not present in the approved source.\n\n## SEO (Build Preparation suggestion, not approved copy)\n\n- **/:** Professional portfolio for Maya Bennett, an End User Computing and Endpoint Engineering specialist showcasing endpoint, automation, compliance, and workplace technology work.\n- **/work/workspace360:** WorkSpace360 case study showing Maya Bennett's standardized endpoint management and device provisioning framework for a hybrid workforce.\n- **/work/secureendpoint:** SecureEndpoint case study covering Maya Bennett's contribution to endpoint policy, encryption, compliance visibility, and remediation.\n- **/work/employeeconnect:** EmployeeConnect case study presenting Maya Bennett's role in Microsoft 365 migration, account automation, adoption support, and documentation.\n",
  "recommended_dependencies": []
}