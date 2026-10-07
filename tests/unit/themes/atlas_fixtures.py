"""Atlas-aware ``page_content`` shapes for the scripted portfolio themes.

Each builder returns a fresh, admission-valid content tree (shared tree + ``atlas``
supplement). ``stress`` sits at the hard limits of ``code_generator/admission.py`` and
mixes scripts and markup-looking text, so layout and validation are exercised at their
worst. Run ``python -m tests.unit.themes.atlas_fixtures <dir>`` to export them as JSON for
``python -m oryxenai.agents.code_generator.cli render --content <file>``.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any


def _section(eyebrow: str, heading: str, intro: str = "", **extra: Any) -> dict[str, Any]:
    return {"eyebrow": eyebrow, "heading": heading, "intro": intro, **extra}


def _hero(**fields: str) -> dict[str, Any]:
    base = {
        "name": "",
        "eyebrow_primary": "",
        "eyebrow_secondary": "",
        "headline_prefix": "",
        "headline_emphasis": "",
        "intro": "",
        "location": "",
        "primary_cta_label": "",
        "secondary_cta_label": "",
    }
    base.update(fields)
    return base


def _pillars(*pairs: tuple[str, str]) -> list[dict[str, str]]:
    return [{"title": title, "description": description} for title, description in pairs]


def _project(**fields: str) -> dict[str, str]:
    base = {
        "kind": "real",
        "title": "",
        "summary": "",
        "role": "",
        "period": "",
        "problem": "",
        "approach": "",
        "outcome": "",
        "external_url": "",
    }
    base.update(fields)
    return base


def designer() -> dict[str, Any]:
    """Three full case studies, statistics, a timeline, a quote; no photo."""
    return {
        "hero": _hero(
            name="Maya Kapoor",
            eyebrow_primary="Product Designer",
            eyebrow_secondary="Healthcare · Fintech",
            headline_prefix="Designing calm software for",
            headline_emphasis="complicated work",
            intro=(
                "Maya is a product designer who turns tangled, high-stakes workflows into calm, "
                "usable software. For eight years she has worked with clinical, financial and "
                "logistics teams to find the real problem first, then design the smallest thing "
                "that solves it."
            ),
            location="Zürich, Switzerland",
        ),
        "metadata": {
            "title": "Maya Kapoor — Product Designer",
            "description": (
                "Maya Kapoor designs calm, usable software for clinical, financial and logistics "
                "teams. Selected work, experience and contact."
            ),
        },
        "marquee_keywords": [
            "Product strategy",
            "Design systems",
            "Interaction design",
            "User research",
            "Prototyping",
            "Accessibility",
            "Service design",
            "Workshop facilitation",
        ],
        "systems_practice": _section(
            "How I work",
            "Clarity first, then craft — in that order.",
            "A short loop of listening, testing and simplifying, repeated until the work is obvious.",
            pillars=_pillars(
                (
                    "Find the real problem",
                    "Interviews, shadowing and data before any pixels, so the team agrees what is broken.",
                ),
                (
                    "Design the smallest thing",
                    "Prototype early, test with real users and ship the simplest version that works.",
                ),
                (
                    "Make it a system",
                    "Reusable patterns and clear documentation so the next ten screens take a day.",
                ),
                (
                    "Stay for the outcome",
                    "Work with engineers through launch and measure whether the change helped people.",
                ),
            ),
        ),
        "technical_capabilities": _section(
            "Toolkit",
            "Methods and tools",
            "",
            groups=[
                {
                    "heading": "Research",
                    "items": [
                        "User interviews",
                        "Contextual inquiry",
                        "Usability testing",
                        "Survey design",
                        "Analytics review",
                    ],
                },
                {
                    "heading": "Design",
                    "items": [
                        "Interaction design",
                        "Design systems",
                        "Prototyping",
                        "Information architecture",
                        "Accessibility (WCAG 2.2)",
                        "Visual design",
                    ],
                },
                {
                    "heading": "Delivery",
                    "items": ["Figma", "Design tokens", "Component specs", "Developer handoff"],
                },
                {
                    "heading": "Leadership",
                    "items": [
                        "Workshop facilitation",
                        "Design critique",
                        "Mentoring",
                        "Roadmapping",
                    ],
                },
            ],
        ),
        "professional_context": _section(
            "Background",
            "Teams I have worked with",
            "",
            organizations=[
                "Helvetia Health",
                "Northwind Pay",
                "Atlas Labs",
                "Studio Mono",
                "Kestrel Mobility",
            ],
        ),
        "connect": _section(
            "Say hello",
            "Let's make something clear.",
            "Open to a small number of product and design-systems engagements each year.",
            destinations=[
                {"label": "Email", "url": "mailto:maya@example.com", "featured": True},
                {
                    "label": "LinkedIn",
                    "url": "https://linkedin.com/in/example-maya",
                    "featured": True,
                },
                {"label": "Case studies", "url": "https://example.com/maya", "featured": False},
            ],
        ),
        "atlas": {
            "about_heading": "A designer who listens before drawing.",
            "about_intro": (
                "Maya grew up between Mumbai and Zürich and still notices how differently people "
                "read the same screen. She leads design for clinical software, mentors a small "
                "team, and keeps one day a week for research with the people who use her work."
            ),
            "about_quote": (
                "Good design feels obvious only after someone has done the hard thinking."
            ),
            "experience": [
                {
                    "dates": "2022 — Present",
                    "role": "Senior Product Designer",
                    "organization": "Helvetia Health",
                    "description": (
                        "Leads design for the clinician dashboard used across sixty hospitals."
                    ),
                    "kind": "real",
                },
                {
                    "dates": "2019 — 2022",
                    "role": "Product Designer",
                    "organization": "Northwind Pay",
                    "description": "Designed merchant onboarding and the first shared design system.",
                    "kind": "real",
                },
                {
                    "dates": "2016 — 2019",
                    "role": "UX Designer",
                    "organization": "Atlas Labs",
                    "description": "Shipped research-led improvements to a logistics planning tool.",
                    "kind": "real",
                },
            ],
            "education": [
                {
                    "credential": "MA Interaction Design",
                    "institution": "ZHdK, Zürich",
                    "dates": "2014 — 2016",
                    "kind": "real",
                }
            ],
            "statistics": [
                {"value": "8+", "label": "Years designing products", "kind": "real"},
                {"value": "14", "label": "Products shipped", "kind": "real"},
                {"value": "-34%", "label": "Charting time at Helvetia Health", "kind": "real"},
            ],
            "projects": [
                _project(
                    title="Clinician dashboard",
                    summary="A calmer home screen for nurses working across dozens of patients.",
                    role="Lead designer",
                    period="2023",
                    problem=(
                        "Nurses lost minutes per patient switching between four screens to find the "
                        "next task, and critical alerts were buried among routine notices."
                    ),
                    approach=(
                        "We shadowed eighteen nurses across three hospitals, mapped the real handoff "
                        "moments and rebuilt the dashboard around one prioritised queue with clear "
                        "alert tiers, prototyping and testing every change on the ward."
                    ),
                    outcome=(
                        "Charting time fell by a third and alert response improved in all three "
                        "pilot hospitals."
                    ),
                ),
                _project(
                    title="Merchant onboarding",
                    summary="A guided setup that took small merchants from signup to first payment.",
                    role="Product designer",
                    period="2021",
                    problem=(
                        "Small merchants abandoned onboarding when asked for documents they did not "
                        "have to hand."
                    ),
                    approach=(
                        "We split the flow into saveable steps, explained why each document mattered "
                        "and let merchants take payments before verification finished."
                    ),
                    outcome="Completed signups rose sharply within the first quarter.",
                ),
                _project(
                    title="Shared design system",
                    summary="One component library for four product teams.",
                    role="Design systems lead",
                    period="2020",
                    problem="Four teams shipped four slightly different buttons, forms and tables.",
                    approach=(
                        "We audited every pattern, agreed the smallest useful set and documented "
                        "usage with live examples and accessibility notes."
                    ),
                ),
            ],
        },
    }


def engineer() -> dict[str, Any]:
    """Four statistics, a link-only project (so case ids are not contiguous), long groups."""
    content = designer()
    content["hero"] = _hero(
        name="Arjun Mehta",
        eyebrow_primary="Staff Platform Engineer",
        eyebrow_secondary="Distributed systems · Data infrastructure",
        headline_prefix="Building infrastructure that stays",
        headline_emphasis="boring under load",
        intro=(
            "Arjun designs the unglamorous systems other teams quietly depend on: schedulers, "
            "stream processors and the guardrails around them. He has taken services from a "
            "handful of requests a second to billions of events a day without a pager storm."
        ),
        location="Bengaluru, India · Remote",
    )
    content["metadata"] = {
        "title": "Arjun Mehta — Staff Platform Engineer",
        "description": (
            "Arjun Mehta builds reliable distributed systems and data infrastructure. Selected "
            "work, experience and ways to get in touch."
        ),
    }
    content["marquee_keywords"] = [
        "Distributed systems",
        "Kubernetes",
        "Go",
        "Rust",
        "Kafka",
        "Postgres",
        "Observability",
        "SRE",
        "Terraform",
        "gRPC",
        "Python",
        "Capacity planning",
    ]
    content["systems_practice"] = _section(
        "Engineering practice",
        "Reliability is a feature you design on day one.",
        "Small blast radius, honest dashboards and boring technology wherever it will do.",
        pillars=_pillars(
            (
                "Design for failure",
                "Assume every dependency fails; make the failure cheap and visible.",
            ),
            ("Measure before tuning", "Profile in production, fix the biggest cost, repeat."),
            (
                "Automate the toil",
                "If a human does it twice, the platform should do it the third time.",
            ),
            (
                "Leave it teachable",
                "Runbooks, diagrams and reviews so the system outlives its authors.",
            ),
        ),
    )
    content["technical_capabilities"] = _section(
        "Toolkit",
        "Languages, platforms and practices",
        "",
        groups=[
            {
                "heading": "Languages",
                "items": ["Go", "Rust", "Python", "TypeScript", "SQL", "C++", "Bash", "Java"],
            },
            {
                "heading": "Data",
                "items": [
                    "Kafka",
                    "Postgres",
                    "ClickHouse",
                    "Redis",
                    "Flink",
                    "Debezium",
                    "Iceberg",
                ],
            },
            {
                "heading": "Infrastructure",
                "items": ["Kubernetes", "Terraform", "AWS", "GCP", "Envoy", "Linkerd", "Argo CD"],
            },
            {
                "heading": "Reliability",
                "items": [
                    "SLOs",
                    "Incident response",
                    "Chaos testing",
                    "Capacity planning",
                    "OpenTelemetry",
                ],
            },
            {
                "heading": "Leadership",
                "items": ["Design reviews", "Mentoring", "Hiring", "Roadmapping"],
            },
        ],
    )
    content["professional_context"] = _section(
        "Background",
        "Where the systems ran",
        "",
        organizations=[
            "Meridian Cloud",
            "Quanta Pay",
            "Larkspur Data",
            "Orbit Logistics",
            "Tessellate",
            "Northstar Labs",
        ],
    )
    content["connect"] = _section(
        "Get in touch",
        "Have a system that keeps you up at night?",
        "Available for architecture reviews and a limited number of advisory engagements.",
        destinations=[
            {"label": "Email", "url": "mailto:arjun@example.com", "featured": True},
            {"label": "GitHub", "url": "https://github.com/example-arjun", "featured": True},
            {"label": "Talks and writing", "url": "https://example.com/arjun", "featured": False},
        ],
    )
    atlas = content["atlas"]
    atlas["about_heading"] = "An engineer who writes the runbook first."
    atlas["about_intro"] = (
        "Arjun has spent twelve years on call for other people's ambitions. He now leads a "
        "platform group of fourteen engineers, reviews designs for half the company, and writes "
        "long, careful post-incident notes that people actually read."
    )
    atlas["about_quote"] = ""
    atlas["experience"] = [
        {
            "dates": "2021 — Present",
            "role": "Staff Platform Engineer",
            "organization": "Meridian Cloud",
            "description": "Leads the scheduler and event-bus teams serving 120 internal services.",
            "kind": "real",
        },
        {
            "dates": "2018 — 2021",
            "role": "Senior Engineer",
            "organization": "Quanta Pay",
            "description": "Rebuilt the ledger pipeline for exactly-once settlement.",
            "kind": "real",
        },
        {
            "dates": "2015 — 2018",
            "role": "Software Engineer",
            "organization": "Larkspur Data",
            "description": "Built ingestion and monitoring for a multi-tenant analytics platform.",
            "kind": "real",
        },
        {
            "dates": "2012 — 2015",
            "role": "Associate Engineer",
            "organization": "Orbit Logistics",
            "description": "Maintained routing services and automated their deployments.",
            "kind": "real",
        },
    ]
    atlas["education"] = [
        {
            "credential": "B.Tech Computer Science",
            "institution": "IIT Delhi",
            "dates": "2008 — 2012",
            "kind": "real",
        },
        {
            "credential": "Distributed Systems Certificate",
            "institution": "Self-directed",
            "dates": "2017",
            "kind": "real",
        },
    ]
    atlas["statistics"] = [
        {"value": "99.98%", "label": "Availability across 120 services", "kind": "real"},
        {"value": "1.2B", "label": "Events processed every day", "kind": "real"},
        {"value": "-42%", "label": "p99 latency after the scheduler rewrite", "kind": "real"},
        {"value": "$2.1M", "label": "Annual infrastructure savings", "kind": "real"},
    ]
    atlas["projects"] = [
        _project(
            title="Event bus rewrite",
            summary="Replaced a brittle queue with a partitioned, replayable event bus.",
            role="Tech lead",
            period="2022 — 2023",
            problem=(
                "The legacy queue dropped messages during failovers and could not replay history, "
                "so every incident ended in a manual reconciliation."
            ),
            approach=(
                "We moved to a partitioned log with idempotent consumers, shadowed production "
                "traffic for six weeks and migrated services one team at a time."
            ),
            outcome="Zero dropped messages across the migration and failover drills.",
        ),
        _project(
            title="Capacity planner",
            summary="An open forecasting tool for stateful services.",
            role="Author",
            period="2020",
            external_url="https://github.com/example-arjun/capacity-planner",
        ),
        _project(
            title="Postgres failover runbook",
            summary="A tested, rehearsed procedure that turned failovers into non-events.",
            role="Author",
            period="2019",
            problem="Failovers depended on one engineer remembering the right command order.",
            approach="We scripted every step, rehearsed it quarterly and measured each drill.",
        ),
    ]
    return content


def chef() -> dict[str, Any]:
    """Non-technical vocabulary, one project, no statistics/organizations/ticker."""
    return {
        "hero": _hero(
            name="Lucia Marchetti",
            eyebrow_primary="Executive Chef",
            headline_prefix="Seasonal cooking with",
            headline_emphasis="quiet confidence",
            intro=(
                "Lucia runs kitchens that cook what the market offers that week. She trains "
                "young cooks, writes short menus, and believes a plate should taste of one "
                "place and one season."
            ),
            location="Bologna, Italy",
        ),
        "metadata": {
            "title": "Lucia Marchetti — Executive Chef",
            "description": (
                "Lucia Marchetti is an executive chef cooking seasonal Emilian food. Menus, "
                "experience and bookings."
            ),
        },
        "marquee_keywords": [],
        "systems_practice": _section(
            "Kitchen philosophy",
            "Cook the week, not the calendar.",
            "",
            pillars=_pillars(
                ("Start at the market", "Menus are written after the producers, never before."),
                (
                    "Waste nothing",
                    "Every trim has a second life as a broth, a sauce or staff meal.",
                ),
                ("Teach the line", "A kitchen is only as good as its youngest cook is trained."),
                ("Keep it short", "Five dishes done well beat fifteen done quickly."),
            ),
        ),
        "technical_capabilities": _section(
            "Craft",
            "What the kitchen does best",
            "",
            groups=[
                {
                    "heading": "Cuisine",
                    "items": ["Emilian classics", "Fresh pasta", "Wood-fire cooking"],
                },
                {"heading": "Kitchen", "items": ["Menu design", "Costing", "Team training"]},
            ],
        ),
        "professional_context": _section("Background", "Kitchens", "", organizations=[]),
        "connect": _section(
            "Reservations",
            "Come hungry.",
            "Dinner service Tuesday to Saturday; private dining on request.",
            destinations=[
                {"label": "Book a table", "url": "mailto:tavola@example.com", "featured": True},
                {
                    "label": "Instagram",
                    "url": "https://instagram.com/example-lucia",
                    "featured": False,
                },
            ],
        ),
        "atlas": {
            "about_heading": "Born in a pasta kitchen, still learning in one.",
            "about_intro": (
                "Lucia learned to roll pasta at her grandmother's table and has cooked in "
                "Bologna, Lyon and Copenhagen since. Today she leads a small team and a short, "
                "changing menu."
            ),
            "about_quote": "",
            "experience": [
                {
                    "dates": "2019 — Present",
                    "role": "Executive Chef",
                    "organization": "Osteria del Mercato",
                    "description": "Leads a team of nine and a menu that changes every week.",
                    "kind": "real",
                },
                {
                    "dates": "2013 — 2019",
                    "role": "Sous Chef",
                    "organization": "Trattoria Alba",
                    "description": "Ran the pasta section and trained new cooks.",
                    "kind": "real",
                },
            ],
            "education": [
                {
                    "credential": "Diploma in Culinary Arts",
                    "institution": "ALMA, Colorno",
                    "dates": "2011 — 2013",
                    "kind": "real",
                }
            ],
            "statistics": [],
            "projects": [
                _project(
                    title="The weekly menu",
                    summary="Five dishes, written every Monday from what the market brought.",
                    role="Chef and author",
                    period="2020 — Present",
                    problem=(
                        "A long fixed menu meant waste, tired cooks and food that did not taste of "
                        "the season."
                    ),
                    approach=(
                        "We replaced it with a short weekly menu built after visiting the "
                        "producers, with costing and prep planned the same morning."
                    ),
                )
            ],
        },
    }


def sparse_samples() -> dict[str, Any]:
    """Thin input: sample rows plus one illustrative project (labels must render)."""
    return {
        "hero": _hero(
            name="Sam Lee",
            eyebrow_primary="Backend Engineer",
            headline_prefix="Building careful software.",
            intro="Sam builds careful software and is looking for a first backend role.",
        ),
        "metadata": {"title": "Sam Lee", "description": "Sam Lee builds careful software."},
        "marquee_keywords": ["Python", "Go"],
        "systems_practice": _section(
            "Focus",
            "Careful, tested software.",
            "",
            pillars=_pillars(
                ("Testing", "Write the test first."),
                ("Clarity", "Small functions with honest names."),
                ("Learning", "Read the source."),
                ("Teamwork", "Review kindly."),
            ),
        ),
        "technical_capabilities": _section(
            "Toolkit", "Languages", "", groups=[{"heading": "Languages", "items": ["Python"]}]
        ),
        "professional_context": _section("Background", "Background", "", organizations=[]),
        "connect": _section("Connect", "Say hello", "", destinations=[]),
        "atlas": {
            "about_heading": "Starting out.",
            "about_intro": "Sam is finishing a degree and building small projects in the open.",
            "about_quote": "",
            "experience": [
                {
                    "dates": "Summer 2025",
                    "role": "Backend Intern",
                    "organization": "A technology team",
                    "description": "Built and tested small internal services.",
                    "kind": "sample",
                }
            ],
            "education": [
                {
                    "credential": "Degree",
                    "institution": "A university",
                    "dates": "2022 — 2026",
                    "kind": "sample",
                }
            ],
            "statistics": [
                {"value": "3", "label": "Projects built", "kind": "sample"},
                {"value": "2", "label": "Languages used", "kind": "sample"},
                {"value": "1", "label": "Internship", "kind": "sample"},
            ],
            "projects": [
                _project(
                    kind="illustrative",
                    title="A small ledger service",
                    summary="A hypothetical service that records transfers reliably.",
                    problem="Transfers must never be lost or applied twice.",
                    approach="Idempotency keys and an append-only log.",
                )
            ],
        },
    }


def _fit(text: str, limit: int) -> str:
    """Repeat ``text`` and trim so it ends exactly at ``limit`` characters."""
    repeated = (text + " ") * (limit // max(len(text), 1) + 2)
    return repeated[:limit].rstrip() if len(repeated.rstrip()) > limit else repeated.rstrip()


def stress() -> dict[str, Any]:
    """Hard maxima, mixed scripts, markup-looking text and unbreakable strings."""
    word = "Supercalifragilisticexpialidocious-"
    name = "Alexandrina Wilhelmina Konstantinopolitanisch-Papadopoulos de la Fuente y Montenegro"
    long_item = "Kubernetes-native event-driven multi-region active-active replication"
    projects = [
        _project(
            title=_fit("A very long project title that keeps going", 160),
            summary=_fit("A summary sentence that is intentionally long.", 600),
            role="Lead",
            period="2020 — 2024",
            problem=_fit("The problem statement runs long.", 1400),
            approach=_fit("The approach explains every step in detail.", 1400),
            outcome=_fit("The outcome is measured and repeated.", 700),
        ),
        _project(
            title="Tom & Jerry <Dev> \"Q\" 'x' 東京 שלום 🚀",
            summary='Links and symbols: <b>bold</b> & "quotes" — it\'s 100% fine.',
            role="Author",
            period="2019",
            external_url="https://example.com/" + "a" * 400,
        ),
        _project(
            title="Third project",
            summary="Short.",
            problem="One line.",
            approach="Another line.",
        ),
    ]
    experience = [
        {
            "dates": f"20{10 + index} — 20{11 + index}",
            "role": _fit(f"Role number {index} with a long descriptive title", 120),
            "organization": _fit(f"Organization {index} International Holdings", 100),
            "description": _fit(f"Description {index} of the responsibilities held.", 600),
            "kind": "real",
        }
        for index in range(12)
    ]
    groups = [
        {
            "heading": _fit(f"Group {index} heading", 120),
            "items": [long_item[: 40 + (item % 80)] + f" {item}" for item in range(30)],
        }
        for index in range(8)
    ]
    return {
        "hero": _hero(
            name=name[:120],
            eyebrow_primary=_fit("Principal Staff Distinguished Engineer", 120),
            eyebrow_secondary=_fit("Everything, everywhere, all at once", 120),
            headline_prefix=_fit(
                "A headline that never seems to finish and refuses to wrap nicely", 220
            ),
            headline_emphasis=_fit("until you are done", 160),
            intro=_fit("An introduction sentence that fills the available space.", 1400),
            location=_fit("Llanfairpwllgwyngyllgogerychwyrndrobwllllantysiliogogogoch", 120),
        ),
        "metadata": {
            "title": _fit("Alexandrina Konstantinopolitanisch-Papadopoulos — Portfolio", 160),
            "description": _fit("A description that is as long as the template allows.", 420),
        },
        "marquee_keywords": [
            (word * 2)[:60] if index % 4 == 0 else f"Keyword {index}" for index in range(20)
        ],
        "systems_practice": _section(
            _fit("Practice", 60),
            _fit("A heading that is the longest one the template accepts", 220),
            _fit("An intro paragraph for the practice section.", 900),
            pillars=_pillars(
                *[
                    (_fit(f"Pillar {n} title", 120), _fit(f"Pillar {n} description text.", 420))
                    for n in range(4)
                ]
            ),
        ),
        "technical_capabilities": _section(
            _fit("Toolkit", 60),
            _fit("Capabilities heading at the limit", 220),
            _fit("Capabilities intro at the limit.", 900),
            groups=[{**group, "items": group["items"][:30]} for group in groups],
        ),
        "professional_context": _section(
            _fit("Background", 60),
            _fit("Where the work happened", 220),
            _fit("Context intro.", 900),
            organizations=[_fit(f"Organization {n} Group Holdings", 160) for n in range(30)],
        ),
        "connect": _section(
            _fit("Connect", 60),
            _fit("Let us talk about the work", 220),
            _fit("Connect intro.", 900),
            destinations=[
                {
                    "label": _fit(f"Destination {n}", 80),
                    "url": "https://example.com/" + "x" * 300 + f"/{n}?a=1&b=2",
                    "featured": n < 2,
                }
                for n in range(11)
            ]
            + [{"label": "Email", "url": "mailto:someone@example.com", "featured": False}],
        ),
        "atlas": {
            "about_heading": _fit("An about heading at the limit", 160),
            "about_intro": _fit("An about paragraph with plenty of words.", 1400),
            "about_quote": _fit("A quote that is long.", 500),
            "experience": experience,
            "education": [
                {
                    "credential": _fit(f"Credential {n}", 120),
                    "institution": _fit(f"Institution {n} of Higher Learning", 120),
                    "dates": f"199{n} — 199{n + 1}",
                    "kind": "real",
                }
                for n in range(8)
            ],
            "statistics": [
                {
                    "value": "1,234,567.89%",
                    "label": _fit("A long statistic label", 100),
                    "kind": "real",
                },
                {"value": "∞", "label": "Unbounded", "kind": "real"},
                {"value": chr(0x2212) + "42 ms", "label": "p99", "kind": "real"},
                {"value": "$9.9B", "label": "Moved", "kind": "real"},
            ],
            "projects": projects,
        },
    }


FIXTURES: dict[str, Callable[[], dict[str, Any]]] = {
    "designer": designer,
    "engineer": engineer,
    "chef": chef,
    "sparse_samples": sparse_samples,
    "stress": stress,
}
# Fixtures that need the illustrative-work opt-in to be admitted.
ALLOW_ILLUSTRATIVE = frozenset({"sparse_samples"})


def export(directory: Path) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, build in FIXTURES.items():
        target = directory / f"{name}.json"
        target.write_text(json.dumps(build(), ensure_ascii=False, indent=1), encoding="utf-8")
        written.append(target)
    return written


if __name__ == "__main__":
    for path in export(Path(sys.argv[1])):
        print(path)
