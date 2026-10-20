"""Development-only migration of pinned Jinja markup to editable React components.

Never runs in a delivery job. Unsupported template syntax fails closed. The
generated TSX is committed, type checked and compared against the host renderer.
Theme scripts are deliberately not copied; interactions live in React hooks.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

from jinja2 import Environment, nodes

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "react-delivery/src/themes"
THEMES = {
    "EditorialForest": "editorial_forest/v1",
    "CobaltClassic": "cobalt_atlas/v1",
    "ObsidianSignal": "obsidian_signal/v1",
    "CobaltAtlas": "cobalt_atlas/v2",
    "ClaretMarquee": "claret_marquee/v1",
}


def expression(source: str) -> str:
    node = Environment(autoescape=True).parse("{{ " + source + " }}").body[0].nodes[0]
    return emit_expression(node)


def emit_expression(node: nodes.Node) -> str:
    e = emit_expression
    if isinstance(node, nodes.Name):
        return "isCase" if node.name == "case" else node.name
    if isinstance(node, nodes.Const):
        return json.dumps(node.value, ensure_ascii=False)
    if isinstance(node, nodes.Getattr):
        return f"{e(node.node)}.{node.attr}"
    if isinstance(node, nodes.Getitem):
        if isinstance(node.arg, nodes.Slice):
            return f"{e(node.node)}.slice({e(node.arg.start) if node.arg.start else 0})"
        return f"{e(node.node)}[{e(node.arg)}]"
    if isinstance(node, nodes.And):
        return f"(truthy({e(node.left)}) ? {e(node.right)} : {e(node.left)})"
    if isinstance(node, nodes.Or):
        return f"(truthy({e(node.left)}) ? {e(node.left)} : {e(node.right)})"
    if isinstance(node, nodes.Not):
        return f"!truthy({e(node.node)})"
    if isinstance(node, nodes.CondExpr):
        return f"(truthy({e(node.test)}) ? {e(node.expr1)} : {e(node.expr2)})"
    if isinstance(node, nodes.BinExpr):
        operator = {nodes.Add: "+", nodes.Sub: "-", nodes.Mod: "%"}[type(node)]
        return f"({e(node.left)} {operator} {e(node.right)})"
    if isinstance(node, nodes.Compare):
        operators = {"eq": "===", "ne": "!==", "gt": ">", "lt": "<", "gteq": ">=", "lteq": "<="}
        return (
            "("
            + e(node.expr)
            + " "
            + " ".join(operators[item.op] + " " + e(item.expr) for item in node.ops)
            + ")"
        )
    if isinstance(node, nodes.Call):
        function = e(node.node).replace(".startswith", ".startsWith")
        return f"{function}({', '.join(e(item) for item in node.args)})"
    if isinstance(node, nodes.Filter):
        value = e(node.node)
        if node.name == "length":
            return f"{value}.length"
        if node.name == "join":
            return f"{value}.join({e(node.args[0])})"
        if node.name == "default":
            return f"({value} ?? {e(node.args[0])})"
    if isinstance(node, nodes.Dict):
        return (
            "{}"
            if not node.items
            else "{" + ",".join(e(item.key) + ":" + e(item.value) for item in node.items) + "}"
        )
    if isinstance(node, nodes.List):
        return "[" + ",".join(e(item) for item in node.items) + "]"
    raise ValueError(f"Unsupported expression: {node!r}")


@dataclass
class Element:
    tag: str
    attrs: list[tuple[str, str | None]] = field(default_factory=list)
    children: list[Element | str] = field(default_factory=list)


class Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Element("root")
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Element(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in {"img", "br", "hr", "input", "r-set"}:
            self.stack.append(node)

    def handle_endtag(self, tag: str) -> None:
        if self.stack[-1].tag != tag:
            raise ValueError(
                f"Unbalanced migration markup at {self.getpos()}: {tag}, {self.stack[-1].tag}"
            )
        self.stack.pop()

    def handle_data(self, data: str) -> None:
        self.stack[-1].children.append(data)


class Compiler:
    def __init__(self) -> None:
        self.expressions: list[str] = []
        self.blocks: list[str] = []
        self.spreads: list[str] = []

    def token(self, expr: str) -> str:
        self.expressions.append(expression(expr))
        return f"EXPR{len(self.expressions) - 1}TOKEN"

    def compile(self, source: str) -> str:
        # Both interactive themes use a conditional opening/closing project tag.
        source = re.sub(
            r"{% if case %}<a class=\"([^\"]+)\".*?{% endif %}",
            lambda m: (
                '<project-link class="'
                + m[1]
                + '" project="{{ project }}" index="{{ loop.index }}">'
            ),
            source,
        )
        source = source.replace(
            "{% if case or project.external_url %}</a>{% else %}</div>{% endif %}",
            "</project-link>",
        )
        source = source.replace(
            "{% if loop.index0 % 3 == 1 %} atlas-art--two{% elif loop.index0 % 3 == 2 %} atlas-art--three{% endif %}",
            "{{ ' atlas-art--two' if loop.index0 % 3 == 1 else (' atlas-art--three' if loop.index0 % 3 == 2 else '') }}",
        )

        # Conditional attributes are JSX object spreads, never HTML strings.
        def attr_block(match: re.Match[str]) -> str:
            condition, raw = match[1], match[2]
            attrs = re.findall(r'([\w-]+)(?:="([^"]*)")?', raw.strip())
            pairs = [
                json.dumps({"class": "className", "tabindex": "tabIndex"}.get(k, k))
                + ":"
                + ("true" if not v else self.interpolated(v, attribute=True))
                for k, v in attrs
            ]
            self.spreads.append(
                f"...(truthy({expression(condition)}) ? {{{', '.join(pairs)}}} : {{}})"
            )
            return f' spread{len(self.spreads) - 1}="" '

        source = re.sub(r"{% if ([^%]+) %}([^<>{}]*?){% endif %}(?=[^<>]*>)", attr_block, source)
        source = re.sub(r"{{\s*(.*?)\s*}}", lambda m: self.token(m[1]), source)
        stack: list[tuple[str, int]] = []

        def block(match: re.Match[str]) -> str:
            command = match[1].strip()
            if command.startswith(("if ", "for ", "set ")):
                kind, _, body = command.partition(" ")
                self.blocks.append(body)
                index = len(self.blocks) - 1
                if kind != "set":
                    stack.append((kind, 0))
                return f'<r-{kind} id="{index}">'
            if command.startswith("elif "):
                kind, count = stack[-1]
                stack[-1] = (kind, count + 1)
                self.blocks.append(command[5:])
                return f'</r-if><r-else><r-if id="{len(self.blocks) - 1}">'
            if command == "else":
                return "</r-if><r-else>"
            if command == "endfor":
                stack.pop()
                return "</r-for>"
            raise ValueError(f"Unsupported template statement: {command}")

        # Track branch structure directly to close nested elif groups correctly.
        def statements(source: str) -> str:
            branch_stack: list[list[str]] = []

            def replace(match: re.Match[str]) -> str:
                cmd = match[1].strip()
                if cmd.startswith("if "):
                    branch_stack.append(["if"])
                elif cmd.startswith("elif "):
                    branch_stack[-1][-1] = "else"
                    branch_stack[-1].append("if")
                elif cmd == "else":
                    branch_stack[-1][-1] = "else"
                elif cmd == "endif":
                    branches = branch_stack.pop()
                    stack.pop()
                    return "".join(f"</r-{branch}>" for branch in reversed(branches))
                return block(match)

            return re.sub(r"{%\s*(.*?)\s*%}", replace, source)

        source = statements(source)
        parser = Parser()
        parser.feed(source)
        if len(parser.stack) != 1:
            raise ValueError("Unclosed migration markup")
        return self.children(parser.root.children)

    def interpolated(self, value: str, *, attribute: bool = False) -> str:
        parts = re.split(r"(EXPR\d+TOKEN)", value)
        # Attribute preprocessing runs before expression tokenization.
        if "{{" in value:
            value = re.sub(r"{{\s*(.*?)\s*}}", lambda m: self.token(m[1]), value)
            parts = re.split(r"(EXPR\d+TOKEN)", value)
        values = [
            self.expressions[int(p[4:-5])]
            if re.fullmatch(r"EXPR\d+TOKEN", p)
            else json.dumps(html.unescape(p), ensure_ascii=False)
            for p in parts
            if p
        ]
        if attribute:
            if not values:
                return '""'
            return values[0] if len(values) == 1 else '"" + ' + " + ".join(values)
        return "".join("{" + v + "}" for v in values)

    def children(self, children: list[Element | str]) -> str:
        output: list[str] = []
        index = 0
        while index < len(children):
            child = children[index]
            if isinstance(child, str):
                # Explicit text nodes preserve meaningful spaces across JSX lines.
                output.append(self.interpolated(child))
            elif child.tag == "r-set":
                target, _, value = self.blocks[int(dict(child.attrs)["id"])].partition(" = ")
                target = "isCase" if target == "case" else target
                return (
                    "".join(output)
                    + "{(() => { const "
                    + target
                    + " = "
                    + expression(value)
                    + "; return <>"
                    + self.children(children[index + 1 :])
                    + "</>; })()}"
                )
            elif child.tag == "r-if":
                condition = expression(self.blocks[int(dict(child.attrs)["id"])])
                alternative = "null"
                if (
                    index + 1 < len(children)
                    and isinstance(children[index + 1], Element)
                    and children[index + 1].tag == "r-else"
                ):
                    index += 1
                    alternative = "<>" + self.children(children[index].children) + "</>"
                output.append(
                    "{truthy("
                    + condition
                    + ") ? <>"
                    + self.children(child.children)
                    + "</> : "
                    + alternative
                    + "}"
                )
            elif child.tag == "r-for":
                target, _, collection = self.blocks[int(dict(child.attrs)["id"])].partition(" in ")
                output.append(
                    "{"
                    + expression(collection)
                    + ".map(("
                    + target
                    + ": any, index: number, items: any[]) => { const loop = { index0: index, index: index + 1, last: index === items.length - 1, first: index === 0 }; return <Fragment key={index}>"
                    + self.children(child.children)
                    + "</Fragment>; })}"
                )
            else:
                attrs = []
                for key, value in child.attrs:
                    if key.startswith("spread"):
                        attrs.append("{" + self.spreads[int(key[6:])] + "}")
                    else:
                        name = {
                            "class": "className",
                            "tabindex": "tabIndex",
                            "srcset": "srcSet",
                            "for": "htmlFor",
                            "fetchpriority": "fetchPriority",
                        }.get(key, key)
                        content = (
                            self.interpolated(value, attribute=True) if value is not None else '""'
                        )
                        if key == "tabindex":
                            content = f"Number({content})"
                        attrs.append(name + "={" + content + "}")
                tag = "ProjectLink" if child.tag == "project-link" else child.tag
                if tag == "a":
                    tag = "PortfolioLink"
                if tag == "article" and "data-view" in dict(child.attrs):
                    tag = "RouteView"
                classes = dict(child.attrs).get("class", "") or ""
                if tag == "nav" and "site-nav" in classes:
                    tag = "PortfolioNav"
                if tag not in {"PortfolioLink", "ProjectLink", "RouteView", "PortfolioNav"} and (
                    tag in {"h1", "h2", "strong"}
                    or re.search(
                        r"\b(atlas-appear|section-title|figure|pillar|ledger-row|group|case-step|facts|lede|thesis-intro|credits-intro|work-empty|thesis-statement|marquee|ticker-track)\b",
                        classes,
                    )
                ):
                    attrs.insert(0, 'as="' + tag + '"')
                    tag = "ThemeElement"
                extra = "<Dust />" if "hero-art" in classes else ""
                opening = "<" + tag + (" " + " ".join(attrs) if attrs else "")
                output.append(
                    opening + " />"
                    if child.tag in {"img", "br", "hr", "input"}
                    else opening + ">" + self.children(child.children) + extra + "</" + tag + ">"
                )
            index += 1
        return "".join(output)


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    for name, source in THEMES.items():
        print(f"Migrating {name}")
        body = Compiler().compile(
            (ROOT / "src/oryxenai/themes" / source / "body.html.j2").read_text(encoding="utf-8")
        )
        header = (
            "// Migrated from the immutable host template; interactions are implemented in React.\n"
        )
        header += 'import { Fragment } from "react";\nimport { truthy, range, ProjectLink, type TemplateValues } from "../template-values";\n'
        header += (
            'import { RouteView, PortfolioLink, PortfolioNav } from "../interactive/routing";\n'
        )
        header += 'import { ThemeElement, Dust } from "../interactive/motion";\n'
        header += f"export function {name}({{ c, d }}: TemplateValues) {{\n"
        if name == "EditorialForest":
            header += "const hero = c.hero; const eyebrow = [hero.eyebrow_primary, hero.eyebrow_secondary].filter(Boolean); const headline_prefix = hero.headline_prefix; const headline_emphasis = hero.headline_emphasis; const systems = c.systems_practice; const capabilities = c.technical_capabilities; const context = c.professional_context; const connect = c.connect;\n"
        (DEST / f"{name}.tsx").write_text(
            header + "return <>" + body + "</>;\n}\n", encoding="utf-8", newline="\n"
        )


if __name__ == "__main__":
    main()
