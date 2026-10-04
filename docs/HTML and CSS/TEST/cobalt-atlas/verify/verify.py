#!/usr/bin/env python
"""Cobalt Atlas verification harness.

Serves the theme folder over plain HTTP (the theme uses Google Fonts and may load
images from anywhere, so there is no content-security policy by default) and
drives it with Playwright. Pass --csp to emulate the Studio's old strict preview
policy and sandbox instead (external fonts are then expected to be blocked).

Run with the repo's existing interpreter (no `uv sync`, no lockfile changes):

    .workspace/venv/Scripts/python.exe "docs/HTML and CSS/TEST/cobalt-atlas/verify/verify.py"

Options: --pages, --widths, --schemes, --shots DIR, --csp, --modes ..., --matrix, --axe PATH
"""

from __future__ import annotations

import argparse
import http.server
import re
import socketserver
import sys
import threading
from pathlib import Path
from typing import ClassVar

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["index.html", "profile-engineer.html", "profile-chef.html", "profile-stress.html"]
WIDTHS = [360, 768, 1280, 1920]
HEIGHTS = {360: 740, 768: 1024, 1280: 800, 1920: 1080}
# Optional (--csp): the Studio's old preview policy plus an opaque-origin sandbox.
CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self'; "
    "connect-src 'none'; base-uri 'none'; form-action 'none'; "
    "sandbox allow-scripts allow-popups allow-popups-to-escape-sandbox"
)
FONT_HOSTS = ("fonts.googleapis.com", "fonts.gstatic.com")
EXPECTED_BROKEN = {"profile-stress.html": ["missing-image.jpg", "missing-portrait.jpg"]}
BUDGETS = {"style.css": 100_000, "theme.js": 48_000}

OVERFLOW_JS = """
() => {
  const vw = document.documentElement.clientWidth;
  const out = [];
  const clipped = (el) => {
    for (let p = el.parentElement; p && p !== document.documentElement; p = p.parentElement) {
      const cs = getComputedStyle(p);
      if (/(hidden|clip|auto|scroll)/.test(cs.overflowX)) {
        const r = p.getBoundingClientRect();
        if (r.left >= -1 && r.right <= vw + 1) return true;
      }
    }
    return false;
  };
  for (const el of document.body.querySelectorAll('*')) {
    if (el.closest('[hidden]')) continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const r = el.getBoundingClientRect();
    if (!r.width && !r.height) continue;
    if (r.right > vw + 1 || r.left < -1) {
      if (clipped(el)) continue;
      const cls = (typeof el.className === 'string' && el.className) ? '.' + el.className.trim().split(/\\s+/).join('.') : '';
      out.push(el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + cls + ' [' + Math.round(r.left) + ',' + Math.round(r.right) + '] vw=' + vw);
      if (out.length >= 8) break;
    }
  }
  window.scrollTo(600, 0);
  const sx = window.scrollX;
  window.scrollTo(0, 0);
  return { offenders: out, scrollX: sx };
}
"""

INIT_JS = """
window.__csp = [];
document.addEventListener('securitypolicyviolation', (e) => window.__csp.push(e.violatedDirective + ' ' + e.blockedURI));
window.__cls = 0; window.__lcp = 0;
try {
  new PerformanceObserver((list) => { for (const e of list.getEntries()) if (!e.hadRecentInput) window.__cls += e.value; }).observe({ type: 'layout-shift', buffered: true });
  new PerformanceObserver((list) => { const es = list.getEntries(); const l = es[es.length - 1]; if (l) window.__lcp = l.startTime; }).observe({ type: 'largest-contentful-paint', buffered: true });
} catch (e) {}
"""


class Handler(http.server.SimpleHTTPRequestHandler):
    policy = "none"  # none | csp
    extensions_map: ClassVar[dict[str, str]] = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript",
        ".css": "text/css",
        ".woff2": "font/woff2",
        ".html": "text/html; charset=utf-8",
        ".svg": "image/svg+xml",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        if self.policy == "csp":
            self.send_header("Content-Security-Policy", CSP)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):  # keep the report readable
        pass


def serve(strict: bool = False, policy: str | None = None) -> tuple[socketserver.TCPServer, int]:
    """Plain HTTP by default. policy="csp" (or the legacy strict=True) adds the old Studio policy."""
    chosen = policy or ("csp" if strict else "none")
    handler = type("PolicyHandler", (Handler,), {"policy": chosen})
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.notes: list[str] = []
        self.checks = 0

    def check(self, ok: bool, label: str, detail: str = "") -> bool:
        self.checks += 1
        if not ok:
            self.failures.append(f"{label}" + (f" -> {detail}" if detail else ""))
        return ok

    def note(self, message: str) -> None:
        self.notes.append(message)


def new_context(browser: Browser, width: int, scheme: str, **extra) -> BrowserContext:
    return browser.new_context(
        viewport={"width": width, "height": HEIGHTS.get(width, 800)},
        color_scheme=scheme,
        **extra,
    )


def watch(page: Page, bucket: dict[str, list[str]]) -> None:
    page.add_init_script(INIT_JS)
    fonts_host = lambda url: any(h in (url or "") for h in FONT_HOSTS)  # noqa: E731
    page.on(
        "console",
        lambda m: (
            bucket["console"].append(f"{m.type}: {m.text}")
            if m.type in ("error", "warning") and not fonts_host((m.location or {}).get("url"))
            else None
        ),
    )
    page.on("pageerror", lambda e: bucket["pageerror"].append(str(e)))
    page.on(
        "requestfailed",
        lambda r: (
            bucket["failed"].append(f"{r.url} ({r.failure})") if not fonts_host(r.url) else None
        ),
    )
    page.on(
        "response",
        lambda r: (
            bucket["http"].append(f"{r.status} {r.url}")
            if r.status >= 400 and not fonts_host(r.url)
            else None
        ),
    )


def fresh_bucket() -> dict[str, list[str]]:
    return {"console": [], "pageerror": [], "failed": [], "http": []}


def poll(page: Page, js: str, arg=None, timeout: int = 8000) -> None:
    """Poll with page.evaluate (CDP callFunctionOn) - unlike wait_for_function it never
    needs 'unsafe-eval', so it works under the strict preview CSP."""
    waited = 0
    while waited <= timeout:
        if page.evaluate(js, arg) if arg is not None else page.evaluate(js):
            return
        page.wait_for_timeout(50)
        waited += 50
    raise TimeoutError(f"poll timed out: {js[:80]}")


def wait_ready(page: Page, timeout: int = 8000) -> None:
    poll(page, "() => document.documentElement.dataset.atlas === 'ready'", timeout=timeout)


def route_ids(page: Page) -> list[str]:
    return page.evaluate("window.AtlasTheme.audit().views")


def scroll_through(page: Page) -> None:
    """Walk the page so lazy images load and scroll-driven code runs, then return to top."""
    page.evaluate(
        """async () => {
          const step = Math.max(300, innerHeight * 0.8);
          for (let y = 0; y < document.documentElement.scrollHeight; y += step) {
            window.scrollTo({top: y, behavior: 'instant'});
            await new Promise((r) => setTimeout(r, 60));
          }
          window.scrollTo({top: 0, behavior: 'instant'});
        }"""
    )
    page.wait_for_timeout(250)


def goto_route(page: Page, base: str, route: str) -> None:
    page.evaluate("(id) => { location.hash = id; }", route)
    poll(
        page,
        "(id) => { const v = document.getElementById(id); return !!v && !v.hidden; }",
        route,
        timeout=4000,
    )
    page.wait_for_timeout(120)
    scroll_through(page)


def check_page(
    browser: Browser,
    report: Report,
    base: str,
    name: str,
    width: int,
    scheme: str,
    shots: Path | None,
) -> None:
    tag = f"{name}@{width}/{scheme}"
    ctx = new_context(browser, width, scheme)
    page = ctx.new_page()
    bucket = fresh_bucket()
    watch(page, bucket)
    page.goto(f"{base}/{name}", wait_until="load")
    wait_ready(page)
    report.check(
        page.evaluate("document.documentElement.classList.contains('js')"), f"{tag} html.js"
    )
    if width == 1280 and scheme == "light":
        loaded = page.evaluate(
            "() => [...document.fonts].filter(f => /Geist|Instrument/.test(f.family) && f.status === 'loaded').map(f => f.family)"
        )
        report.check(
            len(set(loaded)) >= 3,
            f"{tag} Google Fonts loaded (needs network)",
            ", ".join(sorted(set(loaded))) or "none",
        )
    audit = page.evaluate("window.AtlasTheme.audit()")
    report.check(not audit["errors"], f"{tag} audit errors", "; ".join(audit["errors"][:4]))
    for warning in audit["warnings"]:
        report.note(f"{tag} audit warning: {warning}")
    ids = audit["views"]
    for route in ids:
        goto_route(page, base, route)
        result = page.evaluate(OVERFLOW_JS)
        report.check(
            not result["offenders"], f"{tag} #{route} overflow", "; ".join(result["offenders"])
        )
        report.check(
            result["scrollX"] == 0,
            f"{tag} #{route} horizontal scroll possible",
            str(result["scrollX"]),
        )
        h1 = page.evaluate(
            "[...document.querySelectorAll('h1')].filter(h => h.offsetParent !== null).length"
        )
        report.check(h1 == 1, f"{tag} #{route} visible h1 count", str(h1))
        if shots:
            shots.mkdir(parents=True, exist_ok=True)
            safe = re.sub(r"[^a-z0-9-]+", "_", f"{Path(name).stem}-{width}-{scheme}-{route}")
            page.evaluate("window.scrollTo(0,0)")
            page.screenshot(path=str(shots / f"{safe}.png"), full_page=True)
    cls = page.evaluate("window.__cls")
    report.check(cls < 0.1, f"{tag} CLS", f"{cls:.3f}")
    expected = EXPECTED_BROKEN.get(name, [])
    for key, items in bucket.items():
        if expected:
            # Intentional 404 (broken-image test): allow exactly those requests.
            items = [
                i
                for i in items
                if not any(token in i for token in expected)
                and not i.startswith("error: Failed to load resource")
            ]
        report.check(not items, f"{tag} {key}", "; ".join(items[:3]))
    if expected:
        # A sandboxed (opaque-origin) page sees the 404 as ERR_BLOCKED_BY_ORB, so look in both lists.
        broken = [
            i for i in bucket["http"] + bucket["failed"] if any(token in i for token in expected)
        ]
        report.check(
            len(broken) == len(expected),
            f"{tag} intentional broken images requested once each",
            str(broken),
        )
        errors = page.evaluate("document.querySelectorAll('.is-error').length")
        report.check(
            errors == len(expected),
            f"{tag} every broken image got the .is-error fallback",
            str(errors),
        )
    csp = page.evaluate("window.__csp")
    report.check(not csp, f"{tag} CSP violations", "; ".join(csp[:3]))
    ctx.close()


# --------------------------------------------------------------------------
# Mode tests: no-JS, reduced motion, motion + intro, routing, keyboard, a11y
# --------------------------------------------------------------------------
def open_page(
    browser: Browser,
    base: str,
    name: str,
    width: int = 1280,
    scheme: str = "light",
    query: str = "",
    wait: str = "load",
    **ctx_kwargs,
):
    ctx = new_context(browser, width, scheme, **ctx_kwargs)
    page = ctx.new_page()
    bucket = fresh_bucket()
    watch(page, bucket)
    page.goto(f"{base}/{name}{query}", wait_until=wait)
    return ctx, page, bucket


def expect_clean(
    report: Report, tag: str, bucket: dict[str, list[str]], page: Page | None = None
) -> None:
    tokens = next((t for n, t in EXPECTED_BROKEN.items() if tag.startswith(n)), [])
    for key, items in bucket.items():
        if tokens:  # intentional broken-image test page: its 404s are expected
            items = [
                i
                for i in items
                if not any(t in i for t in tokens)
                and not i.startswith("error: Failed to load resource")
            ]
        report.check(not items, f"{tag} {key}", "; ".join(items[:3]))
    if page is not None:
        csp = page.evaluate("() => window.__csp")
        report.check(not csp, f"{tag} CSP violations", "; ".join(csp[:3]))


def active_view(page: Page) -> str:
    return page.evaluate(
        "() => { const v = [...document.querySelectorAll('[data-view]')].filter(x => !x.hidden); return v.map(x => x.id).join(','); }"
    )


def mode_storage_blocked(browser: Browser, report: Report, base: str, strict: bool) -> None:
    if not strict:
        return
    ctx, page, bucket = open_page(browser, base, "index.html")
    wait_ready(page)
    outcome = page.evaluate(
        "() => { try { localStorage.getItem('x'); return 'ok'; } catch (e) { return e.name; } }"
    )
    report.check(
        outcome == "SecurityError",
        "sandbox really is an opaque origin (localStorage throws)",
        str(outcome),
    )
    expect_clean(report, "storage-blocked", bucket, page)
    ctx.close()


def mode_no_js(browser: Browser, report: Report, base: str, name: str, shots: Path | None) -> None:
    for width in (360, 1280):
        tag = f"{name}@{width} no-JS"
        ctx = new_context(browser, width, "light", java_script_enabled=False)
        page = ctx.new_page()
        failures: list[str] = []
        page.on("requestfailed", lambda r, failures=failures: failures.append(r.url))
        page.goto(f"{base}/{name}", wait_until="load")
        views = page.locator("[data-view]")
        count = views.count()
        report.check(count >= 1, f"{tag} views present", str(count))
        report.check(page.locator("[data-view][hidden]").count() == 0, f"{tag} no view is hidden")
        visible = sum(1 for i in range(count) if views.nth(i).is_visible())
        report.check(visible == count, f"{tag} every view is visible", f"{visible}/{count}")
        opacity = page.locator("body").evaluate("e => getComputedStyle(e).opacity")
        report.check(opacity == "1", f"{tag} boot veil does not apply without scripting", opacity)
        nav_visible = page.locator(".site-nav a").first.is_visible()
        report.check(nav_visible, f"{tag} nav links visible without JS")
        report.check(page.locator(".atlas-loader").count() == 0, f"{tag} no loader")
        try:
            overflow = page.evaluate(OVERFLOW_JS)
            report.check(
                not overflow["offenders"], f"{tag} overflow", "; ".join(overflow["offenders"])
            )
        except Exception as error:
            report.note(f"{tag}: evaluate unavailable with JS disabled ({type(error).__name__})")
        report.check(not failures, f"{tag} failed requests", "; ".join(failures[:3]))
        if shots and width == 360:
            shots.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(shots / f"nojs-{Path(name).stem}-{width}.png"), full_page=True)
        ctx.close()


def mode_reduced_motion(browser: Browser, report: Report, base: str, name: str) -> None:
    tag = f"{name} reduced-motion"
    ctx, page, bucket = open_page(
        browser, base, name, reduced_motion="reduce", query="?atlas-motion=1&intro=1"
    )
    wait_ready(page)
    report.check(
        page.evaluate("() => !document.documentElement.hasAttribute('data-motion')"),
        f"{tag} data-motion off",
    )
    report.check(
        page.evaluate(
            "() => document.querySelectorAll('.atlas-loader,[data-split],.count').length === 0"
        ),
        f"{tag} no loader/split/counters",
    )
    hidden = page.evaluate(
        "() => [...document.querySelectorAll('.atlas-appear')].filter(e => e.offsetParent && getComputedStyle(e).opacity !== '1').length"
    )
    report.check(hidden == 0, f"{tag} nothing left transparent", str(hidden))
    infinite = page.evaluate(
        "() => document.getAnimations().filter(a => a.effect && a.effect.getComputedTiming().iterations === Infinity && a.playState === 'running').length"
    )
    report.check(infinite == 0, f"{tag} no infinite animations running", str(infinite))
    expect_clean(report, tag, bucket, page)
    ctx.close()


def mode_motion(browser: Browser, report: Report, base: str, name: str, shots: Path | None) -> None:
    tag = f"{name} motion+intro"
    ctx, page, bucket = open_page(
        browser, base, name, query="?atlas-motion=1&intro=1", wait="commit"
    )
    seen_loader = False
    for _ in range(40):
        if page.evaluate("() => !!document.querySelector('.atlas-loader')"):
            seen_loader = True
            break
        page.wait_for_timeout(50)
    report.check(seen_loader, f"{tag} loader appears")
    wait_ready(page, timeout=6000)
    page.wait_for_timeout(1400)
    report.check(
        page.evaluate(
            "() => !document.querySelector('.atlas-loader') && !document.documentElement.classList.contains('is-loading')"
        ),
        f"{tag} loader finished and removed",
    )
    report.check(
        page.evaluate("() => document.documentElement.dataset.motion === 'on'"),
        f"{tag} data-motion on",
    )
    ids = page.evaluate("() => window.AtlasTheme.audit().views")
    for route in ids:
        goto_route(page, base, route)
        scroll_through(page)
        page.wait_for_timeout(1500)
        pending = page.evaluate(
            "() => [...document.querySelectorAll('[data-view]:not([hidden]) .atlas-appear')].filter(e => !e.classList.contains('is-in-view')).length"
        )
        report.check(pending == 0, f"{tag} #{route} all reveals fired", str(pending))
        faded = page.evaluate(
            "() => [...document.querySelectorAll('[data-view]:not([hidden]) .atlas-appear')].filter(e => getComputedStyle(e).opacity !== '1').length"
        )
        report.check(faded == 0, f"{tag} #{route} reveals fully opaque", str(faded))
        split_bad = page.evaluate("""() => [...document.querySelectorAll('[data-view]:not([hidden]) [data-split]')].filter(h => {
            const norm = (s) => s.replace(/\\s+/g, ' ').trim();
            return norm(h.getAttribute('aria-label') || '') !== norm(h.innerText);
          }).map(h => h.textContent.slice(0, 30)).length""")
        report.check(
            split_bad == 0, f"{tag} #{route} split headings keep their text", str(split_bad)
        )
        counters = page.evaluate(
            "() => [...document.querySelectorAll('[data-view]:not([hidden]) .count')].filter(c => c.textContent !== c.dataset.final).length"
        )
        report.check(
            counters == 0, f"{tag} #{route} counters land on the real number", str(counters)
        )
        title_ok = page.evaluate(
            "() => { const v = document.querySelector('[data-view]:not([hidden])'); return document.title === (v.dataset.title || document.title); }"
        )
        report.check(title_ok, f"{tag} #{route} document.title follows the view")
        focused = page.evaluate(
            "() => { const a = document.activeElement; return a ? a.tagName : ''; }"
        )
        report.check(
            focused in ("H1", "H2", "H3"), f"{tag} #{route} focus moved to heading", focused
        )
        current = page.evaluate(
            "() => document.querySelectorAll('.site-nav a[aria-current=page]').length"
        )
        report.check(current <= 1, f"{tag} #{route} at most one nav item current", str(current))
        if shots and route == ids[0]:
            shots.mkdir(parents=True, exist_ok=True)
            page.screenshot(
                path=str(shots / f"motion-{Path(name).stem}-{route}.png"), full_page=True
            )
    # Rapid navigation must not throw or leave two views visible.
    if len(ids) >= 3:
        page.evaluate(
            "(ids) => { location.hash = ids[1]; setTimeout(() => { location.hash = ids[2]; }, 10); setTimeout(() => { location.hash = ids[0]; }, 25); }",
            ids,
        )
        page.wait_for_timeout(1500)
        report.check(
            active_view(page) == ids[0],
            f"{tag} rapid navigation settles on the last route",
            active_view(page),
        )
    # Theme toggle (view-transition path).
    before = page.evaluate("() => getComputedStyle(document.body).backgroundColor")
    page.click(".theme-toggle")
    page.wait_for_timeout(1100)
    flipped = page.evaluate(
        "() => ({t: document.documentElement.dataset.theme, bg: getComputedStyle(document.body).backgroundColor, p: document.querySelector('.theme-toggle').getAttribute('aria-pressed')})"
    )
    report.check(
        flipped["t"] == "dark" and flipped["bg"] != before and flipped["p"] == "true",
        f"{tag} theme toggle flips to dark",
        str(flipped),
    )
    page.click(".theme-toggle")
    page.wait_for_timeout(1100)
    report.check(
        page.evaluate("() => document.documentElement.dataset.theme") == "light",
        f"{tag} theme toggle flips back",
    )
    expect_clean(report, tag, bucket, page)
    ctx.close()


def mode_routing(browser: Browser, report: Report, base: str, name: str) -> None:
    tag = f"{name} routing"
    ctx, page, _bucket = open_page(browser, base, name)
    wait_ready(page)
    ids = page.evaluate("() => window.AtlasTheme.audit().views")
    ctx.close()
    for route in ids:
        c, p, b = open_page(browser, base, name, query=f"#{route}")
        wait_ready(p)
        p.wait_for_timeout(300)
        report.check(active_view(p) == route, f"{tag} deep link #{route}", active_view(p))
        report.check(
            p.evaluate("() => window.scrollY") < 6,
            f"{tag} deep link #{route} starts at top",
            str(p.evaluate("() => window.scrollY")),
        )
        expect_clean(report, f"{tag} deep #{route}", b, p)
        c.close()
    home = ids[0]
    for weird, expect in (("nope", home), ("%E0%A4%A", home), ("/" + ids[-1], ids[-1])):
        c, p, b = open_page(browser, base, name, query=f"#{weird}")
        wait_ready(p)
        report.check(active_view(p) == expect, f"{tag} odd hash #{weird}", active_view(p))
        expect_clean(report, f"{tag} odd hash #{weird}", b, p)
        c.close()
    # In-view anchors (sections inside a view) switch to their view and scroll to the section.
    anchors = page_anchor_targets(browser, base, name)
    for anchor, owner in anchors:
        c, p, b = open_page(browser, base, name, query=f"#{anchor}")
        wait_ready(p)
        p.wait_for_timeout(500)
        top = p.evaluate("(id) => document.getElementById(id).getBoundingClientRect().top", anchor)
        report.check(
            active_view(p) == owner, f"{tag} #{anchor} shows its owning view", active_view(p)
        )
        report.check(-5 <= top <= 220, f"{tag} #{anchor} scrolled into place", str(round(top)))
        c.close()
    # History: forward / back across views, and the skip link must not change the view.
    if len(ids) >= 3:
        c, p, b = open_page(browser, base, name)
        wait_ready(p)
        for route in (ids[1], ids[2]):
            p.evaluate("(id) => { location.hash = id; }", route)
            poll(
                p,
                "(id) => { const v = document.getElementById(id); return !!v && !v.hidden; }",
                route,
            )
        p.go_back()
        poll(
            p, "(id) => { const v = document.getElementById(id); return !!v && !v.hidden; }", ids[1]
        )
        report.check(
            active_view(p) == ids[1], f"{tag} Back returns to previous view", active_view(p)
        )
        p.go_forward()
        poll(
            p, "(id) => { const v = document.getElementById(id); return !!v && !v.hidden; }", ids[2]
        )
        report.check(active_view(p) == ids[2], f"{tag} Forward returns", active_view(p))
        expect_clean(report, f"{tag} history", b, p)
        c.close()
    # Skip link: first Tab stop on a fresh load (no fragment), and using it must not switch views.
    c, p, b = open_page(browser, base, name)
    wait_ready(p)
    p.keyboard.press("Tab")
    focus = p.evaluate("() => document.activeElement.className")
    report.check("skip-link" in focus, f"{tag} first Tab stop is the skip link", focus)
    c.close()
    target = ids[1] if len(ids) > 1 else ids[0]
    c, p, b = open_page(browser, base, name, query=f"#{target}")
    wait_ready(p)
    p.focus(".skip-link")
    p.keyboard.press("Enter")
    p.wait_for_timeout(500)
    report.check(
        active_view(p) == target, f"{tag} skip link keeps the current view", active_view(p)
    )
    expect_clean(report, f"{tag} skip", b, p)
    c.close()
    # Case-study table of contents (when the page has one).
    for route in ids:
        c, p, b = open_page(browser, base, name, query=f"#{route}")
        wait_ready(p)
        n = p.evaluate(
            "() => document.querySelectorAll('[data-view]:not([hidden]) .case-toc a').length"
        )
        if n >= 2:
            p.click("[data-view]:not([hidden]) .case-toc a:nth-child(2)")
            p.wait_for_timeout(900)
            report.check(
                active_view(p) == route, f"{tag} TOC click keeps the case view", active_view(p)
            )
            cur = p.evaluate(
                "() => document.querySelectorAll('[data-view]:not([hidden]) .case-toc a[aria-current=true]').length"
            )
            report.check(cur == 1, f"{tag} TOC marks one current section", str(cur))
            expect_clean(report, f"{tag} toc", b, p)
            c.close()
            break
        c.close()


def page_anchor_targets(browser: Browser, base: str, name: str) -> list[tuple[str, str]]:
    ctx, page, _ = open_page(browser, base, name)
    wait_ready(page)
    pairs = page.evaluate("""() => {
      const out = [];
      for (const a of document.querySelectorAll('.site-nav a[href^="#"]')) {
        const id = decodeURIComponent(a.getAttribute('href').slice(1));
        const el = document.getElementById(id);
        const owner = el && el.closest('[data-view]');
        if (el && owner && owner !== el) out.push([id, owner.id]);
      }
      return out;
    }""")
    ctx.close()
    return [(a, b) for a, b in pairs]


def mode_keyboard(browser: Browser, report: Report, base: str, name: str) -> None:
    tag = f"{name} keyboard"
    ctx, page, bucket = open_page(browser, base, name)
    wait_ready(page)
    # Palette
    page.keyboard.press("Control+k")
    page.wait_for_timeout(400)
    report.check(
        page.evaluate("() => !!document.querySelector('dialog.palette[open]')"),
        f"{tag} Ctrl+K opens the palette",
    )
    page.keyboard.type("a")
    page.wait_for_timeout(150)
    options = page.evaluate("() => document.querySelectorAll('.palette-list [role=option]').length")
    report.check(options >= 1, f"{tag} palette lists results", str(options))
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)
    report.check(
        page.evaluate("() => !document.querySelector('dialog.palette[open]')"),
        f"{tag} Escape closes the palette",
    )
    page.keyboard.press("Control+k")
    page.wait_for_timeout(300)
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    page.wait_for_timeout(700)
    report.check(
        page.evaluate("() => !document.querySelector('dialog.palette[open]')"),
        f"{tag} Enter chooses and closes",
    )
    # Tab order: every stop is a real, visible control with a focus indicator.
    page.evaluate("() => { location.hash = ''; window.scrollTo(0, 0); }")
    page.wait_for_timeout(300)
    page.evaluate("() => document.activeElement && document.activeElement.blur()")
    bad: list[str] = []
    for _ in range(14):
        page.keyboard.press("Tab")
        info = page.evaluate("""() => { const a = document.activeElement; if (!a || a === document.body) return null;
          const r = a.getBoundingClientRect(); const cs = getComputedStyle(a);
          return {t: a.tagName, c: String(a.className).slice(0, 30), w: r.width, h: r.height, o: cs.outlineStyle, ow: cs.outlineWidth}; }""")
        if info and (info["w"] < 1 or info["h"] < 1):
            bad.append(f"{info['t']}.{info['c']} has no size")
        if info and info["o"] == "none":
            bad.append(f"{info['t']}.{info['c']} has no focus outline")
    report.check(not bad, f"{tag} focus stops are visible with an outline", "; ".join(bad[:4]))
    expect_clean(report, tag, bucket, page)
    ctx.close()
    # Mobile menu
    ctx, page, bucket = open_page(browser, base, name, width=360)
    wait_ready(page)
    page.click(".menu-toggle")
    page.wait_for_timeout(500)
    state = page.evaluate(
        "() => ({e: document.querySelector('.menu-toggle').getAttribute('aria-expanded'), o: document.querySelector('.site-nav').hasAttribute('data-open'), v: getComputedStyle(document.querySelector('.site-nav')).visibility})"
    )
    report.check(
        state == {"e": "true", "o": True, "v": "visible"},
        f"{tag} menu opens and stays open",
        str(state),
    )
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)
    closed = page.evaluate(
        "() => ({o: document.querySelector('.site-nav').hasAttribute('data-open'), f: document.activeElement.className})"
    )
    report.check(
        not closed["o"] and "menu-toggle" in closed["f"],
        f"{tag} Escape closes the menu and returns focus",
        str(closed),
    )
    page.click(".menu-toggle")
    page.wait_for_timeout(400)
    links = page.locator(".site-nav a")
    if links.count() > 1:
        links.nth(1).click()
        page.wait_for_timeout(500)
        report.check(
            page.evaluate("() => !document.querySelector('.site-nav').hasAttribute('data-open')"),
            f"{tag} choosing a link closes the menu",
        )
    expect_clean(report, f"{tag} mobile", bucket, page)
    ctx.close()


def mode_axe(browser: Browser, report: Report, base: str, name: str, axe_src: str) -> None:
    for width, scheme in ((1280, "light"), (1280, "dark"), (360, "light")):
        tag = f"{name}@{width}/{scheme} axe"
        ctx, page, _bucket = open_page(browser, base, name, width=width, scheme=scheme)
        wait_ready(page)
        page.evaluate(axe_src)
        ids = page.evaluate("() => window.AtlasTheme.audit().views")
        for route in ids:
            goto_route(page, base, route)
            result = page.evaluate("""async () => {
              const r = await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice']}});
              return {
                v: r.violations.map(v => ({id: v.id, impact: v.impact, n: v.nodes.length, sample: v.nodes[0] ? v.nodes[0].target.join(' ') : '', help: v.help})),
                inc: r.incomplete.map(v => ({id: v.id, n: v.nodes.length}))
              };
            }""")
            hard = [v for v in result["v"] if v["impact"] in ("serious", "critical")]
            soft = [v for v in result["v"] if v["impact"] not in ("serious", "critical")]
            report.check(
                not hard,
                f"{tag} #{route} serious/critical violations",
                "; ".join(f"{v['id']}({v['n']}) {v['sample']}" for v in hard[:4]),
            )
            for v in soft:
                report.note(f"{tag} #{route} {v['impact']}: {v['id']} x{v['n']} {v['sample']}")
            for v in result["inc"]:
                if v["id"] == "color-contrast":
                    report.note(
                        f"{tag} #{route} contrast needs manual review on {v['n']} node(s) (gradient/blended backgrounds)"
                    )
        ctx.close()


COLLECT_TEXT_JS = """
() => {
  const canvas = document.createElement('canvas'); canvas.width = canvas.height = 1;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  const toRgba = (css) => { ctx.clearRect(0, 0, 1, 1); ctx.fillStyle = '#000'; ctx.fillStyle = css; ctx.fillRect(0, 0, 1, 1); const d = ctx.getImageData(0, 0, 1, 1).data; return [d[0], d[1], d[2], d[3] / 255]; };
  const out = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const seen = new Set();
  while (walker.nextNode()) {
    const node = walker.currentNode;
    if (!node.nodeValue.trim()) continue;
    const el = node.parentElement;
    if (!el || seen.has(el) && false) continue;
    if (el.closest('[hidden],[aria-hidden="true"],.sr-only,script,style,dialog:not([open])')) continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const range = document.createRange(); range.selectNodeContents(node);
    // Text can be clipped by an overflow ancestor (line-clamp, ellipsis, scrolling nav): measure only what is visible.
    const clip = (r) => {
      let left = r.left, top = r.top, right = r.right, bottom = r.bottom;
      for (let q = el; q && q !== document.documentElement; q = q.parentElement) {
        const qs = getComputedStyle(q);
        if (qs.overflowX === 'visible' && qs.overflowY === 'visible') continue;
        const b = q.getBoundingClientRect();
        if (qs.overflowX !== 'visible') { left = Math.max(left, b.left); right = Math.min(right, b.right); }
        if (qs.overflowY !== 'visible') { top = Math.max(top, b.top); bottom = Math.min(bottom, b.bottom); }
      }
      return (right - left > 1 && bottom - top > 1) ? { left, top, width: right - left, height: bottom - top } : null;
    };
    const rects = [...range.getClientRects()].map(clip).filter(Boolean);
    if (!rects.length) continue;
    let opacity = 1; for (let p = el; p; p = p.parentElement) opacity *= parseFloat(getComputedStyle(p).opacity);
    const gradient = cs.webkitTextFillColor === 'rgba(0, 0, 0, 0)' || cs.webkitBackgroundClip === 'text' || cs.backgroundClip === 'text';
    const fg = toRgba(cs.color);
    const size = parseFloat(cs.fontSize), weight = parseInt(cs.fontWeight, 10);
    const cls = (typeof el.className === 'string' && el.className) ? '.' + el.className.trim().split(/\\s+/)[0] : '';
    for (const r of rects) {
      out.push({ sel: el.tagName.toLowerCase() + cls, text: node.nodeValue.trim().slice(0, 28), x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height, fg, opacity, size, weight, gradient });
    }
    el.setAttribute('data-ct', '1');
  }
  return out;
}
"""

HIDE_TEXT_JS = """
() => {
  for (const el of document.querySelectorAll('[data-ct]')) {
    el.style.setProperty('color', 'transparent', 'important');
    el.style.setProperty('-webkit-text-fill-color', 'transparent', 'important');
    el.style.setProperty('text-shadow', 'none', 'important');
    el.style.setProperty('text-decoration-color', 'transparent', 'important');
  }
  for (const el of document.querySelectorAll('.to-top,.scroll-progress,.atlas-route-bar')) el.style.setProperty('visibility', 'hidden', 'important');
  window.scrollTo({ top: 0, behavior: 'instant' });
}
"""


def _lum(rgb):
    import numpy as np

    c = np.asarray(rgb, dtype="float64") / 255.0
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def mode_contrast(browser: Browser, report: Report, base: str, name: str) -> None:
    import io

    import numpy as np
    from PIL import Image

    for width, scheme in ((1280, "light"), (1280, "dark"), (360, "light"), (360, "dark")):
        tag = f"{name}@{width}/{scheme} contrast"
        ctx = new_context(browser, width, scheme, reduced_motion="reduce")
        page = ctx.new_page()
        bucket = fresh_bucket()
        watch(page, bucket)
        page.goto(f"{base}/{name}", wait_until="load")
        wait_ready(page)
        ids = page.evaluate("() => window.AtlasTheme.audit().views")
        for route in ids:
            goto_route(page, base, route)
            items = page.evaluate(COLLECT_TEXT_JS)
            page.evaluate(HIDE_TEXT_JS)
            page.wait_for_timeout(150)
            image = Image.open(io.BytesIO(page.screenshot(full_page=True))).convert("RGB")
            pixels = np.asarray(image)
            height, wide = pixels.shape[0], pixels.shape[1]
            worst: dict[str, tuple[float, str]] = {}
            skipped = 0
            for item in items:
                if item["gradient"]:
                    skipped += 1
                    continue
                x0, y0 = max(0, int(item["x"])), max(0, int(item["y"]))
                x1, y1 = (
                    min(wide, int(item["x"] + item["w"]) + 1),
                    min(height, int(item["y"] + item["h"]) + 1),
                )
                if x1 <= x0 or y1 <= y0:
                    continue
                region = pixels[y0:y1, x0:x1].reshape(-1, 3)
                if len(region) > 4000:
                    region = region[:: len(region) // 4000]
                lums = _lum(region)
                alpha = item["fg"][3] * item["opacity"]
                fg = np.asarray(item["fg"][:3], dtype="float64")
                ratios = []
                for pct in (2, 50, 98):
                    pick = region[
                        np.argsort(lums)[int(len(lums) * pct / 100.0) if pct < 100 else -1]
                    ]
                    blended = fg * alpha + pick.astype("float64") * (1 - alpha)
                    lf, lb = float(_lum(blended)), float(_lum(pick))
                    ratios.append((max(lf, lb) + 0.05) / (min(lf, lb) + 0.05))
                ratio = min(ratios)
                large = item["size"] >= 24 or (item["size"] >= 18.66 and item["weight"] >= 700)
                need = 3.0 if large else 4.5
                key = f'{item["sel"]} "{item["text"]}"'
                if ratio < need and (key not in worst or ratio < worst[key][0]):
                    worst[key] = (ratio, f"need {need}")
            for key, (ratio, need) in sorted(worst.items(), key=lambda kv: kv[1][0])[:6]:
                report.check(False, f"{tag} #{route} low contrast", f"{key} = {ratio:.2f} ({need})")
            report.checks += 1
            if skipped:
                report.note(
                    f"{tag} #{route}: {skipped} gradient-text node(s) not measured (large display numerals)"
                )
        expect_clean(report, tag, bucket)
        ctx.close()


def check_budgets(report: Report) -> None:
    for fname, limit in BUDGETS.items():
        size = (ROOT / fname).stat().st_size
        report.check(size <= limit, f"budget {fname}", f"{size} > {limit}")
        report.note(f"size {fname}: {size} bytes")


def check_two_files(report: Report) -> None:
    """The theme is exactly style.css + theme.js; pages reference nothing else of ours."""
    css = (ROOT / "style.css").read_text(encoding="utf-8")
    report.check("fonts.googleapis.com" in css, "style.css imports its fonts from Google Fonts")
    report.check("data:font" not in css, "style.css embeds no font data")
    js = (ROOT / "theme.js").read_text(encoding="utf-8")
    report.check(
        not re.search(r"\b(fetch|XMLHttpRequest|eval|importScripts)\s*\(", js)
        and "new Function" not in js,
        "theme.js makes no network calls and uses no eval",
    )
    allowed = ("style.css", "theme.js")
    for page in PAGES:
        html = (ROOT / page).read_text(encoding="utf-8")
        tokens = EXPECTED_BROKEN.get(page, [])
        refs = [
            r
            for r in re.findall(r'(?:src|href)="(\./[^"]+)"', html)
            if not r.endswith(allowed) and not any(t in r for t in tokens)
        ]
        report.check(
            not refs, f"{page} references only style.css and theme.js", "; ".join(refs[:3])
        )
    for stray in ("fonts", "assets", "build", "LICENSES"):
        report.check(not (ROOT / stray).exists(), f"no {stray}/ folder")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", nargs="*", default=PAGES)
    parser.add_argument("--widths", nargs="*", type=int, default=WIDTHS)
    parser.add_argument("--schemes", nargs="*", default=["light", "dark"])
    parser.add_argument("--shots", default="")
    parser.add_argument(
        "--csp", action="store_true", help="emulate the Studio's old strict CSP + sandbox"
    )
    parser.add_argument("--axe", default="", help="path to axe.min.js (test-only; not shipped)")
    parser.add_argument(
        "--matrix", action="store_true", help="only the page x width x scheme matrix"
    )
    parser.add_argument(
        "--modes",
        nargs="*",
        default=None,
        help="subset of: storage nojs reduced motion routing keyboard axe contrast (storage needs --csp)",
    )
    args = parser.parse_args()

    report = Report()
    check_budgets(report)
    check_two_files(report)
    server, port = serve(policy="csp" if args.csp else "none")
    base = f"http://127.0.0.1:{port}"
    shots = Path(args.shots) if args.shots else None
    pages = [p for p in args.pages if (ROOT / p).exists()]
    wanted = (
        set(args.modes)
        if args.modes is not None
        else {"storage", "nojs", "reduced", "motion", "routing", "keyboard", "axe", "contrast"}
        - (set() if args.csp else {"storage"})
    )
    axe_src = (
        Path(args.axe).read_text(encoding="utf-8") if args.axe and Path(args.axe).exists() else ""
    )
    if "axe" in wanted and not axe_src and not args.matrix:
        report.note("axe pass skipped: pass --axe path/to/axe.min.js")
    with sync_playwright() as pw:
        browser = pw.chromium.launch()

        def guarded(label: str, fn, *fn_args) -> None:
            try:
                fn(*fn_args)
            except Exception as error:
                report.check(False, f"{label} crashed", repr(error)[:300])

        if args.modes is None or args.matrix or not args.modes:
            for name in pages:
                for width in args.widths:
                    for scheme in args.schemes:
                        guarded(
                            f"{name}@{width}/{scheme}",
                            check_page,
                            browser,
                            report,
                            base,
                            name,
                            width,
                            scheme,
                            shots,
                        )
        if not args.matrix:
            if "storage" in wanted and args.csp:
                guarded("storage", mode_storage_blocked, browser, report, base, True)
            for name in pages:
                if "nojs" in wanted:
                    guarded(f"{name} nojs", mode_no_js, browser, report, base, name, shots)
                if "reduced" in wanted:
                    guarded(f"{name} reduced", mode_reduced_motion, browser, report, base, name)
                if "motion" in wanted:
                    guarded(f"{name} motion", mode_motion, browser, report, base, name, shots)
                if "routing" in wanted:
                    guarded(f"{name} routing", mode_routing, browser, report, base, name)
                if "keyboard" in wanted:
                    guarded(f"{name} keyboard", mode_keyboard, browser, report, base, name)
                if "axe" in wanted and axe_src:
                    guarded(f"{name} axe", mode_axe, browser, report, base, name, axe_src)
                if "contrast" in wanted:
                    guarded(f"{name} contrast", mode_contrast, browser, report, base, name)
        browser.close()
    server.shutdown()

    print(f"checks: {report.checks}  failures: {len(report.failures)}")
    for failure in report.failures:
        print("FAIL", failure)
    for note in report.notes:
        print("note", note)
    return 1 if report.failures else 0


if __name__ == "__main__":
    sys.exit(main())
